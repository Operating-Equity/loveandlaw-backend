"""
Elasticsearch service for lawyer data management and search.
Uses the mapping structure defined in models/elasticsearch_mapping.py
"""

import asyncio
from typing import Dict, List, Any, Optional
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk
import numpy as np
from datetime import datetime
import logging

from src.models.elasticsearch_mapping import (
    LAWYER_INDEX_MAPPING,
    LAWYER_SUGGEST_INDEX_MAPPING,
    SEARCH_TEMPLATES,
    get_index_settings
)
from src.config.settings import settings

logger = logging.getLogger(__name__)


class ElasticsearchService:
    def __init__(self):
        self.client: Optional[AsyncElasticsearch] = None
        self.index_name = "lawyers_v1"
        self.suggest_index = "lawyers_suggest_v1"

    async def initialize(self):
        """Initialize Elasticsearch connection and ensure indices exist."""
        # Configure connection based on whether API key is provided
        if hasattr(settings, 'elasticsearch_api_key') and settings.elasticsearch_api_key:
            # Use API key authentication for Elastic Cloud
            self.client = AsyncElasticsearch(
                hosts=[settings.elasticsearch_url],
                api_key=settings.elasticsearch_api_key,
                verify_certs=True
            )
        elif hasattr(settings, 'ELASTICSEARCH_USER') and settings.ELASTICSEARCH_USER:
            # Use basic auth if available
            self.client = AsyncElasticsearch(
                hosts=[settings.ELASTICSEARCH_URL],
                http_auth=(settings.ELASTICSEARCH_USER, settings.ELASTICSEARCH_PASSWORD),
                verify_certs=False,
                ssl_show_warn=False
            )
        else:
            # Basic connection for local development
            self.client = AsyncElasticsearch(
                hosts=[settings.elasticsearch_url],
                verify_certs=False,
                ssl_show_warn=False
            )

        # Check connection
        if not await self.client.ping():
            raise ConnectionError("Cannot connect to Elasticsearch")

        # Create indices if they don't exist
        await self._ensure_indices()

    async def _ensure_indices(self):
        """Create indices with proper mappings if they don't exist."""
        # Main lawyer index
        if not await self.client.indices.exists(index=self.index_name):
            await self.client.indices.create(
                index=self.index_name,
                body=LAWYER_INDEX_MAPPING
            )
            logger.info(f"Created index: {self.index_name}")

        # Suggestion index
        if not await self.client.indices.exists(index=self.suggest_index):
            await self.client.indices.create(
                index=self.suggest_index,
                body=LAWYER_SUGGEST_INDEX_MAPPING
            )
            logger.info(f"Created index: {self.suggest_index}")

    async def index_lawyer(self, lawyer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Index a single lawyer document."""
        # Transform data to match mapping structure
        doc = self._transform_lawyer_data(lawyer_data)

        # Index main document
        result = await self.client.index(
            index=self.index_name,
            id=doc.get("id"),
            body=doc,
            refresh="wait_for"
        )

        # Index suggestion data
        if doc.get("name"):
            await self._index_suggestion(doc)

        return result

    async def bulk_index_lawyers(self, lawyers_data: List[Dict[str, Any]],
                                batch_size: int = 100) -> Dict[str, Any]:
        """Bulk index multiple lawyers."""
        actions = []
        suggest_actions = []

        for lawyer in lawyers_data:
            doc = self._transform_lawyer_data(lawyer)

            # Main index action
            actions.append({
                "_index": self.index_name,
                "_id": doc.get("id"),
                "_source": doc
            })

            # Suggestion index action
            if doc.get("name"):
                suggest_actions.append({
                    "_index": self.suggest_index,
                    "_source": self._create_suggestion_doc(doc)
                })

        # Bulk index main documents
        success, errors = await async_bulk(
            self.client,
            actions,
            chunk_size=batch_size,
            raise_on_error=False
        )

        # Bulk index suggestions
        if suggest_actions:
            await async_bulk(
                self.client,
                suggest_actions,
                chunk_size=batch_size,
                raise_on_error=False
            )

        return {
            "indexed": success,
            "errors": errors,
            "total": len(lawyers_data)
        }

    async def search_lawyers(self,
                           query_text: Optional[str] = None,
                           filters: Optional[Dict[str, Any]] = None,
                           location: Optional[Dict[str, float]] = None,
                           distance: str = "50mi",
                           size: int = 10,
                           use_semantic: bool = True) -> List[Dict[str, Any]]:
        """
        Search for lawyers using hybrid search (keyword + semantic).

        Args:
            query_text: Text query for searching profiles
            filters: Dictionary of filters (practice_areas, state, etc.)
            location: {"lat": float, "lon": float} for geo queries
            distance: Distance for location-based search
            size: Number of results to return
            use_semantic: Whether to include semantic search
        """
        query = {"bool": {"must": [], "should": [], "filter": []}}

        # Text search
        if query_text:
            query["bool"]["should"].append({
                "multi_match": {
                    "query": query_text,
                    "fields": [
                        "profile_summary^3",
                        "specialties.name^2",
                        "practice_areas^2",
                        "professional_experience",
                        "case_types_handled",
                        "reviews.text",
                        "name^1.5"
                    ],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            })

            # Semantic search if embedding is provided
            if use_semantic and hasattr(self, '_get_embedding'):
                embedding = await self._get_embedding(query_text)
                if embedding:
                    query["bool"]["should"].append({
                        "knn": {
                            "field": "profile_embedding",
                            "query_vector": embedding,
                            "k": 50,
                            "num_candidates": 200,
                            "boost": 0.3
                        }
                    })

        # Apply filters
        if filters:
            filter_queries = self._build_filter_queries(filters)
            query["bool"]["filter"].extend(filter_queries)

        # Location-based filtering
        if location:
            query["bool"]["filter"].append({
                "geo_distance": {
                    "distance": distance,
                    "location": location
                }
            })

        # Add quality boosting factors (removed numeric comparisons that might fail with string data)
        query["bool"]["should"].extend([
            {"term": {"active": {"value": True, "boost": 3.0}}}
        ])

        # Execute search
        response = await self.client.search(
            index=self.index_name,
            body={
                "query": query,
                "size": size,
                "_source": {
                    "excludes": ["profile_embedding", "specialty_embeddings"]
                },
                "sort": [
                    "_score",
                    {"ratings.overall": {"order": "desc", "missing": "_last"}}
                ]
            }
        )

        # Transform results
        results = []
        for hit in response["hits"]["hits"]:
            lawyer = hit["_source"]
            lawyer["match_score"] = hit["_score"]
            lawyer["search_explanation"] = self._generate_match_explanation(hit, query_text)
            results.append(lawyer)

        return results

    async def get_lawyer_by_id(self, lawyer_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific lawyer by ID."""
        try:
            response = await self.client.get(
                index=self.index_name,
                id=lawyer_id
            )
            return response["_source"]
        except:
            return None

    async def update_lawyer(self, lawyer_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a lawyer document."""
        updates["last_updated"] = datetime.utcnow().isoformat()

        return await self.client.update(
            index=self.index_name,
            id=lawyer_id,
            body={"doc": updates},
            refresh="wait_for"
        )

    async def suggest_lawyers(self, prefix: str, state: Optional[str] = None,
                            specialty: Optional[str] = None, size: int = 5) -> List[Dict[str, Any]]:
        """Get lawyer name suggestions for autocomplete."""
        contexts = {}
        if state:
            contexts["state"] = [state]
        if specialty:
            contexts["specialty"] = [specialty]

        body = {
            "suggest": {
                "lawyer-suggest": {
                    "prefix": prefix,
                    "completion": {
                        "field": "suggest",
                        "size": size,
                        "skip_duplicates": True,
                        "contexts": contexts if contexts else None
                    }
                }
            }
        }

        response = await self.client.search(
            index=self.suggest_index,
            body=body
        )

        suggestions = []
        for option in response["suggest"]["lawyer-suggest"][0]["options"]:
            suggestions.append(option["_source"])

        return suggestions

    async def advanced_semantic_search(self,
                                      query_text: str,
                                      context: Optional[str] = None,
                                      filters: Optional[Dict[str, Any]] = None,
                                      size: int = 10) -> List[Dict[str, Any]]:
        """
        Advanced semantic search specifically optimized for natural language queries.
        
        Args:
            query_text: Natural language query
            context: Additional context about the user's situation
            filters: Standard filters (location, budget, etc.)
            size: Number of results
        """
        # Build enhanced query with context
        enhanced_query = query_text
        if context:
            enhanced_query = f"{context} Looking for: {query_text}"
            
        # Build semantic-focused query
        query = {
            "bool": {
                "should": [
                    # Primary semantic search
                    {
                        "semantic": {
                            "field": "profile_semantic",
                            "query": enhanced_query,
                            "boost": 3.0
                        }
                    },
                    {
                        "semantic": {
                            "field": "specialties_semantic",
                            "query": query_text,  # Use original for specialties
                            "boost": 2.5
                        }
                    },
                    # Fallback text search for exact matches
                    {
                        "multi_match": {
                            "query": query_text,
                            "fields": ["name^2", "practice_areas^1.5"],
                            "type": "phrase_prefix"
                        }
                    }
                ],
                "filter": [],
                "minimum_should_match": 1
            }
        }
        
        # Apply filters
        if filters:
            filter_queries = self._build_filter_queries(filters)
            query["bool"]["filter"].extend(filter_queries)
            
        # Always filter for active lawyers
        query["bool"]["filter"].append({"term": {"active": True}})
        
        # Execute search with special handling for semantic fields
        response = await self.client.search(
            index=self.index_name,
            body={
                "query": query,
                "size": size,
                "_source": {
                    "excludes": [
                        "*_embedding",
                        "*_semantic",
                        "*_semantic_input"
                    ]
                },
                "sort": [
                    "_score",
                    {"ratings.overall": {"order": "desc", "missing": "_last"}}
                ],
                "explain": False  # Set to True for debugging
            }
        )
        
        # Process and return results
        results = []
        for hit in response["hits"]["hits"]:
            lawyer = hit["_source"]
            lawyer["match_score"] = hit["_score"]
            lawyer["match_type"] = "semantic"
            results.append(lawyer)
            
        return results

    async def close(self):
        """Close Elasticsearch connection."""
        if self.client:
            await self.client.close()

    def _transform_lawyer_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw lawyer data to match Elasticsearch mapping."""
        # This is a simplified transformation - extend based on actual data
        doc = {
            "id": raw_data.get("id"),
            "normalized_id": raw_data.get("normalized_name_id", raw_data.get("id")),
            "name": raw_data.get("name"),
            "city": raw_data.get("city"),
            "state": raw_data.get("state"),
            "active": True,
            "last_updated": datetime.utcnow().isoformat()
        }

        # Location
        if "coordinate" in raw_data or "location" in raw_data:
            coord = raw_data.get("coordinate") or raw_data.get("location", {})
            if isinstance(coord, dict) and "lat" in coord and "lon" in coord:
                doc["location"] = {"lat": coord["lat"], "lon": coord["lon"]}
            elif isinstance(coord, str) and "POINT" in coord:
                # Parse PostGIS format
                import re
                match = re.match(r'POINT \(([-\d.]+) ([-\d.]+)\)', coord)
                if match:
                    doc["location"] = {"lat": float(match.group(2)), "lon": float(match.group(1))}

        # Practice areas and specialties
        if "categories" in raw_data:
            doc["practice_areas"] = raw_data["categories"]
        elif "practice_areas" in raw_data:
            doc["practice_areas"] = raw_data["practice_areas"]

        # Ratings
        doc["ratings"] = {
            "overall": raw_data.get("rating", raw_data.get("perplexity_score"))
        }

        # Professional info
        for field in ["profile_summary", "education", "professional_experience",
                     "awards", "associations"]:
            if field in raw_data:
                doc[field] = raw_data[field]

        # Languages and payment methods
        if "languages" in raw_data:
            doc["languages"] = raw_data["languages"] if isinstance(raw_data["languages"], list) else [raw_data["languages"]]
        if "payment_methods" in raw_data:
            doc["payment_methods"] = raw_data["payment_methods"] if isinstance(raw_data["payment_methods"], list) else [raw_data["payment_methods"]]

        # Contact info
        if "profile_phones" in raw_data:
            doc["phone_numbers"] = raw_data["profile_phones"] if isinstance(raw_data["profile_phones"], list) else [raw_data["profile_phones"]]

        return doc

    def _build_filter_queries(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build Elasticsearch filter queries from filter dictionary."""
        filter_queries = []

        # Practice areas
        if "practice_areas" in filters:
            areas = filters["practice_areas"]
            if isinstance(areas, str):
                areas = [areas]
            filter_queries.append({
                "terms": {"practice_areas.keyword": areas}
            })

        # State
        if "state" in filters:
            filter_queries.append({
                "term": {"state": filters["state"]}
            })

        # City
        if "city" in filters:
            filter_queries.append({
                "term": {"city.keyword": filters["city"]}
            })

        # Languages
        if "languages" in filters:
            langs = filters["languages"]
            if isinstance(langs, str):
                langs = [langs]
            filter_queries.append({
                "terms": {"languages": langs}
            })

        # Fee structure
        if "free_consultation" in filters:
            filter_queries.append({
                "term": {"fee_structure.free_consultation": filters["free_consultation"]}
            })

        # Years of experience
        if "min_experience" in filters:
            filter_queries.append({
                "range": {"years_of_experience": {"gte": filters["min_experience"]}}
            })

        # Rating
        if "min_rating" in filters:
            filter_queries.append({
                "range": {"ratings.overall": {"gte": filters["min_rating"]}}
            })

        return filter_queries

    def _create_suggestion_doc(self, lawyer: Dict[str, Any]) -> Dict[str, Any]:
        """Create a suggestion document for autocomplete."""
        contexts = {}
        if lawyer.get("state"):
            contexts["state"] = [lawyer["state"]]
            
        # Ensure practice_areas is a list
        practice_areas = lawyer.get("practice_areas", [])
        if isinstance(practice_areas, str):
            practice_areas = [practice_areas]
        elif not isinstance(practice_areas, list):
            practice_areas = []
            
        if practice_areas:
            contexts["specialty"] = practice_areas[:3]  # Top 3 specialties
            
        return {
            "lawyer_id": lawyer["id"],
            "suggest": {
                "input": [lawyer["name"]] + practice_areas[:3],
                "contexts": contexts
            },
            "name": lawyer["name"],
            "city": lawyer.get("city"),
            "state": lawyer.get("state"),
            "specialties": practice_areas[:3]
        }

    def _generate_match_explanation(self, hit: Dict[str, Any], query_text: Optional[str]) -> str:
        """Generate a human-readable explanation of why this lawyer matched."""
        explanations = []

        if query_text and hit.get("highlight"):
            explanations.append(f"Profile matches '{query_text}'")

        source = hit["_source"]
        rating = source.get("ratings", {}).get("overall", 0)
        try:
            if isinstance(rating, str):
                rating = float(rating)
            if rating >= 4.5:
                explanations.append("Highly rated lawyer")
        except (ValueError, TypeError):
            pass

        years_exp = source.get("years_of_experience", 0)
        try:
            if isinstance(years_exp, str):
                years_exp = int(years_exp)
            if years_exp >= 15:
                explanations.append("Extensive experience")
        except (ValueError, TypeError):
            pass

        return " • ".join(explanations) if explanations else "General match"


# Singleton instance
elasticsearch_service = ElasticsearchService()
