FROM python:3.11

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN pip install --upgrade pip
RUN pip install sqlalchemy
RUN pip install pymysql

COPY . /app/
