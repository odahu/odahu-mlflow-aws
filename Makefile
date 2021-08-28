SHELL := /bin/bash

ifneq (,$(wildcard ./.env))
    include .env
    export
endif

cwd  := $(shell pwd)

VERSION  ?= 0.1
MLFLOW_VERSION ?= local-mlflow

.DEFAULT_GOAL := help

## docker-build-mlflow-server: Build MLFlow server using Docker
docker-build-mlflow-server:
ifeq (${REGISTRY},)
	$(error REGISTRY is not set, please set or put in the .env file)
endif
	docker build -t ${REGISTRY}/${MLFLOW_VERSION}-server --target ${MLFLOW_VERSION} -f containers/server.Dockerfile .


## build-dependencies-layer: Build AWS Lambda Layer with dependencies
build-dependencies-layer:
	# Remove old built data
	rm -rf $(cwd)/dist/python-dependencies.zip $(cwd)/odahu_mlflow_aws_sdk/python
	mkdir -p $(cwd)/dist/temp
	# Build Python Lib Dependencies (using python 3.8, because there are no lambci/lambda:build-python3.9)
	# Docs: https://dev.to/mmascioni/using-external-python-packages-with-aws-lambda-layers-526o
	docker run --rm \
	    --volume=$(cwd)/odahu_mlflow_aws_sdk:/lambda-build \
	    -w=/lambda-build \
	    lambci/lambda:build-python3.8 \
	    pip install . --target python
	# Remove mlflow server JS (because it is so big - 50+ Mb)
	rm -rf $(cwd)/odahu_mlflow_aws_sdk/python/mlflow/server/js
	# Move to the dist folder
	cd $(cwd)/odahu_mlflow_aws_sdk && zip -r $(cwd)/dist/python-dependencies.zip python

## push-dependencies-layer: Push dependencies to the S3 Location
push-dependencies-layer:
ifeq (${S3_LOCATION},)
	$(error S3_LOCATION is not set, please set or put in the .env file)
endif
	aws s3 cp $(cwd)/dist/python-dependencies.zip s3://${S3_LOCATION}/lambda/layers/python-dependencies.zip
	echo "Pushed"

## build-push-dependencies-layer: Build & Push dependencies layer
build-push-dependencies-layer: build-dependencies-layer push-dependencies-layer
ifeq (${S3_LOCATION},)
	$(error S3_LOCATION is not set, please set or put in the .env file)
endif
	echo "Done to location s3://${S3_LOCATION}/lambda/layers/python-dependencies.zip"

## help: Show the help message
help: Makefile
	@echo "Choose a command run:"
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sort | sed -e 's/\\$$//' | sed -e 's/##//'
	@echo
