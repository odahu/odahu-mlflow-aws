#
#    Copyright 2021 EPAM Systems
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#
import os
import io
from zipfile import ZipFile

import click
import boto3
from mlflow.utils import cli_args
from mlflow.tracking import MlflowClient
from mlflow.store.artifact.models_artifact_repo import ModelsArtifactRepository
from mlflow.store.artifact.utils.models import get_model_name_and_version

from odahu_mlflow_aws_sdk import config
from odahu_mlflow_aws_sdk.inference import const
from odahu_mlflow_aws_sdk import utils
from odahu_mlflow_aws_sdk.cli.output import output_list_data, output_options
from odahu_mlflow_aws_sdk.cli import columns


@click.group('lambda')
def lambda_func():
    """
    Deploy & manage lambda for pre processing
    """
    pass


def download_model_inference_code(uri_of_model: str):
    if not ModelsArtifactRepository.is_models_uri(uri_of_model):
        raise Exception('Only Model URLs are supported')
    client = MlflowClient()
    name, version = get_model_name_and_version(client, uri_of_model)
    model_info = client.get_model_version(name, version)
    run_id = model_info.run_id

    artifacts = [file.path for file in client.list_artifacts(run_id, '')]
    if const.MLFLOW_MODEL_INFERENCE_FOLDER not in artifacts:
        raise Exception(f'Inference code has not been saved with model {uri_of_model} '
                        f'(name: {name}, version: {version}, run: {run_id})')

    return client.download_artifacts(run_id, const.MLFLOW_MODEL_INFERENCE_FOLDER)

def files_to_zip(path):
    for root, dirs, files in os.walk(path):
        for f in files:
            full_path = os.path.join(root, f)
            archive_name = full_path[len(path) + len(os.sep):]
            yield full_path, archive_name


def make_zip_file_bytes(path):
    buf = io.BytesIO()
    with ZipFile(buf, 'w') as z:
        for full_path, archive_name in files_to_zip(path=path):
            z.write(full_path, archive_name)
    return buf.getvalue()


@lambda_func.command()
@output_options
def list(**output_options_values):
    """
    List deployed functions
    """
    paginator = boto3.client('lambda').get_paginator('list_functions')
    output_list_data([
        function for function
        in utils.flat_list(paginator.paginate(), 'Functions')
        if function.get('Environment', {}).get('Variables', {}).get(const.MODEL_ENDPOINT_ENV)
    ], columns=columns.AwsLambdaFunctions, **output_options_values)


@lambda_func.command()
@click.option("--function-name", "-f", help="Function name", required=True)
@click.option("--gateway-resource", "-u", help="Name of resource in API Gateway (URL)", required=True)
@click.option("--gateway-id", "-g", help="ID of AWS API Gateway", default=config.DEFAULT_API_GATEWAY_ID)
@click.option("--gateway-stage", "-l", help="AWS API Gateway Stage", default=config.DEFAULT_API_GATEWAY_STAGE)
@click.option("--gateway-auth", "-q", help="AWS API Gateway Authorizer", default=config.DEFAULT_API_GATEWAY_AUTHORIZATION)
def register_in_api_gateway(
    function_name,
    gateway_resource,
    gateway_id,
    gateway_stage,
    gateway_auth
):
    # Find lambda ARN
    lambda_client = boto3.client('lambda')
    try:
        function_info = lambda_client.get_function(
            FunctionName=function_name
        )
    except lambda_client.exceptions.ResourceNotFoundException:
        raise Exception(f'Lambda function with name {function_name} is not found')
    function_arn = function_info['Configuration']['FunctionArn']

    api_gateway_client = boto3.client('apigateway')
    try:
        rest_api_info = api_gateway_client.get_rest_api(
            restApiId=gateway_id
        )
    except api_gateway_client.exceptions.NotFoundException:
        raise Exception(f'Unable to find API Gateway with ID: {gateway_id}')

    try:
        stage_information = api_gateway_client.get_stage(
            restApiId=gateway_id,
            stageName=gateway_stage
        )
    except api_gateway_client.exceptions.NotFoundException:
        raise Exception(f'Unable to find Stage with ID: {gateway_stage}')

    # Get all resources
    resources = utils.flat_list(
        [p for p in api_gateway_client.get_paginator('get_resources').paginate(
            restApiId=gateway_id
        )],
        'items'
    )

    root_resource = [r for r in resources if r.get('path') == '/']
    resource = [r for r in resources if r.get('pathPart') == gateway_resource]

    if not root_resource:
        click.echo('Root resource is not found, please create it first')
        return

    if resource:
        resource_info = resource[0]
    else:
        resource_info = api_gateway_client.create_resource(
            restApiId=gateway_id,
            parentId=root_resource[0]['id'],
            pathPart=gateway_resource
        )

    resource_methods = resource_info.get('resourceMethods', {})

    if 'POST' in resource_methods:
        api_gateway_client.delete_method(
            restApiId=gateway_id,
            resourceId=resource_info['id'],
            httpMethod='POST',
        )

    security = {'authorizationType': 'NONE'}
    if gateway_auth:
        security = {'authorizationType': 'CUSTOM', 'authorizerId': gateway_auth}
    resource_method = api_gateway_client.put_method(
        restApiId=gateway_id,
        resourceId=resource_info['id'],
        httpMethod='POST',
        apiKeyRequired=False,
        operationName=gateway_resource,
        **security
    )

    try:
        api_gateway_client.get_method_response(
            restApiId=gateway_id,
            resourceId=resource_info['id'],
            httpMethod='POST',
            statusCode='200'
        )
    except api_gateway_client.exceptions.NotFoundException:
        api_gateway_client.put_method_response(
            restApiId=gateway_id,
            resourceId=resource_info['id'],
            httpMethod='POST',
            statusCode='200'
        )

    try:
        api_gateway_client.get_integration(
            restApiId=gateway_id,
            resourceId=resource_info['id'],
            httpMethod='POST',
        )
        api_gateway_client.delete_integration(
            restApiId=gateway_id,
            resourceId=resource_info['id'],
            httpMethod='POST',
        )
    except api_gateway_client.exceptions.NotFoundException:
        pass

    api_gateway_client.put_integration(
        restApiId=gateway_id,
        resourceId=resource_info['id'],
        httpMethod='POST',
        integrationHttpMethod='POST',
        type='AWS_PROXY',
        uri=f'arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/{function_arn}/invocations',
        credentials=config.DEFAULT_API_GATEWAY_LAMBDA_CALL_ROLE
    )

    # Create deployment
    api_gateway_client.create_deployment(
        restApiId=gateway_id,
        stageName=gateway_stage
    )



