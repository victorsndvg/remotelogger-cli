Bootstrap: docker
From: python:2-alpine

%post 
    apk update
    apk upgrade
    apk add --no-cache bash git openssh
    pip install watchdog
    pip install pika
    git clone https://github.com/victorsndvg/remotelogger-cli.git /opt/remotelogger-cli
    echo '#!/usr/bin/env sh' > /usr/local/bin/start-logger
    echo 'exec python /opt/remotelogger-cli/remotelogger-cli.py "$@"' >> /usr/local/bin/start-logger
    chmod +x /usr/local/bin/start-logger
    
%runscript
    exec python /opt/remotelogger-cli/remotelogger-cli.py "$@"

