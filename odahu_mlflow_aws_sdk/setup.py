#!/usr/bin/env python3
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
from setuptools import setup, find_namespace_packages

# Load requirements from the requirements.txt file
with open('requirements.txt') as f:
    requirements = f.read().splitlines()


setup(
    name='odahu-mlflow-aws-sdk',
    author='Kirill Makhonin',
    author_email='kirill@makhonin.biz,kirill_makhonin@epam.com',
    classifiers=[
        'Programming Language :: Python :: 3.8',
    ],
    keywords='odahu mlflow',
    python_requires='>=3.8',
    packages=find_namespace_packages(),
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'odahu-mlflow-aws=odahu_mlflow_aws_sdk.cli.run:cli'
        ],
    },
    install_requires=requirements,
    # Testing is not yet implemented
    extras_require={
        'testing': [
            'pytest>=5.1.2',
            'pytest-mock>=1.10.4',
            'pytest-cov>=2.7.1',
            'pylint>=2.3.0'
        ]
    },
    version='0.1'
)
