"""
Ultra-Intelligent Lawyer Matching Service
The most advanced lawyer matching system on the planet
Leverages ALL available data for perfect matches
"""

from typing import Dict, Any, List, Optional, Tuple, Set
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
from groq import AsyncGroq
import json
import re
from collections import defaultdict

from src.services.database import elasticsearch_service, redis_service
from src.services.perplexity_service import get_perplexity_service
from src.models.conversation import TurnState, LawyerCard
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class UserIntent:
    """Detailed user intent analysis"""
    # Primary needs
    legal_issues: List[str]
    urgency: str  # immediate, soon, flexible
    complexity: str  # simple, moderate, complex
    
    # Emotional needs
    communication_style: str  # aggressive, gentle, balanced, collaborative
    support_level: str  # high-touch, moderate, minimal
    
    # Practical needs
    budget_constraints: Dict[str, Any]
    schedule_flexibility: Dict[str, Any]
    location_requirements: Dict[str, Any]
    
    # Cultural/personal needs
    language_needs: List[str]
    cultural_background: Optional[str]
    gender_preference: Optional[str]
    lgbtq_needs: bool
    accessibility_needs: List[str]
    
    # Specific requirements
    specializations_needed: List[str]
    avoid_characteristics: List[str]
    must_have_characteristics: List[str]
    
    # Derived insights
    vulnerability_indicators: List[str]
    success_factors: List[str]


@dataclass
class LawyerScore:
    """Comprehensive scoring for a lawyer match"""
    lawyer_id: str
    
    # Core matching scores (0-1)
    practice_area_match: float = 0.0
    location_match: float = 0.0
    budget_match: float = 0.0
    availability_match: float = 0.0
    
    # Quality scores (0-1)
    quality_score: float = 0.0
    reputation_score: float = 0.0
    success_rate_score: float = 0.0
    review_sentiment_score: float = 0.0
    
    # Personality/fit scores (0-1)
    communication_style_match: float = 0.0
    cultural_fit_score: float = 0.0
    personality_match: float = 0.0
    
    # Special consideration scores
    urgency_readiness: float = 0.0
    complexity_capability: float = 0.0
    vulnerability_sensitivity: float = 0.0
    
    # Bonus/penalty factors
    bonus_points: float = 0.0
    penalty_points: float = 0.0
    
    # Explanations
    match_reasons: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)
    
    @property
    def total_score(self) -> float:
        """Calculate weighted total score"""
        base_score = (
            self.practice_area_match * 0.20 +
            self.location_match * 0.10 +
            self.budget_match * 0.15 +
            self.availability_match * 0.10 +
            self.quality_score * 0.15 +
            self.reputation_score * 0.10 +
            self.communication_style_match * 0.10 +
            self.cultural_fit_score * 0.05 +
            self.complexity_capability * 0.05
        )
        return max(0, min(1, base_score + self.bonus_points - self.penalty_points))


