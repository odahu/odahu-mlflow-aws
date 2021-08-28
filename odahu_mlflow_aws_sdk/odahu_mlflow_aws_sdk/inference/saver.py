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
Functions for finding and storing inference code as a part of MlFlow model
"""
import inspect
import os
import shutil
import typing
import ast

import mlflow

from odahu_mlflow_aws_sdk.inference import const


def check_inference_code_lambda_file(lambda_file: str) -> None:
    """
    Validate content of the lambda file (that function with proper name is defined)

    :param lambda_file: path to the file
    :return: nothing
    """
    with open(lambda_file, 'r') as l_file:
        data = l_file.read()
    try:
        tree = ast.parse(data, lambda_file)
    except Exception as lambda_file_parse_exception:
        raise Exception(f'Unable to parse lambda function file ({lambda_file!r})') from lambda_file_parse_exception

    for definition in tree.body:
        if isinstance(definition, ast.FunctionDef) and definition.name == const.LAMBDA_FUNCTION_FUNCTION_NAME:
            handler_def = definition
            break
    else:
        raise Exception(
            f'Unable to find lambda definition function {const.LAMBDA_FUNCTION_FUNCTION_NAME!r} '
            f'in the file {lambda_file!r}'
        )

    if len(handler_def.args.args) != 2:
        raise Exception(
            f'Handle definition function {const.LAMBDA_FUNCTION_FUNCTION_NAME!r} in the file {lambda_file!r} '
            f'takes not 2 arguments'
        )


def check_inference_code_location(folder: str) -> None:
    """
    Validate that inference code folder contains reuired files (handler)

    :param folder: path to the folder with the inference code
    :return: nothing
    """
    if not os.path.isdir(folder):
        raise Exception(f'Inference code location ({folder!r}) should be a folder')
    lambda_function_file = os.path.join(folder, const.LAMBDA_FUNCTION_FILE_NAME)
    if not os.path.exists(lambda_function_file) or not os.path.isfile(lambda_function_file):
        raise Exception(f'Lambda function file ({lambda_function_file!r}) is not found or not a file')
    check_inference_code_lambda_file(lambda_function_file)


def clean_unnecessary_files_in_folder(folder: str) -> None:
    """
    Remove unnecessary files from the folder (used before sending files to the MlFlow)

    :param folder: path to the folder
    :return: nothing
    """
    to_remove = set()
    for filename in os.listdir(folder):
        full_path = os.path.join(folder, filename)
        if filename.startswith('.'):
            to_remove.add(full_path)
        if os.path.isdir(full_path) and filename == '__pycache__':
            to_remove.add(full_path)
    for loc in to_remove:
        shutil.rmtree(loc)


def get_inference_location(location: typing.Optional[str] = None) -> str:
    """
    Get location of the inference code if is not provided, validate

    :param location: (optional) path to the folder with the inference code
    :return: validated path to the folder with the inference code
    """
    if not location:
        stack = inspect.stack()
        caller_file = None
        current_file = os.path.abspath(__file__)
        current_dir = os.path.dirname(current_file)
        for frame in stack:
            if frame.filename != current_file and os.path.dirname(frame.filename) != current_dir:
                caller_file = frame.filename
                break
        else:
            raise Exception('Location of the inference logic folder is not provided and can not be detected')

        locations = [
            os.path.join(os.path.dirname(caller_file), const.DEFAULT_INFERENCE_SERVICE_FOLDER),
            os.path.join(os.path.dirname(caller_file), os.pardir, const.DEFAULT_INFERENCE_SERVICE_FOLDER),
        ]
        location = next(loc for loc in locations if os.path.exists(loc))
    if not os.path.exists(location):
        raise Exception(f'Location of the inference code ({location!r}) does not exist or is not readable')

    # Validate code location and content
    check_inference_code_location(location)

    return location


def save_inference_logic(location: typing.Optional[str] = None, autoclean: bool = True):
    """
    Save inference logic using MlFlow API

    :param location: path to the inference logic
    :param autoclean: remove unnec. files
    :return: nothing
    """
    location = get_inference_location(location)

    if autoclean:
        # Remove pycache, files starting with .
        clean_unnecessary_files_in_folder(location)

    # Call mlflow save logic to save this
    mlflow.log_artifacts(location, const.MLFLOW_MODEL_INFERENCE_FOLDER)
