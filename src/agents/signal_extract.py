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
        
        prompt = f"""Extract structured information from this legal consultation message.

Look for:
1. Legal intents from: {', '.join(self.legal_intents)}
2. Facts:
   - Location (zip, city, state)
   - Dates (filing dates, court dates, separation date)
   - Financial info (income range, assets, budget for lawyer - can be specific amounts like "$5000" or ranges like "$-$$")
   - Family structure (children, ages)
   - Employment status
   - Housing situation
   - Existing legal proceedings
3. Named entities:
   - Spouse/partner names (mark as PERSON)
   - Children names (mark as PERSON)
   - Lawyer/firm names (mark as LAWYER)
   - Court names (mark as COURT)

Message: {text}

Return a JSON object with this structure:
{{
  "legal_intents": ["intent1", "intent2"],
  "facts": {{
    "zip": "12345",
    "state": "CA",
    "children_count": 2,
    "children_ages": [5, 8],
    "separation_date": "2024-01-15",
    "budget_range": "$-$$",
    "budget_amount": 5000,
    "employment": "full-time",
    ...
  }},
  "entities": {{
    "persons": ["name1", "name2"],
    "lawyers": ["lawyer name"],
    "courts": ["court name"]
  }}
}}

Return ONLY valid JSON:"""

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
            # Fall back to regex extraction
            return self._fallback_extraction(text)
    
    def _validate_extracted_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean extracted data"""
        
        # Ensure required keys exist
        validated = {
            "legal_intents": [],
            "facts": {},
            "entities": {}
        }
        
        # Validate legal intents
        if "legal_intents" in data:
            validated["legal_intents"] = [
                intent for intent in data["legal_intents"] 
                if intent in self.legal_intents
            ]
        
        # Validate facts
        if "facts" in data and isinstance(data["facts"], dict):
            facts = data["facts"]
            
            # Validate zip code
            if "zip" in facts and re.match(r'^\d{5}$', str(facts["zip"])):
                validated["facts"]["zip"] = facts["zip"]
            
            # Validate state
            if "state" in facts and len(str(facts["state"])) == 2:
                validated["facts"]["state"] = facts["state"].upper()
            
            # Validate dates
            for date_field in ["separation_date", "filing_date", "court_date"]:
                if date_field in facts:
                    try:
                        # Verify it's a valid date
                        datetime.fromisoformat(facts[date_field])
                        validated["facts"][date_field] = facts[date_field]
                    except:
                        pass
            
            # Copy other valid facts
            for key in ["children_count", "budget_range", "budget_amount", "employment", "housing"]:
                if key in facts:
                    validated["facts"][key] = facts[key]
        
        # Validate entities
        if "entities" in data and isinstance(data["entities"], dict):
            validated["entities"] = data["entities"]
        
        return validated
    
    def _fallback_extraction(self, text: str) -> Dict[str, Any]:
        """Fallback regex-based extraction"""
        result = {
            "legal_intents": [],
            "facts": {},
            "entities": {}
        }
        
        # Extract zip codes
        zip_match = re.search(r'\b\d{5}\b', text)
        if zip_match:
            result["facts"]["zip"] = zip_match.group()
        
        # Extract dates (simple format)
        date_matches = re.findall(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b', text)
        if date_matches:
            result["facts"]["found_dates"] = date_matches
        
        # Check for legal intent keywords
        text_lower = text.lower()
        for intent in self.legal_intents:
            if intent in text_lower:
                result["legal_intents"].append(intent)
        
        # If no specific intent but user is looking for a lawyer, add general family law
        if not result["legal_intents"] and ("lawyer" in text_lower or "attorney" in text_lower):
            result["legal_intents"].append("general_legal_help")
        
        # Extract budget indicators
        if "$" in text:
            # First check for specific dollar amounts
            dollar_amounts = re.findall(r'\$?\s*(\d{1,3}(?:,\d{3})*|\d+)\s*(?:dollars?|usd|USD)?', text)
            if dollar_amounts:
                # Convert the first found amount to integer
                amount_str = dollar_amounts[0].replace(',', '')
                try:
                    amount = int(amount_str)
                    result["facts"]["budget_amount"] = amount
                    # Also set budget range based on amount
                    if amount < 2000:
                        result["facts"]["budget_range"] = "$"
                    elif amount < 5000:
                        result["facts"]["budget_range"] = "$$"
                    elif amount < 10000:
                        result["facts"]["budget_range"] = "$$$"
                    else:
                        result["facts"]["budget_range"] = "$$$$"
                except ValueError:
                    pass
            # Otherwise check for range indicators
            elif "$$$$" in text:
                result["facts"]["budget_range"] = "$$$$"
            elif "$$$" in text:
                result["facts"]["budget_range"] = "$$$"
            elif "$$" in text:
                result["facts"]["budget_range"] = "$$"
            elif "$" in text:
                result["facts"]["budget_range"] = "$"
        
        return result