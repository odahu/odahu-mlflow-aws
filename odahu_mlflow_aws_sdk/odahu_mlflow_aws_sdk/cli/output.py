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
This module provides functions for printing output of command execution in a requested (by user) way
"""
import json
import typing
import datetime
import enum
import time
import inspect

import click
import click.decorators
from texttable import Texttable

from odahu_mlflow_aws_sdk import config

# Protobuf formatting
try:
    from google.protobuf.json_format import MessageToDict
except ModuleNotFoundError:
    def MessageToDict(*args, **kwargs):
        raise Exception('protobuf has not been installed')

# YAML Output
try:
    from yaml import dump
    try:
        from yaml import CDumper as Dumper
    except ImportError:
        from yaml import Dumper

    def dump_yaml(data):
        return dump(data, Dumper=Dumper)
except ModuleNotFoundError:
    def dump_yaml(_):
        raise Exception('PyYAML has not been installed')


class ColumnAlign(enum.Enum):
    """
    Horizontal align of the cell content
    """
    LEFT = 'l'
    CENTER = 'c'
    RIGHT = 'r'


class ColumnVAlign(enum.Enum):
    """
    Vertical align of the cell content
    """
    TOP = 't'
    MIDDLE = 'm'
    BOTTOM = 'b'


def date_from_timestamp(val: int) -> datetime.datetime:
    """
    Load date (with time) from the timestamp, supports unix timestamp (seconds) and millisecond version

    :param val: timestamp
    :type val: int
    :return: date with time
    :rtype: datetime.datetime
    """
    if val > time.time() + 100 * 365 * 24 * 3600:
        return datetime.datetime.utcfromtimestamp(val / 1000)
    else:
        return datetime.datetime.utcfromtimestamp(val)


class ColumnDataType(enum.Enum):
    """
    Type of data in the cell
    """
    # Automatic detection
    AUTO = 'a'
    # Text data
    TEXT = 't'
    # Float in the dec. format (123.33)
    FLOAT_DEC = 'f'
    # Float in the exp. format (12e3)
    FLOAT_EXP = 'e'
    # Integer / number
    INT = 'i'
    # Date time
    DATETIME = 'dt'

    @classmethod
    def default_types(cls) -> typing.List['ColumnDataType']:
        """
        Default types, provided by the texttable package

        :return: default types
        :rtype: typing.List['ColumnDataType']
        """
        return [
            cls.AUTO, cls.TEXT, cls.FLOAT_EXP, cls.FLOAT_DEC, cls.INT
        ]

    @property
    def is_default(self) -> bool:
        """
        Is this type a default type provided by the texttable package

        :return: is this type a default type
        :rtype: bool
        """
        return self in self.default_types()

    @classmethod
    def format(cls, value: object, value_type: 'ColumnDataType') -> str:
        """
        Format data in the cell (ONLY FOR NON DEFAULT TYPES)

        :param value: value in the cell
        :type value: object
        :param value_type: type of the cell data
        :type value_type: ColumnDataType
        :return: formatted value
        :rtype: str
        """
        if value_type.is_default:
            raise Exception('Format should be called only for non default values')
        if value_type == cls.DATETIME:
            if isinstance(value, int):
                date = date_from_timestamp(value)
            elif isinstance(value, str):
                if value.isnumeric():
                    date = date_from_timestamp(int(value))
                else:
                    raise Exception('Only timestamp can be represented as a date')
            elif not isinstance(value, datetime.datetime):
                raise Exception(f'Unsupported for converting to date time: {type(value)}')
            return date.isoformat()
        else:
            raise ValueError(f'Invalid type found: {value_type}')

    @property
    def as_column_dtype(self) -> typing.Union[str, typing.Callable[[object], object]]:
        """
        Convert to the form, `column_dtype` expects

        :return: argument for the texttable
        :rtype: typing.Union[str, typing.Callable[[object], object]]
        """
        if self.is_default:
            return self.value
        else:
            return lambda x: self.format(x, self)


class Column:
    """
    Class for representing column of the output table
    """
    def __init__(self,
                 name: str,
                 key: typing.Union[str, typing.Callable],
                 dtype=ColumnDataType.AUTO,
                 align=ColumnAlign.LEFT,
                 valign=ColumnVAlign.MIDDLE,
                 default=True):
        self.name = name
        self.key = key
        self.dtype = dtype
        self.align = align
        self.valign = valign
        self.default = default


class OutputFormat(enum.Enum):
    """
    Format output. Possible options are: json, yaml, table.
    """

    JSON = 'json'
    YAML = 'yaml'
    TABLE = 'table'

    @classmethod
    def valid_options(cls):
        return [val.value for val in cls]

    @classmethod
    def validate(cls, ctx, param, value: str):
        if '[' in value and value.endswith(']'):
            value.rstrip(']')
            type, formatting = value.split('[', maxsplit=1)
            formatting = formatting.rstrip(']')
        else:
            type, formatting = value, None

        if type not in cls.valid_options():
            raise click.UsageError(
                f'{type} is an invalid type of output, valid types are: {cls.valid_options()}',
                ctx=ctx
            )
        return OutputFormat(type), formatting


def output_options(f: click.decorators.FC) -> click.decorators.FC:
    """
    Build a decorator for click commands for adding output formatting options

    :param f: function to decorate
    :return: decorated function
    """
    func_decs = (
        click.option(
            '-o', '--output',
            help=inspect.getdoc(OutputFormat),
            type=str, default=OutputFormat.TABLE.value,
            show_default=True,
            callback=OutputFormat.validate
        ),
    )
    for dec in func_decs:
        f = dec(f)
    return f


def _build_table_row(
        headers: typing.Iterable[str],
        columns_config: typing.Optional[typing.Tuple[Column]],
        row: dict
) -> typing.Tuple[object, ...]:
    """
    Build content for a table row

    :param headers: name of headers
    :param columns_config: optional configuration of columns
    :param row: row data
    :return: values for columns in a row
    :rtype: typing.Tuple[object, ...]
    """
    ret = []
    for idx, header in enumerate(headers):
        if columns_config:
            column_info = columns_config[idx]
            if callable(column_info.key):
                val = column_info.key(row)
            else:
                val = row.get(column_info.key)
        else:
            val = row.get(header)
        ret.append(val)
    return tuple(ret)


def set_headers_config(
        columns_config: typing.Optional[typing.Iterable[Column]],
        first_item: dict,
        table: Texttable
) -> typing.Iterable[str]:
    """
    Set configuration of headers & columns for the table, return column names

    :param columns_config: optional configuration of columns
    :type columns_config: typing.Optional[typing.Iterable[Column]]
    :param first_item: first row in a column for auto detection (if columns_config is not provided)
    :type first_item: dict
    :param table: table itself
    :type table: Texttable
    :return: column names
    :rtype: typing.Iterable[str]
    """
    if not columns_config:
        return tuple(first_item.keys())

    table.set_cols_dtype([c.dtype.as_column_dtype for c in columns_config])
    table.set_cols_valign([c.valign for c in columns_config])
    table.set_cols_align([c.align for c in columns_config])

    return tuple(c.name for c in columns_config)


def output_single_data(data, **kwargs) -> None:
    """
    Output single item as a table

    :param data: data, which can be converted to the dict (or already is a dict)
    :param kwargs: extra formatting arguments, provided by the output_options
    :return: nothing
    :rtype: None
    """
    return output_list_data([data], **kwargs)


def output_list_data(data: typing.Iterable, **kwargs) -> None:
    """
    Output iterable data as a table

    :param data: iterable data, which can be converted to the dict (or already is a dict)
    :param kwargs: extra formatting arguments, provided by the output_options
    :return: nothing
    :rtype: None
    """
    # Extract formatting configuration
    if 'output' in kwargs:
        output_type, output_formatting = kwargs.get('output')
    else:
        output_type, output_formatting = OutputFormat.TABLE, None

    # Convert to tuple (loads all in memory)
    items = tuple(data)

    # Return empty if no data
    if not items:
        if output_type == OutputFormat.TABLE:
            pass
        elif output_type == OutputFormat.JSON:
            click.echo('[]\n')
        elif output_type == OutputFormat.YAML:
            click.echo('\n')
        return

    # Convert to dict (from dict, protobuf or object with .to_dict() function)
    ret = []
    for row in data:
        if isinstance(row, dict):
            ret.append(row)
        elif hasattr(row, 'to_dict'):
            ret.append(row.to_dict())
        elif hasattr(row, 'to_proto'):
            ret.append(MessageToDict(row.to_proto()))
        else:
            raise Exception('Output function supports only objects with to_dict / to_proto functions')

    # Output final data
    if output_type == OutputFormat.JSON:
        click.echo(json.dumps(
            ret,
            indent=2
        ) + "\n")
    elif output_type == OutputFormat.YAML:
        click.echo(dump_yaml(ret) + "\n")
    elif output_type == OutputFormat.TABLE:
        # Prepare table
        table = Texttable(config.MAX_TABLE_WIDTH)
        table.set_chars([' ', '|', '+', '-'])
        table.set_deco(Texttable.HEADER)
        columns_config = kwargs.get('columns')
        headers = set_headers_config(columns_config, ret[0], table)
        table.add_rows(
            [headers] + [
                _build_table_row(headers, columns_config, row)
                for row in ret
            ]
        )
        click.echo(table.draw() + "\n")
