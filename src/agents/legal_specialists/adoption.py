"""Adoption specialist agent."""

from typing import Dict, Any, Optional, List
from .base import LegalSpecialistAgent, LegalSchemaField
from ...utils.logger import get_logger
from groq import Groq
from ...config.settings import settings
import re
import json

logger = get_logger(__name__)


class AdoptionAgent(LegalSpecialistAgent):
    """Handles adoption case information gathering."""
    
    def __init__(self):
        """Initialize the adoption agent."""
        super().__init__(name="AdoptionAgent")
        self.client = Groq(api_key=settings.groq_api_key)
        self.prompt_template = self._load_prompt_template()
        
    def _load_prompt_template(self) -> str:
        """Load the adoption prompt template."""
        try:
            with open("/Users/arpanghoshal/loveandlaw-backend/prompts/adoption_agent.prompt", "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading prompt: {e}")
            return ""
            
    def _define_schema_fields(self) -> Dict[str, LegalSchemaField]:
        """Define the schema fields for adoption."""
        return {
            "adoption_type": LegalSchemaField(
                name="adoption_type",
                field_type="string",
                required=True,
                options=["Infant Adoption", "Stepparent Adoption", "Foster Care Adoption", "Relative Adoption", "Adult Adoption", "International Adoption"]
            ),
            "role_in_adoption": LegalSchemaField(
                name="role_in_adoption",
                field_type="string",
                required=True,
                options=["Prospective Adoptive Parent", "Birth Parent", "Adoptee", "Other"]
            ),
            "child_age": LegalSchemaField(
                name="child_age",
                field_type="string",
                required=True,
                depends_on={"adoption_type": "Adult Adoption"},
                options=["Infant (0-1)", "Toddler (1-3)", "Child (4-12)", "Teen (13-17)", "Adult (18+)"]
            ),
            "home_study_status": LegalSchemaField(
                name="home_study_status",
                field_type="string",
                required=True,
                depends_on={"role_in_adoption": "Prospective Adoptive Parent"},
                options=["Not Started", "In Progress", "Completed", "Not Required"]
            ),
            "birth_parent_consent": LegalSchemaField(
                name="birth_parent_consent",
                field_type="string",
                required=True,
                depends_on={"role_in_adoption": "Prospective Adoptive Parent"},
                options=["Already Obtained", "In Process", "Not Applicable", "Contested"]
            ),
            "indian_child_welfare_act": LegalSchemaField(
                name="indian_child_welfare_act",
                field_type="boolean",
                required=True
            ),
            "interstate_compact": LegalSchemaField(
                name="interstate_compact",
                field_type="boolean",
                required=True,
                depends_on={"adoption_type": "International Adoption"}
            ),
            "criminal_background_check": LegalSchemaField(
                name="criminal_background_check",
                field_type="string",
                required=True,
                depends_on={"role_in_adoption": "Prospective Adoptive Parent"},
                options=["Completed", "Pending", "Not Started", "Issues Found"]
            ),
            "placement_status": LegalSchemaField(
                name="placement_status",
                field_type="string",
                required=False,
                depends_on={"role_in_adoption": "Prospective Adoptive Parent"},
                options=["Child Not Yet Placed", "Child Currently Placed", "Post-Placement Period", "Finalized"]
            ),
            "legal_representation": LegalSchemaField(
                name="legal_representation",
                field_type="boolean",
                required=True
            ),
            "urgency_factors": LegalSchemaField(
                name="urgency_factors",
                field_type="array",
                required=False
            )
        }
        
    def _define_priority_order(self) -> List[str]:
        """Define the priority order for collecting fields."""
        return [
            "adoption_type",
            "role_in_adoption",
            "child_age",
            "indian_child_welfare_act",
            "home_study_status",
            "birth_parent_consent",
            "criminal_background_check",
            "interstate_compact",
            "placement_status",
            "legal_representation",
            "urgency_factors"
        ]
        
    def get_schema_name(self) -> str:
        """Get the schema section name."""
        return "adoption"
        
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the current state using Llama 4."""
        try:
            case_info = state.get("case_info", {})
            user_input = state.get("user_text", "")
            chat_history = state.get("chat_history", [])
            
            # Check if initial consultation
            if user_input == "START_SPECIALIZED_CONSULTATION":
                # Initialize adoption section if not exists
                if self.get_schema_name() not in case_info:
                    case_info[self.get_schema_name()] = {}
                    
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
                    {"role": "system", "content": "You are an adoption specialist. Follow the instructions carefully and respond ONLY with the JSON format specified."},
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
                
                # Apply special handling for adoption cases
                adoption_info = result.get("extracted_info", {}).get("adoption", {})
                
                # If ICWA applies, set urgency
                if adoption_info.get("indian_child_welfare_act") is True:
                    if "urgency_factors" not in adoption_info:
                        adoption_info["urgency_factors"] = []
                    if "ICWA compliance required" not in adoption_info["urgency_factors"]:
                        adoption_info["urgency_factors"].append("ICWA compliance required")
                        
                # If birth parent consent is contested, set urgency
                if adoption_info.get("birth_parent_consent") == "Contested":
                    if "urgency_factors" not in adoption_info:
                        adoption_info["urgency_factors"] = []
                    if "Contested consent" not in adoption_info["urgency_factors"]:
                        adoption_info["urgency_factors"].append("Contested consent")
                        
                return result
            else:
                logger.error("No valid response format found")
                return self._get_fallback_response(case_info)
                
        except Exception as e:
            logger.error(f"Error in AdoptionAgent: {str(e)}")
            return self._get_fallback_response(state.get("case_info", {}))
            
    def _get_fallback_response(self, case_info: Dict[str, Any]) -> Dict[str, Any]:
        """Get a fallback response when GPT fails."""
        return {
            "question": "I apologize, but I encountered an error. Could you please repeat your last response?",
            "current_state": "error",
            "extracted_info": case_info
        }
        
    def _format_question(self, field_name: str, case_info: Dict[str, Any]) -> str:
        """Format a question for a specific field."""
        person_seeking_help = case_info.get("general_info", {}).get("person_seeking_help", "client")
        person_ref = "you" if person_seeking_help == "client" else f"your {person_seeking_help}"
        
        questions = {
            "adoption_type": f"What type of adoption are {person_ref} pursuing? For example: 'Infant Adoption', 'Stepparent Adoption', 'Foster Care Adoption', 'Relative Adoption', 'Adult Adoption', 'International Adoption'",
            "role_in_adoption": f"What is {person_ref}r role in this adoption? For example: 'Prospective Adoptive Parent', 'Birth Parent', 'Adoptee', 'Other'",
            "child_age": f"What is the age range of the child involved in the adoption? For example: 'Infant (0-1)', 'Toddler (1-3)', 'Child (4-12)', 'Teen (13-17)', 'Adult (18+)'",
            "home_study_status": f"What is the status of {person_ref}r home study? For example: 'Not Started', 'In Progress', 'Completed', 'Not Required'",
            "birth_parent_consent": f"What is the status of birth parent consent? For example: 'Already Obtained', 'In Process', 'Not Applicable', 'Contested'",
            "indian_child_welfare_act": f"Does the Indian Child Welfare Act (ICWA) apply to this adoption? (This applies if the child is a member of or eligible for membership in a federally recognized tribe)",
            "interstate_compact": f"Will this adoption involve crossing state lines or international borders?",
            "criminal_background_check": f"What is the status of {person_ref}r criminal background check? For example: 'Completed', 'Pending', 'Not Started', 'Issues Found'",
            "placement_status": f"What is the current placement status? For example: 'Child Not Yet Placed', 'Child Currently Placed', 'Post-Placement Period', 'Finalized'",
            "legal_representation": f"Do {person_ref} currently have an attorney representing {person_ref} in the adoption?",
            "urgency_factors": f"Are there any time-sensitive factors in {person_ref}r adoption case? (e.g., pending court dates, placement deadlines, birth parent revocation periods)"
        }
        
        return questions.get(field_name, f"Could you provide information about {field_name}?")