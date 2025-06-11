"""
Script to upload lawyer data with semantic search capabilities using ELSER model.
This script processes lawyer data and creates semantic_text fields for enhanced search.
"""

import asyncio
import csv
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd
from datetime import datetime
import sys
from elasticsearch import AsyncElasticsearch, helpers
import numpy as np

# Add parent directory to path to import from src
sys.path.append(str(Path(__file__).parent.parent))

from src.services.elasticsearch_service import elasticsearch_service
from src.models.elasticsearch_mapping import LAWYER_INDEX_NAME, LAWYER_INDEX_MAPPING
from src.utils.logger import get_logger
from src.config.settings import settings

logger = get_logger(__name__)


class SemanticDataUploader:
    """Uploads lawyer data with semantic search fields to Elasticsearch."""

    def __init__(self, data_dir: str = "./.data"):
        self.data_dir = Path(data_dir)
        self.index_name = LAWYER_INDEX_NAME
        self.client: Optional[AsyncElasticsearch] = None
        
    async def initialize(self):
        """Initialize Elasticsearch connection and ensure index exists with proper pipeline."""
        # Configure connection
        if hasattr(settings, 'elasticsearch_api_key') and settings.elasticsearch_api_key:
            self.client = AsyncElasticsearch(
                hosts=[settings.elasticsearch_url],
                api_key=settings.elasticsearch_api_key,
                verify_certs=True
            )
        else:
            self.client = AsyncElasticsearch(
                hosts=[settings.elasticsearch_url],
                verify_certs=False,
                ssl_show_warn=False
            )
        
        # Check connection
        if not await self.client.ping():
            raise ConnectionError("Cannot connect to Elasticsearch")
            
        # Set up ELSER pipeline
        await self._setup_elser_pipeline()
        
        # Create index with semantic fields
        await self._create_semantic_index()
        
    async def _setup_elser_pipeline(self):
        """Set up ELSER model and ingest pipeline."""
        try:
            # Check if ELSER model is deployed
            try:
                model_info = await self.client.ml.get_trained_models(model_id=".elser_model_2_linux-x86_64")
                logger.info("ELSER model v2 is already deployed")
            except:
                logger.info("ELSER model not found, attempting to deploy...")
                # Deploy ELSER model
                await self.client.ml.put_trained_model(
                    model_id=".elser_model_2_linux-x86_64",
                    body={
                        "input": {"field_names": ["text_field"]}
                    }
                )
                
                # Start the deployment
                await self.client.ml.start_trained_model_deployment(
                    model_id=".elser_model_2_linux-x86_64",
                    wait_for="started"
                )
                logger.info("ELSER model deployed successfully")
                
            # Create ingest pipeline for semantic fields
            pipeline_id = "elser-v2-pipeline"
            pipeline_body = {
                "processors": [
                    {
                        "inference": {
                            "model_id": ".elser_model_2_linux-x86_64",
                            "input_output": [
                                {
                                    "input_field": "profile_semantic_input",
                                    "output_field": "profile_semantic"
                                },
                                {
                                    "input_field": "specialties_semantic_input",
                                    "output_field": "specialties_semantic"
                                },
                                {
                                    "input_field": "experience_semantic_input",
                                    "output_field": "experience_semantic"
                                },
                                {
                                    "input_field": "reviews_semantic_input",
                                    "output_field": "reviews_semantic"
                                }
                            ],
                            "on_failure": [
                                {
                                    "set": {
                                        "field": "_semantic_error",
                                        "value": "Semantic processing failed"
                                    }
                                }
                            ]
                        }
                    },
                    {
                        "remove": {
                            "field": [
                                "profile_semantic_input",
                                "specialties_semantic_input", 
                                "experience_semantic_input",
                                "reviews_semantic_input"
                            ],
                            "ignore_missing": True
                        }
                    }
                ]
            }
            
            await self.client.ingest.put_pipeline(
                id=pipeline_id,
                body=pipeline_body
            )
            logger.info(f"Created ingest pipeline: {pipeline_id}")
            
        except Exception as e:
            logger.warning(f"ELSER setup warning: {e}")
            logger.info("Continuing without ELSER - will use standard text search")
    
    async def _create_semantic_index(self):
        """Create index with semantic search mapping."""
        # Check if index exists
        if await self.client.indices.exists(index=self.index_name):
            logger.info(f"Index {self.index_name} already exists")
            # Optionally update mapping
            try:
                await self.client.indices.put_mapping(
                    index=self.index_name,
                    body=LAWYER_INDEX_MAPPING["mappings"]
                )
                logger.info("Updated index mapping")
            except Exception as e:
                logger.warning(f"Could not update mapping: {e}")
        else:
            # Create new index
            await self.client.indices.create(
                index=self.index_name,
                body=LAWYER_INDEX_MAPPING
            )
            logger.info(f"Created index: {self.index_name}")
            
        # Create aliases
        try:
            await self.client.indices.put_alias(
                index=self.index_name,
                name="lawyers"
            )
            await self.client.indices.put_alias(
                index=self.index_name,
                name="lawyers_read"
            )
            await self.client.indices.put_alias(
                index=self.index_name,
                name="lawyers_write"
            )
        except:
            pass  # Aliases might already exist
    
    async def upload_lawyers(self):
        """Load and upload lawyer data with semantic fields."""
        # Use the existing data loader to get transformed data
        from scripts.load_lawyer_data import LawyerDataLoader
        
        loader = LawyerDataLoader(data_dir=str(self.data_dir))
        
        # Load all data files
        logger.info("Loading data files...")
        loader._load_scorecard_weights()
        loader._load_normalized_mapping()
        loader._load_merged_lawyers()
        loader._load_locations()
        loader._load_source_data()
        loader._load_reviews()
        
        # Transform lawyers
        logger.info("Transforming lawyer data...")
        lawyers = loader._transform_lawyers()
        
        # Add semantic fields to each lawyer
        logger.info("Creating semantic fields...")
        semantic_lawyers = []
        
        for lawyer in lawyers:
            # Create semantic input fields by combining relevant text
            semantic_doc = {**lawyer}
            
            # Profile semantic: combine summary, education, experience, awards
            profile_parts = []
            if lawyer.get('profile_summary'):
                profile_parts.append(lawyer['profile_summary'])
            if lawyer.get('education'):
                profile_parts.append(f"Education: {lawyer['education']}")
            if lawyer.get('professional_experience'):
                profile_parts.append(f"Experience: {lawyer['professional_experience']}")
            if lawyer.get('awards'):
                profile_parts.append(f"Awards: {lawyer['awards']}")
            if lawyer.get('associations'):
                profile_parts.append(f"Associations: {lawyer['associations']}")
                
            semantic_doc['profile_semantic_input'] = " ".join(profile_parts)
            
            # Specialties semantic: combine practice areas and specialties
            specialty_parts = []
            if lawyer.get('practice_areas'):
                specialty_parts.extend(lawyer['practice_areas'])
            if lawyer.get('specialties'):
                for spec in lawyer['specialties']:
                    specialty_parts.append(f"{spec['name']} ({spec['category']})")
                    
            semantic_doc['specialties_semantic_input'] = " ".join(specialty_parts)
            
            # Experience semantic: years, licenses, quality signals
            exp_parts = []
            if lawyer.get('years_of_experience'):
                exp_parts.append(f"{lawyer['years_of_experience']} years of experience")
            if lawyer.get('licenses'):
                for lic in lawyer['licenses']:
                    exp_parts.append(f"Licensed in {lic['state']} since {lic.get('year_admitted', 'N/A')}")
            if lawyer.get('quality_signals'):
                signals = lawyer['quality_signals']
                if signals.get('education_score', 0) > 7:
                    exp_parts.append("Top-tier education")
                if signals.get('professional_score', 0) > 7:
                    exp_parts.append("Extensive professional experience")
                    
            semantic_doc['experience_semantic_input'] = " ".join(exp_parts)
            
            # Reviews semantic: combine review texts
            review_parts = []
            if lawyer.get('perplexity_review'):
                review_parts.append(lawyer['perplexity_review'])
            if lawyer.get('reviews'):
                for review in lawyer['reviews'][:5]:  # Limit to top 5 reviews
                    if review.get('text'):
                        review_parts.append(review['text'])
                        
            semantic_doc['reviews_semantic_input'] = " ".join(review_parts)
            
            semantic_lawyers.append(semantic_doc)
        
        # Bulk upload with pipeline
        logger.info(f"Uploading {len(semantic_lawyers)} lawyers to Elasticsearch...")
        
        actions = []
        for doc in semantic_lawyers:
            actions.append({
                "_index": self.index_name,
                "_id": doc.get("id"),
                "_source": doc
            })
        
        # Use bulk helper for efficient upload
        success_count = 0
        error_count = 0
        
        async for ok, result in helpers.async_streaming_bulk(
            self.client,
            actions,
            chunk_size=100,
            raise_on_error=False,
            max_retries=3
        ):
            if ok:
                success_count += 1
            else:
                error_count += 1
                if error_count <= 5:  # Log first 5 errors
                    logger.error(f"Failed to index document: {result}")
        
        logger.info(f"Upload complete: {success_count} successful, {error_count} errors")
        
        # Refresh index
        await self.client.indices.refresh(index=self.index_name)
        
        # Verify upload
        count_response = await self.client.count(index=self.index_name)
        logger.info(f"Total documents in index: {count_response['count']}")
        
    async def close(self):
        """Close Elasticsearch connection."""
        if self.client:
            await self.client.close()


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Upload lawyer data with semantic search')
    parser.add_argument('--data-dir', default='./.data', help='Directory containing CSV files')
    parser.add_argument('--clear-index', action='store_true', help='Clear existing index before loading')
    
    args = parser.parse_args()
    
    uploader = SemanticDataUploader(data_dir=args.data_dir)
    
    try:
        await uploader.initialize()
        
        if args.clear_index:
            try:
                await uploader.client.indices.delete(index=uploader.index_name)
                logger.info(f"Deleted existing index: {uploader.index_name}")
                await uploader._create_semantic_index()
            except:
                pass
        
        await uploader.upload_lawyers()
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise
    finally:
        await uploader.close()


if __name__ == "__main__":
    print("Uploading lawyer data with semantic search capabilities...")
    print("This script uses ELSER model for semantic text processing")
    print("-" * 50)
    
    asyncio.run(main())