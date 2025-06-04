FROM ubuntu:latest
RUN apt-get update && \
    apt-get install -y \
    make \
    g++ \
    wget \
    curl \
    cron \
    iproute2 \
    iputils-ping \
    tar \
    apt-transport-https \
    gnupg && \
    apt-get clean

COPY build.sh .
RUN chmod +x build.sh && ./build.sh
COPY start.sh .
RUN chmod +x start.sh
# change user and pass
ENV START_PORT=30000

CMD ["sh", "-c", "./start.sh -u admin -p admin --start-port $START_PORT -b 0.0.0.0 -t http"]