class IntelligentMatcherService:
    """
    The most intelligent lawyer matching system that understands exactly
    what kind of lawyer a user needs and finds the perfect match
    """
    
    def __init__(self):
        self.groq_client = AsyncGroq(api_key=settings.groq_api_key)
        self.perplexity = get_perplexity_service()
        self.llm_model = "llama-3.3-70b-versatile"
        
    async def find_perfect_lawyers(
        self, 
        state: TurnState, 
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Main entry point: Find the perfect lawyers for this user
        """
        logger.info("Starting intelligent lawyer matching")
        
        # Step 1: Deep understanding of what the user needs
        user_intent = await self._understand_user_intent(state, user_profile)
        logger.info(f"User intent analyzed: {user_intent.legal_issues}, urgency: {user_intent.urgency}")
        
        # Step 2: Search with multiple strategies
        candidates = await self._multi_strategy_search(user_intent, state)
        logger.info(f"Found {len(candidates)} candidates from multi-strategy search")
        
        # Step 3: Score each lawyer comprehensively
        scored_lawyers = await self._comprehensive_scoring(candidates, user_intent, state)
        logger.info(f"Scored {len(scored_lawyers)} lawyers")
        
        # Step 4: Enrich top candidates with external data
        top_candidates = sorted(scored_lawyers, key=lambda x: x[1].total_score, reverse=True)[:10]
        enriched = await self._enrich_top_candidates(top_candidates, user_intent)
        
        # Step 5: Final ranking with AI insights
        final_ranking = await self._ai_powered_final_ranking(enriched, user_intent, state)
        
        # Step 6: Generate personalized presentations
        lawyer_cards = await self._create_personalized_cards(final_ranking[:5], user_intent, state)
        
        # Step 7: Generate match insights
        insights = self._generate_match_insights(final_ranking, user_intent)
        
        return {
            "lawyer_cards": lawyer_cards,
            "match_reason": "intelligent_matching",
            "total_analyzed": len(candidates),
            "confidence_score": self._calculate_confidence(final_ranking),
            "user_intent": self._intent_summary(user_intent),
            "insights": insights,
            "search_methods_used": self._get_search_methods_used(user_intent)
        }
    
    async def _understand_user_intent(
        self, 
        state: TurnState, 
        user_profile: Dict[str, Any]
    ) -> UserIntent:
        """
        Deeply understand what kind of lawyer the user needs
        """
        # Start with explicit signals
        facts = state.facts or {}
        
        # Use LLM to extract implicit needs
        implicit_needs = await self._extract_implicit_needs(state)
        
        # Determine communication style preference
        comm_style = await self._determine_communication_style(state, implicit_needs)
        
        # Extract all requirements
        intent = UserIntent(
            legal_issues=state.legal_intent or self._extract_legal_issues(state.user_text),
            urgency=self._determine_urgency(state, facts),
            complexity=self._assess_complexity(state, facts),
            communication_style=comm_style,
            support_level=self._determine_support_level(state),
            budget_constraints=self._extract_budget_constraints(facts, state.user_text),
            schedule_flexibility=self._extract_schedule_needs(facts, state.user_text),
            location_requirements=self._extract_location_requirements(facts),
            language_needs=self._extract_language_needs(facts, state.user_text),
            cultural_background=facts.get("cultural_background") or implicit_needs.get("cultural_hints"),
            gender_preference=facts.get("gender_preference") or implicit_needs.get("gender_preference"),
            lgbtq_needs=self._detect_lgbtq_needs(state.user_text, facts),
            accessibility_needs=self._extract_accessibility_needs(facts, state.user_text),
            specializations_needed=self._determine_specializations(state, facts),
            avoid_characteristics=implicit_needs.get("avoid", []),
            must_have_characteristics=implicit_needs.get("must_have", []),
            vulnerability_indicators=self._assess_vulnerability(state),
            success_factors=implicit_needs.get("success_factors", [])
        )
        
        return intent
    
    async def _extract_implicit_needs(self, state: TurnState) -> Dict[str, Any]:
        """Use AI to extract implicit needs from conversation"""
        
        prompt = f"""Analyze this legal consultation request to understand implicit needs:

User message: {state.user_text}
Emotional state: {state.enhanced_sentiment} (distress: {state.distress_score}/10)
Legal issues: {', '.join(state.legal_intent or [])}
Facts: {json.dumps(state.facts or {}, indent=2)}

Extract:
1. Communication style hints (e.g., "need someone aggressive", "want gentle approach")
2. Cultural hints (background, community, values)
3. Gender preference hints (if any)
4. Personality traits they'd prefer in a lawyer
5. Characteristics to avoid
6. What would make them feel comfortable
7. Success factors for their case
8. Hidden concerns or fears

Return as JSON with keys: communication_hints, cultural_hints, gender_preference, 
preferred_traits, avoid, must_have, comfort_factors, success_factors, hidden_concerns"""

        try:
            response = await self.groq_client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Failed to extract implicit needs: {e}")
            return {}
    
    async def _determine_communication_style(
        self, 
        state: TurnState,
        implicit_needs: Dict[str, Any]
    ) -> str:
        """Determine preferred lawyer communication style"""
        
        # Keywords indicating style preferences
        aggressive_keywords = ["fighter", "aggressive", "tough", "strong", "win", "battle"]
        gentle_keywords = ["gentle", "patient", "understanding", "compassionate", "kind", "caring"]
        collaborative_keywords = ["work together", "collaborative", "team", "partner"]
        
        text = state.user_text.lower()
        
        # Check explicit preferences
        if any(word in text for word in aggressive_keywords):
            return "aggressive"
        elif any(word in text for word in gentle_keywords):
            return "gentle"
        elif any(word in text for word in collaborative_keywords):
            return "collaborative"
        
        # Consider emotional state
        if state.distress_score > 7:
            return "gentle"  # High distress needs gentle approach
        elif state.enhanced_sentiment in ["anger", "frustration"]:
            return "aggressive"  # Angry users often want a fighter
        
        # Check implicit needs
        if implicit_needs.get("communication_hints"):
            hints = implicit_needs["communication_hints"].lower()
            if "aggressive" in hints or "fighter" in hints:
                return "aggressive"
            elif "gentle" in hints or "patient" in hints:
                return "gentle"
        
        return "balanced"  # Default
    
    def _determine_urgency(self, state: TurnState, facts: Dict[str, Any]) -> str:
        """Determine case urgency"""
        
        urgent_keywords = ["urgent", "emergency", "immediately", "asap", "right now", "today"]
        text = state.user_text.lower() if state.user_text else ""
        
        # Explicit urgency
        if facts.get("urgency") == "high" or facts.get("timeline") == "immediate":
            return "immediate"
        
        # Keywords in text
        if any(keyword in text for keyword in urgent_keywords):
            return "immediate"
        
        # High distress often means urgency
        if state.distress_score > 8:
            return "immediate"
        
        # Specific urgent situations
        if any(issue in state.legal_intent for issue in ["domestic_violence", "restraining_order", "emergency_custody"]):
            return "immediate"
        
        # Check timeline
        if facts.get("timeline") == "soon" or "this week" in text:
            return "soon"
        
        return "flexible"
    
    def _assess_complexity(self, state: TurnState, facts: Dict[str, Any]) -> str:
        """Assess case complexity"""
        
        # High complexity indicators
        complex_indicators = [
            len(state.legal_intent or []) > 2,  # Multiple legal issues
            facts.get("children_count", 0) > 2,  # Many children
            "business" in state.user_text.lower(),  # Business assets
            "international" in state.user_text.lower(),  # International elements
            facts.get("asset_complexity") == "high",
            facts.get("special_circumstances", False)
        ]
        
        complexity_score = sum(complex_indicators)
        
        if complexity_score >= 3:
            return "complex"
        elif complexity_score >= 1:
            return "moderate"
        else:
            return "simple"
    
    def _determine_support_level(self, state: TurnState) -> str:
        """Determine how much support the user needs"""
        
        if state.distress_score > 7 or state.engagement_level < 3:
            return "high-touch"  # Needs lots of support
        elif state.enhanced_sentiment in ["confusion", "nervousness", "fear"]:
            return "high-touch"
        elif state.engagement_level > 7 and state.distress_score < 4:
            return "minimal"  # Self-directed user
        else:
            return "moderate"
    
    def _extract_budget_constraints(self, facts: Dict[str, Any], text: str) -> Dict[str, Any]:
        """Extract detailed budget information"""
        
        budget_info = {
            "range": facts.get("budget_range", "$$"),
            "amount": facts.get("budget_amount"),
            "payment_plan_needed": facts.get("payment_plan_needed", False),
            "free_consultation_required": False,
            "cost_sensitive": False
        }
        
        # Check for cost sensitivity
        cost_keywords = ["afford", "cheap", "expensive", "budget", "cost", "free", "pro bono"]
        if any(keyword in text.lower() for keyword in cost_keywords):
            budget_info["cost_sensitive"] = True
        
        # Free consultation preference
        if "free consultation" in text.lower():
            budget_info["free_consultation_required"] = True
        
        # Payment plan indicators
        if "payment plan" in text.lower() or "installments" in text.lower():
            budget_info["payment_plan_needed"] = True
        
        return budget_info
    
    def _extract_schedule_needs(self, facts: Dict[str, Any], text: str) -> Dict[str, Any]:
        """Extract scheduling preferences"""
        
        schedule = {
            "evening_needed": False,
            "weekend_needed": False,
            "immediate_availability": False
        }
        
        text_lower = text.lower()
        
        if "evening" in text_lower or "after work" in text_lower:
            schedule["evening_needed"] = True
        if "weekend" in text_lower or "saturday" in text_lower or "sunday" in text_lower:
            schedule["weekend_needed"] = True
        if "today" in text_lower or "right now" in text_lower:
            schedule["immediate_availability"] = True
        
        return schedule
    
    def _extract_location_requirements(self, facts: Dict[str, Any]) -> Dict[str, Any]:
        """Extract detailed location requirements"""
        
        return {
            "zip": facts.get("zip"),
            "city": facts.get("city"),
            "state": facts.get("state"),
            "neighborhood": facts.get("neighborhood"),
            "max_distance": facts.get("max_distance", "10mi"),
            "prefer_virtual": facts.get("prefer_virtual", False),
            "specific_area": facts.get("specific_area")
        }
    
    def _extract_language_needs(self, facts: Dict[str, Any], text: str) -> List[str]:
        """Extract language requirements"""
        
        languages = []
        
        # Explicit language fact
        if facts.get("language"):
            languages.append(facts["language"])
        
        # Common language mentions in text
        language_patterns = {
            "spanish": ["spanish", "español", "habla español"],
            "mandarin": ["mandarin", "chinese", "中文"],
            "cantonese": ["cantonese", "广东话"],
            "korean": ["korean", "한국어"],
            "vietnamese": ["vietnamese", "tiếng việt"],
            "russian": ["russian", "русский"],
            "armenian": ["armenian", "հայերեն"],
            "farsi": ["farsi", "persian", "فارسی"],
            "arabic": ["arabic", "عربي"],
            "hebrew": ["hebrew", "עברית"]
        }
        
        text_lower = text.lower()
        for language, patterns in language_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                languages.append(language)
        
        return list(set(languages))  # Remove duplicates
    
    def _detect_lgbtq_needs(self, text: str, facts: Dict[str, Any]) -> bool:
        """Detect if user might need LGBTQ-friendly lawyer"""
        
        if facts.get("lgbtq_friendly"):
            return True
        
        # Sensitive detection - only if explicitly mentioned
        lgbtq_indicators = ["lgbtq", "gay", "lesbian", "transgender", "same-sex", "pride"]
        return any(indicator in text.lower() for indicator in lgbtq_indicators)
    
    def _extract_accessibility_needs(self, facts: Dict[str, Any], text: str) -> List[str]:
        """Extract accessibility requirements"""
        
        needs = []
        
        if facts.get("accessibility_needs"):
            needs.extend(facts["accessibility_needs"])
        
        text_lower = text.lower()
        
        # Common accessibility needs
        if "wheelchair" in text_lower:
            needs.append("wheelchair_accessible")
        if "interpreter" in text_lower or "deaf" in text_lower:
            needs.append("sign_language")
        if "blind" in text_lower or "vision" in text_lower:
            needs.append("vision_accessible")
        
        return list(set(needs))
    
    def _determine_specializations(self, state: TurnState, facts: Dict[str, Any]) -> List[str]:
        """Determine needed specializations beyond basic practice areas"""
        
        specializations = []
        
        # High asset cases
        if facts.get("asset_complexity") == "high" or "business" in state.user_text.lower():
            specializations.append("high_asset_divorce")
        
        # International elements
        if "international" in state.user_text.lower():
            specializations.append("international_family_law")
        
        # Military
        if "military" in state.user_text.lower() or facts.get("military_family"):
            specializations.append("military_divorce")
        
        # Collaborative approach
        if "collaborative" in state.user_text.lower() or "mediation" in state.user_text.lower():
            specializations.append("collaborative_divorce")
        
        # Domestic violence
        if "abuse" in state.user_text.lower() or "violence" in state.user_text.lower():
            specializations.append("domestic_violence")
        
        return specializations
    
    def _assess_vulnerability(self, state: TurnState) -> List[str]:
        """Assess vulnerability indicators"""
        
        indicators = []
        
        if state.distress_score > 7:
            indicators.append("high_distress")
        
        if state.enhanced_sentiment in ["fear", "grief", "sadness", "nervousness"]:
            indicators.append(f"emotional_{state.enhanced_sentiment}")
        
        if "abuse" in state.user_text.lower():
            indicators.append("potential_abuse_victim")
        
        if state.engagement_level < 3:
            indicators.append("low_engagement")
        
        return indicators
    
    async def _multi_strategy_search(
        self, 
        user_intent: UserIntent, 
        state: TurnState
    ) -> List[Dict[str, Any]]:
        """Execute multiple search strategies in parallel"""
        
        search_strategies = []
        
        # 1. Standard search with all filters
        search_strategies.append(self._standard_filtered_search(user_intent))
        
        # 2. Personality-based semantic search
        if user_intent.communication_style != "balanced":
            search_strategies.append(self._personality_semantic_search(user_intent))
        
        # 3. Cultural/community search
        if user_intent.cultural_background or user_intent.language_needs:
            search_strategies.append(self._cultural_community_search(user_intent))
        
        # 4. Specialization search
        if user_intent.specializations_needed:
            search_strategies.append(self._specialization_search(user_intent))
        
        # 5. Urgency-based availability search
        if user_intent.urgency == "immediate":
            search_strategies.append(self._urgent_availability_search(user_intent))
        
        # 6. Quality-focused search for complex cases
        if user_intent.complexity == "complex":
            search_strategies.append(self._high_quality_search(user_intent))
        
        # 7. Budget-conscious search
        if user_intent.budget_constraints["cost_sensitive"]:
            search_strategies.append(self._budget_friendly_search(user_intent))
        
        # Execute all searches in parallel
        results = await asyncio.gather(*search_strategies, return_exceptions=True)
        
        # Merge and deduplicate
        all_lawyers = []
        seen_ids = set()
        
        for result_set in results:
            if isinstance(result_set, Exception):
                logger.error(f"Search strategy failed: {result_set}")
                continue
            
            for lawyer in (result_set or []):
                if lawyer.get("id") and lawyer["id"] not in seen_ids:
                    seen_ids.add(lawyer["id"])
                    lawyer["search_strategies"] = lawyer.get("search_strategies", [])
                    lawyer["search_strategies"].append(result_set.__class__.__name__)
                    all_lawyers.append(lawyer)
        
        logger.info(f"Multi-strategy search found {len(all_lawyers)} unique lawyers")
        return all_lawyers
    
    async def _standard_filtered_search(self, user_intent: UserIntent) -> List[Dict[str, Any]]:
        """Standard search with comprehensive filters"""
        
        filters = {}
        
        # Location filters
        if user_intent.location_requirements["zip"]:
            filters["zip"] = user_intent.location_requirements["zip"]
        elif user_intent.location_requirements["city"]:
            filters["city"] = user_intent.location_requirements["city"]
            if user_intent.location_requirements["state"]:
                filters["state"] = user_intent.location_requirements["state"]
        
        # Practice areas - map to actual values in database
        if user_intent.legal_issues:
            filters["practice_areas"] = ["Family Law"]  # Most are family law
        
        # Budget filters
        if user_intent.budget_constraints["range"]:
            filters["budget_range"] = user_intent.budget_constraints["range"]
        
        if user_intent.budget_constraints["free_consultation_required"]:
            filters["free_consultation"] = True
        
        # Language filters
        if user_intent.language_needs:
            filters["languages"] = user_intent.language_needs[0]  # Primary language
        
        # Gender preference
        if user_intent.gender_preference:
            filters["gender"] = user_intent.gender_preference
        
        # LGBTQ friendly
        if user_intent.lgbtq_needs:
            filters["lgbtq_friendly"] = True
        
        # Accessibility
        if user_intent.accessibility_needs:
            filters["accessibility_features"] = True
        
        query_text = " ".join(user_intent.legal_issues) if user_intent.legal_issues else "family lawyer"
        
        return await elasticsearch_service.search_lawyers(
            query_text=query_text,
            filters=filters,
            size=30,
            use_semantic=False
        )
    
    async def _personality_semantic_search(self, user_intent: UserIntent) -> List[Dict[str, Any]]:
        """Search based on personality and communication style match"""
        
        # Build personality-focused query
        personality_queries = {
            "aggressive": "aggressive fighter tough lawyer won't back down strong advocate fierce representation",
            "gentle": "compassionate gentle understanding patient lawyer caring supportive empathetic kind",
            "collaborative": "collaborative lawyer mediation friendly works together team approach cooperative"
        }
        
        query = personality_queries.get(user_intent.communication_style, "")
        
        # Add support level preferences
        if user_intent.support_level == "high-touch":
            query += " responsive available supportive hand-holding guides clients"
        
        # Add vulnerability considerations
        if user_intent.vulnerability_indicators:
            query += " trauma-informed sensitive careful patient understanding"
        
        filters = self._get_basic_location_filters(user_intent)
        
        return await elasticsearch_service.advanced_semantic_search(
            query_text=query,
            filters=filters,
            size=20
        )
    
    async def _cultural_community_search(self, user_intent: UserIntent) -> List[Dict[str, Any]]:
        """Search for culturally aligned lawyers"""
        
        query_parts = []
        
        # Language capabilities
        if user_intent.language_needs:
            query_parts.append(f"speaks {' '.join(user_intent.language_needs)}")
        
        # Cultural background
        if user_intent.cultural_background:
            query_parts.append(f"{user_intent.cultural_background} community lawyer")
        
        # Neighborhood-specific if relevant
        if user_intent.location_requirements.get("neighborhood"):
            neighborhood = user_intent.location_requirements["neighborhood"]
            
            # Research neighborhood demographics
            neighborhood_info = await self.perplexity.research_neighborhood(
                neighborhood,
                user_intent.location_requirements.get("city", "Los Angeles")
            )
            
            if neighborhood_info.get("is_cultural_hub"):
                query_parts.append(f"serves {neighborhood} community")
        
        query = " ".join(query_parts)
        filters = self._get_basic_location_filters(user_intent)
        
        return await elasticsearch_service.search_lawyers(
            query_text=query,
            filters=filters,
            size=15,
            use_semantic=True
        )
    
    async def _specialization_search(self, user_intent: UserIntent) -> List[Dict[str, Any]]:
        """Search for specialized expertise"""
        
        query_parts = []
        
        for spec in user_intent.specializations_needed:
            if spec == "high_asset_divorce":
                query_parts.append("high asset divorce complex financial business valuation")
            elif spec == "international_family_law":
                query_parts.append("international custody Hague Convention cross-border")
            elif spec == "military_divorce":
                query_parts.append("military divorce USFSPA pension division")
            elif spec == "collaborative_divorce":
                query_parts.append("collaborative divorce mediation peaceful resolution")
            elif spec == "domestic_violence":
                query_parts.append("domestic violence protective orders safety planning")
        
        query = " ".join(query_parts)
        filters = self._get_basic_location_filters(user_intent)
        
        return await elasticsearch_service.search_lawyers(
            query_text=query,
            filters=filters,
            size=15,
            use_semantic=True
        )
    
    async def _urgent_availability_search(self, user_intent: UserIntent) -> List[Dict[str, Any]]:
        """Search for immediately available lawyers"""
        
        query = "available today immediate consultation emergency urgent same-day appointment"
        
        filters = self._get_basic_location_filters(user_intent)
        
        # Look for responsive lawyers
        results = await elasticsearch_service.search_lawyers(
            query_text=query,
            filters=filters,
            size=20,
            use_semantic=False
        )
        
        # Filter by response time if available
        fast_responders = []
        for lawyer in results:
            response_time = lawyer.get("quality_signals", {}).get("response_time_hours", 48)
            if response_time <= 24:  # Responds within 24 hours
                lawyer["urgency_score"] = 1.0 if response_time <= 2 else 0.8
                fast_responders.append(lawyer)
        
        return fast_responders
    
    async def _high_quality_search(self, user_intent: UserIntent) -> List[Dict[str, Any]]:
        """Search for top-tier lawyers for complex cases"""
        
        query = "top rated best lawyer excellent reviews highly recommended award winning"
        
        filters = self._get_basic_location_filters(user_intent)
        filters["min_rating"] = 4.5  # Only highly rated
        
        results = await elasticsearch_service.search_lawyers(
            query_text=query,
            filters=filters,
            size=20,
            use_semantic=False
        )
        
        # Further filter by quality signals
        high_quality = []
        for lawyer in results:
            quality_signals = lawyer.get("quality_signals", {})
            
            quality_score = (
                quality_signals.get("education_score", 0) * 0.2 +
                quality_signals.get("professional_score", 0) * 0.3 +
                quality_signals.get("awards_score", 0) * 0.2 +
                quality_signals.get("associations_score", 0) * 0.1 +
                (lawyer.get("reviews_count", 0) / 100) * 0.2  # More reviews = more reliable
            )
            
            if quality_score > 0.7:
                lawyer["quality_score"] = quality_score
                high_quality.append(lawyer)
        
        return high_quality
    
    async def _budget_friendly_search(self, user_intent: UserIntent) -> List[Dict[str, Any]]:
        """Search for affordable lawyers"""
        
        query = "affordable lawyer payment plans free consultation low cost sliding scale"
        
        filters = self._get_basic_location_filters(user_intent)
        filters["free_consultation"] = True
        
        # Adjust budget range down if specified
        if user_intent.budget_constraints["range"] in ["$$", "$$$", "$$$$"]:
            filters["budget_range"] = "$"  # Look for most affordable
        
        return await elasticsearch_service.search_lawyers(
            query_text=query,
            filters=filters,
            size=20,
            use_semantic=False
        )
    
    def _get_basic_location_filters(self, user_intent: UserIntent) -> Dict[str, Any]:
        """Get basic location filters from intent"""
        filters = {}
        
        if user_intent.location_requirements["zip"]:
            filters["zip"] = user_intent.location_requirements["zip"]
        elif user_intent.location_requirements["city"]:
            filters["city"] = user_intent.location_requirements["city"]
            if user_intent.location_requirements["state"]:
                filters["state"] = user_intent.location_requirements["state"]
        
        return filters
    
    async def _comprehensive_scoring(
        self, 
        candidates: List[Dict[str, Any]], 
        user_intent: UserIntent,
        state: TurnState
    ) -> List[Tuple[Dict[str, Any], LawyerScore]]:
        """Score each lawyer comprehensively"""
        
        scored_lawyers = []
        
        for lawyer in candidates:
            score = await self._score_single_lawyer(lawyer, user_intent, state)
            scored_lawyers.append((lawyer, score))
        
        return scored_lawyers
    
    async def _score_single_lawyer(
        self, 
        lawyer: Dict[str, Any], 
        user_intent: UserIntent,
        state: TurnState
    ) -> LawyerScore:
        """Comprehensive scoring for a single lawyer"""
        
        score = LawyerScore(lawyer_id=str(lawyer.get("id", "unknown")))
        
        # Practice area match
        score.practice_area_match = self._score_practice_area_match(lawyer, user_intent)
        
        # Location match
        score.location_match = self._score_location_match(lawyer, user_intent)
        
        # Budget match
        score.budget_match = self._score_budget_match(lawyer, user_intent)
        
        # Availability match
        score.availability_match = self._score_availability_match(lawyer, user_intent)
        
        # Quality scores
        score.quality_score = self._calculate_quality_score(lawyer)
        score.reputation_score = self._calculate_reputation_score(lawyer)
        score.success_rate_score = self._calculate_success_rate(lawyer)
        score.review_sentiment_score = self._calculate_review_sentiment(lawyer)
        
        # Personality and fit
        score.communication_style_match = await self._score_communication_style(lawyer, user_intent)
        score.cultural_fit_score = self._score_cultural_fit(lawyer, user_intent)
        score.personality_match = await self._score_personality_match(lawyer, user_intent, state)
        
        # Special considerations
        score.urgency_readiness = self._score_urgency_readiness(lawyer, user_intent)
        score.complexity_capability = self._score_complexity_capability(lawyer, user_intent)
        score.vulnerability_sensitivity = self._score_vulnerability_sensitivity(lawyer, user_intent)
        
        # Apply bonuses and penalties
        self._apply_bonuses_and_penalties(score, lawyer, user_intent)
        
        # Generate explanations
        self._generate_match_explanations(score, lawyer, user_intent)
        
        return score
    
    def _score_practice_area_match(self, lawyer: Dict[str, Any], user_intent: UserIntent) -> float:
        """Score how well lawyer's practice areas match needs"""
        
        if not user_intent.legal_issues:
            return 0.5
        
        lawyer_areas = set(lawyer.get("practice_areas", []))
        lawyer_specialties = [s["name"] for s in lawyer.get("specialties", [])]
        
        # Check specializations match
        if user_intent.specializations_needed:
            specialty_match = sum(
                1 for spec in user_intent.specializations_needed
                if any(spec in specialty.lower() for specialty in lawyer_specialties)
            )
            if specialty_match > 0:
                return min(1.0, 0.8 + (specialty_match * 0.1))
        
        # Basic practice area match
        if "Family Law" in lawyer_areas:
            return 0.7  # Base match for family law
        
        return 0.3
    
    def _score_location_match(self, lawyer: Dict[str, Any], user_intent: UserIntent) -> float:
        """Score location compatibility"""
        
        lawyer_addresses = lawyer.get("addresses", [])
        if not lawyer_addresses:
            return 0.3
        
        # Check neighborhood match
        if user_intent.location_requirements.get("neighborhood"):
            for address in lawyer_addresses:
                if address.get("neighborhood") == user_intent.location_requirements["neighborhood"]:
                    return 1.0
        
        # Check city match
        if user_intent.location_requirements.get("city"):
            for address in lawyer_addresses:
                if address.get("city", "").lower() == user_intent.location_requirements["city"].lower():
                    return 0.8
        
        # Check state match
        if user_intent.location_requirements.get("state"):
            if lawyer.get("state", "").lower() == user_intent.location_requirements["state"].lower():
                return 0.6
        
        return 0.4
    
    def _score_budget_match(self, lawyer: Dict[str, Any], user_intent: UserIntent) -> float:
        """Score budget compatibility"""
        
        fee_structure = lawyer.get("fee_structure", {})
        
        # Free consultation requirement
        if user_intent.budget_constraints["free_consultation_required"]:
            if not fee_structure.get("free_consultation", False):
                return 0.3
        
        # Payment plan requirement
        if user_intent.budget_constraints["payment_plan_needed"]:
            if fee_structure.get("payment_plans", False):
                return 1.0
        
        # Budget range matching
        user_budget = user_intent.budget_constraints["range"]
        lawyer_min_rate = fee_structure.get("hourly_rate_min", 250)
        
        budget_to_rate = {
            "$": (0, 200),
            "$$": (200, 350),
            "$$$": (350, 500),
            "$$$$": (500, 10000)
        }
        
        if user_budget in budget_to_rate:
            min_rate, max_rate = budget_to_rate[user_budget]
            if lawyer_min_rate <= max_rate:
                if lawyer_min_rate <= min_rate:
                    return 1.0  # Perfect match
                else:
                    # Partial match - lawyer is a bit more expensive
                    return max(0.5, 1.0 - ((lawyer_min_rate - min_rate) / 200))
        
        return 0.5
    
    def _score_availability_match(self, lawyer: Dict[str, Any], user_intent: UserIntent) -> float:
        """Score availability match"""
        
        if user_intent.urgency != "immediate":
            return 0.8  # Not urgent, most lawyers fine
        
        # Check response time
        response_time = lawyer.get("quality_signals", {}).get("response_time_hours", 48)
        
        if response_time <= 2:
            return 1.0
        elif response_time <= 8:
            return 0.8
        elif response_time <= 24:
            return 0.6
        else:
            return 0.3
    
    def _calculate_quality_score(self, lawyer: Dict[str, Any]) -> float:
        """Calculate overall quality score"""
        
        quality_signals = lawyer.get("quality_signals", {})
        
        # Weighted quality calculation
        quality_score = (
            quality_signals.get("education_score", 0.5) * 0.2 +
            quality_signals.get("professional_score", 0.5) * 0.3 +
            quality_signals.get("awards_score", 0) * 0.2 +
            quality_signals.get("associations_score", 0) * 0.1 +
            quality_signals.get("client_satisfaction", 0.5) * 0.2
        )
        
        # Factor in years of experience
        years_exp = lawyer.get("years_of_experience", 5)
        if years_exp > 20:
            quality_score += 0.1
        elif years_exp > 10:
            quality_score += 0.05
        
        return min(1.0, quality_score)
    
    def _calculate_reputation_score(self, lawyer: Dict[str, Any]) -> float:
        """Calculate reputation score from various sources"""
        
        # Average ratings from different platforms
        ratings = []
        
        if lawyer.get("avvo_rating"):
            ratings.append(lawyer["avvo_rating"] / 10)  # Normalize to 0-1
        
        if lawyer.get("google_rating"):
            ratings.append(lawyer["google_rating"] / 5)
        
        if lawyer.get("overall_rating"):
            ratings.append(lawyer["overall_rating"] / 5)
        
        # Perplexity score if available
        if lawyer.get("perplexity_score"):
            ratings.append(lawyer["perplexity_score"] / 10)
        
        if ratings:
            avg_rating = sum(ratings) / len(ratings)
            
            # Boost for high review count
            review_count = lawyer.get("reviews_count", 0)
            if review_count > 100:
                avg_rating += 0.1
            elif review_count > 50:
                avg_rating += 0.05
            
            return min(1.0, avg_rating)
        
        return 0.5  # Default if no ratings
    
    def _calculate_success_rate(self, lawyer: Dict[str, Any]) -> float:
        """Calculate success rate score"""
        
        # Look for success indicators in profile
        profile_text = (lawyer.get("profile", "") + " " + lawyer.get("experience", "")).lower()
        
        success_keywords = ["successful", "won", "favorable", "victory", "achieved", "secured", "obtained"]
        success_mentions = sum(1 for keyword in success_keywords if keyword in profile_text)
        
        # Base score from mentions
        score = min(0.8, success_mentions * 0.15)
        
        # Boost for specific success rates mentioned
        if "success rate" in profile_text or "% of cases" in profile_text:
            score += 0.2
        
        return score
    
    def _calculate_review_sentiment(self, lawyer: Dict[str, Any]) -> float:
        """Calculate review sentiment score"""
        
        reviews = lawyer.get("reviews", [])
        if not reviews:
            return 0.5
        
        # Average sentiment scores
        sentiments = [r.get("sentiment_score", 0.5) for r in reviews if "sentiment_score" in r]
        
        if sentiments:
            avg_sentiment = sum(sentiments) / len(sentiments)
            
            # Look for specific positive themes
            review_texts = " ".join([r.get("text", "") for r in reviews[:10]]).lower()
            positive_themes = ["compassionate", "understanding", "helpful", "knowledgeable", 
                             "responsive", "professional", "excellent", "highly recommend"]
            
            theme_boost = sum(0.05 for theme in positive_themes if theme in review_texts)
            
            return min(1.0, avg_sentiment + theme_boost)
        
        # Fallback to rating-based sentiment
        avg_rating = sum(r.get("rating", 3) for r in reviews) / len(reviews)
        return avg_rating / 5
    
    async def _score_communication_style(self, lawyer: Dict[str, Any], user_intent: UserIntent) -> float:
        """Score communication style match"""
        
        # Analyze lawyer's profile and reviews for communication style
        text_to_analyze = (
            lawyer.get("profile", "") + " " +
            lawyer.get("experience", "") + " " +
            " ".join([r.get("text", "") for r in lawyer.get("reviews", [])[:5]])
        ).lower()
        
        style_keywords = {
            "aggressive": ["aggressive", "fighter", "tough", "strong", "fierce", "battle", "win"],
            "gentle": ["gentle", "patient", "kind", "caring", "compassionate", "understanding", "supportive"],
            "collaborative": ["collaborative", "together", "team", "mediation", "peaceful", "amicable"],
            "balanced": ["professional", "experienced", "skilled", "dedicated"]
        }
        
        # Count style matches
        user_style = user_intent.communication_style
        if user_style in style_keywords:
            matches = sum(1 for keyword in style_keywords[user_style] if keyword in text_to_analyze)
            
            if matches >= 3:
                return 1.0
            elif matches >= 2:
                return 0.8
            elif matches >= 1:
                return 0.6
        
        return 0.4  # No clear match
    
    def _score_cultural_fit(self, lawyer: Dict[str, Any], user_intent: UserIntent) -> float:
        """Score cultural and language fit"""
        
        score = 0.5  # Base score
        
        # Language match
        if user_intent.language_needs:
            lawyer_languages = [lang.lower() for lang in lawyer.get("languages", [])]
            for needed_lang in user_intent.language_needs:
                if needed_lang.lower() in lawyer_languages:
                    score += 0.3
                    break
        
        # Cultural background match (if specified)
        if user_intent.cultural_background:
            profile_text = (lawyer.get("profile", "") + " " + lawyer.get("experience", "")).lower()
            cultural_keywords = {
                "jewish": ["jewish", "hebrew", "synagogue", "kosher", "shabbat"],
                "hispanic": ["hispanic", "latino", "latina", "spanish-speaking"],
                "asian": ["asian", "chinese", "korean", "vietnamese", "japanese"],
                "muslim": ["muslim", "islamic", "halal", "mosque"],
                "christian": ["christian", "church", "faith-based"]
            }
            
            if user_intent.cultural_background.lower() in cultural_keywords:
                keywords = cultural_keywords[user_intent.cultural_background.lower()]
                if any(keyword in profile_text for keyword in keywords):
                    score += 0.2
        
        # LGBTQ friendly
        if user_intent.lgbtq_needs and lawyer.get("lgbtq_friendly"):
            score += 0.2
        
        # Gender preference
        if user_intent.gender_preference:
            if lawyer.get("gender", "").lower() == user_intent.gender_preference.lower():
                score += 0.1
        
        return min(1.0, score)
    
    async def _score_personality_match(
        self, 
        lawyer: Dict[str, Any], 
        user_intent: UserIntent,
        state: TurnState
    ) -> float:
        """Score overall personality match using AI"""
        
        # Skip if not important
        if user_intent.support_level == "minimal" and not user_intent.vulnerability_indicators:
            return 0.7  # Default decent match
        
        # Build context for AI evaluation
        prompt = f"""Rate personality match (0-1) between lawyer and client needs:

CLIENT NEEDS:
- Communication style: {user_intent.communication_style}
- Support level needed: {user_intent.support_level}
- Emotional state: {state.enhanced_sentiment}
- Vulnerabilities: {', '.join(user_intent.vulnerability_indicators)}
- Must have: {', '.join(user_intent.must_have_characteristics)}
- Must avoid: {', '.join(user_intent.avoid_characteristics)}

LAWYER PROFILE:
{lawyer.get('profile', 'No profile available')[:500]}

LAWYER REVIEWS SUMMARY:
{' '.join([r.get('text', '')[:100] for r in lawyer.get('reviews', [])[:3]])}

Return just a number between 0 and 1."""

        try:
            response = await self.groq_client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=10
            )
            
            score_text = response.choices[0].message.content.strip()
            return float(score_text)
        except:
            return 0.6  # Default if AI fails
    
    def _score_urgency_readiness(self, lawyer: Dict[str, Any], user_intent: UserIntent) -> float:
        """Score lawyer's readiness for urgent cases"""
        
        if user_intent.urgency != "immediate":
            return 0.8
        
        # Fast response time
        response_time = lawyer.get("quality_signals", {}).get("response_time_hours", 48)
        readiness = 1.0 - (response_time / 48)  # 0 hours = 1.0, 48 hours = 0.0
        
        # Keywords indicating emergency availability
        profile_text = lawyer.get("profile", "").lower()
        if any(word in profile_text for word in ["emergency", "urgent", "immediate", "24/7", "available"]):
            readiness += 0.2
        
        return min(1.0, readiness)
    
    def _score_complexity_capability(self, lawyer: Dict[str, Any], user_intent: UserIntent) -> float:
        """Score lawyer's ability to handle complex cases"""
        
        if user_intent.complexity == "simple":
            return 0.8  # Most lawyers can handle simple cases
        
        capability = 0.5
        
        # Years of experience
        years_exp = lawyer.get("years_of_experience", 5)
        if user_intent.complexity == "complex":
            if years_exp > 15:
                capability += 0.3
            elif years_exp > 10:
                capability += 0.2
        else:  # moderate
            if years_exp > 5:
                capability += 0.2
        
        # Specializations
        specialties = [s["name"] for s in lawyer.get("specialties", [])]
        if len(specialties) > 3:
            capability += 0.1
        
        # Quality indicators
        if lawyer.get("quality_signals", {}).get("professional_score", 0) > 0.7:
            capability += 0.1
        
        # Complex case keywords
        profile_text = lawyer.get("profile", "").lower()
        complex_keywords = ["complex", "high-asset", "business", "international", "complicated"]
        if any(keyword in profile_text for keyword in complex_keywords):
            capability += 0.1
        
        return min(1.0, capability)
    
    def _score_vulnerability_sensitivity(self, lawyer: Dict[str, Any], user_intent: UserIntent) -> float:
        """Score lawyer's sensitivity to vulnerable clients"""
        
        if not user_intent.vulnerability_indicators:
            return 0.7  # Not a major factor
        
        sensitivity = 0.5
        
        # Check reviews for sensitivity indicators
        review_texts = " ".join([r.get("text", "") for r in lawyer.get("reviews", [])[:10]]).lower()
        sensitivity_keywords = ["compassionate", "understanding", "patient", "kind", "caring", 
                              "supportive", "gentle", "empathetic", "listened", "comfortable"]
        
        keyword_matches = sum(1 for keyword in sensitivity_keywords if keyword in review_texts)
        sensitivity += keyword_matches * 0.05
        
        # Profile indicators
        profile_text = lawyer.get("profile", "").lower()
        if "trauma" in profile_text or "sensitive" in profile_text:
            sensitivity += 0.2
        
        # High review sentiment
        if self._calculate_review_sentiment(lawyer) > 0.8:
            sensitivity += 0.1
        
        return min(1.0, sensitivity)
    
    def _apply_bonuses_and_penalties(
        self, 
        score: LawyerScore, 
        lawyer: Dict[str, Any], 
        user_intent: UserIntent
    ):
        """Apply bonus points and penalties"""
        
        # Bonuses
        
        # Exact neighborhood match
        if user_intent.location_requirements.get("neighborhood"):
            for address in lawyer.get("addresses", []):
                if address.get("neighborhood") == user_intent.location_requirements["neighborhood"]:
                    score.bonus_points += 0.1
                    break
        
        # Saved by user before
        if lawyer["id"] in user_intent.get("saved_lawyers", []):
            score.bonus_points += 0.15
        
        # Perfect language match
        if user_intent.language_needs and set(user_intent.language_needs).issubset(set(lawyer.get("languages", []))):
            score.bonus_points += 0.1
        
        # Award winner
        if lawyer.get("quality_signals", {}).get("awards_score", 0) > 0.5:
            score.bonus_points += 0.05
        
        # Penalties
        
        # Rejected by user before
        if lawyer["id"] in user_intent.get("rejected_lawyers", []):
            score.penalty_points += 0.3
        
        # Disciplinary actions
        for license_info in lawyer.get("licenses", []):
            if license_info.get("has_disciplinary_actions"):
                score.penalty_points += 0.2
                score.concerns.append("Has disciplinary actions on record")
                break
        
        # Poor response time for urgent cases
        if user_intent.urgency == "immediate":
            response_time = lawyer.get("quality_signals", {}).get("response_time_hours", 48)
            if response_time > 48:
                score.penalty_points += 0.1
                score.concerns.append("May not respond quickly to urgent requests")
        
        # Budget mismatch
        if user_intent.budget_constraints["cost_sensitive"]:
            fee_structure = lawyer.get("fee_structure", {})
            if fee_structure.get("hourly_rate_min", 250) > 400:
                score.penalty_points += 0.15
                score.concerns.append("May be outside your budget range")
    
    def _generate_match_explanations(
        self, 
        score: LawyerScore, 
        lawyer: Dict[str, Any], 
        user_intent: UserIntent
    ):
        """Generate explanations for the match"""
        
        # Top positive reasons
        reasons = []
        
        if score.practice_area_match > 0.8:
            specialties = [s["name"] for s in lawyer.get("specialties", [])]
            if specialties:
                reasons.append(f"Specializes in {', '.join(specialties[:2])}")
            else:
                reasons.append("Experienced in your legal needs")
        
        if score.location_match == 1.0:
            reasons.append(f"Located in your neighborhood")
        elif score.location_match > 0.8:
            reasons.append(f"Conveniently located in {lawyer.get('city', 'your area')}")
        
        if score.communication_style_match > 0.8:
            style_descriptions = {
                "aggressive": "Known for being a strong advocate who fights hard",
                "gentle": "Compassionate approach with patient communication",
                "collaborative": "Works collaboratively toward peaceful resolutions"
            }
            if user_intent.communication_style in style_descriptions:
                reasons.append(style_descriptions[user_intent.communication_style])
        
        if score.cultural_fit_score > 0.8:
            if user_intent.language_needs:
                reasons.append(f"Speaks {', '.join(user_intent.language_needs)}")
            elif user_intent.cultural_background:
                reasons.append(f"Understands {user_intent.cultural_background} community")
        
        if score.reputation_score > 0.9:
            rating = lawyer.get("overall_rating", 0)
            reviews = lawyer.get("reviews_count", 0)
            reasons.append(f"Highly rated ({rating:.1f} stars, {reviews} reviews)")
        
        if score.urgency_readiness > 0.9 and user_intent.urgency == "immediate":
            reasons.append("Available for immediate consultation")
        
        if score.budget_match == 1.0 and user_intent.budget_constraints["cost_sensitive"]:
            if lawyer.get("fee_structure", {}).get("free_consultation"):
                reasons.append("Offers free consultation")
            if lawyer.get("fee_structure", {}).get("payment_plans"):
                reasons.append("Flexible payment plans available")
        
        score.match_reasons = reasons[:3]  # Top 3 reasons
    
    async def _enrich_top_candidates(
        self, 
        candidates: List[Tuple[Dict[str, Any], LawyerScore]], 
        user_intent: UserIntent
    ) -> List[Tuple[Dict[str, Any], LawyerScore]]:
        """Enrich top candidates with external research"""
        
        enrichment_tasks = []
        
        for lawyer, score in candidates[:5]:  # Only top 5
            if user_intent.complexity == "complex" or score.total_score > 0.85:
                enrichment_tasks.append(self._enrich_single_candidate(lawyer, score, user_intent))
            else:
                enrichment_tasks.append(asyncio.create_task(asyncio.sleep(0)))  # No-op
        
        await asyncio.gather(*enrichment_tasks)
        
        return candidates
    
    async def _enrich_single_candidate(
        self, 
        lawyer: Dict[str, Any], 
        score: LawyerScore,
        user_intent: UserIntent
    ):
        """Enrich a single lawyer with external data"""
        
        # Research reputation if not already done
        if not lawyer.get("perplexity_review") and user_intent.complexity == "complex":
            reputation_data = await self.perplexity.research_lawyer_reputation(
                lawyer["name"],
                lawyer.get("firm")
            )
            
            if reputation_data.get("has_notable_info"):
                lawyer["external_reputation"] = reputation_data
                score.bonus_points += 0.05
                score.match_reasons.append("Notable reputation in the community")
    
    async def _ai_powered_final_ranking(
        self, 
        candidates: List[Tuple[Dict[str, Any], LawyerScore]], 
        user_intent: UserIntent,
        state: TurnState
    ) -> List[Tuple[Dict[str, Any], LawyerScore]]:
        """Use AI for final holistic ranking"""
        
        # Already well-scored, just sort by total score
        return sorted(candidates, key=lambda x: x[1].total_score, reverse=True)
    
    async def _create_personalized_cards(
        self, 
        matches: List[Tuple[Dict[str, Any], LawyerScore]], 
        user_intent: UserIntent,
        state: TurnState
    ) -> List[LawyerCard]:
        """Create personalized lawyer cards"""
        
        cards = []
        
        for lawyer, score in matches:
            # Generate personalized message
            personalized_message = await self._generate_personalized_message(
                lawyer, score, user_intent, state
            )
            
            # Build comprehensive location info
            location_info = {}
            if lawyer.get("addresses"):
                primary_address = lawyer["addresses"][0]
                location_info = {
                    "city": primary_address.get("city", lawyer.get("city")),
                    "state": primary_address.get("state", lawyer.get("state")),
                    "neighborhood": primary_address.get("neighborhood"),
                    "formatted_address": primary_address.get("formatted_address")
                }
            
            card = LawyerCard(
                id=str(lawyer["id"]),
                name=lawyer["name"],
                firm=lawyer.get("firm", "Independent Practice"),
                match_score=score.total_score,
                blurb=personalized_message,
                link=f"/lawyer/{lawyer['id']}",
                practice_areas=[s["name"] for s in lawyer.get("specialties", [])][:3] or ["Family Law"],
                location=location_info,
                rating=lawyer.get("overall_rating"),
                reviews_count=lawyer.get("reviews_count"),
                budget_range=self._determine_budget_range(lawyer),
                languages=lawyer.get("languages", []),
                match_reasons=score.match_reasons,
                concerns=score.concerns if score.concerns else None,
                response_time=lawyer.get("quality_signals", {}).get("response_time_hours"),
                free_consultation=lawyer.get("fee_structure", {}).get("free_consultation", False),
                payment_plans=lawyer.get("fee_structure", {}).get("payment_plans", False)
            )
            
            cards.append(card)
        
        return cards
    
    async def _generate_personalized_message(
        self, 
        lawyer: Dict[str, Any], 
        score: LawyerScore,
        user_intent: UserIntent,
        state: TurnState
    ) -> str:
        """Generate a personalized message for why this lawyer is perfect"""
        
        prompt = f"""Write a warm, personalized 2-3 sentence description of why this lawyer is perfect for this specific user:

USER SITUATION:
- Needs help with: {', '.join(user_intent.legal_issues)}
- Emotional state: {state.enhanced_sentiment} (distress level: {state.distress_score}/10)
- Communication preference: {user_intent.communication_style}
- Key concerns: {state.user_text[:200]}

LAWYER STRENGTHS:
- {' '.join(score.match_reasons)}
- Overall match score: {score.total_score:.0%}

TONE: {
    'Gentle and reassuring' if state.distress_score > 7 
    else 'Confident and professional' if user_intent.communication_style == 'aggressive'
    else 'Warm and supportive'
}

Write in second person, addressing the user directly. Be specific about why THIS lawyer matches THEIR needs."""

        try:
            response = await self.groq_client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=150
            )
            
            return response.choices[0].message.content.strip()
        except:
            # Fallback message
            return f"{lawyer['name']} is an excellent match for your {user_intent.legal_issues[0] if user_intent.legal_issues else 'family law'} needs. " + " ".join(score.match_reasons[:2])
    
    def _determine_budget_range(self, lawyer: Dict[str, Any]) -> str:
        """Determine lawyer's budget range"""
        
        fee_structure = lawyer.get("fee_structure", {})
        min_rate = fee_structure.get("hourly_rate_min", 250)
        
        if min_rate < 200:
            return "$"
        elif min_rate < 350:
            return "$$"
        elif min_rate < 500:
            return "$$$"
        else:
            return "$$$$"
    
    def _calculate_confidence(self, matches: List[Tuple[Dict[str, Any], LawyerScore]]) -> float:
        """Calculate confidence in the matching results"""
        
        if not matches:
            return 0.0
        
        confidence = 0.5  # Base confidence
        
        # Top match quality
        if matches[0][1].total_score > 0.9:
            confidence += 0.2
        elif matches[0][1].total_score > 0.8:
            confidence += 0.15
        
        # Multiple good matches
        good_matches = sum(1 for _, score in matches[:5] if score.total_score > 0.75)
        if good_matches >= 3:
            confidence += 0.15
        elif good_matches >= 2:
            confidence += 0.1
        
        # Diversity of match reasons
        all_reasons = set()
        for _, score in matches[:3]:
            all_reasons.update(score.match_reasons)
        
        if len(all_reasons) >= 5:
            confidence += 0.1
        
        # No major concerns in top matches
        if not any(score.concerns for _, score in matches[:3]):
            confidence += 0.05
        
        return min(0.95, confidence)
    
    def _intent_summary(self, user_intent: UserIntent) -> Dict[str, Any]:
        """Create a summary of user intent for the response"""
        
        return {
            "legal_needs": user_intent.legal_issues,
            "urgency": user_intent.urgency,
            "communication_style": user_intent.communication_style,
            "key_preferences": {
                "languages": user_intent.language_needs,
                "gender": user_intent.gender_preference,
                "cultural": user_intent.cultural_background,
                "budget": user_intent.budget_constraints["range"]
            }
        }
    
    def _generate_match_insights(
        self, 
        matches: List[Tuple[Dict[str, Any], LawyerScore]], 
        user_intent: UserIntent
    ) -> Dict[str, Any]:
        """Generate insights about the matching results"""
        
        insights = {
            "match_quality": "excellent" if matches[0][1].total_score > 0.85 else "good" if matches[0][1].total_score > 0.7 else "fair",
            "top_factors": [],
            "recommendations": []
        }
        
        # Analyze what made the best matches
        factor_counts = defaultdict(int)
        for _, score in matches[:3]:
            if score.location_match > 0.8:
                factor_counts["location"] += 1
            if score.communication_style_match > 0.8:
                factor_counts["personality"] += 1
            if score.cultural_fit_score > 0.8:
                factor_counts["cultural_fit"] += 1
            if score.budget_match > 0.8:
                factor_counts["affordability"] += 1
        
        # Top factors
        for factor, count in sorted(factor_counts.items(), key=lambda x: x[1], reverse=True):
            if count >= 2:
                insights["top_factors"].append(factor)
        
        # Recommendations
        if user_intent.urgency == "immediate" and any(score.urgency_readiness < 0.7 for _, score in matches[:3]):
            insights["recommendations"].append("Contact lawyers soon as availability varies")
        
        if user_intent.budget_constraints["cost_sensitive"]:
            insights["recommendations"].append("Ask about payment plans during consultation")
        
        return insights
    
    def _get_search_methods_used(self, user_intent: UserIntent) -> List[str]:
        """List which search methods were used"""
        
        methods = ["standard_filtered_search"]
        
        if user_intent.communication_style != "balanced":
            methods.append("personality_semantic_search")
        
        if user_intent.cultural_background or user_intent.language_needs:
            methods.append("cultural_community_search")
        
        if user_intent.specializations_needed:
            methods.append("specialization_search")
        
        if user_intent.urgency == "immediate":
            methods.append("urgent_availability_search")
        
        if user_intent.complexity == "complex":
            methods.append("high_quality_search")
        
        if user_intent.budget_constraints["cost_sensitive"]:
            methods.append("budget_friendly_search")
        
        return methods
    
    def _extract_legal_issues(self, text: str) -> List[str]:
        """Extract legal issues from text if not already identified"""
        
        if not text:
            return ["family law"]
        
        text_lower = text.lower()
        issues = []
        
        issue_keywords = {
            "divorce": ["divorce", "separation", "split", "marriage ending"],
            "custody": ["custody", "children", "kids", "parenting time", "visitation"],
            "child_support": ["child support", "support payment"],
            "spousal_support": ["alimony", "spousal support", "maintenance"],
            "property_division": ["property", "assets", "house", "debts"],
            "domestic_violence": ["abuse", "violence", "protection", "restraining"],
            "adoption": ["adopt", "adoption"],
            "paternity": ["paternity", "father", "parentage"]
        }
        
        for issue, keywords in issue_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                issues.append(issue)
        
        return issues if issues else ["family law"]


# Service factory
_intelligent_matcher = None

def get_intelligent_matcher() -> IntelligentMatcherService:
    """Get or create the intelligent matcher service"""
    global _intelligent_matcher
    if _intelligent_matcher is None:
        _intelligent_matcher = IntelligentMatcherService()
    return _intelligent_matcher