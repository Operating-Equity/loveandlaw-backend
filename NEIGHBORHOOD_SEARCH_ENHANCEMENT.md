# Neighborhood Search Enhancement Summary

## Overview
Enhanced the location search functionality to support neighborhood-level searches with the following improvements:

## Key Changes

### 1. Elasticsearch Service (`src/services/elasticsearch_service.py`)
- Added `neighborhood_search` parameter to `search_lawyers()` method
- Automatically reduces search radius from 50mi to 5mi for neighborhood searches
- Added neighborhood text search using nested queries on `addresses` field
- Implemented `search_by_neighborhood()` method for dedicated neighborhood searches
- Added `geocode_neighborhood()` method with hardcoded coordinates for common LA neighborhoods
- Added support for extracting matched address information from search results

### 2. Matcher Agent (`src/agents/matcher_agent.py`)
- Updated `_build_filter_query()` to prioritize neighborhood searches
- Added logic to try text-based neighborhood search first, then fallback to geocoding
- Enhanced `_format_lawyer_cards()` to include neighborhood and address information in location data
- Improved location info handling with proper fallbacks for firm names and ratings

### 3. Signal Extract Agent (`src/agents/signal_extract.py`)
- Updated prompt to specifically mention neighborhoods like "Tarzana", "Beverly Hills"
- Enhanced location extraction to capture neighborhood information
- Added neighborhood field extraction in `_process_facts_recursively()`

### 4. Data Loading (`scripts/load_lawyer_data.py`)
- Added `_extract_addresses()` method to parse geocoded address data
- Added `_parse_geocoded_address()` to extract structured address components including neighborhoods
- Addresses now include street, city, state, zip, neighborhood, and coordinates

### 5. Index Configuration
- Updated index name from "lawyers_v1" to "love-and-law-001" to match mapping
- Elasticsearch mapping already supports nested addresses with neighborhood field

## Usage Examples

### 1. Direct Neighborhood Search
```python
results = await elasticsearch_service.search_by_neighborhood(
    neighborhood="Tarzana",
    city="Los Angeles", 
    state="CA",
    filters={"practice_areas": ["divorce"]},
    size=10
)
```

### 2. Through Matcher Agent
When users mention neighborhoods in their requests:
- "I need a divorce lawyer in Tarzana"
- "Looking for a family attorney near Sherman Oaks"
- "Can you find me a custody lawyer in Beverly Hills?"

The system will:
1. Extract the neighborhood via SignalExtractAgent
2. Search for lawyers with addresses matching that neighborhood
3. Fall back to geocoded coordinates if no text matches found
4. Return lawyers within 5 miles of the neighborhood

### 3. Geocoding Support
Currently supports these LA neighborhoods with approximate coordinates:
- Tarzana, Beverly Hills, Santa Monica, Venice, Hollywood
- Downtown, Pasadena, Glendale, Sherman Oaks, Encino
- Westwood, Brentwood, Malibu, Manhattan Beach
- Redondo Beach, Torrance, Long Beach, Burbank, Culver City, Mar Vista

## Testing
Run the test script to verify functionality:
```bash
python test_neighborhood_search.py
```

This tests:
1. Direct neighborhood search
2. Neighborhood + practice area filtering
3. Signal extraction with neighborhoods
4. Full matcher agent integration
5. Geocoding fallback

## Future Enhancements
1. Integrate real geocoding service (Google Maps, Mapbox) for any neighborhood
2. Add more neighborhoods and support for other cities
3. Implement dynamic radius adjustment based on neighborhood density
4. Add neighborhood popularity/safety scores if available
5. Support for landmarks and cross-streets ("near UCLA", "Hollywood and Vine")