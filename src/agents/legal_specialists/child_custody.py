"""Child custody specialist agent."""

from typing import Dict, Any, Optional, List
from .base import LegalSpecialistAgent, LegalSchemaField
from ...utils.logger import get_logger
from groq import Groq
import os
import re
import json

logger = get_logger(__name__)


class ChildCustodyAgent(LegalSpecialistAgent):
    """Handles child custody case information gathering."""
    
    def __init__(self):
        """Initialize the child custody agent."""
        super().__init__(name="ChildCustodyAgent")
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.prompt_template = self._load_prompt_template()
        
    def _load_prompt_template(self) -> str:
        """Load the child custody prompt template."""
        try:
            with open("/Users/arpanghoshal/loveandlaw-backend/prompts/child_custody_agent.prompt", "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading prompt: {e}")
            return ""
            
    def _define_schema_fields(self) -> Dict[str, LegalSchemaField]:
        """Define the schema fields for child custody."""
        return {
            "number_of_children": LegalSchemaField(
                name="number_of_children",
                field_type="integer",
                required=True
            ),
            "minor_children": LegalSchemaField(
                name="minor_children",
                field_type="array",
                required=True
            ),
            "current_living_arrangement": LegalSchemaField(
                name="current_living_arrangement",
                field_type="string",
                required=True,
                options=["Living with me", "Living with other parent", "Split between homes"]
            ),
            "existing_court_orders": LegalSchemaField(
                name="existing_court_orders",
                field_type="boolean",
                required=True
            ),
            "parent_cooperation": LegalSchemaField(
                name="parent_cooperation",
                field_type="string",
                required=True,
                options=["Good", "Fair", "Poor"]
            ),
            "parent_fitness_concerns": LegalSchemaField(
                name="parent_fitness_concerns",
                field_type="boolean",
                required=True
            ),
            "domestic_violence_history": LegalSchemaField(
                name="domestic_violence_history",
                field_type="boolean",
                required=False,
                depends_on={"parent_fitness_concerns": True},
                auto_populate={"parent_fitness_concerns": True, "set_value": True}
            ),
            "custody_type": LegalSchemaField(
                name="custody_type",
                field_type="string",
                required=True,
                options=["Primary Custody", "Shared Custody", "Visitation Rights"]
            ),
            "schedule_preference": LegalSchemaField(
                name="schedule_preference",
                field_type="string",
                required=True,
                options=["Week on/Week off", "Every weekend", "Alternating weekends", "Custom"]
            ),
            "resolution_preference": LegalSchemaField(
                name="resolution_preference",
                field_type="string",
                required=True,
                options=["Mediation", "Litigation", "Not sure"]
            )
        }
        
    def _define_priority_order(self) -> List[str]:
        """Define the priority order for collecting fields."""
        return [
            "number_of_children",
            "minor_children",
            "current_living_arrangement",
            "existing_court_orders",
            "parent_cooperation",
            "parent_fitness_concerns",
            "domestic_violence_history",
            "custody_type",
            "schedule_preference",
            "resolution_preference"
        ]
        
    def get_schema_name(self) -> str:
        """Get the schema section name."""
        return "child_custody"
        
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the current state using GPT-4."""
        try:
            case_info = state.get("case_info", {})
            user_input = state.get("user_text", "")
            chat_history = state.get("chat_history", [])
            
            # Check if initial consultation
            if user_input == "START_SPECIALIZED_CONSULTATION":
                # Check if we already have information from divorce proceedings
                divorce_info = case_info.get("divorce_and_separation", {})
                if divorce_info.get("children"):
                    # Copy children information
                    custody_info = case_info.get(self.get_schema_name(), {})
                    children_info = divorce_info["children"]
                    
                    if children_info.get("number_of_minor_children"):
                        custody_info["number_of_children"] = children_info["number_of_minor_children"]
                    if children_info.get("age_of_minor_children"):
                        # Parse ages into minor_children array
                        ages = self._parse_ages(children_info["age_of_minor_children"])
                        custody_info["minor_children"] = [
                            {"age": age, "current_custody_type": None}
                            for age in ages
                        ]
                    case_info[self.get_schema_name()] = custody_info
                    
            # Format the prompt
            prompt = self.prompt_template.format(
                case_info=case_info,
                chat_history=chat_history,
                user_input=user_input
            )
            
            # Call Llama 4
            response = self.client.chat.completions.create(
                model="meta-llama/llama-4-maverick-17b-128e-instruct",
                messages=[
                    {"role": "system", "content": "You are a child custody specialist. Follow the instructions carefully and respond ONLY with the JSON format specified."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            # Extract JSON from response
            response_text = response.choices[0].message.content
            
            # Parse the response between <RESPOND> tags
            respond_match = re.search(r'<RESPOND>(.*?)</RESPOND>', response_text, re.DOTALL)
            if respond_match:
                result = json.loads(respond_match.group(1))
                
                # Apply auto-population rules
                if result.get("extracted_info", {}).get("child_custody", {}).get("parent_fitness_concerns") is True:
                    if "domestic_violence_history" not in result["extracted_info"]["child_custody"]:
                        result["extracted_info"]["child_custody"]["domestic_violence_history"] = True
                        
                return result
            else:
                logger.error("No valid response format found")
                return self._get_fallback_response(case_info)
                
        except Exception as e:
            logger.error(f"Error in ChildCustodyAgent: {str(e)}")
            return self._get_fallback_response(state.get("case_info", {}))
            
    def _parse_ages(self, ages_str: str) -> List[int]:
        """Parse ages from a string."""
        ages = []
        numbers = re.findall(r'\d+', ages_str)
        for num in numbers:
            age = int(num)
            if 0 < age < 18:  # Only minor children
                ages.append(age)
        return ages
        
    def _get_fallback_response(self, case_info: Dict[str, Any]) -> Dict[str, Any]:
        """Get a fallback response when GPT fails."""
        missing_fields = self._get_missing_fields(case_info)
        if missing_fields:
            next_field = self._get_next_question(case_info)
            if next_field:
                question = self._format_question(next_field, case_info)
                return {
                    "question": question,
                    "current_state": "question_asked",
                    "extracted_info": case_info
                }
                
        return {
            "question": None,
            "current_state": "completed",
            "extracted_info": case_info
        }
        
    def _format_question(self, field_name: str, case_info: Dict[str, Any]) -> str:
        """Format a question for a specific field."""
        person_seeking_help = case_info.get("general_info", {}).get("person_seeking_help", "client")
        person_ref = "you" if person_seeking_help == "client" else f"your {person_seeking_help}"
        
        questions = {
            "number_of_children": f"How many minor children (under 18) are involved in this custody matter?",
            "minor_children": f"Please provide the age and date of birth for your first minor child (format: age, YYYY-MM-DD)",
            "current_living_arrangement": f"What is {person_ref}r children's current living situation? For example: 'Living with me (primary residence)', 'Living with other parent (visits with you)', 'Split between homes (shared time)'",
            "existing_court_orders": f"Are there any existing court orders regarding custody?",
            "parent_cooperation": f"How would {person_ref} describe the level of cooperation between {person_ref} and the other parent? For example: 'Good (effective communication)', 'Fair (some difficulties)', 'Poor (significant challenges)'",
            "parent_fitness_concerns": f"Do {person_ref} have any concerns about the other parent's ability to care for {person_ref}r child?",
            "domestic_violence_history": f"Is there any history of domestic violence between the parents?",
            "custody_type": f"What type of custody arrangement are {person_ref} seeking? For example: 'Primary Custody', 'Shared Custody', 'Visitation Rights'",
            "schedule_preference": f"What type of custody schedule would work best for {person_ref}r situation? For example: 'Week on/Week off (equal time each week)', 'Every weekend (weekends with you)', 'Alternating weekends (every other weekend)', 'Custom (specific schedule needs)'",
            "resolution_preference": f"How would {person_ref} prefer to resolve the custody matter? For example: 'Mediation', 'Litigation', 'Not sure'"
        }
        
        return questions.get(field_name, f"Could you provide information about {field_name}?")