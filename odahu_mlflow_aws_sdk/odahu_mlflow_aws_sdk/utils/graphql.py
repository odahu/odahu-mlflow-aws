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
Util / helper functions for working with GraphQL
"""
import contextlib
import json
import typing
import re

import graphene
import mlflow.types
import pandas as pd

from odahu_mlflow_aws_sdk.inference import exceptions


class BinaryString(graphene.Scalar):
    # TODO: Implementation is needed
    # Docs: https://docs.graphene-python.org/en/stable/types/scalars/#custom-scalars

    @staticmethod
    def serialize(val: bytes):
        raise NotImplementedError('Binary type is not implemented yet')

    @staticmethod
    def parse_literal(node):
        raise NotImplementedError('Binary type is not implemented yet')

    @staticmethod
    def parse_value(value):
        raise NotImplementedError('Bimary type is not implemented yet')


# Mapping of MlFlow types on GraphQL (graphene) types
GRAPHENE_TYPE_MAPPING = {
    mlflow.types.DataType.boolean: graphene.Boolean,
    mlflow.types.DataType.integer: graphene.Int,
    mlflow.types.DataType.long: graphene.Int,
    mlflow.types.DataType.float: graphene.Float,
    mlflow.types.DataType.double: graphene.Float,
    mlflow.types.DataType.string: graphene.String,
    mlflow.types.DataType.binary: BinaryString,
    mlflow.types.DataType.datetime: graphene.types.DateTime
}


def camel(s: str) -> str:
    """
    Make a camel case from a string

    :param s: source string
    :return: camelCased string
    """
    # Ignore strings w/o spaces, dashes and underscore
    if ' ' not in s and '_' not in s and '-' not in s:
        return s
    s = re.sub(r"(_|-)+", " ", s).title().replace(" ", "")
    return ''.join([s[0].lower(), s[1:]])


def build_graphql_types_from_mlflow_schema(schema: mlflow.types.Schema) -> typing.Dict[str, object]:
    """
    Build a schema for Graphene based on the mlflow schema

    :param schema: MlFlow schema
    :return: Graphene Schema (as a dict)
    """
    parameters = {}
    for column in schema.columns:
        name = camel(column.name)
        graphene_type = GRAPHENE_TYPE_MAPPING.get(column.type)
        if not graphene_type:
            raise Exception(f'Unsupported MLFlow type: {column.type}')
        parameters[name] = graphene_type(
            name=name,
            description=column.name,
            required=True
        )
    return parameters


def resolve_schema(_, resolve_info, **kwargs):
    """
    Return schema information

    :param _:
    :param resolve_info:
    :param kwargs:
    :return:
    """
    return str(resolve_info.schema)


def pack_prediction(target_type, fn):
    """
    Decorator: pack result of a prediction to a target type

    :param target_type: target type
    :param fn: wrapped function
    :return: packed result
    """
    def wrapper(*args, **kwargs):
        result = fn(*args, **kwargs)
        try:
            return target_type(**result)
        except Exception as build_response_exception:
            raise Exception(f'Unable to build response object {target_type.__name__} from the {result!r}')
    return wrapper


def remap_inputs(input_schema, fn):
    """
    Decorator: Map camelCased input to original names

    :param input_schema: input schema
    :param fn: wrapped function
    :return: wrapper
    """
    def wrapper(*args, **kwargs):
        values = {}
        for camel_case_name, value in kwargs.items():
            input_record = input_schema.get(camel_case_name)
            if not input_record:
                raise Exception(f'Invalid input, field {camel_case_name!r} is unknown')
            original_name = input_record.kwargs.get('description')
            if not original_name:
                raise Exception(f'Unable to find original name (in description) for field {camel_case_name!r}')
            values[original_name] = value
        return fn(*args, **values)
    return wrapper


def build_invocation_schema(
        input_mlflow_schema: mlflow.types.Schema,
        output_mlflow_schema: mlflow.types.Schema,
        prediction_fn: typing.Callable
) -> graphene.Schema:
    """
    Build a schema for target input & output MlFlow schema

    :param input_mlflow_schema: input MlFlow schema
    :param output_mlflow_schema: output MlFlow schema
    :param prediction_fn: callback to call for predict invocation
    :return: schema
    """
    # TODO: Add support of tensor spec
    # if input_mlflow_schema.is_tensor_spec:
    #    raise Exception('Tensor spec is not supported for graphql')

    if not input_mlflow_schema.has_input_names:
        raise Exception('Schema should have column names declared')

    input = build_graphql_types_from_mlflow_schema(input_mlflow_schema)
    output = build_graphql_types_from_mlflow_schema(output_mlflow_schema)

    # Build output schema
    Prediction = type('Prediction', (graphene.ObjectType,), output)

    Query = type('Query', (graphene.ObjectType,), {
        # Predictions
        'prediction': graphene.Field(Prediction, **input),
        'resolve_prediction': pack_prediction(Prediction, remap_inputs(input, prediction_fn)),
        # Self-introspection
        'schema': graphene.Field(graphene.String),
        'resolve_schema': resolve_schema
    })
    return graphene.Schema(query=Query)


def execute_graphql_query(query: str, schema: graphene.ObjectType) -> pd.DataFrame:
    """
    Execute GraphQL query

    :param query: query
    :param schema: schema for processing a query (with operation declarations)
    :return: processed data (as a pd.DataFrame)
    """
    variables = {}
    with contextlib.suppress(Exception):
        if query and query.startswith('{') and query.endswith('}'):
            parsed = json.loads(query)
            query, variables = parsed.get('query'), parsed.get('variables')

    result = schema.execute(query, variables=variables)
    if result.errors:
        for error in result.errors:
            if isinstance(error.original_error, exceptions.InvalidModelInputException):
                raise error.original_error

        errors_messages = '; '.join(str(err) for err in result.errors)
        raise Exception(f'Unable to execute graphql query: {errors_messages}')
    return result
