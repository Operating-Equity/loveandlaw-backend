from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime
import numpy as np
from groq import AsyncGroq
from src.agents.base import BaseAgent
from src.models.conversation import TurnState, LawyerCard
from src.services.database import elasticsearch_service, redis_service
from src.config.settings import settings
from src.utils.logger import get_logger
import json

logger = get_logger(__name__)


class MatcherAgent(BaseAgent):
    """Advanced lawyer matching with semantic search and personalization"""
    
    def __init__(self):
        super().__init__("matcher")
        self.groq_client = AsyncGroq(api_key=settings.groq_api_key)
        self.cache_ttl = 3600  # 1 hour for lawyer matches
    
    async def process(self, state: TurnState, context: Dict[str, Any]) -> Dict[str, Any]:
        """Match lawyers based on user needs"""
        
        # Skip if distress too high
        if state.distress_score > 6:
            return {"lawyer_cards": [], "match_reason": "distress_too_high"}
        
        # Check if we have enough information
        if not self._has_sufficient_info(state):
            return {
                "lawyer_cards": [],
                "match_reason": "insufficient_info",
                "needed_info": self._get_missing_info(state)
            }
        
        # Generate search embedding
        search_embedding = await self._generate_search_embedding(state, context)
        
        # Build comprehensive search query
        search_query = self._build_search_query(state, context)
        
        # Add embedding to query if generated
        if search_embedding:
            search_query["embedding"] = search_embedding
        
        # Check cache first
        cache_key = self._generate_cache_key(search_query)
        cached_results = await self._get_cached_matches(cache_key)
        
        if cached_results:
            logger.info("Returning cached lawyer matches")
            return cached_results
        
        # Perform search
        lawyers = await elasticsearch_service.search_lawyers(search_query, size=10)
        
        # Rank and personalize results
        ranked_lawyers = await self._rank_and_personalize(lawyers, state, context)
        
        # Convert to LawyerCard format
        lawyer_cards = self._format_lawyer_cards(ranked_lawyers[:5])  # Top 5
        
        # Generate match explanations
        lawyer_cards = await self._add_match_explanations(lawyer_cards, state)
        
        result = {
            "lawyer_cards": lawyer_cards,
            "match_reason": "success",
            "total_matches": len(lawyers)
        }
        
        # Cache results
        await self._cache_matches(cache_key, result)
        
        return result
    
    def _has_sufficient_info(self, state: TurnState) -> bool:
        """Check if we have enough info to match lawyers"""
        has_location = bool(state.facts.get("zip") or state.facts.get("state"))
        has_legal_need = bool(state.legal_intent)
        return has_location and has_legal_need
    
    def _get_missing_info(self, state: TurnState) -> List[str]:
        """Identify what information is missing"""
        missing = []
        if not state.facts.get("zip") and not state.facts.get("state"):
            missing.append("location")
        if not state.legal_intent:
            missing.append("legal_need")
        if not state.facts.get("budget_range"):
            missing.append("budget")
        return missing
    
    async def _generate_search_embedding(self, state: TurnState, context: Dict[str, Any]) -> Optional[List[float]]:
        """Generate embedding for semantic search"""
        try:
            # Create search context
            search_text = f"""
Legal needs: {', '.join(state.legal_intent)}
Situation: {state.user_text[:200]}
Important factors: {', '.join(state.facts.keys())}
"""
            
            # For now, skip embeddings as Groq doesn't support embeddings yet
            # In production, you might use a different embedding service
            # response = await self.openai_client.embeddings.create(
            #     model="text-embedding-3-small",
            #     input=search_text
            # )
            
            # Return None to skip embedding-based search
            return None
            
            # embedding = response.data[0].embedding
            # return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    def _build_search_query(self, state: TurnState, context: Dict[str, Any]) -> Dict[str, Any]:
        """Build comprehensive search query"""
        query = {}
        
        # Location-based search
        if state.facts.get("zip"):
            query["zip"] = state.facts["zip"]
        elif state.facts.get("state"):
            query["state"] = state.facts["state"]
        
        # Practice areas
        if state.legal_intent:
            query["practice_areas"] = state.legal_intent
        
        # Budget considerations
        if state.facts.get("budget_range"):
            query["budget_range"] = state.facts["budget_range"]
        
        # Text search for specific needs
        search_terms = []
        if "custody" in state.legal_intent and state.facts.get("children_count"):
            search_terms.append("child custody expert")
        if "divorce" in state.legal_intent and "property" in state.user_text.lower():
            search_terms.append("property division")
        if "domestic_violence" in state.legal_intent:
            search_terms.append("protective orders emergency")
        
        if search_terms:
            query["text"] = " ".join(search_terms)
        
        return query
    
    async def _rank_and_personalize(
        self, 
        lawyers: List[Dict[str, Any]], 
        state: TurnState, 
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Rank lawyers based on user's specific needs"""
        
        # Get user profile for personalization
        user_profile = context.get("user_profile", {})
        preferences = user_profile.get("preferences", {})
        
        # Score each lawyer
        scored_lawyers = []
        for lawyer in lawyers:
            score = lawyer.get("match_score", 0.5)  # Base Elasticsearch score
            
            # Boost for exact practice area match
            lawyer_areas = set(lawyer.get("practice_areas", []))
            user_needs = set(state.legal_intent)
            overlap = len(lawyer_areas & user_needs)
            score += overlap * 0.1
            
            # Budget match bonus
            if lawyer.get("budget_range") == state.facts.get("budget_range"):
                score += 0.15
            
            # Rating bonus (normalized)
            if lawyer.get("rating"):
                score += (lawyer["rating"] - 4.0) * 0.1  # Assuming 4.0 is average
            
            # Review count bonus (popular lawyers)
            if lawyer.get("reviews_count", 0) > 100:
                score += 0.05
            
            # Specialization bonus
            if self._has_relevant_specialization(lawyer, state):
                score += 0.2
            
            # Distance penalty (if coordinates available)
            # In production, would calculate actual distance
            
            lawyer["personalized_score"] = min(score, 1.0)
            scored_lawyers.append(lawyer)
        
        # Sort by personalized score
        scored_lawyers.sort(key=lambda x: x["personalized_score"], reverse=True)
        
        return scored_lawyers
    
    def _has_relevant_specialization(self, lawyer: Dict[str, Any], state: TurnState) -> bool:
        """Check if lawyer has relevant specialization"""
        description = lawyer.get("description", "").lower()
        
        specialization_keywords = {
            "custody": ["child custody", "parenting time", "visitation rights"],
            "divorce": ["collaborative divorce", "high-asset divorce", "amicable separation"],
            "domestic_violence": ["protective order", "restraining order", "abuse victims"],
            "child_support": ["support modification", "enforcement", "calculations"],
            "adoption": ["adoption law", "stepparent adoption", "international adoption"]
        }
        
        for intent in state.legal_intent:
            if intent in specialization_keywords:
                if any(keyword in description for keyword in specialization_keywords[intent]):
                    return True
        
        return False
    
    def _format_lawyer_cards(self, lawyers: List[Dict[str, Any]]) -> List[LawyerCard]:
        """Convert to LawyerCard format"""
        cards = []
        
        for lawyer in lawyers:
            card = LawyerCard(
                id=lawyer["id"],
                name=lawyer["name"],
                firm=lawyer["firm"],
                match_score=lawyer.get("personalized_score", lawyer.get("match_score", 0.5)),
                blurb=lawyer.get("description", "")[:200] + "..." if len(lawyer.get("description", "")) > 200 else lawyer.get("description", ""),
                link=f"/lawyer/{lawyer['id']}",
                practice_areas=lawyer.get("practice_areas", []),
                location=lawyer.get("location", {}),
                rating=lawyer.get("rating"),
                reviews_count=lawyer.get("reviews_count"),
                budget_range=lawyer.get("budget_range")
            )
            cards.append(card)
        
        return cards
    
    async def _add_match_explanations(
        self, 
        lawyer_cards: List[LawyerCard], 
        state: TurnState
    ) -> List[LawyerCard]:
        """Add personalized match explanations"""
        
        for card in lawyer_cards[:3]:  # Only for top 3 to save API calls
            try:
                prompt = f"""Write a brief (1 sentence) explanation of why this lawyer is a good match.

User needs: {', '.join(state.legal_intent)}
User situation: {state.user_text[:100]}...
Lawyer: {card.name} - {card.blurb}
Practice areas: {', '.join(card.practice_areas)}

Write a warm, specific explanation:"""

                response = await self.groq_client.chat.completions.create(
                    model=settings.alliance_model,  # Using alliance model as it's fast
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=50
                )
                
                explanation = response.choices[0].message.content.strip()
                card.blurb = f"{explanation} {card.blurb}"
                
            except Exception as e:
                logger.error(f"Error generating match explanation: {e}")
        
        return lawyer_cards
    
    def _generate_cache_key(self, query: Dict[str, Any]) -> str:
        """Generate cache key for search query"""
        # Sort query items for consistent keys
        sorted_items = sorted(query.items())
        key_str = json.dumps(sorted_items, sort_keys=True)
        return f"lawyer_match:{hash(key_str)}"
    
    async def _get_cached_matches(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached lawyer matches"""
        try:
            cached = await redis_service.get(cache_key)
            if cached:
                data = json.loads(cached)
                # Convert back to LawyerCard objects
                data["lawyer_cards"] = [LawyerCard(**card) for card in data["lawyer_cards"]]
                return data
        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
        return None
    
    async def _cache_matches(self, cache_key: str, result: Dict[str, Any]):
        """Cache lawyer matches"""
        try:
            # Convert LawyerCards to dicts for JSON serialization
            cache_data = {
                **result,
                "lawyer_cards": [card.dict() for card in result["lawyer_cards"]],
                "cached_at": datetime.utcnow().isoformat()
            }
            await redis_service.set(
                cache_key,
                json.dumps(cache_data),
                ttl=self.cache_ttl
            )
        except Exception as e:
            logger.error(f"Cache storage error: {e}")