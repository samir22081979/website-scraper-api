FROM n8nio/n8n:latest

USER root
# Use Alpine package manager
RUN apk update \
 && apk add --no-cache python3 py3-pip dos2unix \
 && pip3 install --upgrade pip

COPY scraper.py /data/scraper.py
RUN dos2unix /data/scraper.py \
 && chmod +x /data/scraper.py

RUN pip3 install playwright beautifulsoup4 lxml requests \
 && playwright install --with-deps

USER node
