"""Case general agent for initial intake and routing."""

from typing import Dict, Any, Optional, List
import re
from ...utils.logger import get_logger
from ..base import BaseAgent

logger = get_logger(__name__)


class CaseGeneralAgent(BaseAgent):
    """Handles initial case intake and routing to specialized agents."""
    
    VALID_LEGAL_ISSUES = [
        "divorce_and_separation",
        "child_custody", 
        "spousal_support",
        "property_division",
        "child_support",
        "domestic_violence",
        "adoption_process",
        "restraining_order",
        "guardianship_process",
        "child_abuse",
        "paternity_practice",
        "juvenile_delinquency"
    ]
    
    COMBINED_ISSUE_PATTERNS = {
        ("paternity", "custody"): ["paternity_practice", "child_custody"],
        ("divorce", "property"): ["divorce_and_separation", "property_division"],
        ("child support", "custody"): ["child_support", "child_custody"],
        ("domestic violence", "restraining"): ["domestic_violence", "restraining_order"],
        ("guardianship", "abuse"): ["guardianship_process", "child_abuse"],
    }
    
    def __init__(self):
        """Initialize the case general agent."""
        super().__init__(name="CaseGeneralAgent")
        self.state = "gathering"
        self.prompt_template = self._load_prompt()
        
    def _load_prompt(self) -> str:
        """Load the case general prompt template."""
        try:
            with open("/Users/arpanghoshal/loveandlaw-backend/prompts/case_general_agent.prompt", "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading prompt: {e}")
            return ""
            
    def _extract_location(self, text: str) -> Optional[str]:
        """Extract ZIP code from text."""
        # Look for 5-digit ZIP code
        zip_pattern = r'\b\d{5}\b'
        match = re.search(zip_pattern, text)
        return match.group() if match else None
        
    def _identify_legal_issues(self, text: str) -> List[str]:
        """Identify legal issues from user text."""
        text_lower = text.lower()
        identified_issues = []
        
        # Check for combined issues first
        for patterns, issues in self.COMBINED_ISSUE_PATTERNS.items():
            if all(pattern in text_lower for pattern in patterns):
                identified_issues.extend(issues)
                return identified_issues
                
        # Check for individual issues
        issue_keywords = {
            "divorce_and_separation": ["divorce", "separation", "filing for divorce"],
            "child_custody": ["custody", "visitation", "parenting time"],
            "spousal_support": ["alimony", "spousal support", "maintenance"],
            "property_division": ["property division", "asset division", "marital property"],
            "child_support": ["child support", "support payment"],
            "domestic_violence": ["domestic violence", "abuse", "violence"],
            "adoption_process": ["adoption", "adopt"],
            "restraining_order": ["restraining order", "protective order", "protection"],
            "guardianship_process": ["guardianship", "guardian"],
            "child_abuse": ["child abuse", "child neglect"],
            "paternity_practice": ["paternity", "paternity test"],
            "juvenile_delinquency": ["juvenile", "delinquency", "minor crime"]
        }
        
        for issue, keywords in issue_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                identified_issues.append(issue)
                
        return identified_issues if identified_issues else []
        
    def _identify_person_seeking_help(self, text: str) -> str:
        """Identify who needs legal help from the text."""
        text_lower = text.lower()
        
        # Check for mentions of relations
        relations = ["mother", "father", "brother", "sister", "grandmother", 
                    "grandfather", "uncle", "aunt", "cousin", "son", "daughter"]
        
        for relation in relations:
            if f"my {relation}" in text_lower:
                return relation
                
        # Default to client
        return "client"
        
    def _extract_case_details(self, text: str, legal_issue: str) -> Dict[str, Any]:
        """Extract specific case details based on legal issue."""
        details = {}
        text_lower = text.lower()
        
        # Extract common details
        if "minor" in text_lower or "child" in text_lower:
            # Try to extract ages
            age_pattern = r'\b(\d{1,2})\s*(?:year|yr)s?\s*old\b'
            ages = re.findall(age_pattern, text_lower)
            if ages:
                details["child_ages"] = [int(age) for age in ages]
                
        # Extract financial information
        money_pattern = r'\$[\d,]+(?:\.\d{2})?|\d+(?:,\d{3})*(?:\.\d{2})?\s*dollars?'
        money_matches = re.findall(money_pattern, text_lower)
        if money_matches:
            details["financial_mentions"] = money_matches
            
        return details
        
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the current state and generate response."""
        try:
            schema = state.get("schema", {})
            user_input = state.get("user_text", "")
            chat_history = state.get("chat_history", [])
            location_context = state.get("location_context", {})
            
            general_info = schema.get("general_info", {})
            general_family_law = schema.get("general_family_law", {})
            
            # Phase 1: Location Collection
            if not general_info.get("location"):
                zip_code = self._extract_location(user_input)
                if zip_code:
                    general_info["location"] = zip_code
                    # Check if location is valid
                    if location_context.get("valid"):
                        general_info["location_complete"] = True
                        return {
                            "message": f"Thank you for providing your ZIP code in {location_context.get('city')}, {location_context.get('state')}. To help match you with the right attorney, could you please describe the legal issue that you are facing?",
                            "state": "gathering_case",
                            "extracted_info": {
                                "general_info": general_info
                            }
                        }
                    else:
                        return {
                            "message": "I need a valid US ZIP code to help find attorneys in your area. Could you please provide a valid ZIP code?",
                            "state": "gathering",
                            "extracted_info": {}
                        }
                else:
                    # First interaction
                    if not chat_history:
                        return {
                            "message": "Hi there! I'm here to help with your legal needs. Could you please share your ZIP code so I can better assist you?",
                            "state": "gathering",
                            "extracted_info": {}
                        }
                    else:
                        return {
                            "message": "I still need your ZIP code to proceed. Could you please provide it?",
                            "state": "gathering", 
                            "extracted_info": {}
                        }
                        
            # Phase 2: Case Extraction
            if general_info.get("location_complete") and not general_family_law.get("legal_issue"):
                # Identify person seeking help
                if not general_info.get("person_seeking_help"):
                    general_info["person_seeking_help"] = self._identify_person_seeking_help(user_input)
                    
                # Identify legal issues
                legal_issues = self._identify_legal_issues(user_input)
                if legal_issues:
                    general_family_law["legal_issue"] = legal_issues[0] if len(legal_issues) == 1 else legal_issues
                    
                    # Extract case-specific details
                    case_details = self._extract_case_details(user_input, legal_issues[0])
                    
                    return {
                        "message": None,
                        "state": "case_collected",
                        "extracted_info": {
                            "general_info": general_info,
                            "general_family_law": general_family_law,
                            "specific_questions": {
                                legal_issues[0]: case_details
                            } if case_details else {}
                        }
                    }
                else:
                    return {
                        "message": "Thank you. To help match you with the right attorney, could you please describe the legal issue in more detail?",
                        "state": "gathering_case",
                        "extracted_info": {
                            "general_info": general_info
                        }
                    }
                    
            # Phase 3: Remaining Preferences
            missing_fields = []
            field_order = ["gender", "language", "availability_needs", "budget_type", "budget_range"]
            
            for field in field_order:
                if not general_info.get(field):
                    missing_fields.append(field)
                    
            if missing_fields:
                next_field = missing_fields[0]
                question = self._get_preference_question(next_field, general_info)
                
                # Extract preference from current input
                extracted_pref = self._extract_preference(user_input, next_field)
                if extracted_pref:
                    general_info[next_field] = extracted_pref
                    
                return {
                    "message": question,
                    "state": "gathering",
                    "extracted_info": {
                        "general_info": general_info,
                        "general_family_law": general_family_law
                    }
                }
            else:
                # All information collected
                return {
                    "message": None,
                    "state": "complete",
                    "extracted_info": {
                        "general_info": general_info,
                        "general_family_law": general_family_law
                    }
                }
                
        except Exception as e:
            logger.error(f"Error in CaseGeneralAgent: {str(e)}")
            return {
                "message": "I apologize, but I encountered an error. Could you please repeat your last response?",
                "state": "error",
                "extracted_info": {}
            }
            
    def _get_preference_question(self, field: str, general_info: Dict[str, Any]) -> str:
        """Get the question for a specific preference field."""
        person = general_info.get("person_seeking_help", "client")
        person_ref = "you" if person == "client" else f"your {person}"
        
        questions = {
            "gender": f"Do {person_ref} have a preference for your attorney's gender? For example: [\"male\", \"female\", \"no preference at all\"]?",
            "language": f"What language would {person_ref} feel most comfortable communicating in? For example: [\"English\", \"Spanish\", \"Portuguese\"]?",
            "availability_needs": f"How soon do {person_ref} need legal representation? For example: [\"immediately\", \"soon\", \"not too urgent\"]?",
            "budget_type": f"When it comes to legal fees, what type of arrangement would work best for {person_ref}? For example: [\"hourly rates\", \"flat fees\", \"retainers\"]?",
            "budget_range": self._get_budget_range_question(general_info.get("budget_type", "hourly rates"))
        }
        
        return questions.get(field, f"Could you provide information about {field}?")
        
    def _get_budget_range_question(self, budget_type: str) -> str:
        """Get budget range question based on budget type."""
        if budget_type == "hourly rates":
            return "What hourly rate range are you comfortable with? For example: [\"$100-300\", \"$300-500\", \"$500+\"]?"
        elif budget_type == "flat fees":
            return "Do you have a preferred flat fee range in mind? For example: [\"$1,000-3,000\", \"$3,000-5,000\", \"$5,000+\"]?"
        else:
            return "What retainer range works best for you? For example: [\"$1,000-3,000\", \"$3,000-5,000\", \"$5,000+\"]?"
            
    def _extract_preference(self, text: str, field: str) -> Optional[str]:
        """Extract preference value from user input."""
        text_lower = text.lower()
        
        if field == "gender":
            if "male" in text_lower and "female" not in text_lower:
                return "male"
            elif "female" in text_lower:
                return "female"
            elif "no preference" in text_lower or "don't care" in text_lower:
                return "no preference"
                
        elif field == "language":
            if "spanish" in text_lower:
                return "Spanish"
            elif "portuguese" in text_lower:
                return "Portuguese"
            else:
                return "English"
                
        elif field == "availability_needs":
            if "immediately" in text_lower or "urgent" in text_lower or "asap" in text_lower:
                return "immediately"
            elif "soon" in text_lower:
                return "soon"
            elif "not urgent" in text_lower or "no rush" in text_lower:
                return "not too urgent"
                
        elif field == "budget_type":
            if "hourly" in text_lower:
                return "hourly rates"
            elif "flat" in text_lower:
                return "flat fees"
            elif "retainer" in text_lower:
                return "retainers"
                
        elif field == "budget_range":
            # Extract based on numbers in text
            if "$500+" in text or "500+" in text:
                return "$500+"
            elif "$300-500" in text or "300-500" in text:
                return "$300-500"
            elif "$100-300" in text or "100-300" in text:
                return "$100-300"
            # Similar logic for flat fees and retainers
                
        return None