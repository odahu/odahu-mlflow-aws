# MlFlow base server (without start command)
FROM python:3.9.0 as base-mlflow-server

RUN pip install \
    mlflow==1.19.0 \
    pymysql==1.0.2 \
    boto3 && \
    mkdir /mlflow/

EXPOSE 5000

# MlFlow Server for local deployment (with SQLite DB in /mnt/metrics.db)
FROM base-mlflow-server as local-mlflow

CMD mlflow server \
    --host 0.0.0.0 \
    --port 5000 \
    --default-artifact-root ${BUCKET} \
    --backend-store-uri sqlite:///mnt/metrics.db

# MlFlow Server for cloud deployment (with MySQL database)
FROM base-mlflow-server as aws-cloud-mlflow

CMD mlflow server \
    --host 0.0.0.0 \
    --port 5000 \
    --file-store /mnt/persistent-disk \
    --default-artifact-root ${BUCKET} \
    --backend-store-uri mysql+pymysql://${USERNAME}:${PASSWORD}@${HOST}:${PORT}/${DATABASE}
