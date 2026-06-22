FROM python:3.11-alpine

LABEL maintainer="Heimlesss"
LABEL description="Ynov DevSecOps - Flask app for security scanning"

RUN addgroup -S appuser && adduser -S appuser -G appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY app.py .

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 5000

CMD ["python", "app.py"]