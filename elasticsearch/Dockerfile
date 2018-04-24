ARG ELASTICSEARCH_VERSION=2-alpine

FROM elasticsearch:${ELASTICSEARCH_VERSION}

ENV ES_PATH_REPO=/elasticsearch_backup

RUN apk add --no-cache curl ca-certificates


COPY docker-entrypoint.sh /
COPY elasticsearch.yml /usr/share/elasticsearch/config/elasticsearch.yml
