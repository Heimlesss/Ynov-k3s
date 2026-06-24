FROM python:3.13-slim

WORKDIR /app

COPY shared /app/shared
RUN pip install --no-cache-dir -r /app/shared/requirements.txt

COPY waiter /app/waiter
RUN pip install --no-cache-dir -r /app/waiter/requirements.txt

ENV PYTHONPATH=/app

EXPOSE 5001
CMD ["python", "waiter/waiter.py"]
