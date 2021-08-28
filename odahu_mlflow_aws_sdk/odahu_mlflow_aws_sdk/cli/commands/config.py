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

from odahu_mlflow_aws_sdk import config as cfg


@click.group('config')
def config():
    """
    Manage configuration
    """
    pass

@config.command()
def list():
    """
    List config options and their values
    """
    try:
        cfg_file = cfg.get_config_file_section(silent=False)
    except Exception as config_read_exception:
        click.echo(f'Unable to open config file {cfg.get_config_file_path()}: {config_read_exception}', err=True)

    for c_name, c_value in cfg.ALL_VARIABLES.items():
        value = getattr(cfg, c_name)
        click.echo(f'{c_name}: {value!r}', nl=False)
        extra_info = []
        is_default = value != c_value.default
        # Build extra info
        if is_default:
            extra_info.append(f'default: {c_value.default!r}')
        # Output
        if extra_info:
            click.echo(f' ({", ".join(extra_info)})')
        else:
            click.echo('')

@config.command('get-value')
@click.argument('key', type=str)
def get_value(key):
    """
    Get config value (or default)
    """
    if key not in cfg.ALL_VARIABLES:
        click.echo(f'Unknown key {key!r}', err=True)
        sys.exit(1)

    click.echo(getattr(cfg, key))


@config.command('unset')
@click.argument('key', type=str)
def unset_value(key):
    """
    Unset config value (remove from INI)
    """
    if key not in cfg.ALL_VARIABLES:
        click.echo(f'Unknown key {key!r}', err=True)
        sys.exit(1)

    new_values = {
        key: None
    }

    try:
        cfg.update_config_file(
            **new_values
        )
    except Exception as config_update_exception:
        click.echo(f'Unable to unset value of config {key!r}: {config_update_exception}', err=True)
        sys.exit(1)

    click.echo(f'Value of {key!r} has been removed in the config file {cfg.get_config_file_path()}')


@config.command('set')
@click.argument('key', type=str)
@click.argument('value')
def set_value(key, value):
    """
    Set config value (and store in INI)
    """
    if key not in cfg.ALL_VARIABLES:
        click.echo(f'Unknown key {key!r}', err=True)
        sys.exit(1)

    new_values = {
        key: value
    }

    try:
        cfg.update_config_file(
            **new_values
        )
    except Exception as config_update_exception:
        click.echo(f'Unable to set value of config {key!r} to {value!r}: {config_update_exception}', err=True)
        sys.exit(1)


    click.echo(f'Value of {key!r} has been updated in the config file {cfg.get_config_file_path()}')


@config.command()
def location():
    """
    Get locaiton of the config file
    """
    click.echo(cfg.get_config_file_path())