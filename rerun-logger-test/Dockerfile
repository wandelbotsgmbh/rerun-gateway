ARG RERUN_SDK_VERSION=0.33.0
FROM wandelbots.azurecr.io/docker.io/library/python:3.12-slim
ARG RERUN_SDK_VERSION
RUN pip install --no-cache-dir rerun-sdk==${RERUN_SDK_VERSION} numpy
COPY logger.py /logger.py
CMD ["python3", "-u", "/logger.py"]
