FROM python:2-alpine

RUN pip install watchdog; pip install pika
