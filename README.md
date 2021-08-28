# ODAHU MLflow AWS

ODAHU MLflow AWS is a SDK and CLI tool for easy management and deployment of 
pre-processing, validation and post-processing steps for models, packaged using 
[MLflow](https://mlflow.org/) SDK.

In most cases during model development you need to do extra development 
and management of a code for the inference API:

1. Development of a pre-processing logic for transforming an API input to the 
   format model expect to consume.

   For instance: ML model will not recognize name of the car brand (like "Toyota"). ML model expects this to be a number, or set of numbers 
   (in case of the one-hot feature encoding).

2. Development of a validation logic for input data to protect the model agains 
   corrupted or incorrect data.

   For instance: model for predicting wine quality can expect density only 
   in range of (0;1). Values like -1.2 should be considered as invalid and 
   prediction request must be declined with a proper error.

3. Development of a post-processing for transforming an output of a model 
   prediction to a way consumers can recognize.

   For instance: model for predicting wine quality can return values 
   in a range [4;6], but for consumers getting categorical labels like
   a "good" or "bad" string might be more meaningful.

4. Development of a code for deploying a frontend in front of your model
   API. 

   For instance: you want to grant an access to your model by providing API
   keys for consumers.

5. Development of a CLI tool for managing infromation about models and 
   deploying models & inference logic in a cloud / locally.

6. Development of API interfaces in an easy for use API protocols,
   for instance [GraphQL](https://graphql.org/).


This SDK solves problems listed above on an AWS platform using next approaches:

1. Pre-processing, validation and post-processing logic can be implemented
   as a set of Python class functions, SDK invokes them during execution
   of an API request.

   Example: https://github.com/odahu/odahu-mlflow-aws-example/blob/develop/ml_service/lambda_function.py#L83-L128

2. [Providing wrappers](https://github.com/odahu/odahu-mlflow-aws-example/blob/develop/ml_service/lambda_function.py) for pre-processing, validation and post-processing logic
   for different deployment types:
   
   * AWS Lambda function (API Gateway backend, load balancer backend, AWS Kinesis data firehose backend)
   * [Deploying in a Docker container](https://github.com/odahu/odahu-mlflow-aws-example/blob/develop/ml_service/lambda_function.py#L146-L147) using wsgi compatible servers (like gunicorn)
   * [Local execution using python](https://github.com/odahu/odahu-mlflow-aws-example/blob/develop/ml_service/lambda_function.py#L142-L144)
   * [Local execution during testing](https://github.com/odahu/odahu-mlflow-aws-example/blob/develop/ml_training/train.py#L120-L170)

3. [Providing python function](https://github.com/odahu/odahu-mlflow-aws-example/blob/develop/ml_training/train.py#L78-L79) to invoke for inference code saving.

3. Providing easy to use CLI for deploying and managing models.

## Requirements

1. Python 3.8+ (inference processing code will be executed using Python 3.8, 
   can be customized).

2. [Conda](https://conda.io/projects/conda/en/latest/user-guide/install/index.html).

3. AWS Credentials stored in a credentials file.

4. AWS Project to store data and deploy model in.

5. Running MLFlow Tracking and Model Registry server 
   (local server can be run during testing and development, 
   see instructions below - environment preparation section).
## Installation (for development)

1. Clone this repository.

2. Create and activate virtual env `python3.8 -m venv .venv && source .venv/bin/activate`.

3. Go to `odahu_mlflow_aws_sdk` folder and run `python setup.py develop`. 

## Installation (from PYPI)

1. `pip install odahu-mlflow-aws-sdk` (is not published yet)

## Environment preparation

1. For model serving in a SageMaker you need to have compatible Docker image
   stored in AWS ECR.
   
   You can build this image using command `mlflow sagemaker build-and-push-container`.

2. For inference code serving in a Lambda function you need to have compatible
   Lambda Layer with all requirements.

   You can build this function using command `make build-push-dependencies-layer`, 
   only one requirement is to set env. variable `S3_LOCATION` or put in the `.env` file.
   This variable should contain name of the AWS S3 bucket to store AWS Lambda Layer in.

3. If you don't have deployed MLflow server - you can using docker compose 
   deploy it locally (`docker-compose up -d`), only one requirement is to set env. variable `AWS_ARTIFACTS_BUCKET` or put in the `.env` file. 
   This variable should contain name of the AWS S3 bucket to store MLflow models in.

## Models customization

1. Inference code should be located in the dedicated folder (usually named `ml_service`) and should contain:

   1. Subclass of a class `odahu_mlflow_aws_sdk.inference.sdk.BaseModelHandler` with:

      1. `INPUT_SCHEMA` and `OUTPUT_SCHEMA` of type `mlflow.types.Schema` - these fields control how incoming data should be parsed and outcoming data should be transformed.

         [Example](https://github.com/odahu/odahu-mlflow-aws-example/blob/develop/ml_service/lambda_function.py#L64-L81)

      2. (Optiona) Implementation of `pre_process`, `post_process` and `validate` functions.

         [Example](https://github.com/odahu/odahu-mlflow-aws-example/blob/develop/ml_service/lambda_function.py#L83-L128)

    2. Block with exporting of this new created class as a function named `lambda_handler`, a local runner for this class and a WSGI handler.

       [Example](https://github.com/odahu/odahu-mlflow-aws-example/blob/develop/ml_service/lambda_function.py#L131-L147)

2. Model training code should invoke function `odahu_mlflow_aws_sdk.inference.save_inference_logic` to persist 
   inference code. If this function is invoked not in a scope of `mlflow.start_run` - extra arguments should be provided.

   [Example](https://github.com/odahu/odahu-mlflow-aws-example/blob/develop/ml_training/train.py#L78-L79)

3. (Optional) Model inference code can be tested locally, using a test handler.
   This handler imports inference handling logic in a current context and
   provides an API to call to get predictions.

   [Example](https://github.com/odahu/odahu-mlflow-aws-example/blob/develop/ml_training/train.py#L111-L170)

## CLI

CLI (`odahu-mlflow-aws`) provies different commands for easy process of model and inference code management:

*  `config`     Manage configuration
*  `deploy`     Deploy model (SageMaker, AWS Lambda, API Gateway)
*  `lambda`     Deploy & manage lambda for pre processing
*  `mlflow`     Run original mlflow command
*  `models`     Manage available models
*  `sagemaker`  Deploy & manage models, deployed in sagemaker

Documentation can be provided by using `--help` option for the command.

To deploy your model from the model registry you just need to run a command
`odahu-mlflow-aws deploy -m models:/wine-quality-prediction/production` where `-m` is a MLflow URI of your model (run IDs can not be used).

## Configuration

Deployment process depends alot on the environment configuration,
so to adapt deployment process and to not provide arguments on every call you can use built in configuration storage. 

CLI tool uses a file named `.odahu-mlflow-aws` in your home directory (or path provided in a `ODAHU_MLFLOW_AWS_CONFIG` env variable) as a place to store configuration in a INI format.

You can easily manage your configuration using:

* `config list` command - to get all (default and explicitly set) values
* `config set <key> <value>` command - to set a config value and update a file
* `config location` command - to get location of a config file in use
* `config unset <key>` command - to reset a config value to the default (and remove from the file)
* `config get-value <key>` command - to get a value (default or explicitly set) for a key

Example of real configuration:
```
> odahu-mlflow-aws config list
RETRY_ATTEMPTS: 3
BACKOFF_FACTOR: 1
DEBUG: False
MAX_TABLE_WIDTH: 193
MLFLOW_TRACKING_URI: 'http://localhost:5000/'
DEFAULT_SAGEMAKER_INSTANCE_TYPE: 'ml.m4.xlarge'
DEFAULT_SAGEMAKER_INSTANCE_COUNT: 1
DEFAULT_SAGEMAKER_REGION: 'us-east-1' (default: 'us-west-1')
DEFAULT_SAGEMAKER_EXECUTION_ROLE_ARN: 'arn:aws:iam::57xxxxxxxxxxx5:role/SageMakerExecutionPolicy' (default: None)
DEFAULT_SAGEMAKER_S3_MODELS_ARTIFACT: 'xxxxx-mlflow-sagemaker' (default: None)
DEFAULT_SAGEMAKER_INFERENCE_IMAGE: '57xxxxxxxxxxx5.dkr.ecr.us-east-1.amazonaws.com/mlflow-pyfunc:1.19.0' (default: None)
DEFAULT_SAGEMAKER_DELOY_TIMEOUT: 1200
DEFAULT_SAGEMAKER_VPC_CONFIG: None
DEFAULT_SAGEMAKER_VPC_SECURITY_GROUPS: ()
DEFAULT_SAGEMAKER_VPC_SUBNETS: ()
DEFAULT_SAGEMAKER_LOCAL_RUN_PORT: 5005
DEFAULT_LAMBDA_ARN: 'arn:aws:iam::57xxxxxxxxxxx5:role/AWSLambdaInvocationRoleWithSageMaker' (default: '')
DEFAULT_LAMBDA_LAYERS: ['arn:aws:lambda:us-east-1:57xxxxxxxxxxx5:layer:MlFlowPythonDependencies:7'] (default: ())
DEFAULT_LAMBDA_RAM: 256
DEFAULT_LAMBDA_RUNTIME: 'python3.8'
DEFAULT_LAMBDA_TIMEOUT: 120
DEFAULT_API_GATEWAY_ID: 't9xxxxxxc' (default: None)
DEFAULT_API_GATEWAY_STAGE: 'prod' (default: None)
DEFAULT_API_GATEWAY_AUTHORIZATION: 'exxxx2' (default: None)
DEFAULT_API_GATEWAY_LAMBDA_CALL_ROLE: 'arn:aws:iam::57xxxxxxxxxxx5:role/ApiGatewayLogPush' (default: None)
```

All available configuration values are listed in a file [odahu_mlflow_aws_sdk/odahu_mlflow_aws_sdk/config.py](odahu_mlflow_aws_sdk/odahu_mlflow_aws_sdk/config.py)

## Tutorial

1. Add a folder with [an inference code](https://github.com/odahu/odahu-mlflow-aws-example/blob/develop/ml_service) (without postman_collection.json)

2. Add `odahu_mlflow_aws_sdk.inference.save_inference_logic` in your model training script,
   if name of you folder is not a `ml_service` - provide an argument with a path to the folder.

3. Train you model.

4. Using `odahu-mlflow-aws models list` validate that your model has been saved by the MLflow Model Registry server.

```
$> odahu-mlflow-aws models list
      Model Name          Tags           Created at                   Updated at           Latest versions
----------------------------------------------------------------------------------------------------------
wine-quality-prediction          2021-08-27T21:05:15.813000   2021-08-27T21:06:06.767000   Latest: 1      
                                                                                           Production: 2 
```

5. (Optional) Move your model to the "staging" or "production" stage.

6. Using `odahu-mlflow-aws deploy -m models:/<model name>/<version or stage name>` deploy your model.

```
$> odahu-mlflow-aws deploy -m models:/wine-quality-prediction/production                                                   
Staring model deploying algo
2021/08/27 17:36:02 INFO mlflow.sagemaker: Using the python_function flavor for deployment!
2021/08/27 17:36:03 INFO mlflow.sagemaker: Found active endpoint with arn: arn:aws:sagemaker:us-east-1:57xxxxxxxxxxx5:endpoint/wine-quality-prediction. Updating...
2021/08/27 17:36:04 INFO mlflow.sagemaker: Created new model with arn: arn:aws:sagemaker:us-east-1:57xxxxxxxxxxx5:model/wine-quality-prediction-model-jqjw74qis7ywtcodc4bj5g
2021/08/27 17:36:04 INFO mlflow.sagemaker: Created new endpoint configuration with arn: arn:aws:sagemaker:us-east-1:57xxxxxxxxxxx5:endpoint-config/wine-quality-prediction-config-xerbm6obs6kj44sxfjnyvg
2021/08/27 17:36:04 INFO mlflow.sagemaker: Updated endpoint with new configuration!
2021/08/27 17:36:04 INFO mlflow.sagemaker: Waiting for the deployment operation to complete...
2021/08/27 17:36:04 INFO mlflow.sagemaker: The operation is still in progress.
2021/08/27 17:36:25 INFO mlflow.sagemaker: The update operation is still in progress. Current endpoint status: "Updating"
2021/08/27 17:36:45 INFO mlflow.sagemaker: The update operation is still in progress. Current endpoint status: "Updating"
2021/08/27 17:37:06 INFO mlflow.sagemaker: The update operation is still in progress. Current endpoint status: "Updating"
2021/08/27 17:37:26 INFO mlflow.sagemaker: The update operation is still in progress. Current endpoint status: "Updating"
2021/08/27 17:37:47 INFO mlflow.sagemaker: The update operation is still in progress. Current endpoint status: "Updating"
2021/08/27 17:38:07 INFO mlflow.sagemaker: The update operation is still in progress. Current endpoint status: "Updating"
2021/08/27 17:38:27 INFO mlflow.sagemaker: The update operation is still in progress. Current endpoint status: "Updating"
2021/08/27 17:38:48 INFO mlflow.sagemaker: The update operation is still in progress. Current endpoint status: "Updating"
2021/08/27 17:39:09 INFO mlflow.sagemaker: The update operation is still in progress. Current endpoint status: "Updating"
2021/08/27 17:39:29 INFO mlflow.sagemaker: The update operation is still in progress. Current endpoint status: "Updating"
2021/08/27 17:39:50 INFO mlflow.sagemaker: The update operation is still in progress. Current endpoint status: "Updating"
2021/08/27 17:40:10 INFO mlflow.sagemaker: The update operation is still in progress. Current endpoint status: "Updating"
2021/08/27 17:40:31 INFO mlflow.sagemaker: The update operation is still in progress. Current endpoint status: "Updating"
2021/08/27 17:40:51 INFO mlflow.sagemaker: The update operation is still in progress. Current endpoint status: "Updating"
2021/08/27 17:41:12 INFO mlflow.sagemaker: The update operation is still in progress. Current endpoint status: "Updating"
2021/08/27 17:41:32 INFO mlflow.sagemaker: The update operation is still in progress. Current endpoint status: "Updating"
2021/08/27 17:41:53 INFO mlflow.sagemaker: The update operation is still in progress. Current endpoint status: "Updating"
2021/08/27 17:42:13 INFO mlflow.sagemaker: The update operation is still in progress. Current endpoint status: "Updating"
2021/08/27 17:42:34 INFO mlflow.sagemaker: The update operation is still in progress. Current endpoint status: "Updating"
2021/08/27 17:42:54 INFO mlflow.sagemaker: The update operation is still in progress. Current endpoint status: "Updating"
2021/08/27 17:43:15 INFO mlflow.sagemaker: The update operation is still in progress. Current endpoint status: "Updating"
2021/08/27 17:43:35 INFO mlflow.sagemaker: The update operation is still in progress. Current endpoint status: "Updating"
2021/08/27 17:43:56 INFO mlflow.sagemaker: The update operation is still in progress. Current endpoint status: "Updating"
2021/08/27 17:44:16 INFO mlflow.sagemaker: The update operation is still in progress. Current endpoint status: "Updating"
2021/08/27 17:44:27 INFO mlflow.sagemaker: The deployment operation completed successfully with message: "The SageMaker endpoint was updated successfully."
2021/08/27 17:44:27 INFO mlflow.sagemaker: Cleaning up unused resources...
2021/08/27 17:44:27 INFO mlflow.sagemaker: Deleted endpoint configuration with arn: arn:aws:sagemaker:us-east-1:57xxxxxxxxxxx5:endpoint-config/wine-quality-prediction-config-qzlablfbdtabsvbyhjyjbkeg
Updating code of exisitng function 'wine-quality-prediction-invocation'
Function wine-quality-prediction-invocation has been updated
arn:aws:lambda:us-east-1:57xxxxxxxxxxx5:function:wine-quality-prediction-invocation:3
```

7. Query over HTTP (using JSON / GraphQL / CSV) your model, you can use [a prebuilt Postman collection](https://github.com/odahu/odahu-mlflow-aws-example/blob/develop/ml_service/AWS.postman_collection.json).

## Example model

You can take [a wine quality model](https://github.com/odahu/odahu-mlflow-aws-example/tree/develop) as an example.