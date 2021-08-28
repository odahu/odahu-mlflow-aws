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
import json
import os

import mlflow.sagemaker
import click
import sys

from odahu_mlflow_aws_sdk import config
from mlflow.utils import cli_args
from mlflow.pyfunc import FLAVOR_NAME as PYFUNC_FLAVOR_NAME


@click.group()
def sagemaker():
    """
    Deploy & manage models, deployed in sagemaker
    """
    pass


@sagemaker.command('deploy-model')
@click.option("--app-name", "-a", help="Application name", required=True)
@cli_args.MODEL_URI
@click.option(
    "--execution-role-arn", "-e",
    default=config.DEFAULT_SAGEMAKER_EXECUTION_ROLE_ARN,
    help="SageMaker execution role",
    show_default=True,
    required=True
)
@click.option(
    "--bucket", "-b",
    default=config.DEFAULT_SAGEMAKER_S3_MODELS_ARTIFACT,
    help="S3 bucket to store model artifacts",
    show_default=True,
    required=True
)
@click.option(
    "--image-url", "-i",
    default=config.DEFAULT_SAGEMAKER_INFERENCE_IMAGE,
    help="ECR URL for the Docker image",
    required=True
)
@click.option(
    "--region-name",
    default=config.DEFAULT_SAGEMAKER_REGION,
    help="Name of the AWS region in which to deploy the application",
    required=True
)
@click.option(
    "--mode",
    default=mlflow.sagemaker.DEPLOYMENT_MODE_CREATE,
    help="The mode in which to deploy the application."
    " Must be one of the following: {mds}".format(mds=", ".join(mlflow.sagemaker.DEPLOYMENT_MODES)),
)
@click.option(
    "--archive",
    "-ar",
    is_flag=True,
    help=(
        "If specified, any SageMaker resources that become inactive (i.e as the"
        " result of an update in {mode_replace} mode) are preserved."
        " These resources may include unused SageMaker models and endpoint"
        " configurations that were associated with a prior version of the application"
        " endpoint. Otherwise, if `--archive` is unspecified, these resources are"
        " deleted. `--archive` must be specified when deploying asynchronously with"
        " `--async`.".format(mode_replace=mlflow.sagemaker.DEPLOYMENT_MODE_REPLACE)
    ),
)
@click.option(
    "--instance-type",
    "-t",
    default=config.DEFAULT_SAGEMAKER_INSTANCE_TYPE,
    help="The type of SageMaker ML instance on which to deploy the model. For a list of"
    " supported instance types, see"
    " https://aws.amazon.com/sagemaker/pricing/instance-types/.",
    required=True
)
@click.option(
    "--instance-count",
    "-c",
    default=config.DEFAULT_SAGEMAKER_INSTANCE_COUNT,
    help="The number of SageMaker ML instances on which to deploy the model",
    required=True
)
@click.option(
    "--vpc-config",
    "-v",
    default=config.DEFAULT_SAGEMAKER_VPC_CONFIG,
    help="Path to a file containing a JSON-formatted VPC configuration. This"
    " configuration will be used when creating the new SageMaker model associated"
    " with this application. For more information, see"
    " https://docs.aws.amazon.com/sagemaker/latest/dg/API_VpcConfig.html",
)
@click.option(
    "--timeout",
    default=config.DEFAULT_SAGEMAKER_DELOY_TIMEOUT,
    help=(
        "If the command is executed synchronously, the deployment process will return"
        " after the specified number of seconds if no definitive result (success or"
        " failure) is achieved. Once the function returns, the caller is responsible"
        " for monitoring the health and status of the pending deployment via"
        " native SageMaker APIs or the AWS console."
    ),
    required=True
)
def deploy_model(
    app_name,
    model_uri,
    execution_role_arn,
    bucket,
    image_url,
    region_name,
    mode,
    archive,
    instance_type,
    instance_count,
    vpc_config,
    timeout,
):
    """
    Deploys MLFlow model as a model endpoint
    """
    if vpc_config:
        if not os.path.exists(vpc_config):
            click.echo(f'Unable to find VPC config file in location {vpc_config!r}', err=True)
            sys.exit(2)

        with open(vpc_config, "r") as f:
            vpc_config = json.load(f)
    else:
        vpc_subnets = config.DEFAULT_SAGEMAKER_VPC_SUBNETS
        vpc_sg = config.DEFAULT_SAGEMAKER_VPC_SECURITY_GROUPS
        if vpc_subnets or vpc_sg:
            vpc_config = {
                'SecurityGroupIds': vpc_sg,
                'Subnets': vpc_subnets,
            }
        else:
            vpc_config = None

    click.echo('Staring model deploying algo')
    mlflow.sagemaker.deploy(
        app_name=app_name,
        model_uri=model_uri,
        execution_role_arn=execution_role_arn,
        bucket=bucket,
        image_url=image_url,
        region_name=region_name,
        mode=mode,
        archive=archive,
        instance_type=instance_type,
        instance_count=instance_count,
        vpc_config=vpc_config,
        flavor=PYFUNC_FLAVOR_NAME,
        synchronous=True,
        timeout_seconds=timeout,
    )


@sagemaker.command('run-local')
@cli_args.MODEL_URI
@click.option('--port', '-p', default=config.DEFAULT_SAGEMAKER_LOCAL_RUN_PORT, type=int)
@click.option(
    "--image-url", "-i",
    default=config.DEFAULT_SAGEMAKER_INFERENCE_IMAGE,
    help="ECR URL for the Docker image",
    show_default=True,
    required=True
)
def run_local(model_uri, port, image_url):
    mlflow.sagemaker.run_local(
        model_uri=model_uri,
        port=port,
        image=image_url,
        flavor=PYFUNC_FLAVOR_NAME
    )