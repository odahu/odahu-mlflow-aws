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
Configuration module
Original: https://github.com/odahu/odahu-flow/blob/develop/packages/sdk/odahuflow/sdk/config.py
"""
import configparser
import logging
import os
from pathlib import Path

# Get list of all variables

ALL_VARIABLES = {}

_LOGGER = logging.getLogger()

_INI_FILE_TRIED_TO_BE_LOADED = False
_INI_FILE_CONTENT: configparser.ConfigParser = None
_INI_FILE_DEFAULT_CONFIG_PATH = Path.home().joinpath('.odahu-mlflow-aws')
_DEFAULT_INI_SECTION = 'general'


def reset_context():
    """
    Reset configuration context
    :return: None
    """
    global _INI_FILE_TRIED_TO_BE_LOADED
    global _INI_FILE_CONTENT

    _INI_FILE_TRIED_TO_BE_LOADED = False
    _INI_FILE_CONTENT = None


def get_config_file_path():
    """
    Return the config path.
    ODAHU_MLFLOW_AWS_CONFIG environment can override path value
    :return: Path -- config path
    """
    config_path_from_env = os.getenv('ODAHU_MLFLOW_AWS_CONFIG')

    return Path(config_path_from_env) if config_path_from_env else _INI_FILE_DEFAULT_CONFIG_PATH


def _load_config_file():
    """
    Load configuration file if it has not been loaded. Update _INI_FILE_TRIED_TO_BE_LOADED, _INI_FILE_CONTENT
    :return: None
    """
    global _INI_FILE_TRIED_TO_BE_LOADED

    if _INI_FILE_TRIED_TO_BE_LOADED:
        return

    config_path = get_config_file_path()
    _INI_FILE_TRIED_TO_BE_LOADED = True

    _LOGGER.debug('Trying to load configuration file {}'.format(config_path))

    try:
        if config_path.exists():
            config = configparser.ConfigParser()
            config.read(str(config_path))

            global _INI_FILE_CONTENT
            _INI_FILE_CONTENT = config

            _LOGGER.debug('Configuration file {} has been loaded'.format(config_path))
        else:
            _LOGGER.debug('Cannot find configuration file {}'.format(config_path))
    except Exception as exc:
        _LOGGER.exception('Cannot read config file {}'.format(config_path), exc_info=exc)


def get_config_file_section(section=_DEFAULT_INI_SECTION, silent=False):
    """
    Get section from config file
    :param section: (Optional) name of section
    :type section: str
    :param silent: (Optional) ignore if there is no file
    :type silent: bool
    :return: dict[str, str] -- values from section
    """
    _load_config_file()
    if not _INI_FILE_CONTENT:
        if silent:
            return dict()
        else:
            raise Exception('Configuration file cannot be loaded')

    if not _INI_FILE_CONTENT.has_section(section):
        return {}

    return dict(_INI_FILE_CONTENT[section])


def get_config_file_variable(variable, section=_DEFAULT_INI_SECTION):
    """
    Get variable by name from specific (or default) section
    :param variable: Name of variable
    :type variable: str
    :param section: (Optional) name of section
    :type section: str
    :return: str or None -- value
    """
    if not variable:
        return None

    _load_config_file()
    if not _INI_FILE_CONTENT:
        return None

    return _INI_FILE_CONTENT.get(section, variable, fallback=None)


def update_config_file(section=_DEFAULT_INI_SECTION, **new_values):
    """
    Update config file with new values
    :param section: (Optional) name of section to update
    :type section: str
    :param new_values: new values
    :type new_values: dict[str, typing.Optional[str]]
    :return: None
    """
    global _INI_FILE_TRIED_TO_BE_LOADED
    global _INI_FILE_CONTENT

    _load_config_file()
    config_path = get_config_file_path()

    content = _INI_FILE_CONTENT if _INI_FILE_CONTENT else configparser.ConfigParser()

    config_path.parent.mkdir(mode=0o775, parents=True, exist_ok=True)
    config_path.touch(mode=0o600, exist_ok=True)

    if not content.has_section(section):
        content.add_section(section)

    for key, value in new_values.items():
        if value:
            content.set(section, key, value)
        else:
            if section in content and key in content[section]:
                del content[section][key]

    with config_path.open('w') as config_file:
        content.write(config_file)

    _INI_FILE_TRIED_TO_BE_LOADED = True
    _INI_FILE_CONTENT = content

    reinitialize_variables()

    _LOGGER.debug('Configuration file {} has been updated'.format(config_path))


def _load_variable(name, cast_type=None, configurable_manually=True):
    """
    Load variable from config file, env. Cast it to desired type.
    :param name: name of variable
    :type name: str
    :param cast_type: (Optional) function to cast
    :type cast_type: Callable[[str], any]
    :param configurable_manually: (Optional) could this variable be configured manually or not
    :type configurable_manually: bool
    :return: Any -- variable value
    """
    value = None

    # 1st level - configuration file
    if configurable_manually:
        conf_value = get_config_file_variable(name)
        if conf_value:
            value = conf_value

    # 2nd level - env. variable
    env_value = os.environ.get(name)
    if env_value:
        value = env_value

    return cast_type(value) if value is not None else None


class ConfigVariableInformation:
    """
    Object holds information about variable (name, default value, casting function, description and etc.)
    """

    def __init__(self, name, default, cast_func, description, configurable_manually):
        """
        Build information about variable
        :param name: name of variable
        :type name: str
        :param default: default value
        :type default: Any
        :param cast_func: cast function
        :type cast_func: Callable[[str], any]
        :param description: description
        :type description: str
        :param configurable_manually: is configurable manually
        :type configurable_manually: bool
        """
        self._name = name
        self._default = default
        self._cast_func = cast_func
        self._description = description
        self._configurable_manually = configurable_manually

    @property
    def name(self):
        """
        Get name of variable
        :return: str -- name
        """
        return self._name

    @property
    def default(self):
        """
        Get default variable value
        :return: Any -- default value
        """
        return self._default

    @property
    def cast_func(self):
        """
        Get cast function (from string to desired type)
        :return: Callable[[str], any] -- casting function
        """
        return self._cast_func

    @property
    def description(self):
        """
        Get human-readable description
        :return: str -- description
        """
        return self._description

    @property
    def configurable_manually(self):
        """
        Is this variable human-configurabe?
        :return: bool -- is human configurable
        """
        return self._configurable_manually


def cast_bool(value):
    """
    Convert string to bool
    :param value: string or bool
    :type value: str or bool
    :return: bool
    """
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    return value.lower() in ['true', '1', 't', 'y', 'yes']


def cast_list_of_strings(value):
    """
    Convert string to list of strings
    :param value: string
    :type value: str or bool
    :return: bool
    """
    if value is None:
        return None

    if isinstance(value, (list, tuple)):
        return value

    return value.split(',')

def reinitialize_variables():
    """
    Reinitialize variables due to new ENV variables
    :return: None
    """
    for value_information in ALL_VARIABLES.values():
        explicit_value = _load_variable(value_information.name,
                                        value_information.cast_func,
                                        value_information.configurable_manually)
        value = explicit_value if explicit_value is not None else value_information.default

        globals()[value_information.name] = value


class ConfigVariableDeclaration:
    """
    Class that builds declaration of variable (and returns it's value as an instance)
    """

    def __new__(cls, name, default=None, cast_func=str, description=None, configurable_manually=True):
        """
        Create new instance
        :param name: name of variable
        :type name: str
        :param default: (Optional) default variable value [will not be passed to cast_func]
        :type default: Any
        :param cast_func: (Optional) cast function for variable value
        :type cast_func: Callable[[str], any]
        :param description: (Optional) human-readable variable description
        :type description: str
        :param configurable_manually: (Optional) can be modified by config file or CLI
        :type configurable_manually: bool
        :return: Any -- default or explicit value
        """
        information = ConfigVariableInformation(name, default, cast_func, description, configurable_manually)

        explicit_value = _load_variable(name, cast_func, configurable_manually)
        value = explicit_value if explicit_value is not None else default
        ALL_VARIABLES[information.name] = information
        return value


##################################################################################################################
#                                            Variables                                                           #
##################################################################################################################

# Transport (HTTP)

RETRY_ATTEMPTS = ConfigVariableDeclaration(
    'RETRY_ATTEMPTS', 3, int,
    'How many retries HTTP client should make in case of transient error', True
)

BACKOFF_FACTOR = ConfigVariableDeclaration(
    'BACKOFF_FACTOR', 1, int,
    'Backoff factor for retries (See https://urllib3.readthedocs.io/en/latest/reference/urllib3.util.html)', True
)

# Verbose tracing
DEBUG = ConfigVariableDeclaration('DEBUG', False, cast_bool,
                                  'Enable verbose program output',
                                  True)

# Formatting
try:
    terminal_size = os.get_terminal_size()
    _default_max_table_width = terminal_size.columns.real
except Exception:
    _default_max_table_width = 230

MAX_TABLE_WIDTH = ConfigVariableDeclaration(
    'MAX_TABLE_WIDTH', _default_max_table_width, int,
    'Max width of the output table in console', True
)

# MLFlow Config
MLFLOW_TRACKING_URI = ConfigVariableDeclaration(
    'MLFLOW_TRACKING_URI', 'http://localhost:5000/', str, 'MLFlow Tracking URL', True
)

# AWS SageMaker config

DEFAULT_SAGEMAKER_INSTANCE_TYPE = ConfigVariableDeclaration(
    'DEFAULT_SAGEMAKER_INSTANCE_TYPE', 'ml.m4.xlarge', str,
    'Default shape for the sagemaker instance', True
)

DEFAULT_SAGEMAKER_INSTANCE_COUNT = ConfigVariableDeclaration(
    'DEFAULT_SAGEMAKER_INSTANCE_COUNT', 1, int,
    'Default count of instances for the sagemaker model deployment'
)

DEFAULT_SAGEMAKER_REGION = ConfigVariableDeclaration(
    'DEFAULT_SAGEMAKER_REGION', 'us-west-1', str,
    'Default region where to deploy SageMaker model', True
)

DEFAULT_SAGEMAKER_EXECUTION_ROLE_ARN = ConfigVariableDeclaration(
    'DEFAULT_SAGEMAKER_EXECUTION_ROLE_ARN', None, str,
    'Execution role for AWS SageMaker', True
)

DEFAULT_SAGEMAKER_S3_MODELS_ARTIFACT = ConfigVariableDeclaration(
    'DEFAULT_SAGEMAKER_S3_MODELS_ARTIFACT', None, str,
    'Default S3 bucket name for model artifacts', True
)

DEFAULT_SAGEMAKER_INFERENCE_IMAGE = ConfigVariableDeclaration(
    'DEFAULT_SAGEMAKER_INFERENCE_IMAGE', None, str,
    'Default Docker image for inference process', True
)

DEFAULT_SAGEMAKER_DELOY_TIMEOUT = ConfigVariableDeclaration(
    'DEFAULT_SAGEMAKER_DELOY_TIMEOUT', 1200, int,
    'Default timeout for the deploy process of SageMaker', True
)

DEFAULT_SAGEMAKER_VPC_CONFIG = ConfigVariableDeclaration(
    'DEFAULT_SAGEMAKER_VPC_CONFIG', None, str,
    'Path to the file with default VPC config', True
)

DEFAULT_SAGEMAKER_VPC_SECURITY_GROUPS = ConfigVariableDeclaration(
    'DEFAULT_SAGEMAKER_VPC_SECURITY_GROUPS', (), cast_list_of_strings,
    'Path to the file with default VPC config', True
)

DEFAULT_SAGEMAKER_VPC_SUBNETS = ConfigVariableDeclaration(
    'DEFAULT_SAGEMAKER_VPC_SUBNETS', (), cast_list_of_strings,
    'Path to the file with default VPC config', True
)

DEFAULT_SAGEMAKER_LOCAL_RUN_PORT = ConfigVariableDeclaration(
    'DEFAULT_SAGEMAKER_LOCAL_RUN_PORT', 5005, int,
    'Default port to run SageMaker model locally on', True
)

DEFAULT_LAMBDA_ARN = ConfigVariableDeclaration(
    'DEFAULT_LAMBDA_ARN', '', str,
    'Default ARN for lambda function', True
)

DEFAULT_LAMBDA_LAYERS = ConfigVariableDeclaration(
    'DEFAULT_LAMBDA_LAYERS', (), cast_list_of_strings,
    'Default Lambda layers', True
)

DEFAULT_LAMBDA_RAM = ConfigVariableDeclaration(
    'DEFAULT_LAMBDA_RAM', 256, int,
    'Default Lambda RAM Size', True
)

DEFAULT_LAMBDA_RUNTIME = ConfigVariableDeclaration(
    'DEFAULT_LAMBDA_RUNTIME', 'python3.8', str,
    'Default Lambda Runtime', True
)

DEFAULT_LAMBDA_TIMEOUT = ConfigVariableDeclaration(
    'DEFAULT_LAMBDA_TIMEOUT', 120, int,
    'Default Lambda Timeout', True
)

DEFAULT_API_GATEWAY_ID = ConfigVariableDeclaration(
    'DEFAULT_API_GATEWAY_ID', None, str,
    'Default API Gateway Where publish function to', True
)

DEFAULT_API_GATEWAY_STAGE = ConfigVariableDeclaration(
    'DEFAULT_API_GATEWAY_STAGE', None, str,
    'Default Stage to use on API Gateway', True
)

DEFAULT_API_GATEWAY_AUTHORIZATION = ConfigVariableDeclaration(
    'DEFAULT_API_GATEWAY_AUTHORIZATION', None, str,
    'Default API Gateway Authorization', True
)

DEFAULT_API_GATEWAY_LAMBDA_CALL_ROLE = ConfigVariableDeclaration(
    'DEFAULT_API_GATEWAY_LAMBDA_CALL_ROLE', None, str,
    'Default API Gateway Role for lambda calling', True
)
