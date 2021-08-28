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
Constants declaration
"""

# Default location where to find inference code
DEFAULT_INFERENCE_SERVICE_FOLDER = 'ml_service'

# Expected name of the file and function inside
LAMBDA_FUNCTION_FILE_NAME = 'lambda_function.py'
LAMBDA_FUNCTION_FILE_CODE = 'lambda_function'
LAMBDA_FUNCTION_FUNCTION_NAME = 'lambda_handler'
LAMBDA_FUNCTION_HANDLER = f'{LAMBDA_FUNCTION_FILE_CODE}.{LAMBDA_FUNCTION_FUNCTION_NAME}'

LAMBDA_FUNCTION_TAG = 'type', 'mlflow-aws-model-handler'

# Name of the folder inside MLFlow model
MLFLOW_MODEL_INFERENCE_FOLDER = 'inference_service'

# Model endpoint env variable shows where to load
MODEL_ENDPOINT_ENV = 'MODEL_ENDPOINT_ENV'


CONTENT_TYPE_GRAPHQL = 'application/graphql'


AWS_LAMBDA_KINESIS_DATA_FIREHOSE_KEYS = {'invocationId', 'deliveryStreamArn', 'records'}
AWS_LAMBDA_API_GATEWAY_OR_LOAD_BALANCER = {'requestContext', 'httpMethod', 'headers', 'body'}

SERVER_PORT = ('SERVER_PORT', 9000)
