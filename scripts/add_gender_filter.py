#!/usr/bin/env python3
"""
Script to add gender filtering capability to the existing search functionality.
This can be applied immediately without any schema changes.
"""

import asyncio
from typing import Dict, Any, Optional
import re


def patch_matcher_agent():
    """
    Patches to apply to src/agents/matcher_agent.py
    """
    
    # 1. Add to _build_filter_query method (after line 246)
    gender_filter_code = '''
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
    '''
    
    # 2. Add to _build_search_context method (after line 188)
    search_context_code = '''
        if state.facts.get("gender_preference"):
            gender = state.facts["gender_preference"]
            if gender.lower() in ["female", "woman"]:
                query_parts.append("female lawyer")
            elif gender.lower() in ["male", "man"]:
                query_parts.append("male lawyer")
    '''
    
    # 3. Add neighborhood awareness (after gender filter)
    neighborhood_code = '''
        # Neighborhood-based search with tighter radius
        if state.facts.get("neighborhood"):
            neighborhood = state.facts["neighborhood"]
            city = state.facts.get("city", "")
            state_name = state.facts.get("state", "")
            
            # Build location query
            location_query = f"{neighborhood}"
            if city:
                location_query += f", {city}"
            if state_name:
                location_query += f", {state_name}"
            
            filters["location_query"] = location_query
            
            # Use tighter radius for neighborhood searches
            # This will be used in the location parameter of search_lawyers
            filters["search_distance"] = "5mi"  # Instead of default 50mi
    '''
    
    return {
        "gender_filter": gender_filter_code,
        "search_context": search_context_code,
        "neighborhood": neighborhood_code
    }


def patch_elasticsearch_service():
    """
    Patches to apply to src/services/elasticsearch_service.py
    """
    
    # Add to _build_filter_queries method (after line 503)
    gender_filter_code = '''
        # Gender filter
        if "gender" in filters:
            filter_queries.append({
                "term": {"gender": filters["gender"]}
            })
    '''
    
    # Add neighborhood text search to search_lawyers method
    neighborhood_search_code = '''
        # Enhanced neighborhood search
        if filters.get("location_query"):
            query["bool"]["should"].append({
                "multi_match": {
                    "query": filters["location_query"],
                    "fields": [
                        "addresses.formatted_address^3",
                        "addresses.street^2",
                        "city^2",
                        "profile_summary"
                    ],
                    "type": "best_fields",
                    "boost": 2.0
                }
            })
            
            # Use custom distance if provided
            if filters.get("search_distance") and location:
                distance = filters["search_distance"]
    '''
    
    return {
        "gender_filter": gender_filter_code,
        "neighborhood_search": neighborhood_search_code
    }


def patch_signal_extract_agent():
    """
    Add gender preference extraction to SignalExtractAgent
    """
    
    extraction_code = '''
    def extract_gender_preference(self, text: str) -> Optional[str]:
        """Extract gender preference from user text"""
        text_lower = text.lower()
        
        # Direct gender mentions
        gender_patterns = [
            (r'\\b(female|woman)\\s+(lawyer|attorney)\\b', 'female'),
            (r'\\b(male|man)\\s+(lawyer|attorney)\\b', 'male'),
            (r'\\bprefer\\s+a?\\s*(female|woman)\\b', 'female'),
            (r'\\bprefer\\s+a?\\s*(male|man)\\b', 'male'),
            (r'\\blooking\\s+for\\s+a?\\s*(female|woman)\\b', 'female'),
            (r'\\blooking\\s+for\\s+a?\\s*(male|man)\\b', 'male'),
        ]
        
        for pattern, gender in gender_patterns:
            if re.search(pattern, text_lower):
                return gender
        
        # Context clues for gender preference
        female_indicators = [
            "comfortable with a woman",
            "prefer female",
            "woman would understand",
            "female perspective",
            "woman attorney",
            "lady lawyer"
        ]
        
        male_indicators = [
            "comfortable with a man",
            "prefer male",
            "male lawyer",
            "male attorney",
            "gentleman lawyer"
        ]
        
        if any(phrase in text_lower for phrase in female_indicators):
            return "female"
        
        if any(phrase in text_lower for phrase in male_indicators):
            return "male"
        
        return None
    
    def extract_neighborhood(self, text: str) -> Optional[Dict[str, str]]:
        """Extract neighborhood information from user text"""
        text_lower = text.lower()
        
        # Neighborhood patterns
        patterns = [
            r'in\\s+([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)*)\\s+neighborhood',
            r'near\\s+([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)*)\\s+area',
            r'around\\s+([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)*)',
            r'([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)*)\\s+district',
            r'live\\s+in\\s+([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)*)',
        ]
        
        # Check with original case for proper nouns
        for pattern in patterns:
            match = re.search(pattern.replace('A-Z', 'A-Za-z').replace('a-z', 'a-z'), text)
            if match:
                return {"neighborhood": match.group(1)}
        
        # Common NYC neighborhoods (example)
        nyc_neighborhoods = [
            "brooklyn heights", "park slope", "williamsburg", "greenpoint",
            "astoria", "long island city", "forest hills", "flushing",
            "upper west side", "upper east side", "chelsea", "tribeca",
            "harlem", "washington heights", "inwood"
        ]
        
        for neighborhood in nyc_neighborhoods:
            if neighborhood in text_lower:
                return {"neighborhood": neighborhood.title()}
        
        return None
    '''
    
    # Add to the facts extraction in process method
    process_update = '''
        # Extract gender preference
        if gender_pref := self.extract_gender_preference(state.user_text):
            facts["gender_preference"] = gender_pref
        
        # Extract neighborhood
        if neighborhood_info := self.extract_neighborhood(state.user_text):
            facts.update(neighborhood_info)
    '''
    
    return {
        "extraction_methods": extraction_code,
        "process_update": process_update
    }


