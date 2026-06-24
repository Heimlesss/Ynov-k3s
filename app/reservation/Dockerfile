FROM python:3.13-slim

WORKDIR /app

COPY shared /app/shared
RUN pip install --no-cache-dir -r /app/shared/requirements.txt

COPY reservation /app/reservation
RUN pip install --no-cache-dir -r /app/reservation/requirements.txt

ENV PYTHONPATH=/app

EXPOSE 5004
CMD ["python", "reservation/reservation.py"]
