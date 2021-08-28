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
import sys

import click
from mlflow.tracking.client import MlflowClient

from odahu_mlflow_aws_sdk import config
from odahu_mlflow_aws_sdk.cli.output import output_options, output_list_data, output_single_data
from odahu_mlflow_aws_sdk.cli import columns


@click.group()
def models():
    """
    Manage available models

    :return:
    """
    pass

@models.command('list')
@output_options
def models_list(**output_options_values):
    """
    List all models, registered in mlflow
    """
    try:
        output_list_data(
            MlflowClient(config.MLFLOW_TRACKING_URI).list_registered_models(),
            **output_options_values,
            columns=columns.MlFlowModel
        )
    except Exception as list_exception:
        click.echo(f'Unable to list models: {list_exception}', err=True)
        sys.exit(1)


@models.command('describe')
@output_options
@click.argument('name', type=str)
def models_get_model(name, **output_options_values):
    """
    Get information about model
    """
    try:
        models = MlflowClient(config.MLFLOW_TRACKING_URI).search_registered_models(
            filter_string=f"name = '{name}'"
        )
        if not models:
            click.echo(f'Model with name {name} has not been found', err=True)
            sys.exit(2)
        output_single_data(
            models[0],
            **output_options_values,
            columns=columns.MlFlowModel
        )
    except Exception as list_exception:
        click.echo(f'Unable to get model {name}: {list_exception}', err=True)
        sys.exit(1)


@models.command('list-versions')
@output_options
@click.argument('name', type=str)
def models_list_versions(name, **output_options_values):
    """
    Get information about model
    """
    try:
        output_list_data(
            MlflowClient(config.MLFLOW_TRACKING_URI).search_model_versions(
                filter_string=f"name = '{name}'"
            ),
            **output_options_values,
            columns=columns.MlFlowModelVersion
        )
    except Exception as list_exception:
        click.echo(f'Unable to list model {name} versions: {list_exception}', err=True)
        sys.exit(1)
