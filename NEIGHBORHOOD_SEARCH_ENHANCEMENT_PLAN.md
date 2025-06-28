# Neighborhood-Level Search Enhancement Plan

## Overview
This document outlines the enhancements needed to support neighborhood-level lawyer searches with gender filtering in the LoveAndLaw backend.

## Current Capabilities

### Existing Location Search Features:
- **Geo-point search**: Uses Elasticsearch geo_distance queries
- **Distance-based filtering**: Default 50mi radius (configurable)
- **City/State filtering**: Text and keyword-based filtering
- **Gender field**: Already in schema as keyword field
- **Nested addresses**: Support for multiple office locations

### Limitations:
1. No explicit neighborhood field in the schema
2. ZIP to coordinates conversion is a placeholder
3. Default 50mi radius too broad for neighborhood searches
4. Gender filter not exposed in the search API
5. No neighborhood boundary support (polygon search)

## Proposed Enhancements

### 1. Schema Updates

Add neighborhood-specific fields to the Elasticsearch mapping:

```python
# In elasticsearch_mapping.py, add to addresses nested field:
"neighborhood": {"type": "keyword"},
"district": {"type": "keyword"},
"borough": {"type": "keyword"},  # For NYC-style divisions

# Add to root level for primary location:
"primary_neighborhood": {"type": "keyword"},
"service_areas": {  # Lawyers may serve multiple neighborhoods
    "type": "keyword"
}
```

### 2. Enhanced Location Search

#### A. Neighborhood-Aware Distance Search
```python
# In matcher_agent.py _build_filter_query method:
if state.facts.get("neighborhood"):
    # Use smaller radius for neighborhood searches
    filters["location"] = {
        "center": self._get_neighborhood_center(
            state.facts["neighborhood"], 
            state.facts.get("city"),
            state.facts.get("state")
        ),
        "distance": "3mi"  # Smaller radius for neighborhood
    }
```

#### B. Multi-Level Location Filtering
```python
# Support hierarchical location filtering
if state.facts.get("neighborhood") and state.facts.get("city"):
    filters["addresses.neighborhood"] = state.facts["neighborhood"]
    filters["addresses.city"] = state.facts["city"]
elif state.facts.get("zip"):
    # Enhanced ZIP handling with real geocoding
    coords = await self._geocode_zip(state.facts["zip"])
    filters["location"] = {
        "lat": coords["lat"],
        "lon": coords["lon"],
        "distance": "5mi"
    }
```

### 3. Gender Filter Implementation

```python
# In matcher_agent.py _build_filter_query method, add:
if state.facts.get("gender_preference"):
    filters["gender"] = state.facts["gender_preference"]
    
# In _build_search_context method, add:
if state.facts.get("gender_preference"):
    query_parts.append(f"{state.facts['gender_preference']} lawyer")
```

### 4. Enhanced Search Service

```python
# In elasticsearch_service.py, add neighborhood search method:
async def search_by_neighborhood(
    self,
    neighborhood: str,
    city: Optional[str] = None,
    state: Optional[str] = None,
    gender: Optional[str] = None,
    practice_areas: Optional[List[str]] = None,
    distance: str = "3mi",
    size: int = 10
) -> List[Dict[str, Any]]:
    """Search lawyers by neighborhood with tighter geographic constraints."""
    
    query = {"bool": {"must": [], "filter": []}}
    
    # Neighborhood text search
    query["bool"]["must"].append({
        "multi_match": {
            "query": neighborhood,
            "fields": [
                "addresses.neighborhood^3",
                "addresses.formatted_address^2",
                "service_areas^2",
                "primary_neighborhood^3"
            ],
            "type": "best_fields"
        }
    })
    
    # Additional filters
    if city:
        query["bool"]["filter"].append({"term": {"city.keyword": city}})
    if state:
        query["bool"]["filter"].append({"term": {"state": state}})
    if gender:
        query["bool"]["filter"].append({"term": {"gender": gender}})
    if practice_areas:
        query["bool"]["filter"].append({
            "terms": {"practice_areas.keyword": practice_areas}
        })
    
    # Geographic constraint
    if neighborhood_center := await self._get_neighborhood_center(neighborhood, city, state):
        query["bool"]["filter"].append({
            "geo_distance": {
                "distance": distance,
                "location": neighborhood_center
            }
        })
    
    # Execute search with neighborhood-specific sorting
    response = await self.client.search(
        index=self.index_name,
        body={
            "query": query,
            "size": size,
            "sort": [
                "_score",
                {
                    "_geo_distance": {
                        "location": neighborhood_center,
                        "order": "asc",
                        "unit": "mi"
                    }
                } if neighborhood_center else {"ratings.overall": {"order": "desc"}}
            ]
        }
    )
    
    return self._process_search_results(response)
```

