ARG SDK_VERSION
ARG ARCHITECTURE
FROM egeoffrey/egeoffrey-sdk-alpine:${SDK_VERSION}-${ARCHITECTURE}
RUN apk update && apk add nginx && rm -rf /var/cache/apk/*
RUN pip install --upgrade setuptools && pip install fuzzywuzzy redis==2.10.6 rq==0.12.0 slackclient pyicloud feedparser
RUN mkdir -p /run/nginx
COPY . $WORKDIR
