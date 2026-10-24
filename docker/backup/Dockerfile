# Backup runner: pg_dump, gzip and aws-cli, all available on arm64.
FROM alpine:3.21

RUN apk add --no-cache \
      postgresql17-client \
      aws-cli \
      coreutils \
      tzdata

COPY backup.sh schedule.sh restore.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/backup.sh /usr/local/bin/schedule.sh /usr/local/bin/restore.sh

ENTRYPOINT ["sh", "/usr/local/bin/schedule.sh"]
