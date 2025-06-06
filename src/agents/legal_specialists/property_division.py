"""Property division specialist agent."""

from typing import Dict, Any, Optional, List
from .base import LegalSpecialistAgent, LegalSchemaField
from ...utils.logger import setup_logger
from groq import Groq
import os
import re
import json

logger = setup_logger(__name__)


class PropertyDivisionAgent(LegalSpecialistAgent):
    """Handles property division case information gathering."""
    
    def __init__(self):
        """Initialize the property division agent."""
        super().__init__()
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.prompt_template = self._load_prompt_template()
        
    def _load_prompt_template(self) -> str:
        """Load the property division prompt template."""
        try:
            with open("/Users/arpanghoshal/loveandlaw-backend/prompts/property_division_agent.prompt", "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading prompt: {e}")
            return ""
            
    def _define_schema_fields(self) -> Dict[str, LegalSchemaField]:
        """Define the schema fields for property division."""
        return {
            "pre_nuptial_agreement": LegalSchemaField(
                name="pre_nuptial_agreement",
                field_type="string",
                required=True,
                options=["Yes", "No"]
            ),
            "main_assets": LegalSchemaField(
                name="main_assets",
                field_type="array",
                required=True
            ),
            "debts_division_needed": LegalSchemaField(
                name="debts_division_needed",
                field_type="string",
                required=True,
                options=["Yes", "No"]
            ),
            "complex_financial_matters": LegalSchemaField(
                name="complex_financial_matters",
                field_type="string",
                required=True,
                options=["Yes", "No"]
            ),
            "mediation_preferred": LegalSchemaField(
                name="mediation_preferred",
                field_type="string",
                required=True,
                options=["Yes", "No"]
            )
        }
        
    def _define_priority_order(self) -> List[str]:
        """Define the priority order for collecting fields."""
        return [
            "pre_nuptial_agreement",
            "main_assets",
            "debts_division_needed",
            "complex_financial_matters",
            "mediation_preferred"
        ]
        
    def get_schema_name(self) -> str:
        """Get the schema section name."""
        return "property_division"
        
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the current state using GPT-4."""
        try:
            case_info = state.get("case_info", {})
            user_input = state.get("user_text", "")
            chat_history = state.get("chat_history", [])
            
            # Handle yes/no conversion
            if user_input.lower() in ["yes", "yeah", "yep", "y"]:
                user_input = "Yes"
            elif user_input.lower() in ["no", "nope", "nah", "n"]:
                user_input = "No"
                
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
                    {"role": "system", "content": "You are a property division specialist. Follow the instructions carefully and respond ONLY with the JSON format specified."},
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
                
                # Check if all fields are complete
                pd_info = result.get("extracted_info", {}).get(self.get_schema_name(), {})
                if (pd_info.get("pre_nuptial_agreement") and
                    pd_info.get("main_assets") and len(pd_info["main_assets"]) > 0 and
                    pd_info.get("debts_division_needed") and
                    pd_info.get("complex_financial_matters") and
                    pd_info.get("mediation_preferred")):
                    
                    result["question"] = "PROPERTY_DIVISION_COMPLETE"
                    result["current_state"] = "completed"
                    
                return result
            else:
                logger.error("No valid response format found")
                return self._get_fallback_response(case_info)
                
        except Exception as e:
            logger.error(f"Error in PropertyDivisionAgent: {str(e)}")
            return self._get_fallback_response(state.get("case_info", {}))
            
    def _get_fallback_response(self, case_info: Dict[str, Any]) -> Dict[str, Any]:
        """Get a fallback response when GPT fails."""
        pd_info = case_info.get(self.get_schema_name(), {})
        
        # Get next missing field
        if not pd_info.get("pre_nuptial_agreement"):
            question = "Do you have a prenuptial or postnuptial agreement?"
        elif not pd_info.get("main_assets"):
            question = "What are the main assets involved in your case?"
        elif not pd_info.get("debts_division_needed"):
            question = "Are there any debts that need to be divided?"
        elif not pd_info.get("complex_financial_matters"):
            question = "Do you need assistance with complex financial matters?"
        elif not pd_info.get("mediation_preferred"):
            question = "Would you prefer mediation to resolve the property division?"
        else:
            return {
                "question": "PROPERTY_DIVISION_COMPLETE",
                "current_state": "completed",
                "extracted_info": case_info
            }
            
        return {
            "question": question,
            "current_state": "question_selection",
            "extracted_info": case_info
        }