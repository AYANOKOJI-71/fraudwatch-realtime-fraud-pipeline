FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY pyproject.toml ./
COPY apps ./apps
RUN pip install --no-cache-dir .
USER 10001
CMD ["python", "-m", "apps.worker.service"]
