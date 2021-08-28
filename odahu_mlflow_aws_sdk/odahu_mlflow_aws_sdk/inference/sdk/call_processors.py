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
import urllib3
import sys
import os
import json
from io import StringIO

from mlflow.pyfunc import scoring_server

from odahu_mlflow_aws_sdk.inference import const
from .encoding import EncodedDataInformation, EncoderType


class CallProcessor:
    """
    Call processor is responsible for sending prepared data to the model (over HTTP / AWS SageMaker API / in memory)
    """
    ENCODING_ENABLED = True

    def encode_data(self, payload: object, encoder: EncoderType = EncoderType.JSON) -> EncodedDataInformation:
        if encoder == EncoderType.JSON:
            result = StringIO()
            scoring_server.predictions_to_json(payload, result)
            return EncodedDataInformation(
                payload=result.getvalue(),
                content_type=scoring_server.CONTENT_TYPE_JSON
            )
        else:
            raise ValueError(f'Unknown encoder: {encoder}')

    def call(self, payload, encoder: EncoderType = EncoderType.JSON) -> object:
        if self.ENCODING_ENABLED:
            # Encode data
            encoded_data = self.encode_data(payload, encoder=encoder)
            # Return decoded data (for this encoder)
            return self.process_call(
                payload,
                encoder,
                encoded_data
            )
        else:
            return self.process_call(payload, EncoderType.NONE, None)

    def process_call(
            self,
            payload,
            encoder: EncoderType,
            encoded_data: typing.Optional[EncodedDataInformation]
    ) -> bytes:
        raise NotImplementedError('process_call should be implemented in the final class')


class InMemoryCallProcessor(CallProcessor):
    ENCODING_ENABLED = False

    def __init__(self, py_model):
        self.py_model = py_model

    def process_call(self, payload, encoder, encoded_data) -> object:
        return self.py_model.predict(payload)


class HttpModelCallProcessor(CallProcessor):
    def __init__(self, endpoint_name):
        self._endpoint_name = endpoint_name
        self._pool = urllib3.PoolManager()

    def process_call(self, payload, encoder, encoded_data) -> object:
        response = self._pool.request(
            'POST',
            self._endpoint_name,
            headers={
                'Content-Type': encoded_data.content_type
            },
            body=encoded_data.payload,
            preload_content=False
        )
        return json.loads(response.data)


class SageMakerCallProcessor(CallProcessor):
    def __init__(self, endpoint_name):
        try:
            import boto3
        except Exception as boto3_import_exception:
            raise Exception('Unable to load boto3 library') from boto3_import_exception
        boto3 = sys.modules['boto3']

        self._runtime = boto3.client('runtime.sagemaker')
        self._endpoint_name = endpoint_name

    def process_call(self, payload, encoder, encoded_data):
        # Invoke sagemaker API
        response = self._runtime.invoke_endpoint(
            EndpointName=self._endpoint_name,
            ContentType=encoded_data.content_type,
            Body=encoded_data.payload
        )
        return json.loads(response['Body'].read())


def build_processor(endpoint=os.getenv(const.MODEL_ENDPOINT_ENV)) -> CallProcessor:
    """
    Build appropriate processor.
    For in memory models processor should be built manually

    :param endpoint: endpoint
    :return: CallProcessor
    """
    if not endpoint:
        raise Exception('Model endpoint is not set')
    if endpoint.startswith('http'):
        return HttpModelCallProcessor(endpoint)
    else:
        return SageMakerCallProcessor(endpoint)
