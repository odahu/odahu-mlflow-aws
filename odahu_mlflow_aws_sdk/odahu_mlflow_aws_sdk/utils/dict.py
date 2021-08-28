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
Util / helper functions for working with dictionaries
"""


def find_dict_value_ignore_case(storage: dict, key: str, default=None, validate_type=None):
    """
    Find value in a dictionary by a key with ignoring a case

    :param storage: dictionary to find data in
    :param key: name of a key
    :param default: default value to return
    :param validate_type: (optional) validate that value is a type of a target type
    :return: found value
    """
    key_lower = key.lower()
    for k in storage.keys():
        if isinstance(k, str):
            if k.lower() == key_lower:
                value = storage[k]
                if validate_type and not isinstance(value, validate_type):
                    raise Exception(f'Value of {k} is not a {validate_type}')
                return value
    return default
