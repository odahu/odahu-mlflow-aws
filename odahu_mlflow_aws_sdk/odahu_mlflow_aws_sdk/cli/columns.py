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
This module contains declarations of columns can be used for table outputs in CLI commands
"""
from odahu_mlflow_aws_sdk.cli.output import Column, ColumnVAlign, ColumnAlign, ColumnDataType

# MlFlow Model information
MlFlowModel = (
    Column('Model Name', 'name', default=True),
    Column('Tags', lambda rec: '\n'.join(f'{tag["key"]}: {tag["value"]}' for tag in rec.get('tags', {})), default=True),
    Column('Created at', 'creationTimestamp', dtype=ColumnDataType.DATETIME, default=True),
    Column('Updated at', 'lastUpdatedTimestamp', dtype=ColumnDataType.DATETIME, default=True),
    Column('Latest versions',
           lambda x: '\n'.join(
               (
                   f'{v["currentStage"]}: {v["version"]}'
                    if v['currentStage'] not in (None, 'None')
                    else f'Latest: {v["version"]}'
               )
               for v in x['latestVersions']
           ),
           default=True),
)

# MlFlow Model version information
MlFlowModelVersion = (
    Column('Model Name', 'name', default=True),
    Column('Version', 'version', default=True),
    Column('Tags', lambda rec: '\n'.join(f'{tag["key"]}: {tag["value"]}' for tag in rec.get('tags', {})), default=True),
    Column('Created at', 'creationTimestamp', dtype=ColumnDataType.DATETIME, default=True),
    Column('Updated at', 'lastUpdatedTimestamp', dtype=ColumnDataType.DATETIME, default=True),
    Column('User ID', 'userId', default=True),
    Column('Current stage', 'currentStage', default=True),
    Column('Description', 'description', default=True),
    Column('Source', 'source', default=True),
    Column('Run ID', 'runId', default=True),
    Column('Status', 'status', default=True),
    Column('Run Link', 'runLink', default=False),
)

# AWS Lambda Function information
AwsLambdaFunctions = (
    Column('Function name', 'FunctionName', default=True),
    Column('Description', 'Description', default=True),
)
