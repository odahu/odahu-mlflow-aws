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
This package provides:
1. Functions for building Handlers for pre/post processing and validations (see inference.sdk)
2. Functions for storing inference code as a part of MlFlow model (see inference.sdk)
3. CLI for simple one-command deploy (odahu-mlflow-aws deploy -m models:/wine-model/production)
4. CLI for more complex scenarios (see odahu-mlflow-aws --help)
5. CLI for managing config (config can be used to persist config values), see odahu-mlflow-aws config --help
   (config file is stored in a file .odahu-mlflow-aws of the home directory in an INI format)
"""
