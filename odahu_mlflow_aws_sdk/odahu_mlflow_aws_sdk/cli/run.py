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
"""
This module provides root level command
"""
import click
import os

from odahu_mlflow_aws_sdk import config

from .commands import ALL_GROUPS


@click.group(context_settings={'show_default': True})
@click.version_option()
@click.option('--debug/--no-debug', default=False)
def cli(debug: bool):
    config.DEBUG = debug
    os.environ['MLFLOW_TRACKING_URI'] = config.MLFLOW_TRACKING_URI


# Add all subgroups / commands to the root command
for group in ALL_GROUPS:
    cli.add_command(group)
