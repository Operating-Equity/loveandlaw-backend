"""
Quick implementation guide for adding gender filter to existing search.
This can be applied immediately without schema changes.
"""

# Step 1: Update matcher_agent.py _build_filter_query method
# Add this section after line 246 (languages filter):

def add_gender_filter_to_build_filter_query(self, state, filters):
    """
    Add this logic to the _build_filter_query method in MatcherAgent
    """
    # Gender preference filter
    if state.facts.get("gender_preference"):
        gender_pref = state.facts["gender_preference"].lower()
        # Normalize gender values
        if gender_pref in ["female", "woman", "f"]:
            filters["gender"] = "female"
        elif gender_pref in ["male", "man", "m"]:
            filters["gender"] = "male"
        elif gender_pref == "non-binary":
            filters["gender"] = "non-binary"
        # If "no preference" or similar, don't add filter
    
    return filters


# Step 2: Update elasticsearch_service.py _build_filter_queries method
# Add this after line 485 (languages filter):

def add_gender_filter_to_build_filter_queries(self, filters, filter_queries):
    """
    Add this logic to the _build_filter_queries method in ElasticsearchService
    """
    # Gender filter
    if "gender" in filters:
        filter_queries.append({
            "term": {"gender": filters["gender"]}
        })
    
    return filter_queries


# Step 3: Update SignalExtractAgent to extract gender preferences
# Add this pattern matching in the signal extraction:

async def extract_gender_preference(self, text: str) -> Optional[str]:
    """
    Extract gender preference from user text
    """
    import re
    
    text_lower = text.lower()
    
    # Direct gender mentions
    gender_patterns = [
        (r'\b(female|woman)\s+(lawyer|attorney)\b', 'female'),
        (r'\b(male|man)\s+(lawyer|attorney)\b', 'male'),
        (r'\bprefer\s+a?\s*(female|woman)\b', 'female'),
        (r'\bprefer\s+a?\s*(male|man)\b', 'male'),
        (r'\blooking\s+for\s+a?\s*(female|woman)\b', 'female'),
        (r'\blooking\s+for\s+a?\s*(male|man)\b', 'male'),
        (r'\bneed\s+a?\s*(female|woman)\s+(lawyer|attorney)\b', 'female'),
        (r'\bneed\s+a?\s*(male|man)\s+(lawyer|attorney)\b', 'male'),
    ]
    
    for pattern, gender in gender_patterns:
        if re.search(pattern, text_lower):
            return gender
    
    # Check for contextual clues
    if any(phrase in text_lower for phrase in [
        "comfortable with a woman",
        "prefer female",
        "woman would understand",
        "female perspective"
    ]):
        return "female"
    
    if any(phrase in text_lower for phrase in [
        "comfortable with a man",
        "prefer male",
        "male lawyer",
        "male attorney"
    ]):
        return "male"
    
    return None


# Step 4: Quick test script to verify gender filtering works

async def test_gender_filter():
    """
    Test script to verify gender filtering functionality
    """
    from src.services.database import elasticsearch_service
    
    # Test search with gender filter
    results = await elasticsearch_service.search_lawyers(
        query_text="divorce lawyer",
        filters={
            "gender": "female",
            "state": "NY",
            "practice_areas": ["divorce"]
        },
        size=5
    )
    
    print(f"Found {len(results)} female divorce lawyers in NY")
    for lawyer in results:
        print(f"- {lawyer.get('name')} ({lawyer.get('gender', 'not specified')})")
    
    return results


# Step 5: Update the search context building to mention gender preference

def update_search_context_for_gender(self, state, query_parts):
    """
    Add to _build_search_context method in MatcherAgent
    """
    if state.facts.get("gender_preference"):
        gender = state.facts["gender_preference"]
        if gender.lower() in ["female", "woman"]:
            query_parts.append("female lawyer")
        elif gender.lower() in ["male", "man"]:
            query_parts.append("male lawyer")


# Step 6: Immediate neighborhood search enhancement (without schema changes)

def add_neighborhood_search_to_filters(self, state, filters):
    """
    Add basic neighborhood search without schema changes
    """
    if state.facts.get("neighborhood"):
        neighborhood = state.facts["neighborhood"]
        city = state.facts.get("city", "")
        
        # Use neighborhood in location-based text search
        # This will search in formatted_address and other text fields
        filters["neighborhood_text"] = f"{neighborhood} {city}".strip()
        
        # Use tighter radius for neighborhood searches
        if state.facts.get("zip"):
            filters["search_radius"] = "5mi"  # Instead of default 50mi
    
    return filters


# Usage example for WebSocket message processing:
example_user_message = {
    "type": "user_msg",
    "text": "I need a female divorce lawyer in Brooklyn Heights",
    "cid": "12345"
}

# The SignalExtractAgent would extract:
extracted_facts = {
    "gender_preference": "female",
    "legal_intent": ["divorce"],
    "neighborhood": "Brooklyn Heights",
    "city": "Brooklyn",
    "state": "NY"
}

# The MatcherAgent would build filters:
search_filters = {
    "gender": "female",
    "practice_areas": ["divorce"],
    "state": "NY",
    "city": "Brooklyn",
    "location": {
        # Coordinates for Brooklyn Heights center
        "lat": 40.6959,
        "lon": -73.9937
    },
    "search_radius": "3mi"
}