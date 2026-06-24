FROM python:3.13-slim

WORKDIR /app

COPY shared /app/shared
RUN pip install --no-cache-dir -r /app/shared/requirements.txt

COPY kitchen /app/kitchen
RUN pip install --no-cache-dir -r /app/kitchen/requirements.txt

ENV PYTHONPATH=/app

CMD ["python", "kitchen/kitchen.py"]
