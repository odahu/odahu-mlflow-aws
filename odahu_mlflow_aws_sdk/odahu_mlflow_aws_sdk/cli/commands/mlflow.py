import os

import mlflow.cli
import click

from odahu_mlflow_aws_sdk import config


@click.group('mlflow')
def mlflow_cli():
    """
    Run original mlflow command

    :return:
    """
    pass


for command in mlflow.cli.cli.commands.values():
    mlflow_cli.add_command(command)
