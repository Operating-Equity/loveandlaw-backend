"""Spousal support specialist agent."""

from typing import Dict, Any, Optional, List
from .base import LegalSpecialistAgent, LegalSchemaField
from ...utils.logger import setup_logger
from groq import Groq
import os
import re
import json

logger = setup_logger(__name__)


class SpousalSupportAgent(LegalSpecialistAgent):
    """Handles spousal support case information gathering."""
    
    def __init__(self):
        """Initialize the spousal support agent."""
        super().__init__()
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.prompt_template = self._load_prompt_template()
        
    def _load_prompt_template(self) -> str:
        """Load the spousal support prompt template."""
        try:
            with open("/Users/arpanghoshal/loveandlaw-backend/prompts/spousal_support_agent.prompt", "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading prompt: {e}")
            return ""
            
    def _define_schema_fields(self) -> Dict[str, LegalSchemaField]:
        """Define the schema fields for spousal support."""
        return {
            "spousal_support_status": LegalSchemaField(
                name="spousal_support_status",
                field_type="string",
                required=True,
                options=["Seeking support", "Asked to pay", "Both apply", "None"]
            ),
            "current_support_status": LegalSchemaField(
                name="current_support_status",
                field_type="string",
                required=True,
                options=["No don't receive", "Yes receive", "Yes pay"]
            ),
            "marriage_status": LegalSchemaField(
                name="marriage_status",
                field_type="string",
                required=True,
                options=["Married and living together", "Married and not living together", "Divorced"]
            ),
            "marriage_years": LegalSchemaField(
                name="marriage_years",
                field_type="string",
                required=True
            ),
            "separation_date": LegalSchemaField(
                name="separation_date",
                field_type="string",
                required=False,
                depends_on={"marriage_status": "Divorced"}
            ),
            "spouse_occupation": LegalSchemaField(
                name="spouse_occupation",
                field_type="string",
                required=True
            ),
            "support_factors": LegalSchemaField(
                name="support_factors",
                field_type="boolean",
                required=True
            ),
            "preferred_resolution": LegalSchemaField(
                name="preferred_resolution",
                field_type="string",
                required=True,
                options=["Mediation", "Litigation", "Not sure"]
            ),
            "client_income": LegalSchemaField(
                name="client_income",
                field_type="string",
                required=True,
                options=["Up to $50,000", "$50,000-$100,000", "$100,000-$150,000", "Above $150,000"]
            ),
            "spouse_income": LegalSchemaField(
                name="spouse_income",
                field_type="string",
                required=True,
                options=["Up to $50,000", "$50,000-$100,000", "$100,000-$150,000", "Above $150,000"]
            )
        }
        
    def _define_priority_order(self) -> List[str]:
        """Define the priority order for collecting fields."""
        return [
            "spousal_support_status",
            "current_support_status",
            "marriage_status",
            "marriage_years",
            "separation_date",
            "client_income",
            "spouse_income",
            "spouse_occupation",
            "support_factors",
            "preferred_resolution"
        ]
        
    def get_schema_name(self) -> str:
        """Get the schema section name."""
        return "spousal_support"
        
    def _apply_auto_population(self, case_info: Dict[str, Any]) -> Dict[str, Any]:
        """Apply auto-population rules specific to spousal support cases."""
        schema_data = case_info.get(self.get_schema_name(), {})
        
        # Auto-set separation_date based on marriage_status
        if schema_data.get("marriage_status") in ["Married and living together", "Married and not living together"]:
            schema_data["separation_date"] = False
            
        # If spousal_support_status is "None", set current_support_status
        if schema_data.get("spousal_support_status") == "None":
            schema_data["current_support_status"] = "No don't receive"
            
        # Map numeric incomes to ranges
        for field in ["client_income", "spouse_income"]:
            if field in schema_data and isinstance(schema_data[field], (int, float)):
                income = schema_data[field]
                if income <= 50000:
                    schema_data[field] = "Up to $50,000"
                elif income <= 100000:
                    schema_data[field] = "$50,000-$100,000"
                elif income <= 150000:
                    schema_data[field] = "$100,000-$150,000"
                else:
                    schema_data[field] = "Above $150,000"
                    
        return schema_data
        
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the current state using GPT-4."""
        try:
            case_info = state.get("case_info", {})
            user_input = state.get("user_text", "")
            chat_history = state.get("chat_history", [])
            
            # Check for completion signal
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
                    {"role": "system", "content": "You are a spousal support specialist. Follow the instructions carefully and respond ONLY with the JSON format specified."},
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
            logger.error(f"Error in SpousalSupportAgent: {str(e)}")
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
            "question": "Thank you for providing all the necessary information about your spousal support case. Please wait a moment while I provide you with the best attorney that matches your legal needs.",
            "current_state": "completed",
            "extracted_info": case_info
        }
        
    def _format_question(self, field_name: str, case_info: Dict[str, Any]) -> str:
        """Format a question for a specific field."""
        person_seeking_help = case_info.get("general_info", {}).get("person_seeking_help", "client")
        person_ref = "you" if person_seeking_help == "client" else f"your {person_seeking_help}"
        
        questions = {
            "spousal_support_status": f"What is {person_ref}r current spousal support situation? For example: 'Seeking support', 'Asked to pay', 'Both apply', 'None'",
            "current_support_status": f"Do {person_ref} currently receive or pay spousal support? For example: 'No don't receive', 'Yes receive', 'Yes pay'",
            "marriage_status": f"What is {person_ref}r current marital status? For example: 'Married and living together', 'Married and not living together', 'Divorced'",
            "marriage_years": f"How many years were {person_ref} married?",
            "separation_date": f"When did {person_ref} separate?",
            "client_income": f"What is {person_ref}r gross annual income? For example: 'Up to $50,000', '$50,000-$100,000', '$100,000-$150,000', 'Above $150,000'",
            "spouse_income": f"What is {person_ref}r spouse's gross annual income? For example: 'Up to $50,000', '$50,000-$100,000', '$100,000-$150,000', 'Above $150,000'",
            "spouse_occupation": f"What is {person_ref}r spouse's occupation?",
            "support_factors": f"Are there any special factors that should be considered (health issues, career sacrifices, etc.)?",
            "preferred_resolution": f"How would {person_ref} prefer to resolve this matter? For example: 'Mediation', 'Litigation', 'Not sure'"
        }
        
        return questions.get(field_name, f"Could you provide information about {field_name}?")