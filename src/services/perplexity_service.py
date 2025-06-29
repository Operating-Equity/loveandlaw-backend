"""
Perplexity API integration for enhanced lawyer matching and neighborhood research
"""

import os
import httpx
import asyncio
from typing import Dict, List, Optional, Any
import json
from datetime import datetime, timedelta


class PerplexityService:
    """Service for interacting with Perplexity API for real-time research"""
    
    def __init__(self):
        self.api_key = os.getenv('PERPLEXITY_API_KEY')
        self.base_url = "https://api.perplexity.ai"
        self.timeout = 30.0
        self._cache = {}  # Simple in-memory cache
        self._cache_ttl = timedelta(hours=24)
    
    async def research_neighborhood(self, neighborhood: str, city: str = "Los Angeles") -> Dict[str, Any]:
        """Research a neighborhood for demographic and cultural information"""
        
        cache_key = f"neighborhood_{neighborhood}_{city}".lower()
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]['data']
        
        query = f"""
        Tell me about the {neighborhood} neighborhood in {city}:
        1. Demographics and cultural communities
        2. Is it known for any specific ethnic or religious communities?
        3. Major landmarks and community centers
        4. General character of the area
        Provide a concise summary focused on community characteristics.
        """
        
        try:
            result = await self._query_perplexity(query)
            parsed = self._parse_neighborhood_info(result, neighborhood)
            self._cache_result(cache_key, parsed)
            return parsed
        except Exception as e:
            print(f"Perplexity research failed: {e}")
            return {"neighborhood": neighborhood, "cultural_info": None}
    
    async def research_cultural_areas(self, culture: str, city: str = "Los Angeles") -> List[str]:
        """Find neighborhoods known for specific cultural communities"""
        
        cache_key = f"culture_{culture}_{city}".lower()
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]['data']
        
        query = f"""
        List the main neighborhoods in {city} known for having significant {culture} communities.
        Include areas with {culture} schools, places of worship, restaurants, and community centers.
        Provide just the neighborhood names, focusing on the most prominent areas.
        """
        
        try:
            result = await self._query_perplexity(query)
            neighborhoods = self._parse_neighborhood_list(result)
            self._cache_result(cache_key, neighborhoods)
            return neighborhoods
        except Exception as e:
            print(f"Cultural area research failed: {e}")
            return []
    
    async def research_lawyer_reputation(self, lawyer_name: str, firm_name: str = None) -> Dict[str, Any]:
        """Research a lawyer's reputation and specialties"""
        
        cache_key = f"lawyer_{lawyer_name}_{firm_name}".lower().replace(" ", "_")
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]['data']
        
        query = f"""
        Research lawyer {lawyer_name}{f' at {firm_name}' if firm_name else ''} in Los Angeles:
        1. Notable cases or specialties
        2. Community involvement
        3. Any awards or recognitions
        4. Client review themes
        Provide factual information only, be concise.
        """
        
        try:
            result = await self._query_perplexity(query)
            parsed = self._parse_lawyer_info(result, lawyer_name)
            self._cache_result(cache_key, parsed)
            return parsed
        except Exception as e:
            print(f"Lawyer research failed: {e}")
            return {"lawyer": lawyer_name, "additional_info": None}
    
    async def enhance_search_context(self, user_query: str) -> Dict[str, Any]:
        """Enhance understanding of user's search intent"""
        
        query = f"""
        A user searching for a family lawyer said: "{user_query}"
        
        Extract and clarify:
        1. Specific legal needs mentioned
        2. Location preferences (neighborhoods, areas)
        3. Lawyer characteristics desired (gender, language, cultural understanding)
        4. Any urgency indicators
        5. Budget considerations implied
        
        Provide structured extraction, not advice.
        """
        
        try:
            result = await self._query_perplexity(query)
            return self._parse_search_context(result)
        except Exception as e:
            print(f"Context enhancement failed: {e}")
            return {}
    
    async def _query_perplexity(self, query: str, model: str = "llama-3.1-sonar-small-128k-online") -> str:
        """Make a query to Perplexity API"""
        
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY not set in environment")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant providing factual information for a legal services platform. Be concise and factual."
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            "temperature": 0.1,  # Low temperature for factual responses
            "top_p": 0.9,
            "return_citations": True,
            "search_domain_filter": ["perplexity.ai"],
            "search_recency_filter": "year"
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            
            data = response.json()
            return data['choices'][0]['message']['content']
    
    def _parse_neighborhood_info(self, response: str, neighborhood: str) -> Dict[str, Any]:
        """Parse neighborhood research response"""
        return {
            "neighborhood": neighborhood,
            "cultural_info": response,
            "is_cultural_hub": any(
                keyword in response.lower() 
                for keyword in ["significant", "community", "known for", "hub", "center"]
            ),
            "extracted_at": datetime.utcnow().isoformat()
        }
    
    def _parse_neighborhood_list(self, response: str) -> List[str]:
        """Extract neighborhood names from response"""
        # Simple extraction - look for capitalized words that might be neighborhoods
        lines = response.strip().split('\n')
        neighborhoods = []
        
        for line in lines:
            # Remove bullets, numbers, etc.
            clean_line = line.strip().lstrip('•-*123456789. ')
            if clean_line and len(clean_line) < 50:  # Likely a neighborhood name
                neighborhoods.append(clean_line.split(',')[0].strip())
        
        return neighborhoods[:10]  # Limit to top 10
    
    def _parse_lawyer_info(self, response: str, lawyer_name: str) -> Dict[str, Any]:
        """Parse lawyer research response"""
        return {
            "lawyer": lawyer_name,
            "additional_info": response,
            "has_notable_info": len(response) > 100,
            "extracted_at": datetime.utcnow().isoformat()
        }
    
    def _parse_search_context(self, response: str) -> Dict[str, Any]:
        """Parse search context enhancement"""
        # This is a simplified parser - in production you might want
        # to use structured output from Perplexity
        context = {
            "enhanced_query": response,
            "extracted_preferences": {},
            "urgency_detected": "urgent" in response.lower() or "immediately" in response.lower()
        }
        
        # Extract key preferences
        if "gender:" in response.lower():
            context["extracted_preferences"]["gender"] = "female" if "woman" in response.lower() or "female" in response.lower() else None
        
        return context
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached result is still valid"""
        if key not in self._cache:
            return False
        
        cached_time = self._cache[key]['timestamp']
        return datetime.utcnow() - cached_time < self._cache_ttl
    
    def _cache_result(self, key: str, data: Any):
        """Cache a result with timestamp"""
        self._cache[key] = {
            'data': data,
            'timestamp': datetime.utcnow()
        }


# Singleton instance
_perplexity_service = None

def get_perplexity_service() -> PerplexityService:
    """Get or create the Perplexity service singleton"""
    global _perplexity_service
    if _perplexity_service is None:
        _perplexity_service = PerplexityService()
    return _perplexity_service