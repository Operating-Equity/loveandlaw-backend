"""
Elasticsearch mapping structure for lawyer data model.
This defines the schema for efficient lawyer search with both keyword (BM25) and semantic vector search.
"""

from typing import Dict, Any


# Index name as specified in documentation
LAWYER_INDEX_NAME = "love-and-law-001"

LAWYER_INDEX_MAPPING: Dict[str, Any] = {
    "settings": {
        "analysis": {
            "analyzer": {
                "lowercase_keyword": {
                    "type": "custom",
                    "tokenizer": "keyword",
                    "filter": ["lowercase"]
                },
                "name_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "asciifolding"]
                },
                "description_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "stop", "snowball"]
                }
            }
        },
        "index": {
            "number_of_shards": 3,
            "number_of_replicas": 1,
            "refresh_interval": "30s",
            # Enable ELSER model for semantic search
            "default_pipeline": "elser-v2-pipeline"
        }
    },
    "mappings": {
        "properties": {
            # Core identification
            "id": {"type": "integer"},
            "normalized_id": {"type": "integer"},
            "name": {
                "type": "text",
                "analyzer": "name_analyzer",
                "fields": {
                    "keyword": {"type": "keyword"},
                    "suggest": {"type": "completion"}
                }
            },

            # Location data for geo queries
            "location": {
                "type": "geo_point"
            },
            "city": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword"}}
            },
            "state": {
                "type": "keyword"
            },
            "addresses": {
                "type": "nested",
                "properties": {
                    "formatted_address": {"type": "text"},
                    "street": {"type": "text"},
                    "city": {"type": "keyword"},
                    "state": {"type": "keyword"},
                    "zip": {"type": "keyword"},
                    "location": {"type": "geo_point"},
                    "place_id": {"type": "keyword"}
                }
            },

            # Practice areas and specialties for filtering
            "practice_areas": {
                "type": "text",
                "analyzer": "lowercase_keyword",
                "fields": {"keyword": {"type": "keyword"}}
            },
            "specialties": {
                "type": "nested",
                "properties": {
                    "name": {"type": "keyword"},
                    "category": {"type": "keyword"},
                    "subcategory": {"type": "keyword"},
                    "experience_years": {"type": "float"}
                }
            },

            # Quality signals for ranking
            "ratings": {
                "properties": {
                    "google": {"type": "float"},
                    "avvo": {"type": "float"},
                    "justia": {"type": "float"},
                    "findlaw": {"type": "float"},
                    "overall": {"type": "float"},
                    "review_count": {"type": "integer"}
                }
            },

            # Reviews for sentiment and keyword matching
            "reviews": {
                "type": "nested",
                "properties": {
                    "source": {"type": "keyword"},
                    "rating": {"type": "float"},
                    "text": {
                        "type": "text",
                        "analyzer": "description_analyzer"
                    },
                    "timestamp": {"type": "date"},
                    "sentiment_score": {"type": "float"}
                }
            },

            # Professional information
            "profile_summary": {
                "type": "text",
                "analyzer": "description_analyzer",
                "fields": {
                    "keyword": {"type": "keyword", "ignore_above": 10000}
                }
            },
            "education": {
                "type": "text",
                "analyzer": "description_analyzer"
            },
            "professional_experience": {
                "type": "text",
                "analyzer": "description_analyzer"
            },
            "awards": {
                "type": "text",
                "analyzer": "description_analyzer"
            },
            "associations": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword"}}
            },

            # Licenses and bar admissions
            "licenses": {
                "type": "nested",
                "properties": {
                    "state": {"type": "keyword"},
                    "status": {"type": "keyword"},
                    "year_admitted": {"type": "integer"},
                    "duration_years": {"type": "float"},
                    "has_disciplinary_actions": {"type": "boolean"}
                }
            },
            "years_of_experience": {"type": "float"},

            # Client preferences
            "languages": {
                "type": "keyword"
            },
            "payment_methods": {
                "type": "keyword"
            },
            "fee_structure": {
                "properties": {
                    "consultation_fee": {"type": "float"},
                    "hourly_rate_min": {"type": "float"},
                    "hourly_rate_max": {"type": "float"},
                    "flat_fee_available": {"type": "boolean"},
                    "payment_plans": {"type": "boolean"},
                    "free_consultation": {"type": "boolean"}
                }
            },

            # Contact information
            "phone_numbers": {
                "type": "keyword"
            },
            "website": {"type": "keyword"},
            "profile_urls": {
                "properties": {
                    "avvo": {"type": "keyword"},
                    "justia": {"type": "keyword"},
                    "findlaw": {"type": "keyword"}
                }
            },

            # Scoring and quality metrics
            "scorecards": {
                "type": "nested",
                "properties": {
                    "specialty": {"type": "keyword"},
                    "score": {"type": "float"},
                    "weights": {"type": "object", "enabled": False}
                }
            },
            "quality_signals": {
                "properties": {
                    "education_score": {"type": "float"},
                    "professional_score": {"type": "float"},
                    "awards_score": {"type": "float"},
                    "associations_score": {"type": "float"},
                    "response_time_hours": {"type": "float"},
                    "client_satisfaction": {"type": "float"}
                }
            },

            # AI-generated content and embeddings
            "perplexity_score": {"type": "float"},
            "perplexity_review": {
                "type": "text",
                "analyzer": "description_analyzer"
            },

            # Semantic search fields using ELSER model
            "profile_semantic": {
                "type": "semantic_text",
                "inference_id": ".elser-2-elasticsearch"  # Built-in ELSER v2 model
            },
            "specialties_semantic": {
                "type": "semantic_text",
                "inference_id": ".elser-2-elasticsearch"
            },
            "experience_semantic": {
                "type": "semantic_text",
                "inference_id": ".elser-2-elasticsearch"
            },
            "reviews_semantic": {
                "type": "semantic_text",
                "inference_id": ".elser-2-elasticsearch"
            },

            # Dense vectors for additional semantic search (optional fallback)
            "profile_embedding": {
                "type": "dense_vector",
                "dims": 1536,  # OpenAI ada-3 dimensions
                "index": True,
                "similarity": "cosine"
            },
            "specialty_embeddings": {
                "type": "nested",
                "properties": {
                    "specialty": {"type": "keyword"},
                    "embedding": {
                        "type": "dense_vector",
                        "dims": 1536,
                        "index": True,
                        "similarity": "cosine"
                    }
                }
            },

            # Metadata
            "last_updated": {"type": "date"},
            "active": {"type": "boolean"},
            "verification_status": {"type": "keyword"},

            # Additional searchable content
            "blog_content": {
                "type": "text",
                "analyzer": "description_analyzer"
            },
            "case_types_handled": {
                "type": "text",
                "analyzer": "lowercase_keyword",
                "fields": {"keyword": {"type": "keyword"}}
            },

            # Demographics (for diversity matching if requested)
            "gender": {"type": "keyword"},
            "lgbtq_friendly": {"type": "boolean"},
            "accessibility_features": {"type": "keyword"}
        }
    }
}


