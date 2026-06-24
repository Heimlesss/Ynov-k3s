FROM python:3.13-slim

WORKDIR /app

COPY shared /app/shared
RUN pip install --no-cache-dir -r /app/shared/requirements.txt

COPY customer /app/customer
RUN pip install --no-cache-dir -r /app/customer/requirements.txt

ENV PYTHONPATH=/app

CMD ["python", "customer/customer.py"]
