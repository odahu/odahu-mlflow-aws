
from .mlflow import mlflow_cli as mlflow_cli_g
from .models import models as models_g
from .config import config as config_g
from .sagemaker import sagemaker as sagemaker_g
from .lambda_func import lambda_func as lambda_func_g
from .deploy import deploy as deploy_g

ALL_GROUPS = (
    mlflow_cli_g,
    models_g,
    config_g,
    sagemaker_g,
    lambda_func_g,
    deploy_g
)