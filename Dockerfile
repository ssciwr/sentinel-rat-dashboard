FROM rocker/shiny:4.3.2

ENV DEBIAN_FRONTEND=noninteractive
ENV POSTGRES_DB=sentinel_db
ENV POSTGRES_HOST=db
ENV POSTGRES_PORT=5432
ENV POSTGRES_USER=sentinel_user
ENV POSTGRES_PASSWORD=sentinel_pass

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

COPY install.R /tmp/install.R
RUN Rscript /tmp/install.R

COPY src/ /srv/shiny-server/

RUN pip3 install --no-cache-dir "psycopg[binary]"

EXPOSE 3838

CMD ["sh", "-c", "python3 /srv/shiny-server/dashboard/init_db.py && R -e 'shiny::runApp(\"/srv/shiny-server/dashboard\", host=\"0.0.0.0\", port=3838)'"]
