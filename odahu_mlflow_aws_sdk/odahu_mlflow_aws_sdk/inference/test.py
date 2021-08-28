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
This module provides a test handler for running tests against a model with using of an inference code logic
"""
import os.path
import inspect
import typing
from importlib.machinery import SourceFileLoader

import mlflow
import mlflow.pyfunc


from odahu_mlflow_aws_sdk.inference.sdk.handler import BaseModelHandler
from odahu_mlflow_aws_sdk.inference import const
from odahu_mlflow_aws_sdk.inference.sdk.test_handler import TestHandler
from odahu_mlflow_aws_sdk.inference.saver import get_inference_location


def load_model(
        run_id: typing.Optional[str] = None,
        model_name: typing.Optional[str] = None
):
    """
    Load model python flavor (in a memory)

    :param run_id: run id
    :param model_name: model name
    :return:
    """
    if not run_id:
        run_info = mlflow.active_run()
        if not run_info:
            raise Exception(f'Unable to find active run to detect a model')
        run_id = run_info.info.run_id

    if not model_name:
        client = mlflow.tracking.MlflowClient()
        artifacts = client.list_artifacts(run_id)
        raise NotImplementedError('Model name should be provided')

    model_uri = f'runs:/{run_id}/{model_name}'
    return mlflow.pyfunc.load_model(model_uri)


def find_class_in_module(
        module,
        target_class: typing.Optional[str] = None,
):
    """
    Find class in a module which should be used for handling

    :param module:
    :param target_class:
    :return:
    """
    clsmembers = inspect.getmembers(module, inspect.isclass)
    found = None
    for name, class_type in clsmembers:
        if issubclass(class_type, BaseModelHandler) and not found:
            found = class_type
        if target_class and name == target_class:
            return class_type
    return found


def create_test_handler(
        run_id: typing.Optional[str] = None,
        model_name: typing.Optional[str] = None,
        handler_class_name: typing.Optional[str] = None,
        inference_code_location: typing.Optional[str] = None
) -> TestHandler:
    """
    Create test handler which can be used to invoke pre, post and validation logic for the model

    :param run_id: (optional) ID of run
    :param model_name: name of model
    :param handler_class_name: (optional) name of a class name in an inference code
    :param inference_code_location: (optional) location of the inference code
    :return: test handler
    """
    # Locate (if not provided) and load model
    model = load_model(run_id, model_name)
    # Locate inference
    location = get_inference_location(inference_code_location)
    try:
        lambda_handler_file = os.path.abspath(os.path.join(location, const.LAMBDA_FUNCTION_FILE_NAME))
        inference_module = SourceFileLoader('inference_module', lambda_handler_file).load_module()
    except Exception as inference_load_exception:
        raise Exception(f'Error during loading inference code') from inference_load_exception
    # Locate (if not provided) and load handler
    handler = find_class_in_module(inference_module, handler_class_name)
    # Build test handler
    return TestHandler(
        handler,
        model
    )
