FROM python:3.11-slim

LABEL maintainer="Heimlesss"
LABEL description="Ynov DevSecOps - Flask app for security scanning"

RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 5000

CMD ["python", "app.py"]
