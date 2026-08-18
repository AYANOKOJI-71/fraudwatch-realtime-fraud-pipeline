FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY pyproject.toml ./
COPY apps ./apps
RUN pip install --no-cache-dir .
USER 10001
EXPOSE 4200
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "4200"]
