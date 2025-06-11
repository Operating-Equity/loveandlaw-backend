"""Divorce and separation specialist agent."""

from typing import Dict, Any, Optional, List
from .base import LegalSpecialistAgent, LegalSchemaField
from ...utils.logger import get_logger
from groq import Groq
from ...config.settings import settings
import re
import json

logger = get_logger(__name__)


class DivorceAndSeparationAgent(LegalSpecialistAgent):
    """Handles divorce and separation case information gathering."""
    
    def __init__(self):
        """Initialize the divorce and separation agent."""
        super().__init__(name="DivorceAndSeparationAgent")
        self.client = Groq(api_key=settings.groq_api_key)
        self.prompt_template = self._load_prompt_template()
        
    def _load_prompt_template(self) -> str:
        """Load the divorce and separation prompt template."""
        try:
            with open("/Users/arpanghoshal/loveandlaw-backend/prompts/divorce_and_separation_agent.prompt", "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading prompt: {e}")
            return ""
            
    def _define_schema_fields(self) -> Dict[str, LegalSchemaField]:
        """Define the schema fields for divorce and separation."""
        return {
            "divorce_status": LegalSchemaField(
                name="divorce_status",
                field_type="string",
                required=True,
                options=["Filing for Divorce", "Legal Separation"]
            ),
            "contested": LegalSchemaField(
                name="contested",
                field_type="string",
                required=True,
                options=["Contested", "Uncontested"]
            ),
            "assistance_needed": LegalSchemaField(
                name="assistance_needed",
                field_type="string",
                required=True,
                options=["Property Division", "Spousal Support", "Both"]
            ),
            "has_children": LegalSchemaField(
                name="has_children",
                field_type="boolean",
                required=True
            ),
            "disputes": LegalSchemaField(
                name="disputes",
                field_type="boolean",
                required=False,
                depends_on={"has_children": True, "minor_children": True}
            ),
            "minor_children": LegalSchemaField(
                name="minor_children",
                field_type="boolean",
                required=False,
                depends_on={"has_children": True}
            ),
            "number_of_minor_children": LegalSchemaField(
                name="number_of_minor_children",
                field_type="integer",
                required=False,
                depends_on={"minor_children": True}
            ),
            "age_of_minor_children": LegalSchemaField(
                name="age_of_minor_children",
                field_type="string",
                required=False,
                depends_on={"minor_children": True}
            ),
            "marital_assets_value": LegalSchemaField(
                name="marital_assets_value",
                field_type="string",
                required=True,
                options=["Below $100,000", "$100,000–$500,000", "$500,000–$1,000,000", "Over $1,000,000"]
            ),
            "prenuptial_or_postnuptial": LegalSchemaField(
                name="prenuptial_or_postnuptial",
                field_type="boolean",
                required=True
            ),
            "urgent_matters": LegalSchemaField(
                name="urgent_matters",
                field_type="boolean",
                required=True
            )
        }
        
    def _define_priority_order(self) -> List[str]:
        """Define the priority order for collecting fields."""
        return [
            "divorce_status",
            "contested",
            "has_children",
            "number_of_minor_children",
            "age_of_minor_children",
            "disputes",
            "marital_assets_value",
            "prenuptial_or_postnuptial",
            "urgent_matters",
            "assistance_needed"
        ]
        
    def get_schema_name(self) -> str:
        """Get the schema section name."""
        return "divorce_and_separation"
        
    def _apply_auto_population(self, case_info: Dict[str, Any]) -> Dict[str, Any]:
        """Apply auto-population rules specific to divorce cases."""
        schema_data = case_info.get(self.get_schema_name(), {})
        
        # If has_children is false, set related fields to null
        if schema_data.get("has_children") is False:
            schema_data["disputes"] = None
            schema_data["minor_children"] = None
            schema_data["number_of_minor_children"] = None
            schema_data["age_of_minor_children"] = None
            
        # Parse ages to determine minor children
        if schema_data.get("age_of_minor_children"):
            ages_str = schema_data["age_of_minor_children"]
            ages = self._parse_ages(ages_str)
            minor_ages = [age for age in ages if age < 18]
            
            if minor_ages:
                schema_data["minor_children"] = True
                schema_data["number_of_minor_children"] = len(minor_ages)
                schema_data["age_of_minor_children"] = ", ".join(str(age) for age in minor_ages)
            else:
                schema_data["minor_children"] = False
                schema_data["number_of_minor_children"] = 0
                schema_data["disputes"] = None
                
        return schema_data
        
    def _parse_ages(self, ages_str: str) -> List[int]:
        """Parse ages from a string."""
        ages = []
        # Find all numbers in the string
        numbers = re.findall(r'\d+', ages_str)
        for num in numbers:
            age = int(num)
            if 0 < age < 100:  # Reasonable age range
                ages.append(age)
        return ages
        
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the current state using GPT-4."""
        try:
            case_info = state.get("case_info", {})
            user_input = state.get("user_text", "")
            chat_history = state.get("chat_history", [])
            
            # Check for special transitions
            if "CHILD_CUSTODY_COMPLETE" in user_input or any("CHILD CUSTODY CONSULTATION COMPLETE" in msg for msg in chat_history):
                # Continue with remaining divorce questions
                case_info[self.get_schema_name()]["_skip_child_custody"] = True
                
            if "SPOUSAL_SUPPORT_COMPLETE" in user_input or any("SPOUSAL SUPPORT CONSULTATION COMPLETE" in msg for msg in chat_history):
                return {
                    "question": "Thank you for providing all the necessary information about your spousal support case. Please wait a moment while I provide you with the best attorney that matches your legal needs.",
                    "current_state": "completed",
                    "extracted_info": case_info
                }
                
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
                    {"role": "system", "content": "You are a divorce and separation specialist. Follow the instructions carefully and respond ONLY with the JSON format specified."},
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
                
                # Handle state transitions
                current_state = result.get("current_state", "")
                
                # Map states correctly
                if current_state == "Child_Custody":
                    result["current_state"] = "child_custody"
                elif current_state == "Property_Division":
                    result["current_state"] = "property_division"
                elif current_state == "Spousal_Support":
                    result["current_state"] = "spousal_support"
                elif current_state == "Property_Division and Spousal_Support":
                    result["current_state"] = "property_division"  # Handle property first
                    
                return result
            else:
                logger.error("No valid response format found")
                return self._get_fallback_response(case_info)
                
        except Exception as e:
            logger.error(f"Error in DivorceAndSeparationAgent: {str(e)}")
            return self._get_fallback_response(state.get("case_info", {}))
            
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
            "divorce_status": f"Are {person_ref} seeking a divorce or legal separation? For example: 'Filing for Divorce', 'Legal Separation'",
            "contested": f"Is this a contested or uncontested matter? For example: 'Contested (spouse disagrees)', 'Uncontested (mutual agreement)'",
            "has_children": f"Do {person_ref} have any children from this marriage?",
            "number_of_minor_children": f"How many children do {person_ref} have?",
            "age_of_minor_children": f"What are the ages of {person_ref}r children?",
            "disputes": f"Are there any custody disputes or disagreements regarding the children?",
            "marital_assets_value": f"What is the approximate value of {person_ref}r marital assets? For example: 'Below $100,000', '$100,000–$500,000', '$500,000–$1,000,000', 'Over $1,000,000'",
            "prenuptial_or_postnuptial": f"Do {person_ref} have a prenuptial or postnuptial agreement?",
            "urgent_matters": f"Are there any urgent matters that need immediate attention?",
            "assistance_needed": f"What type of assistance do {person_ref} need? For example: 'Property Division', 'Spousal Support', 'Both'"
        }
        
        return questions.get(field_name, f"Could you provide information about {field_name}?")