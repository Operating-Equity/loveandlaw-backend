#!/usr/bin/env python3
"""Populate Elasticsearch with sample lawyer data"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.services.database import elasticsearch_service
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Sample lawyer data
SAMPLE_LAWYERS = [
    {
        "id": "lawyer-001",
        "name": "Sarah Johnson",
        "firm": "Johnson Family Law",
        "practice_areas": ["divorce", "custody", "child_support"],
        "location": {
            "zip": "19104",
            "city": "Philadelphia",
            "state": "PA",
            "coordinates": {"lat": 39.9526, "lon": -75.1652}
        },
        "description": "Compassionate family law attorney with 15 years experience helping families navigate difficult transitions. Specializes in collaborative divorce and child custody arrangements.",
        "budget_range": "$$",
        "rating": 4.8,
        "reviews_count": 127
    },
    {
        "id": "lawyer-002",
        "name": "Michael Chen",
        "firm": "Chen & Associates",
        "practice_areas": ["divorce", "property_division", "alimony"],
        "location": {
            "zip": "19103",
            "city": "Philadelphia",
            "state": "PA",
            "coordinates": {"lat": 39.9496, "lon": -75.1703}
        },
        "description": "Experienced divorce attorney focused on fair property division and spousal support negotiations. Known for strategic approach and attention to detail.",
        "budget_range": "$$$",
        "rating": 4.6,
        "reviews_count": 89
    },
    {
        "id": "lawyer-003",
        "name": "Maria Rodriguez",
        "firm": "Rodriguez Legal Services",
        "practice_areas": ["custody", "visitation", "domestic_violence"],
        "location": {
            "zip": "19107",
            "city": "Philadelphia",
            "state": "PA",
            "coordinates": {"lat": 39.9488, "lon": -75.1486}
        },
        "description": "Dedicated advocate for parents and children in custody disputes. Extensive experience with domestic violence cases and protective orders.",
        "budget_range": "$$",
        "rating": 4.9,
        "reviews_count": 156
    },
    {
        "id": "lawyer-004",
        "name": "David Thompson",
        "firm": "Thompson & Partners",
        "practice_areas": ["divorce", "mediation", "prenuptial"],
        "location": {
            "zip": "19106",
            "city": "Philadelphia",
            "state": "PA",
            "coordinates": {"lat": 39.9475, "lon": -75.1433}
        },
        "description": "Certified mediator helping couples reach amicable divorce settlements. Also handles prenuptial and postnuptial agreements.",
        "budget_range": "$$$",
        "rating": 4.7,
        "reviews_count": 98
    },
    {
        "id": "lawyer-005",
        "name": "Lisa Anderson",
        "firm": "Anderson Family Law Center",
        "practice_areas": ["adoption", "guardianship", "paternity"],
        "location": {
            "zip": "19102",
            "city": "Philadelphia", 
            "state": "PA",
            "coordinates": {"lat": 39.9534, "lon": -75.1685}
        },
        "description": "Specializes in adoption law, guardianship matters, and paternity cases. Committed to helping families grow and protect their children.",
        "budget_range": "$$",
        "rating": 5.0,
        "reviews_count": 67
    },
    {
        "id": "lawyer-006",
        "name": "James Wilson",
        "firm": "Wilson Legal Group",
        "practice_areas": ["divorce", "custody", "property_division"],
        "location": {
            "zip": "10001",
            "city": "New York",
            "state": "NY",
            "coordinates": {"lat": 40.7505, "lon": -73.9965}
        },
        "description": "Manhattan-based family law attorney with expertise in high-asset divorces and complex custody arrangements.",
        "budget_range": "$$$$",
        "rating": 4.5,
        "reviews_count": 203
    },
    {
        "id": "lawyer-007",
        "name": "Emily Brown",
        "firm": "Brown & Associates",
        "practice_areas": ["divorce", "child_support", "alimony"],
        "location": {
            "zip": "19104",
            "city": "Philadelphia",
            "state": "PA",
            "coordinates": {"lat": 39.9584, "lon": -75.1967}
        },
        "description": "Affordable family law representation focusing on child support and alimony modifications. Free consultations available.",
        "budget_range": "$",
        "rating": 4.4,
        "reviews_count": 72
    },
    {
        "id": "lawyer-008",
        "name": "Robert Kim",
        "firm": "Kim Law Offices",
        "practice_areas": ["custody", "visitation", "relocation"],
        "location": {
            "zip": "19147",
            "city": "Philadelphia",
            "state": "PA",
            "coordinates": {"lat": 39.9309, "lon": -75.1534}
        },
        "description": "Child custody specialist with focus on interstate custody disputes and relocation cases. Bilingual services available.",
        "budget_range": "$$",
        "rating": 4.7,
        "reviews_count": 114
    }
]


async def populate_lawyers():
    """Populate Elasticsearch with sample lawyer data"""
    try:
        # Initialize Elasticsearch
        await elasticsearch_service.initialize()
        logger.info("Connected to Elasticsearch")
        
        # Index each lawyer
        success_count = 0
        for lawyer in SAMPLE_LAWYERS:
            try:
                await elasticsearch_service.index_lawyer(lawyer)
                success_count += 1
                logger.info(f"Indexed lawyer: {lawyer['name']} ({lawyer['id']})")
            except Exception as e:
                logger.error(f"Failed to index {lawyer['name']}: {e}")
        
        logger.info(f"Successfully indexed {success_count}/{len(SAMPLE_LAWYERS)} lawyers")
        
        # Test search
        logger.info("\nTesting search functionality...")
        
        # Search by zip code
        results = await elasticsearch_service.search_lawyers({"zip": "19104"})
        logger.info(f"Found {len(results)} lawyers in zip 19104")
        
        # Search by practice area
        results = await elasticsearch_service.search_lawyers({"practice_areas": ["custody"]})
        logger.info(f"Found {len(results)} lawyers for custody cases")
        
        # Search by budget
        results = await elasticsearch_service.search_lawyers({"budget_range": "$$"})
        logger.info(f"Found {len(results)} lawyers in $$ budget range")
        
    except Exception as e:
        logger.error(f"Error populating lawyers: {e}")
        raise
    finally:
        await elasticsearch_service.close()


if __name__ == "__main__":
    print("Populating Elasticsearch with sample lawyer data...")
    print("Make sure Elasticsearch is running on localhost:9200")
    print("-" * 50)
    
    asyncio.run(populate_lawyers())