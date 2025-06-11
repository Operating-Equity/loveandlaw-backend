"""Child abuse specialist agent."""

from typing import Dict, Any, Optional, List
from .base import LegalSpecialistAgent, LegalSchemaField
from ...utils.logger import get_logger
from groq import Groq
from ...config.settings import settings
import re
import json

logger = get_logger(__name__)


class ChildAbuseAgent(LegalSpecialistAgent):
    """Handles child abuse case information gathering."""
    
    def __init__(self):
        """Initialize the child abuse agent."""
        super().__init__(name="ChildAbuseAgent")
        self.client = Groq(api_key=settings.groq_api_key)
        self.prompt_template = self._load_prompt_template()
        
    def _load_prompt_template(self) -> str:
        """Load the child abuse prompt template."""
        try:
            with open("/Users/arpanghoshal/loveandlaw-backend/prompts/child_abuse_agent.prompt", "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading prompt: {e}")
            return ""
            
    def _define_schema_fields(self) -> Dict[str, LegalSchemaField]:
        """Define the schema fields for child abuse cases."""
        return {
            "immediate_safety": LegalSchemaField(
                name="immediate_safety",
                field_type="boolean",
                required=True
            ),
            "reporter_role": LegalSchemaField(
                name="reporter_role",
                field_type="string",
                required=True,
                options=["Parent/Guardian", "Mandated Reporter", "Family Member", "Other"]
            ),
            "type_of_abuse": LegalSchemaField(
                name="type_of_abuse",
                field_type="array",
                required=True,
                options=["Physical", "Sexual", "Emotional/Psychological", "Neglect", "Multiple Types"]
            ),
            "child_age": LegalSchemaField(
                name="child_age",
                field_type="integer",
                required=True
            ),
            "reporting_status": LegalSchemaField(
                name="reporting_status",
                field_type="string",
                required=True,
                options=["Not Yet Reported", "Report Filed", "Under Investigation", "Investigation Complete"]
            ),
            "cps_involvement": LegalSchemaField(
                name="cps_involvement",
                field_type="boolean",
                required=True
            ),
            "law_enforcement_involved": LegalSchemaField(
                name="law_enforcement_involved",
                field_type="boolean",
                required=True
            ),
            "child_current_location": LegalSchemaField(
                name="child_current_location",
                field_type="string",
                required=True,
                options=["Safe with Reporter", "With Non-Offending Parent", "In Foster Care", "Still in Dangerous Situation", "Unknown"]
            ),
            "perpetrator_relationship": LegalSchemaField(
                name="perpetrator_relationship",
                field_type="string",
                required=True,
                options=["Parent", "Step-parent", "Other Family Member", "Caregiver", "Other Known Person", "Unknown"]
            ),
            "evidence_documentation": LegalSchemaField(
                name="evidence_documentation",
                field_type="string",
                required=False,
                options=["Photos/Videos", "Medical Records", "Witness Statements", "None Yet", "Other"]
            ),
            "protective_order_status": LegalSchemaField(
                name="protective_order_status",
                field_type="string",
                required=False,
                options=["Not Needed", "Planning to File", "Filed", "Granted", "Denied"]
            ),
            "legal_representation": LegalSchemaField(
                name="legal_representation",
                field_type="boolean",
                required=True
            )
        }
        
    def _define_priority_order(self) -> List[str]:
        """Define the priority order for collecting fields."""
        return [
            "immediate_safety",  # HIGHEST PRIORITY
            "child_current_location",
            "reporter_role",
            "child_age",
            "type_of_abuse",
            "perpetrator_relationship",
            "reporting_status",
            "cps_involvement",
            "law_enforcement_involved",
            "evidence_documentation",
            "protective_order_status",
            "legal_representation"
        ]
        
    def get_schema_name(self) -> str:
        """Get the schema section name."""
        return "child_abuse"
        
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the current state using Llama 4."""
        try:
            case_info = state.get("case_info", {})
            user_input = state.get("user_text", "")
            chat_history = state.get("chat_history", [])
            
            # Check if initial consultation
            if user_input == "START_SPECIALIZED_CONSULTATION":
                # Initialize child abuse section if not exists
                if self.get_schema_name() not in case_info:
                    case_info[self.get_schema_name()] = {}
                    
                # Immediately ask about safety
                return {
                    "question": "I want to help ensure everyone's safety. Is the child currently in immediate danger or unsafe situation?",
                    "current_state": "safety_assessment",
                    "extracted_info": {self.get_schema_name(): {}}
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
                    {"role": "system", "content": "You are a child abuse specialist with a safety-first approach. Prioritize immediate safety and mandatory reporting requirements. Follow the instructions carefully and respond ONLY with the JSON format specified."},
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
                
                # Apply safety logic
                abuse_info = result.get("extracted_info", {}).get("child_abuse", {})
                
                # If child is not safe, add urgent flag
                if abuse_info.get("immediate_safety") is False or \
                   abuse_info.get("child_current_location") == "Still in Dangerous Situation":
                    result["urgent_action_needed"] = True
                    result["safety_resources"] = [
                        "National Child Abuse Hotline: 1-800-4-A-CHILD (1-800-422-4453)",
                        "Call 911 if immediate danger",
                        "Contact local Child Protective Services"
                    ]
                    
                # If reporter is mandated reporter and hasn't reported
                if abuse_info.get("reporter_role") == "Mandated Reporter" and \
                   abuse_info.get("reporting_status") == "Not Yet Reported":
                    result["mandatory_reporting_reminder"] = True
                    
                return result
            else:
                logger.error("No valid response format found")
                return self._get_fallback_response(case_info)
                
        except Exception as e:
            logger.error(f"Error in ChildAbuseAgent: {str(e)}")
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
            "immediate_safety": f"Is the child currently in immediate danger or an unsafe situation?",
            "child_current_location": f"Where is the child right now? For example: 'Safe with Reporter', 'With Non-Offending Parent', 'In Foster Care', 'Still in Dangerous Situation', 'Unknown'",
            "reporter_role": f"What is {person_ref}r role in this situation? For example: 'Parent/Guardian', 'Mandated Reporter', 'Family Member', 'Other'",
            "child_age": f"What is the age of the child involved?",
            "type_of_abuse": f"What type(s) of abuse are {person_ref} concerned about? For example: 'Physical', 'Sexual', 'Emotional/Psychological', 'Neglect', 'Multiple Types'",
            "perpetrator_relationship": f"What is the relationship of the suspected abuser to the child? For example: 'Parent', 'Step-parent', 'Other Family Member', 'Caregiver', 'Other Known Person', 'Unknown'",
            "reporting_status": f"What is the current status of reporting this abuse? For example: 'Not Yet Reported', 'Report Filed', 'Under Investigation', 'Investigation Complete'",
            "cps_involvement": f"Is Child Protective Services (CPS) currently involved?",
            "law_enforcement_involved": f"Has law enforcement been contacted or are they involved?",
            "evidence_documentation": f"Have {person_ref} documented any evidence? For example: 'Photos/Videos', 'Medical Records', 'Witness Statements', 'None Yet', 'Other'",
            "protective_order_status": f"What is the status of any protective/restraining orders? For example: 'Not Needed', 'Planning to File', 'Filed', 'Granted', 'Denied'",
            "legal_representation": f"Do {person_ref} currently have an attorney representing {person_ref} in this matter?"
        }
        
        return questions.get(field_name, f"Could you provide information about {field_name}?")
        
    def _get_safety_resources(self) -> Dict[str, Any]:
        """Get safety resources for child abuse cases."""
        return {
            "hotlines": [
                {"name": "National Child Abuse Hotline", "number": "1-800-4-A-CHILD (1-800-422-4453)"},
                {"name": "Emergency Services", "number": "911"}
            ],
            "resources": [
                "Local Child Protective Services",
                "Children's Advocacy Centers",
                "Safe Houses/Shelters"
            ],
            "immediate_actions": [
                "Ensure child's immediate safety",
                "Document injuries with photos if safe to do so",
                "Seek medical attention if needed",
                "Contact authorities if mandated reporter"
            ]
        }