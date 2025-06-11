"""Guardianship specialist agent."""

from typing import Dict, Any, Optional, List
from .base import LegalSpecialistAgent, LegalSchemaField
from ...utils.logger import get_logger
from groq import Groq
from ...config.settings import settings
import re
import json

logger = get_logger(__name__)


class GuardianshipAgent(LegalSpecialistAgent):
    """Handles guardianship case information gathering."""
    
    def __init__(self):
        """Initialize the guardianship agent."""
        super().__init__(name="GuardianshipAgent")
        self.client = Groq(api_key=settings.groq_api_key)
        self.prompt_template = self._load_prompt_template()
        
    def _load_prompt_template(self) -> str:
        """Load the guardianship prompt template."""
        try:
            with open("/Users/arpanghoshal/loveandlaw-backend/prompts/guardianship_agent.prompt", "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading prompt: {e}")
            return ""
            
    def _define_schema_fields(self) -> Dict[str, LegalSchemaField]:
        """Define the schema fields for guardianship."""
        return {
            "guardianship_type": LegalSchemaField(
                name="guardianship_type",
                field_type="string",
                required=True,
                options=["Minor Guardianship", "Adult Guardianship", "Temporary Guardianship", "Emergency Guardianship", "Limited Guardianship", "Full Guardianship"]
            ),
            "role_in_case": LegalSchemaField(
                name="role_in_case",
                field_type="string",
                required=True,
                options=["Proposed Guardian", "Current Guardian", "Ward", "Family Member", "Other"]
            ),
            "ward_age": LegalSchemaField(
                name="ward_age",
                field_type="integer",
                required=True
            ),
            "ward_current_situation": LegalSchemaField(
                name="ward_current_situation",
                field_type="string",
                required=True,
                options=["Living Independently", "With Family", "In Care Facility", "Hospital", "Other"]
            ),
            "reason_for_guardianship": LegalSchemaField(
                name="reason_for_guardianship",
                field_type="array",
                required=True,
                options=["Parent Death", "Parent Incapacity", "Parent Absence", "Mental Disability", "Physical Disability", "Developmental Disability", "Dementia/Alzheimer's", "Other Medical Condition", "Substance Abuse", "Other"]
            ),
            "current_caregiver": LegalSchemaField(
                name="current_caregiver",
                field_type="string",
                required=True,
                options=["Self", "Family Member", "Friend", "Professional Caregiver", "State/Institution", "None"]
            ),
            "parent_consent": LegalSchemaField(
                name="parent_consent",
                field_type="string",
                required=True,
                depends_on={"guardianship_type": "Minor Guardianship"},
                options=["Both Parents Consent", "One Parent Consents", "Parents Deceased", "Parents Rights Terminated", "Consent Disputed", "Not Applicable"]
            ),
            "capacity_evaluation": LegalSchemaField(
                name="capacity_evaluation",
                field_type="string",
                required=True,
                depends_on={"guardianship_type": "Adult Guardianship"},
                options=["Not Started", "Scheduled", "Completed - Incapacitated", "Completed - Has Capacity", "Disputed"]
            ),
            "court_petition_status": LegalSchemaField(
                name="court_petition_status",
                field_type="string",
                required=True,
                options=["Not Filed", "Preparing to File", "Filed", "Hearing Scheduled", "Granted", "Denied", "Under Appeal"]
            ),
            "alternatives_considered": LegalSchemaField(
                name="alternatives_considered",
                field_type="array",
                required=False,
                options=["Power of Attorney", "Healthcare Proxy", "Representative Payee", "Supported Decision Making", "Trust", "None"]
            ),
            "objections_expected": LegalSchemaField(
                name="objections_expected",
                field_type="boolean",
                required=True
            ),
            "financial_management": LegalSchemaField(
                name="financial_management",
                field_type="boolean",
                required=True
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
            "guardianship_type",
            "role_in_case", 
            "ward_age",
            "reason_for_guardianship",
            "ward_current_situation",
            "current_caregiver",
            "parent_consent",  # Only for minor guardianship
            "capacity_evaluation",  # Only for adult guardianship
            "court_petition_status",
            "objections_expected",
            "alternatives_considered",
            "financial_management",
            "legal_representation",
            "urgency_factors"
        ]
        
    def get_schema_name(self) -> str:
        """Get the schema section name."""
        return "guardianship"
        
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the current state using Llama 4."""
        try:
            case_info = state.get("case_info", {})
            user_input = state.get("user_text", "")
            chat_history = state.get("chat_history", [])
            
            # Check if initial consultation
            if user_input == "START_SPECIALIZED_CONSULTATION":
                # Initialize guardianship section if not exists
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
                    {"role": "system", "content": "You are a guardianship specialist. Follow the instructions carefully and respond ONLY with the JSON format specified."},
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
                
                # Apply special handling for guardianship cases
                guardianship_info = result.get("extracted_info", {}).get("guardianship", {})
                
                # If emergency guardianship, set urgency
                if guardianship_info.get("guardianship_type") == "Emergency Guardianship":
                    if "urgency_factors" not in guardianship_info:
                        guardianship_info["urgency_factors"] = []
                    if "Emergency guardianship required" not in guardianship_info["urgency_factors"]:
                        guardianship_info["urgency_factors"].append("Emergency guardianship required")
                        
                # If capacity is disputed, set urgency
                if guardianship_info.get("capacity_evaluation") == "Disputed":
                    if "urgency_factors" not in guardianship_info:
                        guardianship_info["urgency_factors"] = []
                    if "Capacity dispute" not in guardianship_info["urgency_factors"]:
                        guardianship_info["urgency_factors"].append("Capacity dispute")
                        
                # If ward is in hospital or unsafe situation
                if guardianship_info.get("ward_current_situation") == "Hospital":
                    if "urgency_factors" not in guardianship_info:
                        guardianship_info["urgency_factors"] = []
                    if "Ward in hospital" not in guardianship_info["urgency_factors"]:
                        guardianship_info["urgency_factors"].append("Ward in hospital")
                        
                return result
            else:
                logger.error("No valid response format found")
                return self._get_fallback_response(case_info)
                
        except Exception as e:
            logger.error(f"Error in GuardianshipAgent: {str(e)}")
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
            "guardianship_type": f"What type of guardianship are {person_ref} seeking? For example: 'Minor Guardianship', 'Adult Guardianship', 'Temporary Guardianship', 'Emergency Guardianship', 'Limited Guardianship', 'Full Guardianship'",
            "role_in_case": f"What is {person_ref}r role in this guardianship case? For example: 'Proposed Guardian', 'Current Guardian', 'Ward', 'Family Member', 'Other'",
            "ward_age": f"What is the age of the person who needs a guardian (the ward)?",
            "ward_current_situation": f"Where is the ward currently living? For example: 'Living Independently', 'With Family', 'In Care Facility', 'Hospital', 'Other'",
            "reason_for_guardianship": f"What is the reason guardianship is needed? You can select multiple: 'Parent Death', 'Parent Incapacity', 'Parent Absence', 'Mental Disability', 'Physical Disability', 'Developmental Disability', 'Dementia/Alzheimer's', 'Other Medical Condition', 'Substance Abuse', 'Other'",
            "current_caregiver": f"Who is currently caring for the ward? For example: 'Self', 'Family Member', 'Friend', 'Professional Caregiver', 'State/Institution', 'None'",
            "parent_consent": f"What is the status of parental consent for the guardianship? For example: 'Both Parents Consent', 'One Parent Consents', 'Parents Deceased', 'Parents Rights Terminated', 'Consent Disputed', 'Not Applicable'",
            "capacity_evaluation": f"What is the status of the capacity evaluation? For example: 'Not Started', 'Scheduled', 'Completed - Incapacitated', 'Completed - Has Capacity', 'Disputed'",
            "court_petition_status": f"What is the current status of the guardianship petition? For example: 'Not Filed', 'Preparing to File', 'Filed', 'Hearing Scheduled', 'Granted', 'Denied', 'Under Appeal'",
            "alternatives_considered": f"Have {person_ref} considered any alternatives to guardianship? You can select multiple: 'Power of Attorney', 'Healthcare Proxy', 'Representative Payee', 'Supported Decision Making', 'Trust', 'None'",
            "objections_expected": f"Do {person_ref} expect anyone to object to the guardianship?",
            "financial_management": f"Will the guardianship include managing the ward's finances?",
            "legal_representation": f"Do {person_ref} currently have an attorney for the guardianship proceedings?",
            "urgency_factors": f"Are there any urgent or time-sensitive factors in {person_ref}r guardianship case? (e.g., pending medical decisions, immediate safety concerns, court deadlines)"
        }
        
        return questions.get(field_name, f"Could you provide information about {field_name}?")