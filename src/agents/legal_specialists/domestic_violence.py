"""Domestic violence specialist agent."""

from typing import Dict, Any, Optional, List
from .base import LegalSpecialistAgent, LegalSchemaField
from ...utils.logger import setup_logger
from groq import Groq
import os
import re
import json

logger = setup_logger(__name__)


class DomesticViolenceAgent(LegalSpecialistAgent):
    """Handles domestic violence case information gathering with high sensitivity."""
    
    def __init__(self):
        """Initialize the domestic violence agent."""
        super().__init__()
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.prompt_template = self._load_prompt_template()
        
    def _load_prompt_template(self) -> str:
        """Load the domestic violence prompt template."""
        try:
            with open("/Users/arpanghoshal/loveandlaw-backend/prompts/domestic_violence_agent.prompt", "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading prompt: {e}")
            return ""
            
    def _define_schema_fields(self) -> Dict[str, LegalSchemaField]:
        """Define the schema fields for domestic violence cases."""
        return {
            "immediate_danger": LegalSchemaField(
                name="immediate_danger",
                field_type="boolean",
                required=True
            ),
            "existing_protective_orders": LegalSchemaField(
                name="existing_protective_orders",
                field_type="boolean",
                required=True
            ),
            "violence_directed_towards": LegalSchemaField(
                name="violence_directed_towards",
                field_type="string",
                required=True,
                options=["Me", "My children", "Other family members"]
            ),
            "need_order_assistance": LegalSchemaField(
                name="need_order_assistance",
                field_type="boolean",
                required=False,
                depends_on={"existing_protective_orders": True}
            ),
            "children_safety_concerns": LegalSchemaField(
                name="children_safety_concerns",
                field_type="boolean",
                required=True
            ),
            "need_safety_planning": LegalSchemaField(
                name="need_safety_planning",
                field_type="boolean",
                required=True
            )
        }
        
    def _define_priority_order(self) -> List[str]:
        """Define the priority order for collecting fields."""
        return [
            "immediate_danger",  # Most critical - check safety first
            "existing_protective_orders",
            "violence_directed_towards",
            "need_order_assistance",
            "children_safety_concerns",
            "need_safety_planning"
        ]
        
    def get_schema_name(self) -> str:
        """Get the schema section name."""
        return "domestic_violence"
        
    def _apply_auto_population(self, case_info: Dict[str, Any]) -> Dict[str, Any]:
        """Apply auto-population rules specific to domestic violence cases."""
        schema_data = case_info.get(self.get_schema_name(), {})
        
        # If no existing protective orders, skip assistance question
        if schema_data.get("existing_protective_orders") is False:
            schema_data["need_order_assistance"] = None
            
        return schema_data
        
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the current state using GPT-4 with high sensitivity."""
        try:
            case_info = state.get("case_info", {})
            user_input = state.get("user_text", "")
            chat_history = state.get("chat_history", [])
            
            # Check for immediate danger first
            dv_info = case_info.get(self.get_schema_name(), {})
            if dv_info.get("immediate_danger") is True and "safety_resources_provided" not in dv_info:
                # Provide immediate safety resources
                dv_info["safety_resources_provided"] = True
                case_info[self.get_schema_name()] = dv_info
                
                return {
                    "question": "Your safety is our top priority. If you're in immediate danger, please call 911 or the National Domestic Violence Hotline at 1-800-799-7233. They can help you create a safety plan. Would you like to continue with finding legal representation?",
                    "current_state": "safety_check",
                    "extracted_info": case_info,
                    "priority_status": "urgent"
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
                    {"role": "system", "content": "You are a domestic violence specialist. Be extremely sensitive and supportive. Follow the instructions carefully and respond ONLY with the JSON format specified."},
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
                
                # Set priority status if immediate danger
                if result.get("extracted_info", {}).get(self.get_schema_name(), {}).get("immediate_danger"):
                    result["priority_status"] = "urgent"
                    
                return result
            else:
                logger.error("No valid response format found")
                return self._get_fallback_response(case_info)
                
        except Exception as e:
            logger.error(f"Error in DomesticViolenceAgent: {str(e)}")
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
        """Format a question for a specific field with sensitivity."""
        person_seeking_help = case_info.get("general_info", {}).get("person_seeking_help", "client")
        person_ref = "you" if person_seeking_help == "client" else f"your {person_seeking_help}"
        
        questions = {
            "immediate_danger": f"I understand this is difficult. Are {person_ref} currently in immediate danger or seeking a restraining order?",
            "existing_protective_orders": f"Have {person_ref} already filed for any protective orders?",
            "violence_directed_towards": f"I'm sorry you're going through this. Who has the violence been directed towards? For example: 'Me', 'My children', 'Other family members'",
            "need_order_assistance": f"Do {person_ref} need assistance with enforcing or modifying an existing protective order?",
            "children_safety_concerns": f"Are there any safety concerns regarding children?",
            "need_safety_planning": f"Would {person_ref} like assistance with safety planning?"
        }
        
        return questions.get(field_name, f"Could you provide information about {field_name}?")