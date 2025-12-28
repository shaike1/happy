FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir psycopg2-binary requests

COPY notifier.py /app/

CMD ["python", "-u", "/app/notifier.py"]
