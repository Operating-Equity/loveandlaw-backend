#!/usr/bin/env python3
"""
Test Elasticsearch connection and basic operations
"""
import asyncio
from elasticsearch import AsyncElasticsearch
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_elasticsearch():
    """Test Elasticsearch connection"""
    es_url = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
    print(f"Testing connection to Elasticsearch at: {es_url}")
    
    es = AsyncElasticsearch([es_url])
    
    try:
        # Test connection
        info = await es.info()
        print("✅ Elasticsearch connection successful!")
        print(f"   Version: {info['version']['number']}")
        print(f"   Cluster name: {info['cluster_name']}")
        
        # Check if lawyers index exists
        index_exists = await es.indices.exists(index="lawyers_v1")
        if index_exists:
            print("✅ lawyers_v1 index exists")
            # Get document count
            count = await es.count(index="lawyers_v1")
            print(f"   Documents in index: {count['count']}")
        else:
            print("❌ lawyers_v1 index does not exist")
            print("   Run scripts/populate_lawyers.py to create and populate it")
        
    except Exception as e:
        print(f"❌ Elasticsearch connection failed: {e}")
        print("\nMake sure Elasticsearch is running:")
        print("  - Docker: docker run -p 9200:9200 -e 'discovery.type=single-node' elasticsearch:8.17.0")
        print("  - Or install locally and start the service")
    finally:
        await es.close()

if __name__ == "__main__":
    asyncio.run(test_elasticsearch())