@lambda_func.command()
@click.option("--function-name", "-f", help="Function name", required=True)
@click.option("--model-endpoint", "-i", help="Model endpoint name", required=True)
@click.option("--layers", "-l", help="Layers name", default=config.DEFAULT_LAMBDA_LAYERS, multiple=True)
@click.option("--ram", "-r", help="RAM size", type=int, default=config.DEFAULT_LAMBDA_RAM)
@click.option("--arn", "-a", help="ARN name", default=config.DEFAULT_LAMBDA_ARN)
@click.option("--runtime", "-s", help="Lambda runtime", default=config.DEFAULT_LAMBDA_RUNTIME)
@click.option("--timeout", "-t", help="Lambda timeout", default=config.DEFAULT_LAMBDA_TIMEOUT, type=int)
@click.option("--publish/--no-publish", help="Publish", default=True)
@click.option("--publish-in-gateway/--no-publish-in-gateway", help="Publish in API Gateway", default=False)
@click.option("--gateway-resource", "-u", help="Name of resource in API Gateway (URL)")
@click.option("--gateway-id", "-g", help="ID of AWS API Gateway", default=config.DEFAULT_API_GATEWAY_ID)
@click.option("--gateway-stage", "-l", help="AWS API Gateway Stage", default=config.DEFAULT_API_GATEWAY_STAGE)
@click.option("--gateway-auth", "-q", help="AWS API Gateway Authorizer", default=config.DEFAULT_API_GATEWAY_AUTHORIZATION)
@cli_args.MODEL_URI
def deploy(
    function_name,
    model_endpoint,
    layers,
    ram,
    arn,
    runtime,
    timeout,
    publish,
    model_uri,
    publish_in_gateway,
    gateway_resource,
    gateway_id,
    gateway_stage,
    gateway_auth
):
    """
    Deploy lambda handler for model
    """
    inference_code_location = download_model_inference_code(model_uri)
    lambda_client = boto3.client('lambda')
    try:
        current_function = lambda_client.get_function(
            FunctionName=function_name
        )
    except lambda_client.exceptions.ResourceNotFoundException:
        current_function = None
        pass

    # If current function exists
    if current_function:
        click.echo(f'Updating code of exisitng function {function_name!r}')
        function_info = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=make_zip_file_bytes(inference_code_location),
            Publish=publish
        )
        click.echo(f'Function {function_name} has been updated')
    else:
        function_info = lambda_client.create_function(
            Code={
                'ZipFile': make_zip_file_bytes(inference_code_location),
            },
            Description=f'Processing layer for model {model_uri}',
            FunctionName=function_name,
            Handler=const.LAMBDA_FUNCTION_HANDLER,
            Publish=publish,
            Timeout=timeout,
            MemorySize=ram,
            Role=arn,
            Runtime=runtime,
            Layers=layers,
            Environment={
                'Variables': {
                    const.MODEL_ENDPOINT_ENV: model_endpoint
                }
            },
            Tags={
                const.LAMBDA_FUNCTION_TAG[0]: const.LAMBDA_FUNCTION_TAG[1],
                'model': model_uri
            }
        )
        click.echo(f'Function {function_name} has been published')

    click.echo(function_info['FunctionArn'])

    if publish_in_gateway:
        if not publish:
            click.echo('Ignoring API Gateway publication, because publish was disabled', err=True)
            return
        if not gateway_resource:
            click.echo('Gateway Resource name has not been provided', err=True)
            return
        register_in_api_gateway.callback(
            function_name=function_name,
            gateway_resource=gateway_resource,
            gateway_id=gateway_id,
            gateway_stage=gateway_stage,
            gateway_auth=gateway_auth
        )
