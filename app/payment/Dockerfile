FROM python:3.13-slim

WORKDIR /app

COPY shared /app/shared
RUN pip install --no-cache-dir -r /app/shared/requirements.txt

COPY payment /app/payment
RUN pip install --no-cache-dir -r /app/payment/requirements.txt

ENV PYTHONPATH=/app

EXPOSE 5003
CMD ["python", "payment/payment.py"]
