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
import typing
import json
import csv
from io import StringIO

import pandas as pd
import numpy as np

from mlflow.pyfunc import scoring_server

from odahu_mlflow_aws_sdk.inference.sdk.handler import BaseModelHandler, PredictionRequestResponse
from odahu_mlflow_aws_sdk.inference.sdk.call_processors import InMemoryCallProcessor
from odahu_mlflow_aws_sdk.inference import const


class TestHandler:
    """
    Handler for testing model
    """
    def __init__(self, handler_cls: type, model_py_func):
        self.handler_cls = handler_cls
        self.model_py_func = model_py_func
        self.handler = handler_cls(InMemoryCallProcessor(model_py_func))  # type: BaseModelHandler

    def _parse_response(self, response):
        if not isinstance(response, PredictionRequestResponse):
            raise Exception('Endpoint returned not an instance of PredictionRequestResponse')
        return json.loads(response.content_str)

    def query_graphl(self, query_string: str):
        response = self.handler.handle_request(
            PredictionRequestResponse(
                content=query_string,
                content_type=const.CONTENT_TYPE_GRAPHQL
            )
        )
        if not isinstance(response, PredictionRequestResponse):
            raise Exception('GRAPHQL endpoint returned not an instance of PredictionRequestResponse')
        return json.loads(response.content_str)

    def query_df(self, df: typing.Union[pd.DataFrame, pd.Series, np.ndarray]):
        result = StringIO()
        scoring_server.predictions_to_json(payload, result)

        return self._parse_response(self.handler.handle_request(
            PredictionRequestResponse(
                content=result.getvalue(),
                content_type=scoring_server.CONTENT_TYPE_JSON
            )
        ))

    def query(self, **kwargs):
        result = StringIO()

        column_names = tuple(kwargs.keys())
        writer = csv.DictWriter(result, fieldnames=column_names)
        writer.writeheader()
        writer.writerow(kwargs)

        return self._parse_response(self.handler.handle_request(
            PredictionRequestResponse(
                content=result.getvalue(),
                content_type=scoring_server.CONTENT_TYPE_CSV
            )
        ))[0]
