FROM n8nio/n8n:latest

USER root
RUN apt-get update \
 && apt-get install -y python3 python3-pip dos2unix \
 && pip3 install --upgrade pip

COPY scraper.py /data/scraper.py
RUN dos2unix /data/scraper.py \
 && chmod +x /data/scraper.py

RUN pip3 install playwright beautifulsoup4 lxml requests \
 && playwright install --with-deps

USER node
