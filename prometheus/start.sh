#!/usr/bin/env bash
set -e

PROM_VERSION="3.7.3"
ARCHIVE="prometheus-${PROM_VERSION}.linux-amd64.tar.gz"
PROM_DIR="/tmp/prometheus"

echo "🔍 Baixando Prometheus..."
curl -L -o /tmp/${ARCHIVE} "https://github.com/prometheus/prometheus/releases/download/v${PROM_VERSION}/${ARCHIVE}"
tar -xzf /tmp/${ARCHIVE} -C /tmp
mv /tmp/prometheus-${PROM_VERSION}.linux-amd64 "$PROM_DIR"

echo "🧩 Gerando prometheus.yml a partir de template..."
# Se tiver envsubst disponível:
#   envsubst < prometheus.tpl.yml > prometheus.yml
# Como não sabemos se o Render tem envsubst, fazemos com sed:
sed -e "s|\${GRAFANA_USERNAME}|$GRAFANA_USERNAME|g" \
    -e "s|\${GRAFANA_API_KEY}|$GRAFANA_API_KEY|g" \
    prometheus.tpl.yml > prometheus.yml

echo "🚀 Iniciando Prometheus..."
exec $PROM_DIR/prometheus \
  --config.file=prometheus.yml \
  --storage.tsdb.path=/tmp/prom-data \
  --web.listen-address=0.0.0.0:$PORT
