FROM python:3.11-slim
RUN pip install flask[async] requests temporalio
WORKDIR /app
CMD ["python", "app.py"]