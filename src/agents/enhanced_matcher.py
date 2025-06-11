"""
Enhanced Lawyer Matching Algorithm 2.0
Implements intelligent, progressive information gathering and multi-stage matching
"""

from typing import Dict, Any, List, Optional, Tuple
import asyncio
from dataclasses import dataclass
from enum import Enum
from groq import AsyncGroq

from src.services.database import elasticsearch_service
from src.agents.base import BaseAgent
from src.models.conversation import TurnState
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class InformationCategory(Enum):
    """Categories of information needed for matching"""
    LOCATION = "location"
    PRACTICE_AREA = "practice_area"
    BUDGET = "budget"
    TIMELINE = "timeline"
    LANGUAGE = "language"
    SPECIALIZATION = "specialization"
    PREFERENCES = "preferences"


@dataclass
class InformationCompleteness:
    """Track completeness of user information"""
    location: float = 0.0
    practice_area: float = 0.0
    budget: float = 0.0
    timeline: float = 0.0
    language: float = 0.0
    specialization: float = 0.0
    preferences: float = 0.0
    
    @property
    def total_score(self) -> float:
        """Calculate weighted total completeness score"""
        weights = {
            "location": 0.25,
            "practice_area": 0.30,
            "budget": 0.15,
            "timeline": 0.10,
            "language": 0.05,
            "specialization": 0.10,
            "preferences": 0.05
        }
        
        score = 0.0
        for field, weight in weights.items():
            score += getattr(self, field) * weight
        return score
    
    @property
    def missing_required(self) -> List[str]:
        """Get list of missing required information"""
        required = ["location", "practice_area"]
        missing = []
        for field in required:
            if getattr(self, field) < 0.5:
                missing.append(field)
        return missing


