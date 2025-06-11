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
        
        # Build search context from conversation
        search_context = self._build_search_context(state, context)
        
        # Build filter query
        filters = self._build_filter_query(state)
        
        # Check cache first
        cache_key = self._generate_cache_key({"context": search_context, "filters": filters})
        cached_results = await self._get_cached_matches(cache_key)
        
        if cached_results:
            logger.info("Returning cached lawyer matches")
            return cached_results
        
        # Determine search method based on query complexity
        if self._should_use_semantic_search(state):
            # Use advanced semantic search for complex natural language queries
            lawyers = await elasticsearch_service.advanced_semantic_search(
                query_text=search_context["query"],
                context=search_context.get("situation"),
                filters=filters,
                size=10
            )
        else:
            # Use standard search for simpler queries
            lawyers = await elasticsearch_service.search_lawyers(
                query_text=search_context.get("query"),
                filters=filters,
                location=filters.get("location"),
                size=10,
                use_semantic=True
            )
        
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
        """Check if we have enough info to match lawyers - be more thorough"""
        
        # Count how many key signals we have
        signal_score = 0
        required_signals = []
        
        # Location (essential)
        if state.facts.get("zip") or (state.facts.get("city") and state.facts.get("state")):
            signal_score += 2
        else:
            required_signals.append("location")
            
        # Legal need (essential)
        if state.legal_intent and len(state.legal_intent) > 0:
            signal_score += 2
        else:
            required_signals.append("specific legal issue")
            
        # Budget information (very important)
        if state.facts.get("budget_amount") or state.facts.get("budget_range"):
            signal_score += 2
        else:
            required_signals.append("budget")
            
        # Timeline/urgency
        if state.facts.get("timeline") or state.facts.get("urgency"):
            signal_score += 1
        else:
            required_signals.append("timeline")
            
        # Family situation (if relevant)
        if "custody" in state.legal_intent or "child_support" in state.legal_intent:
            if state.facts.get("children_count") or state.facts.get("family"):
                signal_score += 1
            else:
                required_signals.append("family details")
                
        # Special circumstances
        if state.facts.get("special_circumstances") or state.facts.get("preferences"):
            signal_score += 1
            
        # Goals and priorities
        if state.facts.get("goals") or state.facts.get("priorities"):
            signal_score += 1
            
        # Store what's missing for later use
        self._missing_signals = required_signals
        
        # Need at least 6 points to proceed with matching
        # This ensures we have location + legal need + at least one other major factor
        return signal_score >= 6
    
    def _get_missing_info(self, state: TurnState) -> List[str]:
        """Identify what information is missing"""
        # Return the signals identified during sufficient_info check
        return getattr(self, '_missing_signals', [])
    
    def _build_search_context(self, state: TurnState, context: Dict[str, Any]) -> Dict[str, str]:
        """Build search context for semantic search"""
        # Extract key information from conversation
        legal_needs = ', '.join(state.legal_intent) if state.legal_intent else "family law attorney"
        
        # Build natural language query
        query_parts = []
        
        # Add legal needs
        if state.legal_intent:
            query_parts.append(f"lawyer for {legal_needs}")
        
        # Add specific requirements from facts
        if state.facts.get("child_involved"):
            query_parts.append("experienced with child custody")
        if state.facts.get("domestic_violence"):
            query_parts.append("handles domestic violence cases")
        if state.facts.get("urgent"):
            query_parts.append("available for urgent consultation")
        if state.facts.get("languages"):
            query_parts.append(f"speaks {state.facts['languages']}")
            
        # Build situation context
        situation = state.user_text[:500] if state.user_text else ""
        if context.get("user_profile", {}).get("summary"):
            situation = f"{context['user_profile']['summary']} Current situation: {situation}"
            
        return {
            "query": " ".join(query_parts) or "family law attorney",
            "situation": situation
        }
    
    def _should_use_semantic_search(self, state: TurnState) -> bool:
        """Determine if semantic search is appropriate"""
        # Use semantic search for complex queries or natural language
        has_complex_needs = len(state.legal_intent) > 1 if state.legal_intent else False
        has_specific_requirements = len(state.facts) > 3
        has_narrative = len(state.user_text) > 100 if state.user_text else False
        
        return has_complex_needs or has_specific_requirements or has_narrative
    
    def _build_filter_query(self, state: TurnState) -> Dict[str, Any]:
        """Build filter query for Elasticsearch"""
        filters = {}
        
        # Location filters
        if state.facts.get("zip"):
            # Convert zip to coordinates if possible
            filters["location"] = self._zip_to_coordinates(state.facts["zip"])
        elif state.facts.get("state"):
            filters["state"] = state.facts["state"]
        elif state.facts.get("city") and state.facts.get("state"):
            filters["city"] = state.facts["city"]
            filters["state"] = state.facts["state"]
        
        # Practice areas
        if state.legal_intent:
            filters["practice_areas"] = state.legal_intent
        
        # Budget and fee structure
        if state.facts.get("budget_amount"):
            # Handle specific budget amounts
            budget = state.facts["budget_amount"]
            if budget < 2000:
                filters["free_consultation"] = True
                filters["payment_plans"] = True
            elif budget < 5000:
                filters["max_hourly_rate"] = 250
            elif budget < 10000:
                filters["max_hourly_rate"] = 350
        elif state.facts.get("budget_range"):
            if state.facts["budget_range"] == "low" or state.facts["budget_range"] == "$":
                filters["free_consultation"] = True
            elif state.facts["budget_range"] == "high" or state.facts["budget_range"] == "$$$":
                filters["min_rating"] = 4.5
        
        # Languages
        if state.facts.get("languages"):
            filters["languages"] = state.facts["languages"]
        
        # Experience level
        if state.facts.get("experience_preference"):
            if state.facts["experience_preference"] == "senior":
                filters["min_experience"] = 10
            elif state.facts["experience_preference"] == "experienced":
                filters["min_experience"] = 5
        
        # Quality filters
        if not state.facts.get("budget_range") or state.facts.get("budget_range") != "low":
            filters["min_rating"] = 3.5
        
        return filters
    
    def _zip_to_coordinates(self, zip_code: str) -> Optional[Dict[str, float]]:
        """Convert ZIP code to coordinates (simplified - in production use geocoding service)"""
        # This is a placeholder - in production, use a geocoding service
        # For now, return None to use text-based location search
        return None
    
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