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
import os

from flask import Flask, Response, request

from odahu_mlflow_aws_sdk.inference.sdk.request_response import PredictionRequestResponse
from odahu_mlflow_aws_sdk.inference import const
from odahu_mlflow_aws_sdk.inference import exceptions

PREDICTOR_TYPE = typing.Callable[[PredictionRequestResponse], PredictionRequestResponse]


class FlaskPredictingApp:
    """
    Flask app for running inference pre, post and validation logic locally (or in the Docker)
    """

    def __init__(self, predictor: PREDICTOR_TYPE):
        self.app = Flask('predictingApp')
        self.predictor = predictor

        self.app.add_url_rule('/', endpoint='root', methods=('POST',), view_func=self.handle_request)

    def handle_request(self):
        model_request = PredictionRequestResponse(
            content=request.get_data(),
            content_type=request.content_type
        )
        try:
            model_response = self.predictor(model_request)
            return Response(
                status=200,
                response=model_response.content_str,
                headers=model_response.as_headers
            )
        except exceptions.InvalidModelInputException as input_exception:
            return Response(
                status=400,
                response=str(input_exception),
                headers={}
            )
        except Exception as general_exception:
            return Response(
                status=500,
                response=str(general_exception),
                headers={}
            )

    def run(self):
        port = os.getenv(*const.SERVER_PORT)
        return self.app.run(port=port)