"""Child support specialist agent."""

from typing import Dict, Any, Optional, List
from .base import LegalSpecialistAgent, LegalSchemaField
from ...utils.logger import get_logger
from groq import Groq
from ...config.settings import settings
import re
import json

logger = get_logger(__name__)


class ChildSupportAgent(LegalSpecialistAgent):
    """Handles child support case information gathering."""
    
    def __init__(self):
        """Initialize the child support agent."""
        super().__init__(name="ChildSupportAgent")
        self.client = Groq(api_key=settings.groq_api_key)
        self.prompt_template = self._load_prompt_template()
        
    def _load_prompt_template(self) -> str:
        """Load the child support prompt template."""
        try:
            with open("/Users/arpanghoshal/loveandlaw-backend/prompts/child_support.prompt", "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading prompt: {e}")
            return ""
            
    def _define_schema_fields(self) -> Dict[str, LegalSchemaField]:
        """Define the schema fields for child support."""
        return {
            "support_role": LegalSchemaField(
                name="support_role",
                field_type="string",
                required=True,
                options=["seeking", "paying", "both"]
            ),
            "existing_order": LegalSchemaField(
                name="existing_order",
                field_type="boolean",
                required=True
            ),
            "financial_changes": LegalSchemaField(
                name="financial_changes",
                field_type="boolean",
                required=False,
                depends_on={"existing_order": True}
            ),
            "enforcement_needed": LegalSchemaField(
                name="enforcement_needed",
                field_type="boolean",
                required=False,
                depends_on={"existing_order": True}
            ),
            "additional_expenses": LegalSchemaField(
                name="additional_expenses",
                field_type="boolean",
                required=True
            ),
            "additional_expenses_details": LegalSchemaField(
                name="additional_expenses_details",
                field_type="string",
                required=False,
                depends_on={"additional_expenses": True}
            ),
            "mediation_preferred": LegalSchemaField(
                name="mediation_preferred",
                field_type="boolean",
                required=True
            )
        }
        
    def _define_priority_order(self) -> List[str]:
        """Define the priority order for collecting fields."""
        return [
            "support_role",
            "existing_order",
            "financial_changes",
            "enforcement_needed",
            "additional_expenses",
            "additional_expenses_details",
            "mediation_preferred"
        ]
        
    def get_schema_name(self) -> str:
        """Get the schema section name."""
        return "child_support"
        
    def _apply_auto_population(self, case_info: Dict[str, Any]) -> Dict[str, Any]:
        """Apply auto-population rules specific to child support cases."""
        schema_data = case_info.get(self.get_schema_name(), {})
        
        # If no existing order, set dependent fields to null
        if schema_data.get("existing_order") is False:
            schema_data["financial_changes"] = None
            schema_data["enforcement_needed"] = None
            
        # If no additional expenses, clear details
        if schema_data.get("additional_expenses") is False:
            schema_data["additional_expenses_details"] = None
            
        return schema_data
        
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the current state using GPT-4."""
        try:
            case_info = state.get("case_info", {})
            user_input = state.get("user_text", "")
            chat_history = state.get("chat_history", [])
            
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
                    {"role": "system", "content": "You are a child support specialist. Follow the instructions carefully and respond ONLY with the JSON format specified."},
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
                result["extracted_info"] = {
                    self.get_schema_name(): self._apply_auto_population(
                        {self.get_schema_name(): result.get("extracted_info", {}).get(self.get_schema_name(), {})}
                    )
                }
                
                return result
            else:
                logger.error("No valid response format found")
                return self._get_fallback_response(case_info)
                
        except Exception as e:
            logger.error(f"Error in ChildSupportAgent: {str(e)}")
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
                    "current_state": "gathering_info",
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
            "support_role": f"Are {person_ref} seeking child support or being asked to pay? For example: 'Seeking', 'Paying', 'Both'",
            "existing_order": f"Is there an existing child support order?",
            "financial_changes": f"Has there been a significant change in financial circumstances since the order was issued?",
            "enforcement_needed": f"Do {person_ref} need help enforcing the existing support order?",
            "additional_expenses": f"Are there additional child-related expenses that need to be addressed?",
            "additional_expenses_details": f"What additional expenses need to be considered?",
            "mediation_preferred": f"Would {person_ref} prefer to resolve this through mediation?"
        }
        
        return questions.get(field_name, f"Could you provide information about {field_name}?")