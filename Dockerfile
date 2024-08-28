# Dockerfile

FROM python:3.7

RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y

RUN apt-get install espeak -y

WORKDIR /app

COPY ./ .

COPY requirements/main.txt /app/requirements/

RUN pip install --no-cache-dir -r /app/requirements/main.txt

EXPOSE 5000

CMD ["python", "run.py", "--cli"]
