#!/usr/bin/env python3
"""Test script to verify data loading setup"""

import os
from pathlib import Path
import pandas as pd

def test_data_directory():
    """Check if .data directory and files exist"""
    data_dir = Path("./.data")
    
    if not data_dir.exists():
        print("❌ .data directory not found!")
        return False
    
    print("✅ .data directory found")
    
    # Check for required files
    required_files = [
        "merged_lawyers.csv",
        "lawyer_normalized_mapping.csv",
        "merged_lawyers_locations.csv",
        "merged_lawyers_source_data.csv",
        "googleplacesreview.csv",
        "perplexityreview.csv",
        "scorecardweights.csv"
    ]
    
    all_files_exist = True
    for file in required_files:
        file_path = data_dir / file
        if file_path.exists():
            size_mb = file_path.stat().st_size / (1024 * 1024)
            print(f"✅ {file}: {size_mb:.2f} MB")
        else:
            print(f"❌ {file}: NOT FOUND")
            all_files_exist = False
    
    return all_files_exist

def test_csv_loading():
    """Try loading a small sample from each CSV"""
    try:
        print("\n📊 Testing CSV loading...")
        
        # Test loading the scorecard weights (small file)
        scorecard_df = pd.read_csv("./.data/scorecardweights.csv", nrows=5)
        print(f"✅ Scorecard weights loaded: {scorecard_df.shape[0]} rows, {scorecard_df.shape[1]} columns")
        
        # Test loading lawyers data (just headers)
        lawyers_df = pd.read_csv("./.data/merged_lawyers.csv", nrows=1)
        print(f"✅ Merged lawyers columns: {list(lawyers_df.columns)[:5]}... ({len(lawyers_df.columns)} total)")
        
        return True
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return False

def test_elasticsearch_connection():
    """Check if Elasticsearch is accessible"""
    import urllib.request
    import json
    
    try:
        print("\n🔍 Testing Elasticsearch connection...")
        req = urllib.request.Request("http://localhost:9200")
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read())
            print(f"✅ Elasticsearch {data['version']['number']} is running")
            return True
    except Exception as e:
        print(f"❌ Elasticsearch not accessible: {e}")
        print("💡 Run ./start-elasticsearch.sh to start Elasticsearch")
        return False

def main():
    print("🔧 Testing LoveAndLaw data loading setup\n")
    
    # Run tests
    data_ok = test_data_directory()
    csv_ok = test_csv_loading() if data_ok else False
    es_ok = test_elasticsearch_connection()
    
    print("\n📋 Summary:")
    print(f"  Data files: {'✅ OK' if data_ok else '❌ FAILED'}")
    print(f"  CSV loading: {'✅ OK' if csv_ok else '❌ FAILED'}")
    print(f"  Elasticsearch: {'✅ OK' if es_ok else '❌ FAILED'}")
    
    if data_ok and csv_ok:
        print("\n✨ Ready to load data!")
        print("Run: python scripts/load_lawyer_data.py")
    else:
        print("\n⚠️  Please fix the issues above before proceeding")

if __name__ == "__main__":
    main()