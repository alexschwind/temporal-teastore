FROM python:3.11-slim
RUN pip install flask[async] requests temporalio
WORKDIR /app
COPY . /app
ENV PYTHONUNBUFFERED=1
CMD ["python", "app.py"]