# Separate index for faster autocomplete/suggestions
LAWYER_SUGGEST_INDEX_MAPPING: Dict[str, Any] = {
    "settings": {
        "index": {
            "number_of_shards": 1,
            "number_of_replicas": 1
        }
    },
    "mappings": {
        "properties": {
            "lawyer_id": {"type": "integer"},
            "suggest": {
                "type": "completion",
                "contexts": [
                    {
                        "name": "state",
                        "type": "category"
                    },
                    {
                        "name": "specialty",
                        "type": "category"
                    }
                ]
            },
            "name": {"type": "keyword"},
            "city": {"type": "keyword"},
            "state": {"type": "keyword"},
            "specialties": {"type": "keyword"}
        }
    }
}


# Query templates for common search patterns
SEARCH_TEMPLATES = {
    "hybrid_search": {
        "query": {
            "bool": {
                "must": [],
                "should": [
                    {
                        "multi_match": {
                            "query": "{{query_text}}",
                            "fields": [
                                "profile_summary^3",
                                "specialties.name^2",
                                "practice_areas^2",
                                "professional_experience",
                                "case_types_handled",
                                "reviews.text"
                            ],
                            "type": "best_fields",
                            "fuzziness": "AUTO"
                        }
                    },
                    {
                        "knn": {
                            "field": "profile_embedding",
                            "query_vector": "{{query_embedding}}",
                            "k": 100,
                            "num_candidates": 1000,
                            "boost": 0.3
                        }
                    }
                ],
                "filter": []
            }
        }
    },

    "location_based": {
        "query": {
            "bool": {
                "must": [
                    {
                        "geo_distance": {
                            "distance": "{{distance}}",
                            "location": {
                                "lat": "{{lat}}",
                                "lon": "{{lon}}"
                            }
                        }
                    }
                ]
            }
        }
    },

    "specialty_match": {
        "query": {
            "nested": {
                "path": "specialties",
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"specialties.category": "{{category}}"}}
                        ],
                        "should": [
                            {"range": {"specialties.experience_years": {"gte": 5}}}
                        ]
                    }
                }
            }
        }
    }
}


def get_index_settings(index_name: str = LAWYER_INDEX_NAME) -> Dict[str, Any]:
    """Get the complete index settings including aliases."""
    return {
        "index": index_name,
        "body": {
            **LAWYER_INDEX_MAPPING,
            "aliases": {
                "lawyers": {},
                "lawyers_read": {},
                "lawyers_write": {}
            }
        }
    }
