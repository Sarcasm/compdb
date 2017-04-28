FROM ubuntu:trusty

MAINTAINER Guillaume Papin "guillaume.papin@epitech.eu"

RUN apt-get update && apt-get install -y --no-install-recommends \
        python-pip \
        python-virtualenv \
        python3-pip \
        runit \
        \
        && apt-get clean \
        && rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh /

ENTRYPOINT ["/entrypoint.sh"]