### 5. Geocoding Service Integration

```python
# New file: src/services/geocoding_service.py
import aiohttp
from typing import Dict, Optional, Tuple
from src.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class GeocodingService:
    """Service for converting addresses to coordinates and neighborhood data."""
    
    def __init__(self):
        self.api_key = settings.google_maps_api_key  # or other geocoding service
        self.cache = {}  # Simple in-memory cache
    
    async def geocode_address(self, address: str) -> Optional[Dict[str, Any]]:
        """Convert address to coordinates and extract neighborhood info."""
        if address in self.cache:
            return self.cache[address]
            
        async with aiohttp.ClientSession() as session:
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                "address": address,
                "key": self.api_key
            }
            
            async with session.get(url, params=params) as response:
                data = await response.json()
                
                if data["status"] == "OK" and data["results"]:
                    result = data["results"][0]
                    
                    # Extract components
                    components = {
                        comp["types"][0]: comp["long_name"]
                        for comp in result["address_components"]
                    }
                    
                    location_data = {
                        "lat": result["geometry"]["location"]["lat"],
                        "lon": result["geometry"]["location"]["lng"],
                        "formatted_address": result["formatted_address"],
                        "neighborhood": components.get("neighborhood"),
                        "city": components.get("locality"),
                        "state": components.get("administrative_area_level_1"),
                        "zip": components.get("postal_code"),
                        "country": components.get("country")
                    }
                    
                    self.cache[address] = location_data
                    return location_data
                    
        return None
    
    async def get_neighborhood_center(
        self, 
        neighborhood: str, 
        city: Optional[str] = None,
        state: Optional[str] = None
    ) -> Optional[Dict[str, float]]:
        """Get center coordinates for a neighborhood."""
        address_parts = [neighborhood]
        if city:
            address_parts.append(city)
        if state:
            address_parts.append(state)
            
        address = ", ".join(address_parts)
        location_data = await self.geocode_address(address)
        
        if location_data:
            return {"lat": location_data["lat"], "lon": location_data["lon"]}
        return None

geocoding_service = GeocodingService()
```

### 6. SignalExtractAgent Enhancement

```python
# Update signal extraction to capture neighborhood and gender preferences
neighborhood_patterns = [
    r"in (\w+) neighborhood",
    r"near (\w+) area",
    r"around (\w+)",
    r"(\w+) district",
    r"live in (\w+)"
]

gender_patterns = [
    r"(female|woman) lawyer",
    r"(male|man) lawyer",
    r"prefer a (female|male|woman|man)",
    r"looking for a (female|male|woman|man)"
]
```

### 7. API Updates

#### A. WebSocket Message Enhancement
```python
# Add to WebSocketMessage type for location requests:
type: Literal[..., "neighborhood_request"]
neighborhood_options: Optional[List[str]] = None
```

#### B. REST Endpoint Enhancement
```python
# Update /v1/match endpoint to accept:
{
    "facts": {
        "neighborhood": "Brooklyn Heights",
        "city": "Brooklyn",
        "state": "NY",
        "gender_preference": "female",
        "practice_area": "divorce",
        "search_radius": "3mi"  # Optional, defaults based on search type
    }
}
```

## Implementation Priority

1. **Phase 1** (Immediate):
   - Add gender filter to existing search
   - Implement basic neighborhood text search
   - Add configurable search radius

2. **Phase 2** (1-2 weeks):
   - Integrate geocoding service
   - Add neighborhood fields to schema
   - Implement neighborhood-aware distance search

3. **Phase 3** (Future):
   - Polygon-based neighborhood boundaries
   - Service area matching
   - Neighborhood popularity analytics

## Testing Approach

1. **Unit Tests**:
   - Gender filter application
   - Neighborhood extraction from text
   - Distance calculation for neighborhoods

2. **Integration Tests**:
   - End-to-end neighborhood search
   - Gender + neighborhood combination
   - Geocoding service integration

3. **Load Testing**:
   - Neighborhood search performance
   - Geocoding API rate limits
   - Cache effectiveness

## Monitoring & Analytics

Track:
- Neighborhood search usage
- Gender preference statistics
- Search radius effectiveness
- Neighborhood coverage gaps

## Privacy Considerations

- Gender preferences are sensitive data
- Neighborhood-level location is more specific than city
- Implement appropriate consent and data retention policies
- Consider allowing lawyers to opt-out of gender-based filtering

## Next Steps

1. Review and approve enhancement plan
2. Set up geocoding service credentials
3. Create Elasticsearch mapping migration
4. Implement Phase 1 features
5. Deploy to staging for testing