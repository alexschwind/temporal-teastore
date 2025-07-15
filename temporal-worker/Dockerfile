FROM python:3.11-slim
RUN pip install temporalio requests
WORKDIR /app

COPY . /app

ENV PYTHONUNBUFFERED=1

CMD [ "python", "run_worker.py" ]