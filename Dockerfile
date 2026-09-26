FROM alpine

RUN apk add texlive-xetex \
    texmf-dist-latexextra \
    mysql-client \
	mariadb-connector-c \
    socat \
    coreutils \
    xxd \
    python3 \
    uv


WORKDIR /tmp
COPY entrypoint.sh /entrypoint.sh
COPY cleanup.sh /cleanup.sh
CMD ["uv install -r requirements.txt"]
CMD ["socat", "-6", "tcp-l:1337,fork,reuseaddr", "EXEC:/entrypoint.sh"]
