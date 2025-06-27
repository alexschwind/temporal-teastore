FROM python:3.11-slim
RUN pip install temporalio requests
WORKDIR /app
CMD [ "python", "run_worker.py" ]