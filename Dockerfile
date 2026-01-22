FROM python:3.11-slim

ENV PIP_BREAK_SYSTEM_PACKAGES=1

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY webcal.py .

RUN echo "0 19 * * * python /app/webcal.py > /proc/1/fd/1 2>&1" | crontab - && \
    touch /var/log/cron.log

CMD cron && tail -f /var/log/cron.log
