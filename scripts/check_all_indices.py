"""
Check all available Elasticsearch indices.
"""

import asyncio
import json
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.elasticsearch_service import elasticsearch_service


async def check_indices():
    """List all available indices."""
    try:
        # Initialize connection
        print("🔌 Connecting to Elasticsearch...")
        await elasticsearch_service.initialize()
        print("✅ Connected successfully!")
        
        # Get all indices
        print("\n📋 Available indices:")
        indices = await elasticsearch_service.client.cat.indices(format='json')
        
        if not indices:
            print("❌ No indices found!")
            return
            
        # Display indices
        print(f"\nFound {len(indices)} index(es):\n")
        print(f"{'Index Name':<40} {'Docs':<10} {'Size':<10} {'Status':<10}")
        print("-" * 70)
        
        for idx in indices:
            name = idx.get('index', 'N/A')
            docs = idx.get('docs.count', '0')
            size = idx.get('store.size', 'N/A')
            status = idx.get('status', 'N/A')
            print(f"{name:<40} {docs:<10} {size:<10} {status:<10}")
        
        # Check for love-and-law related indices
        print("\n🔍 Looking for love-and-law indices...")
        love_law_indices = [idx for idx in indices if 'love' in idx.get('index', '').lower() or 'law' in idx.get('index', '').lower()]
        
        if love_law_indices:
            print(f"✅ Found {len(love_law_indices)} love-and-law related index(es):")
            for idx in love_law_indices:
                print(f"  - {idx.get('index')} ({idx.get('docs.count', '0')} docs)")
        else:
            print("⚠️  No love-and-law indices found")
            
        # Check for lawyers indices
        print("\n🔍 Looking for lawyer indices...")
        lawyer_indices = [idx for idx in indices if 'lawyer' in idx.get('index', '').lower()]
        
        if lawyer_indices:
            print(f"✅ Found {len(lawyer_indices)} lawyer index(es):")
            for idx in lawyer_indices:
                print(f"  - {idx.get('index')} ({idx.get('docs.count', '0')} docs)")
        else:
            print("⚠️  No lawyer indices found")
            
        # Check cluster health
        print("\n🏥 Cluster health:")
        health = await elasticsearch_service.client.cluster.health()
        print(f"  Status: {health['status']}")
        print(f"  Number of nodes: {health['number_of_nodes']}")
        print(f"  Active shards: {health['active_shards']}")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if elasticsearch_service.client:
            await elasticsearch_service.close()


if __name__ == "__main__":
    asyncio.run(check_indices())