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
from io import StringIO

from mlflow.types import Schema
from mlflow.pyfunc import scoring_server

from odahu_mlflow_aws_sdk.inference.sdk.request_response import PredictionRequestResponse
from odahu_mlflow_aws_sdk.inference.sdk.call_processors import CallProcessor, build_processor
from odahu_mlflow_aws_sdk.inference.sdk.flask_handler import FlaskPredictingApp
from odahu_mlflow_aws_sdk.inference import const
from odahu_mlflow_aws_sdk.inference import exceptions
from odahu_mlflow_aws_sdk.utils import graphql as gql
from odahu_mlflow_aws_sdk.utils import json as jut
from odahu_mlflow_aws_sdk.utils import find_dict_value_ignore_case


class BaseModelHandler:
    INPUT_SCHEMA: typing.Optional[Schema] = None
    OUTPUT_SCHEMA: typing.Optional[Schema] = None

    def __init__(
            self,
            call_processor: CallProcessor,
            local_service: bool = False,
            wsgi: bool = False,
            aws_lambda_payload = None
    ):
        self._call_processor: CallProcessor = call_processor
        # AWS Lambda specific case
        self._aws_lambda_event = None
        self._aws_lambda_context = None
        if aws_lambda_payload:
            self._aws_lambda_event, self._aws_lambda_context = aws_lambda_payload

    def pre_process(self, query):
        """
        This function can be implemented to provide custom logic how input query should be "mapped" to
        expected for the model set of values

        :param query: model prediction
        :type query: typing.Union[pd.DataFrame, pd.Series]
        :return: post processed data, ready to be sent to model prediction endpoint
        :rtype: typing.Union[pd.DataFrame, pd.Series]
        """
        return query

    def post_process(self, prediction_response):
        """
        This function can be implemented to provide custom logic how prediction should be "mapped" to the response

        :param prediction_response: model prediction response
        :type prediction_response: typing.Union[pd.DataFrame, pd.Series]
        :return: post processed data
        :rtype: typing.Union[pd.DataFrame, pd.Series]
        """
        return prediction_response

    def validate(self, query):
        """
        This function can be implemented to validate that input query (before pre_process) is valid,
        e.g. values are in expected ranges

        :param query: Query to be validated
        :type query: typing.Union[pd.DataFrame, pd.Series]
        :return: nothing
        :rtype: None
        """
        pass

    def inference(self, prepared_query):
        return self._call_processor.call(prepared_query)

    def predict(self, values):
        """
        Run a prediction chain

        :param values:
        :return:
        """
        # Validate values
        self.validate(values)
        # Pre-process values
        prepared_query = self.pre_process(values)
        # Call prediciton function
        prediction_response = self.inference(prepared_query)
        # Return post-processed value
        return self.post_process(prediction_response)

    def predict_graphql(self, _, _1, **kwargs):
        """
        Handle execution of the graphql query.
        This function:
        - casts to the dataframe
        - invokes predict
        - casts back to the dict
        :param kwargs: dict -- request
        :return: dict -- response
        """
        data = scoring_server.parse_json_input(
            json_input=StringIO(json.dumps([kwargs])), # TODO: Optimize
            orient="records",
            schema=self.INPUT_SCHEMA,
        )
        try:
            raw_predictions = self.predict(data)
        except exceptions.InvalidModelInputException:
            raise
        except Exception as predicting_exception:
            raise Exception('Unable to make a prediction') from predicting_exception
        return jut.to_single_object_json(raw_predictions, self.OUTPUT_SCHEMA)

    def handle_request(self, request: PredictionRequestResponse) -> PredictionRequestResponse:
        if not self.INPUT_SCHEMA:
            raise Exception('Schema is not set for the handler')

        if request.content_type == const.CONTENT_TYPE_GRAPHQL:
            if not self.OUTPUT_SCHEMA:
                raise Exception('Output schema should be set for graphql handler')
            graphql_schema = gql.build_invocation_schema(self.INPUT_SCHEMA, self.OUTPUT_SCHEMA, self.predict_graphql)
            response = gql.execute_graphql_query(request.content_str, graphql_schema)
            return PredictionRequestResponse(
                content=json.dumps(response.data),
                content_type=scoring_server.CONTENT_TYPE_JSON
            )
        # Code below is copied from the mlflow
        elif request.content_type == scoring_server.CONTENT_TYPE_CSV:
            csv_input = StringIO(request.content_str)
            data = scoring_server.parse_csv_input(csv_input=csv_input)
        elif request.content_type == scoring_server.CONTENT_TYPE_JSON:
            data = scoring_server.infer_and_parse_json_input(request.content_str, self.INPUT_SCHEMA)
        elif request.content_type == scoring_server.CONTENT_TYPE_JSON_SPLIT_ORIENTED:
            data = scoring_server.parse_json_input(
                json_input=StringIO(request.content_str),
                orient="split",
                schema=self.INPUT_SCHEMA,
            )
        elif request.content_type == scoring_server.CONTENT_TYPE_JSON_RECORDS_ORIENTED:
            data = scoring_server.parse_json_input(
                json_input=StringIO(request.content_str),
                orient="records",
                schema=self.INPUT_SCHEMA,
            )
        elif request.content_type == scoring_server.CONTENT_TYPE_JSON_SPLIT_NUMPY:
            data = scoring_server.parse_split_oriented_json_input_to_numpy(request.content_str)
        else:
            raise NotImplementedError(f'Not implemented yet for content type {request.content_type}')

        # Process response
        try:
            raw_predictions = self.predict(data)
            result = StringIO()
            scoring_server.predictions_to_json(raw_predictions, result)
            # Return
            return PredictionRequestResponse(
                content=result.getvalue(),
                content_type=scoring_server.CONTENT_TYPE_JSON
            )
        except exceptions.InvalidModelInputException:
            raise
        except Exception as predicting_exception:
            raise Exception('Unable to make a prediction') from predicting_exception

    def build_flask_app(self):
        app = FlaskPredictingApp(self.handle_request)
        return app

    @classmethod
    def start_local_service(cls):
        handler = cls(build_processor())
        app = handler.build_flask_app()
        return app.run()

    @classmethod
    def wsgi_handler(cls):
        handler = cls(build_processor())
        return handler.build_flask_app().app

    def handle_lambda_for_kinesis_data_firehose(self, event, context):
        # TODO: Implement Kinesis Data Firehose stream prediction
        raise NotImplementedError('Support for Kinesis Data Firehose is not implemented yet')

    def handle_lambda_for_api_gateway_or_load_balancer(self, event, context):
        method = event.get('httpMethod')
        body = event.get('body')
        is_base64_encoded = event.get('isBase64Encoded')
        headers = event.get('headers', {})
        # TODO: Restore multi-value handlers
        # headers.update(event.get('multiValueHeaders', {}))

        # Validate
        if method != 'POST':
            raise Exception('Only POST HTTP requests are supported')
        if not body:
            raise Exception('POST HTTP Request does not contain a body')
        if is_base64_encoded:
            # TODO: Add Bas64 encoding of body
            raise Exception('BASE64 Encoding of body is not yet supported')
        # Parse AWS Lambda event object and build request object
        request = PredictionRequestResponse(
            content=body,
            content_type=find_dict_value_ignore_case(headers, 'content-type', default=None, validate_type=str)
        )
        try:
            # Generate an output for input
            response = self.handle_request(request)
            # Return response
            return {
                'statusCode': 200,
                'headers': response.as_headers,
                'body': response.content_str
            }
        except exceptions.InvalidModelInputException as input_exception:
            return {
                'statusCode': 400, # Bad Request
                'headers': {},
                'body': str(input_exception)
            }
        except Exception as general_exception:
            return {
                'statusCode': 500, # Server error
                'headers': {},
                'body': str(general_exception)
            }

    @classmethod
    def handle_lambda(cls, event, context):
        """
        Handler for the AWS lambda call
        :param event:
        :param context:
        :return:
        """
        handler = cls(build_processor(), aws_lambda_payload=(event, context))
        if isinstance(event, dict):
            event_keys = set(event.keys())
            if const.AWS_LAMBDA_KINESIS_DATA_FIREHOSE_KEYS.issubset(event_keys):
                return handler.handle_lambda_for_kinesis_data_firehose(event, context)
            elif const.AWS_LAMBDA_API_GATEWAY_OR_LOAD_BALANCER.issubset(event_keys):
                return handler.handle_lambda_for_api_gateway_or_load_balancer(event, context)

        raise Exception(
            'Unsupported event object has been received, this Lambda function can be used only with: '
            'AWS API Gateway, AWS ELB/ALB & AWS Kinesis Data Firehose'
        )
