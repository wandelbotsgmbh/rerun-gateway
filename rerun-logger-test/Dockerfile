FROM python:3.11-slim
RUN pip install --no-cache-dir rerun-sdk==0.33.0 numpy
COPY logger.py /logger.py
CMD ["python3", "-u", "/logger.py"]
