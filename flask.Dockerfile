FROM python:3.11-slim
RUN pip install flask[async] requests temporalio
WORKDIR /app
CMD ["flask", "--app", "app.py", "run", "--host=0.0.0.0", "--debug"]