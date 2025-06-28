# External API Integration Guide for Enhanced Neighborhood Search

## Current Implementation ✅
Your backend now supports:
- **Gender filtering**: "woman lawyer" → filters by gender
- **Neighborhood search**: "Tarzana" → 5-mile radius search
- **Skill matching**: "litigation", "courtroom" → matches specialties

## Run the Test
```bash
python test_boss_queries.py
```

## Recommended External APIs

### 1. Google Places API (Best for Neighborhoods)
**Why**: Provides accurate neighborhood boundaries and cultural area data
```python
# Example integration in search_service.py
import googlemaps

gmaps = googlemaps.Client(key='YOUR_API_KEY')

def get_neighborhood_coords(neighborhood_name, city="Los Angeles"):
    result = gmaps.places(f"{neighborhood_name}, {city}")
    if result['results']:
        location = result['results'][0]['geometry']['location']
        return location['lat'], location['lng']
```

### 2. Census API (For Demographic Data)
**Why**: Identify areas with specific cultural demographics
```python
# Example: Find areas with high Jewish population
import census

c = census.Census("YOUR_API_KEY")

def get_jewish_neighborhoods(city="Los Angeles"):
    # Get census tracts with demographic data
    # Filter by religious/cultural indicators
    pass
```

### 3. Mapbox Geocoding API (Alternative to Google)
**Why**: More affordable, good neighborhood data
```python
import mapbox

geocoder = mapbox.Geocoder(access_token='YOUR_TOKEN')

def geocode_neighborhood(name):
    response = geocoder.forward(f"{name}, Los Angeles, CA")
    if response.geojson()['features']:
        coords = response.geojson()['features'][0]['center']
        return coords[1], coords[0]  # lat, lng
```

### 4. Here Maps API (For Community Data)
**Why**: Provides POI data that can indicate cultural areas
```python
# Find areas with synagogues, Jewish schools, kosher restaurants
# as indicators of Jewish neighborhoods
```

## Quick Implementation Steps

### Option 1: Google Places (Recommended)
```bash
pip install googlemaps
```

Add to `.env`:
```
GOOGLE_PLACES_API_KEY=your_key_here
```

Update `ElasticsearchService._get_coordinates()`:
```python
def _get_coordinates(self, location: str) -> Optional[Tuple[float, float]]:
    # Try Google Places first
    if self.gmaps_client:
        try:
            result = self.gmaps_client.geocode(location)
            if result:
                loc = result[0]['geometry']['location']
                return loc['lat'], loc['lng']
        except:
            pass
    
    # Fallback to existing implementation
    return self._fallback_geocoding(location)
```

### Option 2: Community-Specific Data
For "Jewish areas" specifically, consider:
1. **JewishLA.org API** (if available)
2. **Synagogue location data** from Google Places
3. **Community center databases**

## Implementation Priority
1. **Now**: Current implementation works! Test with `test_boss_queries.py`
2. **Next Week**: Add Google Places for better geocoding
3. **Future**: Add demographic/community data for cultural areas

## Sample Enhancement
```python
# In matcher_agent.py
async def _identify_cultural_areas(self, culture: str, city: str) -> List[str]:
    """Identify neighborhoods with specific cultural presence"""
    if culture.lower() == "jewish" and city.lower() == "los angeles":
        # Could query external API here
        return ["Encino", "Sherman Oaks", "Valley Village", 
                "Studio City", "Tarzana", "Pico-Robertson"]
    return []
```

The system is ready to use now, and these APIs would make it even better!