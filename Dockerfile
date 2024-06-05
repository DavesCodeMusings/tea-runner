FROM python:alpine
LABEL org.opencontainers.image.source = "https://github.com/DavesCodeMusings/tea-runner"
WORKDIR /usr/src/app
RUN apk update
RUN apk add git rsync
RUN apk add docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY tea_runner.py .
CMD [ "python", "tea_runner.py" ]
