#!/bin/bash
# =============================================================
# Script 1: Install & Run OpenSearch via Docker
# Rumah Sakit Sehat Selalu - QA System
# =============================================================

echo "=== Installing OpenSearch via Docker ==="

# 1. Pull OpenSearch image
docker pull opensearchproject/opensearch:2.11.0

# 2. Run OpenSearch (single-node, no security for dev)
docker run -d \
  --name opensearch-hospital \
  -p 9200:9200 \
  -p 9600:9600 \
  -e "discovery.type=single-node" \
  -e "OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m" \
  -e "plugins.security.disabled=true" \
  opensearchproject/opensearch:2.11.0

echo "Waiting for OpenSearch to start..."
sleep 15

# 3. Verify OpenSearch is running
curl -X GET "http://localhost:9200" 
echo ""
echo "=== OpenSearch is ready at http://localhost:9200 ==="
