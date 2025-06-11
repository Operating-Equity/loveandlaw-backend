from typing import Dict, Any, List
import json
import re
from datetime import datetime
from groq import AsyncGroq
from src.agents.base import BaseAgent
from src.models.conversation import TurnState
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SignalExtractAgent(BaseAgent):
    """Extract structured information from user messages"""
    
    def __init__(self):
        super().__init__("signal_extract")
        self.groq_client = AsyncGroq(api_key=settings.groq_api_key)
        
        # Legal intent categories
        self.legal_intents = [
            "divorce", "custody", "child_support", "alimony", "property_division",
            "restraining_order", "adoption", "paternity", "visitation", "mediation",
            "prenuptial", "separation", "domestic_violence", "guardianship", "general_legal_help"
        ]
    
    async def process(self, state: TurnState, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract signals and facts from user text"""
        
        # Extract structured information
        extracted_data = await self._extract_signals(state.user_text)
        
        # Merge with existing facts
        updated_facts = {**state.facts, **extracted_data.get("facts", {})}
        
        # Update legal intents
        new_intents = extracted_data.get("legal_intents", [])
        updated_intents = list(set(state.legal_intent + new_intents))
        
        return {
            "facts": updated_facts,
            "legal_intent": updated_intents,
            "extracted_entities": extracted_data.get("entities", {})
        }
    
    async def _extract_signals(self, text: str) -> Dict[str, Any]:
        """Extract structured information using LLM"""
        
        prompt = f"""You are an expert signal extraction system for legal consultations. Your task is to extract EVERY possible piece of information from the user's message, no matter how small or implicit.

Message: {text}

Extract ALL information dynamically. Be creative and comprehensive. Look for:
- Any legal issues or intents mentioned (even vaguely)
- ALL numbers (amounts, dates, ages, counts, percentages, etc.)
- ALL locations (cities, states, addresses, regions)
- ALL time references (dates, durations, deadlines, "how long ago")
- ALL people mentioned (names, relationships, roles)
- ALL financial information (income, expenses, assets, debts, budgets)
- ALL preferences or requirements stated
- ALL emotional states or concerns expressed
- ALL goals, desires, or outcomes wanted
- ANY special circumstances or constraints
- ANY evidence, documents, or proof mentioned
- IMPLICIT information (what can be inferred?)

DO NOT limit yourself to predefined categories. Extract EVERYTHING that could be relevant to a legal consultation.

For legal intents, consider these but also identify any others: {', '.join(self.legal_intents)}

Return a dynamic JSON structure that captures ALL extracted information. Create new fields as needed. Structure it logically but don't constrain yourself to a fixed schema.

Example structure (but add ANY fields needed):
{{
  "legal_intents": ["identified intents"],
  "facts": {{
    // Organize dynamically based on what you find
    // Create nested structures as appropriate
    // Add any fields that make sense for the data
  }},
  "entities": {{
    // Any named entities found
  }},
  "inferred_information": {{
    // Things not explicitly stated but can be reasonably inferred
  }},
  "questions_for_clarification": [
    // What additional info would be helpful?
  ]
}}

Be exhaustive. Extract EVERYTHING. Return ONLY valid JSON:"""

        try:
            response = await self.groq_client.chat.completions.create(
                model=settings.signal_extract_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Validate and clean the data
            cleaned_result = self._validate_extracted_data(result)
            
            return cleaned_result
            
        except Exception as e:
            logger.error(f"Error in signal extraction: {e}")
            # Fall back to simpler Groq extraction
            return await self._fallback_extraction(text)
    
    def _validate_extracted_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Flexibly validate and process dynamically extracted data"""
        
        # Start with base structure
        validated = {
            "legal_intents": [],
            "facts": {},
            "entities": {},
            "metadata": {}
        }
        
        # Validate legal intents - keep both recognized and new ones
        if "legal_intents" in data and isinstance(data["legal_intents"], list):
            validated["legal_intents"] = data["legal_intents"]  # Keep all intents, even new ones
        
        # Process facts dynamically - preserve whatever structure Groq creates
        if "facts" in data and isinstance(data["facts"], dict):
            validated["facts"] = self._process_facts_recursively(data["facts"])
        
        # Copy entities as-is
        if "entities" in data and isinstance(data["entities"], dict):
            validated["entities"] = data["entities"]
        
        # Copy any additional fields that Groq created
        for key in data:
            if key not in ["legal_intents", "facts", "entities", "metadata"]:
                validated[key] = data[key]
        
        # Include metadata
        if "metadata" in data:
            validated["metadata"] = data["metadata"]
        
        # Add extraction metadata
        validated["metadata"]["extraction_method"] = "groq_dynamic"
        
        return validated
    
    def _process_facts_recursively(self, facts: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively process facts while maintaining backward compatibility"""
        processed = {}
        
        # Process each fact dynamically
        for key, value in facts.items():
            if isinstance(value, dict):
                # Recursively process nested dictionaries
                processed[key] = self._process_facts_recursively(value)
                
                # Special handling for backward compatibility
                if key == "financial" and "budget_amount" in value:
                    processed["budget_amount"] = value["budget_amount"]
                    if "budget_range" in value:
                        processed["budget_range"] = value["budget_range"]
                elif key == "location":
                    if "zip" in value:
                        processed["zip"] = value["zip"]
                    if "state" in value:
                        processed["state"] = value["state"]
                elif key == "family" and "children_count" in value:
                    processed["children_count"] = value["children_count"]
            else:
                # Copy non-dict values as-is
                processed[key] = value
        
        return processed
    
    async def _fallback_extraction(self, text: str) -> Dict[str, Any]:
        """Fallback extraction using Groq with simpler prompt"""
        
        # Try again with a simpler, more focused prompt
        try:
            fallback_prompt = f"""Extract information from this message. If unsure, make your best guess.

Message: {text}

Return JSON with ANY information you can find:
{{
  "legal_intents": [],
  "facts": {{}},
  "entities": {{}}
}}"""

            response = await self.groq_client.chat.completions.create(
                model=settings.signal_extract_model,
                messages=[{"role": "user", "content": fallback_prompt}],
                temperature=0.3,  # Slightly higher for fallback
                max_tokens=300,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result["metadata"] = {"extraction_method": "groq_fallback"}
            return result
            
        except Exception as e:
            logger.error(f"Both extraction attempts failed: {e}")
            # Return minimal structure if everything fails
            return {
                "legal_intents": [],
                "facts": {},
                "entities": {},
                "metadata": {"extraction_method": "failed", "error": str(e)}
            }