FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
ENV PYTHONPATH=/app
ENV HF_HOME=/models
CMD ["python", "-m", "src.bootstrap.entrypoint"]
