"""Paternity practice specialist agent."""

from typing import Dict, Any, Optional, List
from .base import LegalSpecialistAgent, LegalSchemaField
from ...utils.logger import get_logger
from groq import Groq
from ...config.settings import settings
import re
import json

logger = get_logger(__name__)


class PaternityPracticeAgent(LegalSpecialistAgent):
    """Handles paternity case information gathering."""
    
    def __init__(self):
        """Initialize the paternity practice agent."""
        super().__init__(name="PaternityPracticeAgent")
        self.client = Groq(api_key=settings.groq_api_key)
        self.prompt_template = self._load_prompt_template()
        
    def _load_prompt_template(self) -> str:
        """Load the paternity practice prompt template."""
        try:
            with open("/Users/arpanghoshal/loveandlaw-backend/prompts/paternity_practice_agent.prompt", "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading prompt: {e}")
            return ""
            
    def _define_schema_fields(self) -> Dict[str, LegalSchemaField]:
        """Define the schema fields for paternity cases."""
        return {
            "role_in_case": LegalSchemaField(
                name="role_in_case",
                field_type="string",
                required=True,
                options=["Mother", "Alleged Father", "Legal Father", "Child", "Guardian", "Other"]
            ),
            "child_age": LegalSchemaField(
                name="child_age",
                field_type="integer",
                required=True
            ),
            "paternity_status": LegalSchemaField(
                name="paternity_status",
                field_type="string",
                required=True,
                options=["Not Established", "Acknowledged", "Disputed", "Legally Established", "Seeking to Establish", "Seeking to Disestablish"]
            ),
            "birth_certificate_status": LegalSchemaField(
                name="birth_certificate_status",
                field_type="string",
                required=True,
                options=["Father Not Listed", "Father Listed", "Incorrect Father Listed", "Amendment Needed", "Amendment in Process"]
            ),
            "acknowledgment_status": LegalSchemaField(
                name="acknowledgment_status",
                field_type="string",
                required=True,
                options=["No Acknowledgment", "Voluntary Acknowledgment Signed", "Acknowledgment Contested", "Acknowledgment Rescinded", "Not Applicable"]
            ),
            "dna_test_status": LegalSchemaField(
                name="dna_test_status",
                field_type="string",
                required=True,
                options=["Not Requested", "Requested", "Scheduled", "Completed - Positive", "Completed - Negative", "Results Disputed", "Refused"]
            ),
            "child_support_involvement": LegalSchemaField(
                name="child_support_involvement",
                field_type="boolean",
                required=True
            ),
            "custody_visitation_issues": LegalSchemaField(
                name="custody_visitation_issues",
                field_type="boolean",
                required=True
            ),
            "marriage_status": LegalSchemaField(
                name="marriage_status",
                field_type="string",
                required=True,
                options=["Never Married to Each Other", "Married When Child Born", "Married After Child Born", "Divorced", "Separated"]
            ),
            "presumed_father_exists": LegalSchemaField(
                name="presumed_father_exists",
                field_type="boolean",
                required=True
            ),
            "time_limitations_concern": LegalSchemaField(
                name="time_limitations_concern",
                field_type="boolean",
                required=True
            ),
            "court_case_status": LegalSchemaField(
                name="court_case_status",
                field_type="string",
                required=True,
                options=["No Case Filed", "Planning to File", "Case Filed", "Hearing Scheduled", "Order Issued", "Case Closed", "Appealing"]
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
            "role_in_case",
            "child_age",
            "paternity_status",
            "birth_certificate_status",
            "marriage_status",
            "presumed_father_exists",
            "acknowledgment_status",
            "dna_test_status",
            "child_support_involvement",
            "custody_visitation_issues",
            "time_limitations_concern",
            "court_case_status",
            "legal_representation",
            "urgency_factors"
        ]
        
    def get_schema_name(self) -> str:
        """Get the schema section name."""
        return "paternity_practice"
        
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the current state using Llama 4."""
        try:
            case_info = state.get("case_info", {})
            user_input = state.get("user_text", "")
            chat_history = state.get("chat_history", [])
            
            # Check if initial consultation
            if user_input == "START_SPECIALIZED_CONSULTATION":
                # Initialize paternity section if not exists
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
                    {"role": "system", "content": "You are a paternity law specialist. Follow the instructions carefully and respond ONLY with the JSON format specified."},
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
                
                # Apply special handling for paternity cases
                paternity_info = result.get("extracted_info", {}).get("paternity_practice", {})
                
                # If time limitations concern exists, set urgency
                if paternity_info.get("time_limitations_concern") is True:
                    if "urgency_factors" not in paternity_info:
                        paternity_info["urgency_factors"] = []
                    if "Time limitations apply" not in paternity_info["urgency_factors"]:
                        paternity_info["urgency_factors"].append("Time limitations apply")
                        
                # If child is older (approaching 18), set urgency
                age = paternity_info.get("child_age")
                if age and age >= 17:
                    if "urgency_factors" not in paternity_info:
                        paternity_info["urgency_factors"] = []
                    if "Child approaching majority" not in paternity_info["urgency_factors"]:
                        paternity_info["urgency_factors"].append("Child approaching majority")
                        
                # If presumed father exists and paternity disputed
                if paternity_info.get("presumed_father_exists") is True and \
                   paternity_info.get("paternity_status") == "Disputed":
                    if "urgency_factors" not in paternity_info:
                        paternity_info["urgency_factors"] = []
                    if "Presumed father complication" not in paternity_info["urgency_factors"]:
                        paternity_info["urgency_factors"].append("Presumed father complication")
                        
                return result
            else:
                logger.error("No valid response format found")
                return self._get_fallback_response(case_info)
                
        except Exception as e:
            logger.error(f"Error in PaternityPracticeAgent: {str(e)}")
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
            "role_in_case": f"What is {person_ref}r role in this paternity case? For example: 'Mother', 'Alleged Father', 'Legal Father', 'Child', 'Guardian', 'Other'",
            "child_age": f"What is the age of the child involved in the paternity case?",
            "paternity_status": f"What is the current paternity status? For example: 'Not Established', 'Acknowledged', 'Disputed', 'Legally Established', 'Seeking to Establish', 'Seeking to Disestablish'",
            "birth_certificate_status": f"What is the status of the father on the birth certificate? For example: 'Father Not Listed', 'Father Listed', 'Incorrect Father Listed', 'Amendment Needed', 'Amendment in Process'",
            "acknowledgment_status": f"Has there been a voluntary acknowledgment of paternity? For example: 'No Acknowledgment', 'Voluntary Acknowledgment Signed', 'Acknowledgment Contested', 'Acknowledgment Rescinded', 'Not Applicable'",
            "dna_test_status": f"What is the status of DNA/genetic testing? For example: 'Not Requested', 'Requested', 'Scheduled', 'Completed - Positive', 'Completed - Negative', 'Results Disputed', 'Refused'",
            "child_support_involvement": f"Is child support involved in this case?",
            "custody_visitation_issues": f"Are there custody or visitation issues to address?",
            "marriage_status": f"What was the relationship status when the child was born? For example: 'Never Married to Each Other', 'Married When Child Born', 'Married After Child Born', 'Divorced', 'Separated'",
            "presumed_father_exists": f"Is there a presumed father (e.g., mother's husband at time of birth)?",
            "time_limitations_concern": f"Are there any time limitation concerns? (Some states have deadlines for challenging or establishing paternity)",
            "court_case_status": f"What is the current court status? For example: 'No Case Filed', 'Planning to File', 'Case Filed', 'Hearing Scheduled', 'Order Issued', 'Case Closed', 'Appealing'",
            "legal_representation": f"Do {person_ref} currently have an attorney for the paternity matter?",
            "urgency_factors": f"Are there any urgent factors? (e.g., pending deadlines, child approaching 18, medical decisions needed)"
        }
        
        return questions.get(field_name, f"Could you provide information about {field_name}?")