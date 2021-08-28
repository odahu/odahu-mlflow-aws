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
Functions for working with a JSON
"""
import numpy as np
import pandas as pd


def to_single_object_json(data, output_schema):
    """
    Convert single object to a target output schema

    :param data:
    :param output_schema:
    :return:
    """
    if isinstance(data, pd.DataFrame):
        resp = data.to_dict(orient='index')
    elif isinstance(data, pd.Series):
        resp = pd.DataFrame(data).to_dict(orient='index')
    elif isinstance(data, (np.ndarray, list)):
        values = data.tolist() if isinstance(data, np.ndarray) else data
        if len(values) != len(output_schema.columns):
            raise Exception(
                f'Response contains {len(values)} field(s), but schema declares {len(output_schema.columns)} value(s)'
            )
        return {
            key.name: values[idx]
            for idx, key in enumerate(output_schema.columns)
        }
    else:
        raise Exception('Unsupported response')

    if not resp:
        raise Exception('Response is not found or empty')

    keys = tuple(resp.keys())
    if not keys:
        raise Exception('Records are not found in results')

    if len(keys) > 1:
        raise Exception('More then one record found in results')

    return resp[keys[0]]


# CODE BELOW IS A COPY FROM THE https://github.com/mlflow/mlflow (Apache 2.0 license)
#
#    Copyright [yyyy] [name of copyright owner]
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
def _get_jsonable_obj(data, pandas_orient="records"):
    """Attempt to make the data json-able via standard library.
    Look for some commonly used types that are not jsonable and convert them into json-able ones.
    Unknown data types are returned as is.

    :param data: data to be converted, works with pandas and numpy, rest will be returned as is.
    :param pandas_orient: If `data` is a Pandas DataFrame, it will be converted to a JSON
                          dictionary using this Pandas serialization orientation.

    COPIED FROM MLFLOW
    """

    if isinstance(data, np.ndarray):
        return data.tolist()
    if isinstance(data, pd.DataFrame):
        return data.to_dict(orient=pandas_orient)
    if isinstance(data, pd.Series):
        return pd.DataFrame(data).to_dict(orient=pandas_orient)
    else:  # by default just return whatever this is and hope for the best
        return data