class EnhancedMatcherAgent(BaseAgent):
    """Enhanced lawyer matching with progressive information gathering"""
    
    def __init__(self):
        super().__init__("enhanced_matcher")
        self.groq_client = AsyncGroq(api_key=settings.groq_api_key)
        self.model = "llama-3.3-70b-versatile"
        self.temperature = 0.1
        
        # Base weights for scoring
        self.base_weights = {
            "practice_area": 0.30,
            "location": 0.20,
            "budget": 0.20,
            "quality": 0.15,
            "preferences": 0.15
        }
    
    async def process(self, state: TurnState) -> TurnState:
        """Process matching with progressive information gathering"""
        try:
            logger.info(f"Enhanced matcher starting with user text: {state.user_text[:100]}...")
            logger.info(f"Legal intent: {state.legal_intent}, Facts: {state.facts}")
            
            # Calculate information completeness
            completeness = self._calculate_completeness(state)
            logger.info(f"Information completeness: {completeness.total_score:.2f}")
            
            # Check if we need more information
            # Lower threshold to 0.4 and allow matching even with missing info
            if completeness.total_score < 0.4 and completeness.missing_required:
                questions = await self._generate_targeted_questions(
                    state, completeness
                )
                state.suggestions = questions
                state.metrics["needs_more_info"] = True
                state.metrics["completeness_score"] = completeness.total_score
                
                # Still try to match lawyers if we have basic info
                if completeness.location == 0 and completeness.practice_area == 0:
                    return state  # Only return if we have NO info at all
            
            # Build multi-layer query
            query = await self._build_enhanced_query(state, completeness)
            
            # Execute searches
            results = await self._execute_searches(query, state)
            
            # Score and rank results
            scored_results = await self._score_results(
                results, state, completeness
            )
            
            # Generate match explanations
            top_matches = scored_results[:5]
            for match in top_matches:
                match["match_explanation"] = await self._generate_explanation(
                    match, state
                )
            
            # Format based on user state
            if state.distress_score > 6:
                state.lawyer_matches = self._format_empathetic_results(top_matches)
            else:
                state.lawyer_matches = self._format_standard_results(top_matches)
            
            # Add follow-up suggestions
            state.suggestions = await self._generate_follow_up_suggestions(
                state, top_matches
            )
            
            # Update metrics
            state.metrics["matches_found"] = len(top_matches)
            state.metrics["completeness_score"] = completeness.total_score
            state.metrics["search_method"] = query.get("method", "standard")
            
        except Exception as e:
            logger.error(f"Error in enhanced matching: {e}")
            state.errors.append(f"Matching error: {str(e)}")
        
        return state
    
    def _calculate_completeness(self, state: TurnState) -> InformationCompleteness:
        """Calculate how complete the user's information is"""
        completeness = InformationCompleteness()
        facts = state.facts or {}
        
        # Location completeness
        if facts.get("zip") or facts.get("city"):
            completeness.location = 1.0
        elif facts.get("state"):
            completeness.location = 0.7
        
        # Practice area completeness
        if state.legal_intent:
            completeness.practice_area = 1.0
        else:
            # Check for any family law keywords
            keywords = [
                "divorce", "custody", "support", "adoption", "separation",
                "alimony", "visitation", "guardian", "paternity", "restraining",
                "abuse", "violence", "property", "assets", "lawyer", "attorney",
                "legal", "court", "file", "help"
            ]
            if any(keyword in state.user_text.lower() for keyword in keywords):
                completeness.practice_area = 0.8
        
        # Budget completeness
        if facts.get("budget"):
            completeness.budget = 1.0
        elif any(term in state.user_text.lower() 
                for term in ["can't afford", "low income", "expensive"]):
            completeness.budget = 0.5
        
        # Timeline completeness
        if facts.get("timeline") or facts.get("urgency"):
            completeness.timeline = 1.0
        elif any(term in state.user_text.lower() 
                for term in ["urgent", "emergency", "immediately", "asap"]):
            completeness.timeline = 0.8
        
        # Language preferences
        if facts.get("language"):
            completeness.language = 1.0
        
        # Specialization needs
        if facts.get("special_needs") or facts.get("complications"):
            completeness.specialization = 1.0
        
        return completeness
    
    async def _generate_targeted_questions(
        self, 
        state: TurnState, 
        completeness: InformationCompleteness
    ) -> List[str]:
        """Generate questions for missing information"""
        questions = []
        
        # Priority questions for missing required info
        if "location" in completeness.missing_required:
            questions.append("What city or zip code are you in? This helps me find lawyers near you.")
        
        if "practice_area" in completeness.missing_required:
            if state.distress_score > 7:
                questions.append("What kind of legal help do you need most urgently?")
            else:
                questions.append("What specific family law issue can I help you with today?")
        
        # Additional helpful questions based on gaps
        if completeness.budget < 0.5 and len(questions) < 3:
            questions.append("Do you have a budget range in mind for legal fees?")
        
        if completeness.timeline < 0.5 and state.distress_score > 5:
            questions.append("How urgent is your situation?")
        
        return questions[:3]  # Limit to 3 questions
    
    async def _build_enhanced_query(
        self, 
        state: TurnState, 
        completeness: InformationCompleteness
    ) -> Dict[str, Any]:
        """Build multi-layer search query"""
        facts = state.facts or {}
        
        # Essential query
        essential_query = {
            "practice_areas": state.legal_intent or [],
            "location": {
                "zip": facts.get("zip"),
                "city": facts.get("city"),
                "state": facts.get("state")
            }
        }
        
        # Preference query
        preference_query = {
            "budget": facts.get("budget"),
            "language": facts.get("language"),
            "specializations": facts.get("special_needs", [])
        }
        
        # Determine if semantic search is needed
        needs_semantic = self._needs_semantic_search(state.user_text)
        
        query = {
            "essential": essential_query,
            "preferences": preference_query,
            "method": "semantic" if needs_semantic else "standard"
        }
        
        if needs_semantic:
            query["semantic"] = await self._build_semantic_query(state)
        
        return query
    
    def _needs_semantic_search(self, text: str) -> bool:
        """Determine if semantic search would be beneficial"""
        semantic_indicators = [
            "aggressive", "compassionate", "experienced", "won't back down",
            "understands", "patient", "fighter", "gentle", "tough",
            "speaks my language", "gets it", "been through this"
        ]
        
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in semantic_indicators)
    
    async def _build_semantic_query(self, state: TurnState) -> str:
        """Build semantic search query from user context"""
        # Extract key phrases that indicate preferences
        prompt = f"""Based on this user's situation, create a semantic search query for finding lawyers.
        
User's text: {state.user_text}
Legal issues: {', '.join(state.legal_intent or [])}
Emotional state: {state.sentiment} (distress level: {state.distress_score})

Generate a natural language query that captures what kind of lawyer would best serve this person.
Focus on personality traits, approach style, and specializations that match their needs."""

        response = await self._call_llm(prompt)
        return response.strip()
    
    async def _call_llm(self, prompt: str) -> str:
        """Call the LLM with the given prompt"""
        try:
            response = await self.groq_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that generates search queries and matching criteria."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=200
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            return ""
    
    async def _execute_searches(
        self, 
        query: Dict[str, Any], 
        state: TurnState
    ) -> List[Dict[str, Any]]:
        """Execute parallel searches based on query"""
        search_tasks = []
        
        # Standard search
        # Build filters for search_lawyers
        filters = {}
        
        # Add location filters
        location_data = query["essential"]["location"]
        # Note: ZIP is not in the mapping, so we'll use city/state
        if location_data.get("city"):
            filters["city"] = location_data["city"]
        if location_data.get("state"):
            # Map state abbreviations to full names (as stored in DB)
            state_map = {
                "IL": "illinois", "CA": "california", "TX": "texas", "AZ": "arizona",
                "WA": "washington", "NY": "new-york", "FL": "florida", "PA": "pennsylvania",
                "OH": "ohio", "GA": "georgia", "NC": "north-carolina", "MI": "michigan",
                "NJ": "new-jersey", "VA": "virginia", "MA": "massachusetts", "IN": "indiana",
                "MO": "missouri", "TN": "tennessee", "WI": "wisconsin", "MD": "maryland",
                "MN": "minnesota", "CO": "colorado", "AL": "alabama", "SC": "south-carolina",
                "LA": "louisiana", "KY": "kentucky", "OR": "oregon", "OK": "oklahoma",
                "CT": "connecticut", "IA": "iowa", "UT": "utah", "NV": "nevada",
                "AR": "arkansas", "MS": "mississippi", "KS": "kansas", "NM": "new-mexico",
                "NE": "nebraska", "WV": "west-virginia", "ID": "idaho", "HI": "hawaii",
                "NH": "new-hampshire", "ME": "maine", "RI": "rhode-island", "MT": "montana",
                "DE": "delaware", "SD": "south-dakota", "ND": "north-dakota", "AK": "alaska",
                "VT": "vermont", "WY": "wyoming", "DC": "district-of-columbia"
            }
            
            state_input = location_data["state"]
            # If it's an abbreviation, map it; otherwise assume it's already full name
            if len(state_input) == 2:
                filters["state"] = state_map.get(state_input.upper(), state_input.lower())
            else:
                filters["state"] = state_input.lower()
            
        # Add practice areas - map our legal intents to actual practice areas in DB
        if query["essential"]["practice_areas"]:
            # Map common legal intents to practice areas in the database
            practice_area_map = {
                "divorce": "Family Law",
                "custody": "Family Law", 
                "child_custody": "Family Law",
                "child_support": "Family Law",
                "alimony": "Family Law",
                "spousal_support": "Family Law",
                "adoption": "Family Law",
                "guardianship": "Family Law",
                "domestic_violence": "Family Law",
                "restraining_order": "Family Law",
                "property_division": "Family Law",
                "separation": "Family Law",
                "paternity": "Family Law"
            }
            
            # Convert legal intents to practice areas
            practice_areas = []
            for intent in query["essential"]["practice_areas"]:
                mapped_area = practice_area_map.get(intent.lower(), intent)
                if mapped_area not in practice_areas:
                    practice_areas.append(mapped_area)
            
            if practice_areas:
                filters["practice_areas"] = practice_areas
            
        # Add budget - extract the budget range string from the facts
        if query["preferences"]["budget"]:
            # If it's a dict (from signal extract), convert to budget string
            if isinstance(query["preferences"]["budget"], dict):
                # Skip complex budget objects for now
                pass
            else:
                # It's a simple string like "$$"
                filters["budget"] = query["preferences"]["budget"]
        
        # Create query text from user's message or practice areas
        query_text = None
        if state.legal_intent:
            query_text = " ".join(state.legal_intent)
        
        # Check if elasticsearch is initialized
        if not elasticsearch_service.client:
            logger.error("Elasticsearch client not initialized")
            return []
        
        logger.info(f"Searching with query_text='{query_text}', filters={filters}")
            
        search_tasks.append(
            elasticsearch_service.search_lawyers(
                query_text=query_text,
                filters=filters,
                size=20,
                use_semantic=False  # Disable semantic for standard search
            )
        )
        
        # Semantic search if needed
        if query.get("semantic"):
            search_tasks.append(
                elasticsearch_service.advanced_semantic_search(
                    query["semantic"], 
                    filters=filters,
                    size=10
                )
            )
        
        # Execute searches in parallel
        results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # Merge results
        merged_results = []
        seen_ids = set()
        
        logger.info(f"Search returned {len(results)} result sets")
        
        for i, result_set in enumerate(results):
            if isinstance(result_set, Exception):
                logger.error(f"Search error in task {i}: {result_set}")
                continue
            
            logger.info(f"Result set {i} has {len(result_set) if result_set else 0} lawyers")
                
            for lawyer in result_set:
                if lawyer["id"] not in seen_ids:
                    seen_ids.add(lawyer["id"])
                    merged_results.append(lawyer)
        
        logger.info(f"Total merged results: {len(merged_results)}")
        return merged_results
    
    async def _score_results(
        self,
        results: List[Dict[str, Any]],
        state: TurnState,
        completeness: InformationCompleteness
    ) -> List[Dict[str, Any]]:
        """Score and rank results with contextual weights"""
        # Adjust weights based on context
        weights = self._adjust_weights_for_context(state, completeness)
        
        scored_results = []
        for lawyer in results:
            score = self._calculate_match_score(lawyer, state, weights)
            lawyer["final_score"] = score["total"]
            lawyer["score_components"] = score
            scored_results.append(lawyer)
        
        # Sort by final score
        scored_results.sort(key=lambda x: x["final_score"], reverse=True)
        
        return scored_results
    
    def _adjust_weights_for_context(
        self,
        state: TurnState,
        completeness: InformationCompleteness
    ) -> Dict[str, float]:
        """Adjust scoring weights based on user context"""
        weights = self.base_weights.copy()
        
        # Crisis situations prioritize availability
        if state.distress_score > 7:
            weights["preferences"] = 0.25  # Increase preference weight
            weights["quality"] = 0.10      # Decrease quality weight
        
        # High engagement users get more personalized matches
        if state.engagement_level > 7:
            weights["preferences"] = 0.20
            weights["quality"] = 0.20
        
        # Normalize weights
        total = sum(weights.values())
        for k in weights:
            weights[k] = weights[k] / total
        
        return weights
    
    def _calculate_match_score(
        self,
        lawyer: Dict[str, Any],
        state: TurnState,
        weights: Dict[str, float]
    ) -> Dict[str, float]:
        """Calculate multi-factor match score"""
        scores = {
            "practice_area": self._score_practice_area(lawyer, state),
            "location": self._score_location(lawyer, state),
            "budget": self._score_budget(lawyer, state),
            "quality": self._score_quality(lawyer),
            "preferences": self._score_preferences(lawyer, state)
        }
        
        # Calculate weighted total
        total = sum(scores[k] * weights[k] for k in scores)
        scores["total"] = total
        
        return scores
    
    def _score_practice_area(self, lawyer: Dict[str, Any], state: TurnState) -> float:
        """Score practice area match"""
        if not state.legal_intent:
            return 0.5
        
        lawyer_areas = set(lawyer.get("practice_areas", []))
        user_areas = set(state.legal_intent)
        
        if not lawyer_areas:
            return 0.0
        
        # Calculate overlap
        overlap = len(lawyer_areas & user_areas)
        return overlap / len(user_areas) if user_areas else 0.5
    
    def _score_location(self, lawyer: Dict[str, Any], state: TurnState) -> float:
        """Score location match"""
        facts = state.facts or {}
        lawyer_loc = lawyer.get("location", {})
        
        # Exact zip match
        if facts.get("zip") and lawyer_loc.get("zip") == facts["zip"]:
            return 1.0
        
        # Same city
        if facts.get("city") and lawyer_loc.get("city") == facts["city"]:
            return 0.8
        
        # Same state
        if facts.get("state") and lawyer_loc.get("state") == facts["state"]:
            return 0.6
        
        return 0.3
    
    def _score_budget(self, lawyer: Dict[str, Any], state: TurnState) -> float:
        """Score budget compatibility"""
        facts = state.facts or {}
        user_budget = facts.get("budget", "$$")
        lawyer_budget = lawyer.get("budget_range", "$$")
        
        budget_map = {"$": 1, "$$": 2, "$$$": 3, "$$$$": 4}
        user_level = budget_map.get(user_budget, 2)
        lawyer_level = budget_map.get(lawyer_budget, 2)
        
        # Perfect match
        if user_level == lawyer_level:
            return 1.0
        
        # Lawyer is cheaper than user's budget
        if lawyer_level < user_level:
            return 0.9
        
        # Lawyer is one level more expensive
        if lawyer_level == user_level + 1:
            return 0.6
        
        # Lawyer is much more expensive
        return 0.3
    
    def _score_quality(self, lawyer: Dict[str, Any]) -> float:
        """Score based on quality metrics"""
        rating = lawyer.get("rating", 0)
        reviews = lawyer.get("reviews_count", 0)
        
        # Normalize rating (0-5 scale to 0-1)
        rating_score = rating / 5.0 if rating else 0.5
        
        # Consider review count (more reviews = more reliable)
        if reviews >= 50:
            review_factor = 1.0
        elif reviews >= 20:
            review_factor = 0.8
        elif reviews >= 5:
            review_factor = 0.6
        else:
            review_factor = 0.4
        
        return rating_score * review_factor
    
    def _score_preferences(self, lawyer: Dict[str, Any], state: TurnState) -> float:
        """Score based on user preferences and special needs"""
        score = 0.5  # Base score
        facts = state.facts or {}
        
        # Language match
        if facts.get("language"):
            lawyer_languages = lawyer.get("languages", [])
            if facts["language"] in lawyer_languages:
                score += 0.2
        
        # Special needs match
        if facts.get("special_needs"):
            lawyer_specs = lawyer.get("specializations", [])
            for need in facts["special_needs"]:
                if need in lawyer_specs:
                    score += 0.1
        
        # Semantic match score if available
        if "semantic_score" in lawyer:
            score = (score + lawyer["semantic_score"]) / 2
        
        return min(score, 1.0)
    
    async def _generate_explanation(
        self,
        lawyer: Dict[str, Any],
        state: TurnState
    ) -> str:
        """Generate explanation for why this lawyer was matched"""
        components = lawyer.get("score_components", {})
        
        explanations = []
        
        # Practice area match
        if components.get("practice_area", 0) > 0.8:
            explanations.append(f"specializes in {', '.join(lawyer.get('practice_areas', []))}")
        
        # Location match
        if components.get("location", 0) > 0.8:
            explanations.append("located near you")
        elif components.get("location", 0) > 0.6:
            explanations.append("in your area")
        
        # Budget match
        if components.get("budget", 0) > 0.8:
            explanations.append("fits your budget")
        
        # Quality
        if lawyer.get("rating", 0) >= 4.5:
            explanations.append(f"highly rated ({lawyer['rating']:.1f} stars)")
        
        # Join explanations
        if explanations:
            return "Matched because: " + ", ".join(explanations)
        else:
            return "Good general match for your needs"
    
    def _format_empathetic_results(
        self,
        matches: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Format results with empathy for distressed users"""
        formatted = []
        
        for lawyer in matches:
            formatted.append({
                "id": lawyer.get("id", ""),
                "name": lawyer.get("name", "Unknown"),
                "firm": lawyer.get("firm", "Independent Practice"),
                "match_score": f"{lawyer['final_score']:.0%}",
                "blurb": self._create_empathetic_blurb(lawyer),
                "link": f"/lawyer/{lawyer['id']}",
                "urgency_note": "Available for urgent consultations" 
                    if lawyer.get("emergency_available") else None
            })
        
        return formatted
    
    def _create_empathetic_blurb(self, lawyer: Dict[str, Any]) -> str:
        """Create an empathetic description for distressed users"""
        blurb_parts = []
        
        if lawyer.get("rating", 0) >= 4.5:
            blurb_parts.append("Highly trusted by clients")
        
        if "compassionate" in lawyer.get("description", "").lower():
            blurb_parts.append("known for compassionate approach")
        
        if lawyer.get("emergency_available"):
            blurb_parts.append("available for urgent cases")
        
        return ". ".join(blurb_parts) if blurb_parts else lawyer.get("description", "")[:150]
    
    def _format_standard_results(
        self,
        matches: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Format results in standard way"""
        formatted = []
        
        for lawyer in matches:
            formatted.append({
                "id": lawyer.get("id", ""),
                "name": lawyer.get("name", "Unknown"),
                "firm": lawyer.get("firm", "Independent Practice"),
                "match_score": f"{lawyer['final_score']:.0%}",
                "blurb": (lawyer.get("description", "") or "")[:200],
                "link": f"/lawyer/{lawyer['id']}",
                "match_explanation": lawyer.get("match_explanation", ""),
                "practice_areas": lawyer.get("practice_areas", []),
                "location": lawyer.get("location", {}),
                "rating": lawyer.get("rating"),
                "reviews_count": lawyer.get("reviews_count"),
                "budget_range": lawyer.get("budget_range")
            })
        
        return formatted
    
    async def _generate_follow_up_suggestions(
        self,
        state: TurnState,
        matches: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate follow-up suggestions based on matches"""
        suggestions = []
        
        if matches:
            suggestions.append("Would you like to know more about any of these lawyers?")
            
            if state.distress_score > 6:
                suggestions.append("Should I help you prepare questions for your consultation?")
            else:
                suggestions.append("What questions do you have about the lawyers I found?")
            
            if not state.facts.get("timeline"):
                suggestions.append("When would you like to schedule a consultation?")
        else:
            suggestions.append("Would you like me to search in nearby areas?")
            suggestions.append("Should we adjust your criteria?")
        
        return suggestions[:3]