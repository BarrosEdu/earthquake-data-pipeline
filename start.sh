#!/usr/bin/env bash
set -e

# Baixa Prometheus para Linux dentro do container/dyno do Render
# (versão de exemplo, pode ajustar a URL se sair versão nova)
PROM_VERSION="3.7.3"
ARCHIVE="prometheus-${PROM_VERSION}.linux-amd64.tar.gz"

curl -L -o /tmp/${ARCHIVE} "https://github.com/prometheus/prometheus/releases/download/v${PROM_VERSION}/${ARCHIVE}"
tar -xzf /tmp/${ARCHIVE} -C /tmp
mv /tmp/prometheus-${PROM_VERSION}.linux-amd64 /tmp/prometheus-dir

# Roda Prometheus usando o prometheus.yml do repo
/tmp/prometheus-dir/prometheus \
  --config.file=prometheus.yml \
  --storage.tsdb.path=/tmp/prom-data \
  --web.listen-address=0.0.0.0:$PORT
