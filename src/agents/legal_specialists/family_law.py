"""Family law specialist agent for general family law intake."""

from typing import Dict, Any, Optional, List
from .base import LegalSpecialistAgent, LegalSchemaField
from ...utils.logger import get_logger
from groq import Groq
import os

logger = get_logger(__name__)


class FamilyLawAgent(LegalSpecialistAgent):
    """Handles general family law case intake and routing."""
    
    def __init__(self):
        """Initialize the family law agent."""
        super().__init__(name="FamilyLawAgent")
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.prompt_template = self._load_prompt_template()
        
    def _load_prompt_template(self) -> str:
        """Load the family law prompt template."""
        try:
            with open("/Users/arpanghoshal/loveandlaw-backend/prompts/family_law_agent.prompt", "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading prompt: {e}")
            return ""
            
    def _define_schema_fields(self) -> Dict[str, LegalSchemaField]:
        """Define the schema fields for family law intake."""
        return {
            "age": LegalSchemaField(
                name="age",
                field_type="integer",
                required=True
            ),
            "occupation": LegalSchemaField(
                name="occupation", 
                field_type="string",
                required=True
            ),
            "existing_case": LegalSchemaField(
                name="existing_case",
                field_type="boolean",
                required=True
            ),
            "specialization": LegalSchemaField(
                name="specialization",
                field_type="string",
                required=True,
                options=["Litigation", "Mediation", "Collaborative"]
            ),
            "previous_attorney": LegalSchemaField(
                name="previous_attorney",
                field_type="boolean",
                required=True
            ),
            "legal_issue": LegalSchemaField(
                name="legal_issue",
                field_type="string",
                required=True,
                options=[
                    "Divorce and Separation",
                    "Child Custody",
                    "Property Division", 
                    "Child Support",
                    "Domestic Violence",
                    "Spousal Support",
                    "Adoption",
                    "Guardianship",
                    "Paternity",
                    "Restraining Orders",
                    "Juvenile Delinquency"
                ]
            )
        }
        
    def _define_priority_order(self) -> List[str]:
        """Define the priority order for collecting fields."""
        return [
            "age",
            "occupation",
            "existing_case",
            "previous_attorney",
            "specialization",
            "legal_issue"
        ]
        
    def get_schema_name(self) -> str:
        """Get the schema section name."""
        return "general_family_law"
        
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
                    {"role": "system", "content": "You are a family law intake specialist. Follow the instructions carefully and respond ONLY with the JSON format specified."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            # Extract JSON from response
            response_text = response.choices[0].message.content
            
            # Parse the response between <RESPOND> tags
            import re
            respond_match = re.search(r'<RESPOND>(.*?)</RESPOND>', response_text, re.DOTALL)
            if respond_match:
                import json
                result = json.loads(respond_match.group(1))
                
                # Check if transitioning to specialized agent
                if result.get("current_state") != "question_asked":
                    # Map legal issue to correct agent state
                    legal_issue = result.get("extracted_info", {}).get("general_family_law", {}).get("legal_issue")
                    if legal_issue:
                        state_map = {
                            "Divorce and Separation": "divorce_and_separation",
                            "Child Custody": "child_custody",
                            "Property Division": "property_division",
                            "Child Support": "child_support",
                            "Domestic Violence": "domestic_violence",
                            "Spousal Support": "spousal_support",
                            "Adoption": "adoption_process",
                            "Guardianship": "guardianship_process",
                            "Paternity": "paternity_practice",
                            "Restraining Orders": "restraining_order",
                            "Juvenile Delinquency": "juvenile_delinquency"
                        }
                        result["current_state"] = state_map.get(legal_issue, "completed")
                        
                return result
            else:
                logger.error("No valid response format found")
                return {
                    "question": "I apologize, but I need to gather some information. What is your age?",
                    "current_state": "question_asked",
                    "extracted_info": {}
                }
                
        except Exception as e:
            logger.error(f"Error in FamilyLawAgent: {str(e)}")
            return {
                "question": "I apologize for the confusion. Could you please tell me your age?",
                "current_state": "question_asked",
                "extracted_info": {}
            }
            
    def _format_question(self, field_name: str, case_info: Dict[str, Any]) -> str:
        """Format a question for a specific field."""
        person_seeking_help = case_info.get("general_info", {}).get("person_seeking_help", "client")
        person_ref = "you" if person_seeking_help == "client" else f"your {person_seeking_help}"
        
        questions = {
            "age": f"What is {person_ref}r age?",
            "occupation": f"What is {person_ref}r occupation?",
            "existing_case": f"Do {person_ref} have an existing family law case?",
            "previous_attorney": f"Have {person_ref} worked with an attorney before on this matter?",
            "specialization": f"What type of legal approach would {person_ref} prefer? For example: 'Litigation (court proceedings)', 'Mediation (collaborative negotiation)', 'Collaborative (team approach)'",
            "legal_issue": f"What type of family law matter do {person_ref} need help with? For example: 'Divorce and Separation', 'Child Custody', 'Property Division', 'Child Support', 'Domestic Violence'"
        }
        
        return questions.get(field_name, f"Could you provide information about {field_name}?")