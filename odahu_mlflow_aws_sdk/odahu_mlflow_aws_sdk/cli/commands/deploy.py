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
import click

from mlflow.utils import cli_args
import mlflow.sagemaker
from mlflow.tracking import MlflowClient
from mlflow.store.artifact.models_artifact_repo import ModelsArtifactRepository
from mlflow.store.artifact.utils.models import get_model_name_and_version


from odahu_mlflow_aws_sdk import config
from odahu_mlflow_aws_sdk.cli.commands import sagemaker
from odahu_mlflow_aws_sdk.cli.commands import lambda_func


@click.command()
@cli_args.MODEL_URI
def deploy(model_uri):
    """
    Deploy model (SageMaker, AWS Lambda, API Gateway)
    """
    # Load model
    if not ModelsArtifactRepository.is_models_uri(model_uri):
        raise Exception('Only Model URLs are supported')
    client = MlflowClient()
    name, version = get_model_name_and_version(client, model_uri)
    function_name = f'{name}-invocation'
    # Deploy SageMaker Endpoint
    sagemaker.deploy_model.callback(
        app_name=name,
        model_uri=model_uri,
        execution_role_arn=config.DEFAULT_SAGEMAKER_EXECUTION_ROLE_ARN,
        bucket=config.DEFAULT_SAGEMAKER_S3_MODELS_ARTIFACT,
        image_url=config.DEFAULT_SAGEMAKER_INFERENCE_IMAGE,
        region_name=config.DEFAULT_SAGEMAKER_REGION,
        mode=mlflow.sagemaker.DEPLOYMENT_MODE_ADD,
        archive=False,
        instance_type=config.DEFAULT_SAGEMAKER_INSTANCE_TYPE,
        instance_count=config.DEFAULT_SAGEMAKER_INSTANCE_COUNT,
        vpc_config=config.DEFAULT_SAGEMAKER_VPC_CONFIG,
        timeout=config.DEFAULT_SAGEMAKER_DELOY_TIMEOUT
    )
    # Create lambda & API gateway
    lambda_func.deploy.callback(
        function_name=function_name,
        model_endpoint=name,
        layers=config.DEFAULT_LAMBDA_LAYERS,
        ram=config.DEFAULT_LAMBDA_RAM,
        arn=config.DEFAULT_LAMBDA_ARN,
        runtime=config.DEFAULT_LAMBDA_RUNTIME,
        timeout=config.DEFAULT_LAMBDA_TIMEOUT,
        publish=True,
        model_uri=model_uri,
        publish_in_gateway=True,
        gateway_resource=name,
        gateway_id=config.DEFAULT_API_GATEWAY_ID,
        gateway_stage=config.DEFAULT_API_GATEWAY_STAGE,
        gateway_auth=config.DEFAULT_API_GATEWAY_AUTHORIZATION
    )