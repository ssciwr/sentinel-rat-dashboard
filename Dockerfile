FROM rocker/shiny:4.3.2

ENV DEBIAN_FRONTEND=noninteractive
# src/ is copied to /srv/shiny-server/, so the `dashboard` package lives there.
# The package is not pip-installed (pyproject pins requires-python >=3.13, newer
# than the base image's Python), so put it on the path explicitly.
ENV PYTHONPATH=/srv/shiny-server
ENV POSTGRES_DB=sentinel_db
ENV POSTGRES_HOST=db
ENV POSTGRES_PORT=5432
ENV POSTGRES_USER=sentinel_user
ENV POSTGRES_PASSWORD=sentinel_pass

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    libpq-dev \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

COPY install.R /tmp/install.R
RUN Rscript /tmp/install.R

COPY src/ /srv/shiny-server/

# The dashboard ORM package uses Python 3.13-only syntax (PEP 695 generics),
# newer than the base image's system Python. Provide a real 3.13 interpreter
# (via uv) in a fixed-path venv and install the package's runtime deps into it.
# reticulate (used by the R app) and init_db both run against this interpreter.
# Versions are pinned and installs are restricted to pre-built wheels
# (--only-binary=:all:) so no source-distribution setup scripts run at build.
RUN pip3 install --no-cache-dir --only-binary=:all: uv==0.12.23 \
    && uv venv --python 3.13 /opt/py313 \
    && uv pip install --python /opt/py313/bin/python --no-cache --only-binary=:all: \
    "psycopg[binary]==3.3.4" "sqlalchemy==2.0.51" "geoalchemy2==0.20.0"
ENV RETICULATE_PYTHON=/opt/py313/bin/python

EXPOSE 3838

# db-init creates the schema in the compose stack; running init_db here too is
# idempotent and keeps the image usable standalone. Use the 3.13 interpreter.
CMD ["sh", "-c", "/opt/py313/bin/python -m dashboard.init_db && R -e 'shiny::runApp(\"/srv/shiny-server/dashboard\", host=\"0.0.0.0\", port=3838)'"]
