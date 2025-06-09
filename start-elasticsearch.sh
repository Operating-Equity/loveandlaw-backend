#!/bin/bash
# Script to start Elasticsearch in Docker

echo "Starting Elasticsearch in Docker..."
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -p 9300:9300 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  elasticsearch:8.17.0

echo "Waiting for Elasticsearch to start..."
sleep 10

# Check if Elasticsearch is running
curl -X GET "http://localhost:9200/_cluster/health?pretty"
echo "Elasticsearch should now be running at http://localhost:9200"