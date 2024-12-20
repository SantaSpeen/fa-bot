FROM python:3.12.7-alpine

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY ./src .

CMD [ "python", "./main.py"]
