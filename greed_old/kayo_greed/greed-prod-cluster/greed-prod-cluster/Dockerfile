FROM python:3.10-slim

WORKDIR /bot

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    git \
    ffmpeg \
    ca-certificates \
    libgtk-3-0 \
    libdbus-1-3 \
    libgbm1 \
    libnss3 \
    libxkbcommon-x11-0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libxfixes3 \
    libasound2 \
    libatspi2.0-0 \
    libpango-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libdrm2 \
    libv4l-dev \
    libxshmfence1 \
    fonts-liberation \
    libappindicator3-1 \
    libnss3-tools \
    imagemagick \
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.sh .
RUN sh requirements.sh

RUN playwright install

RUN pip install redis

COPY . .

CMD ["python3", "main.py"]
