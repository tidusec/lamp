
FROM python:3.14


WORKDIR /code


COPY ./requirements.txt /code/requirements.txt


RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt


COPY . /code/app
COPY www /www


CMD ["fastapi", "run", "app/main.py", "--port", "80"]