# Imagem do honeypot Apache do laboratorio SentinelIoT.
#
# O contexto de build e a pasta scripts/lab/, por isso os COPY usam
# caminhos como honeypot/web e honeypot/cgi (conteudo compartilhado com
# a documentacao e com o agente).
FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends apache2 python3 ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && a2enmod cgi \
    && (a2dissite 000-default || true)

COPY honeypot/web/ /var/www/sentinel/
COPY honeypot/cgi/ /usr/lib/cgi-bin/
COPY honeypot/apache/sentinel-honeypot.conf /etc/apache2/sites-available/sentinel-honeypot.conf

RUN a2ensite sentinel-honeypot \
    && chmod 0755 /usr/lib/cgi-bin/*.py \
    && mkdir -p /var/run/apache2 /var/lock/apache2 /var/log/apache2 \
        /var/log/sentinel/apache \
    && chown -R www-data:www-data /var/log/sentinel

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1/', timeout=3)"

CMD ["apache2ctl", "-D", "FOREGROUND"]
