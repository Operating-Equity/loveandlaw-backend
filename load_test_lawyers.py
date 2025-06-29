"""
Quick script to load a few test lawyers for intelligent matching demo
"""

import asyncio
from elasticsearch import AsyncElasticsearch
import json

test_lawyers = [
    {
        "id": 10001,
        "name": "Sarah Kim",
        "firm": "Kim Family Law",
        "city": "Los Angeles",
        "state": "california",
        "languages": ["English", "Korean"],
        "practice_areas": ["Family Law"],
        "specialties": [{"name": "Child Custody", "category": "Family Law"}],
        "profile": "Aggressive advocate for parents in high-conflict custody battles. Korean-speaking attorney who understands cultural sensitivities.",
        "budget_range": "$$",
        "overall_rating": 4.8,
        "reviews_count": 127,
        "quality_signals": {
            "response_time_hours": 2,
            "education_score": 0.9,
            "professional_score": 0.85
        },
        "fee_structure": {
            "free_consultation": True,
            "hourly_rate_min": 250,
            "payment_plans": True
        }
    },
    {
        "id": 10002, 
        "name": "Michael Chen",
        "firm": "Peaceful Resolutions Law",
        "city": "Chicago",
        "state": "illinois",
        "practice_areas": ["Family Law"],
        "specialties": [{"name": "Collaborative Divorce", "category": "Family Law"}],
        "profile": "Collaborative divorce specialist focused on peaceful resolutions and co-parenting success. Offers flexible payment plans.",
        "budget_range": "$",
        "overall_rating": 4.6,
        "reviews_count": 89,
        "fee_structure": {
            "free_consultation": True,
            "hourly_rate_min": 150,
            "payment_plans": True
        }
    },
    {
        "id": 10003,
        "name": "Elizabeth Sterling",
        "firm": "Sterling & Associates",
        "city": "New York",
        "state": "new-york",
        "practice_areas": ["Family Law"],
        "specialties": [{"name": "High Asset Divorce", "category": "Family Law"}],
        "profile": "Top-tier attorney handling complex high-asset divorces with international properties and business valuations.",
        "budget_range": "$$$$",
        "overall_rating": 4.9,
        "reviews_count": 203,
        "quality_signals": {
            "education_score": 0.95,
            "professional_score": 0.95,
            "awards_score": 0.9
        }
    },
    {
        "id": 10004,
        "name": "Maria Rodriguez",
        "firm": "Safe Haven Legal",
        "city": "Phoenix", 
        "state": "arizona",
        "gender": "female",
        "practice_areas": ["Family Law"],
        "specialties": [{"name": "Domestic Violence", "category": "Family Law"}],
        "profile": "Compassionate female attorney specializing in domestic violence cases. Patient, understanding approach with trauma-informed practice.",
        "budget_range": "$$",
        "overall_rating": 4.7,
        "reviews_count": 156,
        "reviews": [
            {"text": "She was so patient and understanding during my difficult time", "rating": 5}
        ]
    },
    {
        "id": 10005,
        "name": "Carlos Martinez",
        "firm": "Martinez Legal Aid",
        "city": "Miami",
        "state": "florida", 
        "languages": ["English", "Spanish"],
        "practice_areas": ["Family Law"],
        "specialties": [{"name": "Child Support", "category": "Family Law"}],
        "profile": "Spanish-speaking attorney helping families with child support matters. Affordable rates and payment plans available.",
        "budget_range": "$",
        "overall_rating": 4.5,
        "reviews_count": 112,
        "fee_structure": {
            "free_consultation": True,
            "hourly_rate_min": 125,
            "payment_plans": True
        }
    }
]

async def load_test_data():
    """Load test lawyers into Elasticsearch"""
    
    es = AsyncElasticsearch("http://localhost:9200")
    
    try:
        # Create index if not exists
        if not await es.indices.exists(index="love-and-law-001"):
            await es.indices.create(index="love-and-law-001")
        
        # Load test lawyers
        for lawyer in test_lawyers:
            await es.index(
                index="love-and-law-001",
                id=lawyer["id"],
                body=lawyer
            )
        
        # Refresh index
        await es.indices.refresh(index="love-and-law-001")
        
        # Verify
        count = await es.count(index="love-and-law-001")
        print(f"✅ Loaded {count['count']} test lawyers")
        
    finally:
        await es.close()

if __name__ == "__main__":
    asyncio.run(load_test_data())