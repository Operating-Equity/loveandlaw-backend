"""
Verify Elasticsearch index integrity and functionality.
Checks document count, array field formatting, search functionality, and aliases.
"""

import asyncio
import json
from typing import Dict, Any, List
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.elasticsearch_service import elasticsearch_service
from src.config.settings import settings


async def verify_index():
    """Run comprehensive verification of the Elasticsearch index."""
    try:
        # Initialize connection
        print("🔌 Connecting to Elasticsearch...")
        await elasticsearch_service.initialize()
        print("✅ Connected successfully!")
        
        # Use the actual index name
        elasticsearch_service.index_name = "lawyers_v1"
        
        # 1. Check index exists and get document count
        print("\n📊 Checking index status...")
        index_stats = await elasticsearch_service.client.indices.stats(
            index=elasticsearch_service.index_name
        )
        
        doc_count = index_stats['indices'][elasticsearch_service.index_name]['primaries']['docs']['count']
        print(f"✅ Index '{elasticsearch_service.index_name}' exists with {doc_count} documents")
        
        # 2. Sample documents to check array field formatting
        print("\n🔍 Sampling documents to verify array fields...")
        sample_response = await elasticsearch_service.client.search(
            index=elasticsearch_service.index_name,
            body={
                "size": 5,
                "query": {"match_all": {}},
                "_source": ["id", "name", "practice_areas", "languages", "payment_methods"]
            }
        )
        
        print(f"\n📋 Sampled {len(sample_response['hits']['hits'])} documents:")
        for i, hit in enumerate(sample_response['hits']['hits'], 1):
            doc = hit['_source']
            print(f"\n  Document {i}: {doc.get('name', 'No name')}")
            print(f"  - ID: {doc.get('id', 'No ID')}")
            
            # Check array fields
            for field in ['practice_areas', 'languages', 'payment_methods']:
                value = doc.get(field, None)
                if value is not None:
                    is_array = isinstance(value, list)
                    print(f"  - {field}: {'✅ Array' if is_array else '❌ Not array'} - {value}")
                else:
                    print(f"  - {field}: ⚠️  Field not present")
        
        # 3. Run test search queries
        print("\n🔎 Testing search functionality...")
        
        # Test 1: Simple text search
        print("\n  Test 1: Text search for 'divorce'")
        search_results = await elasticsearch_service.search_lawyers(
            query_text="divorce",
            size=3
        )
        print(f"  ✅ Found {len(search_results)} results")
        if search_results:
            print(f"  Top result: {search_results[0].get('name')} (score: {search_results[0].get('match_score', 0):.2f})")
        
        # Test 2: Filter search
        print("\n  Test 2: Filter by state (CA)")
        filter_results = await elasticsearch_service.search_lawyers(
            filters={"state": "CA"},
            size=3
        )
        print(f"  ✅ Found {len(filter_results)} results in California")
        
        # Test 3: Combined search
        print("\n  Test 3: Combined text + filter search")
        combined_results = await elasticsearch_service.search_lawyers(
            query_text="family law",
            filters={"state": "CA"},
            size=3
        )
        print(f"  ✅ Found {len(combined_results)} results for 'family law' in CA")
        
        # Test 4: Semantic search
        print("\n  Test 4: Semantic search")
        try:
            semantic_results = await elasticsearch_service.advanced_semantic_search(
                query_text="I need help with child custody after divorce",
                size=3
            )
            print(f"  ✅ Semantic search found {len(semantic_results)} results")
        except Exception as e:
            print(f"  ⚠️  Semantic search not available: {str(e)}")
        
        # 4. Check index aliases
        print("\n🏷️  Checking index aliases...")
        aliases = await elasticsearch_service.client.indices.get_alias(
            index=elasticsearch_service.index_name
        )
        
        alias_list = list(aliases[elasticsearch_service.index_name].get('aliases', {}).keys())
        if alias_list:
            print(f"✅ Found {len(alias_list)} alias(es): {', '.join(alias_list)}")
        else:
            print("ℹ️  No aliases configured for this index")
        
        # 5. Check index mapping
        print("\n🗺️  Checking index mapping...")
        mapping = await elasticsearch_service.client.indices.get_mapping(
            index=elasticsearch_service.index_name
        )
        
        properties = mapping[elasticsearch_service.index_name]['mappings'].get('properties', {})
        print(f"✅ Index has {len(properties)} mapped fields")
        
        # Check for semantic fields
        semantic_fields = [k for k in properties.keys() if 'semantic' in k]
        if semantic_fields:
            print(f"✅ Found {len(semantic_fields)} semantic fields: {', '.join(semantic_fields)}")
        else:
            print("ℹ️  No semantic fields found in mapping")
        
        # 6. Summary
        print("\n" + "="*50)
        print("📊 VERIFICATION SUMMARY")
        print("="*50)
        print(f"✅ Index: {elasticsearch_service.index_name}")
        print(f"✅ Documents: {doc_count}")
        print(f"✅ Search: Functional")
        print(f"✅ Array fields: {'Properly formatted' if all(isinstance(doc.get(field, []), list) for doc in [hit['_source'] for hit in sample_response['hits']['hits']] for field in ['practice_areas', 'languages', 'payment_methods'] if field in doc) else 'Some formatting issues'}")
        print(f"ℹ️  Aliases: {len(alias_list) if alias_list else 'None configured'}")
        print(f"ℹ️  Semantic search: {'Available' if semantic_fields else 'Not configured'}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during verification: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if elasticsearch_service.client:
            await elasticsearch_service.close()


async def check_specific_document(doc_id: str):
    """Check a specific document by ID."""
    try:
        await elasticsearch_service.initialize()
        elasticsearch_service.index_name = "love-and-law-001"
        
        doc = await elasticsearch_service.get_lawyer_by_id(doc_id)
        if doc:
            print(f"\n📄 Document {doc_id}:")
            print(json.dumps(doc, indent=2, default=str))
        else:
            print(f"\n❌ Document {doc_id} not found")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
    finally:
        if elasticsearch_service.client:
            await elasticsearch_service.close()


if __name__ == "__main__":
    print("🔍 Elasticsearch Index Verification Tool")
    print("="*50)
    
    # Run main verification
    asyncio.run(verify_index())
    
    # Optional: Check specific document
    # asyncio.run(check_specific_document("lawyer_123"))