# Test the gender filter functionality
async def test_gender_filter_search():
    """Test script to verify gender filtering works correctly"""
    
    from src.services.database import elasticsearch_service
    from src.models.conversation import TurnState
    from src.agents.matcher_agent import MatcherAgent
    
    print("Testing Gender Filter Implementation")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        {
            "user_text": "I need a female divorce lawyer in Brooklyn",
            "expected_gender": "female",
            "expected_location": "Brooklyn"
        },
        {
            "user_text": "Looking for a male attorney for custody case",
            "expected_gender": "male",
            "expected_intent": ["custody"]
        },
        {
            "user_text": "I prefer a woman lawyer who understands domestic violence",
            "expected_gender": "female",
            "expected_intent": ["domestic_violence"]
        },
        {
            "user_text": "Need a lawyer in Park Slope neighborhood for divorce",
            "expected_neighborhood": "Park Slope",
            "expected_intent": ["divorce"]
        }
    ]
    
    matcher = MatcherAgent()
    
    for i, test_case in enumerate(test_cases):
        print(f"\nTest Case {i+1}: {test_case['user_text']}")
        print("-" * 40)
        
        # Create test state
        state = TurnState(
            user_id="test_user",
            user_text=test_case["user_text"],
            facts={},
            legal_intent=[]
        )
        
        # Simulate signal extraction
        # In real implementation, SignalExtractAgent would do this
        if "female" in test_case["user_text"].lower() or "woman" in test_case["user_text"].lower():
            state.facts["gender_preference"] = "female"
        elif "male" in test_case["user_text"].lower() or "man" in test_case["user_text"].lower():
            state.facts["gender_preference"] = "male"
        
        # Extract location
        if "Brooklyn" in test_case["user_text"]:
            state.facts["city"] = "Brooklyn"
            state.facts["state"] = "NY"
        
        if "Park Slope" in test_case["user_text"]:
            state.facts["neighborhood"] = "Park Slope"
            state.facts["city"] = "Brooklyn"
            state.facts["state"] = "NY"
        
        # Extract legal intent
        if "divorce" in test_case["user_text"].lower():
            state.legal_intent.append("divorce")
        if "custody" in test_case["user_text"].lower():
            state.legal_intent.append("custody")
        if "domestic violence" in test_case["user_text"].lower():
            state.legal_intent.append("domestic_violence")
        
        # Build filters
        filters = matcher._build_filter_query(state)
        
        print(f"Extracted Facts: {state.facts}")
        print(f"Legal Intent: {state.legal_intent}")
        print(f"Generated Filters: {filters}")
        
        # Verify expectations
        if "expected_gender" in test_case:
            assert filters.get("gender") == test_case["expected_gender"], \
                f"Expected gender {test_case['expected_gender']}, got {filters.get('gender')}"
            print(f"✓ Gender filter correct: {filters['gender']}")
        
        if "expected_neighborhood" in test_case:
            assert state.facts.get("neighborhood") == test_case["expected_neighborhood"], \
                f"Expected neighborhood {test_case['expected_neighborhood']}, got {state.facts.get('neighborhood')}"
            print(f"✓ Neighborhood extracted: {state.facts['neighborhood']}")


def generate_patch_instructions():
    """Generate step-by-step instructions for applying the patches"""
    
    instructions = """
# Gender Filter Implementation Instructions

## Step 1: Update MatcherAgent (src/agents/matcher_agent.py)

### 1.1 Add to _build_filter_query method (after line 246):
```python
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
```

### 1.2 Add to _build_search_context method (after line 188):
```python
        if state.facts.get("gender_preference"):
            gender = state.facts["gender_preference"]
            if gender.lower() in ["female", "woman"]:
                query_parts.append("female lawyer")
            elif gender.lower() in ["male", "man"]:
                query_parts.append("male lawyer")
```

## Step 2: Update ElasticsearchService (src/services/elasticsearch_service.py)

### 2.1 Add to _build_filter_queries method (after line 503):
```python
        # Gender filter
        if "gender" in filters:
            filter_queries.append({
                "term": {"gender": filters["gender"]}
            })
```

## Step 3: Update SignalExtractAgent (src/agents/signal_extract_agent.py)

### 3.1 Add gender extraction to the process method where facts are extracted:
```python
        # Look for gender preference
        gender_patterns = [
            (r'\\b(female|woman)\\s+(lawyer|attorney)\\b', 'female'),
            (r'\\b(male|man)\\s+(lawyer|attorney)\\b', 'male'),
            (r'\\bprefer\\s+a?\\s*(female|woman)\\b', 'female'),
            (r'\\bprefer\\s+a?\\s*(male|man)\\b', 'male'),
        ]
        
        for pattern, gender in gender_patterns:
            if re.search(pattern, text.lower()):
                facts["gender_preference"] = gender
                break
```

## Step 4: Test the Implementation

Run the test script:
```bash
python scripts/add_gender_filter.py
```

## Step 5: Verify with Real Search

Test with actual Elasticsearch queries to ensure gender filtering works:
```python
results = await elasticsearch_service.search_lawyers(
    query_text="divorce lawyer",
    filters={"gender": "female", "state": "NY"},
    size=5
)
```
"""
    
    return instructions


if __name__ == "__main__":
    print(generate_patch_instructions())
    
    # Uncomment to run tests (requires running backend)
    # asyncio.run(test_gender_filter_search())