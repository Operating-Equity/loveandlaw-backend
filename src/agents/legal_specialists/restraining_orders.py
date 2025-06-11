"""Restraining orders specialist agent."""

from typing import Dict, Any, Optional, List
from .base import LegalSpecialistAgent, LegalSchemaField
from ...utils.logger import get_logger
from groq import Groq
from ...config.settings import settings
import re
import json

logger = get_logger(__name__)


class RestrainingOrdersAgent(LegalSpecialistAgent):
    """Handles restraining order case information gathering."""
    
    def __init__(self):
        """Initialize the restraining orders agent."""
        super().__init__(name="RestrainingOrdersAgent")
        self.client = Groq(api_key=settings.groq_api_key)
        self.prompt_template = self._load_prompt_template()
        
    def _load_prompt_template(self) -> str:
        """Load the restraining orders prompt template."""
        try:
            with open("/Users/arpanghoshal/loveandlaw-backend/prompts/restraining_orders_agent.prompt", "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading prompt: {e}")
            return ""
            
    def _define_schema_fields(self) -> Dict[str, LegalSchemaField]:
        """Define the schema fields for restraining orders."""
        return {
            "immediate_danger": LegalSchemaField(
                name="immediate_danger",
                field_type="boolean",
                required=True
            ),
            "role_in_case": LegalSchemaField(
                name="role_in_case",
                field_type="string",
                required=True,
                options=["Petitioner/Victim", "Respondent", "Protected Party", "Attorney", "Other"]
            ),
            "order_type_needed": LegalSchemaField(
                name="order_type_needed",
                field_type="string",
                required=True,
                options=["Emergency Protective Order", "Temporary Restraining Order", "Permanent Restraining Order", "Civil Harassment Order", "Workplace Violence Order", "Elder Abuse Order", "Not Sure"]
            ),
            "relationship_to_respondent": LegalSchemaField(
                name="relationship_to_respondent",
                field_type="string",
                required=True,
                options=["Spouse/Partner", "Ex-Spouse/Ex-Partner", "Dating/Dated", "Family Member", "Roommate", "Neighbor", "Co-worker", "Stranger", "Other"]
            ),
            "types_of_abuse": LegalSchemaField(
                name="types_of_abuse",
                field_type="array",
                required=True,
                options=["Physical Violence", "Threats", "Stalking", "Harassment", "Sexual Abuse", "Financial Abuse", "Emotional/Psychological", "Property Damage", "Cyber Harassment"]
            ),
            "most_recent_incident": LegalSchemaField(
                name="most_recent_incident",
                field_type="string",
                required=True,
                options=["Within 24 hours", "Within 1 week", "Within 1 month", "Within 6 months", "Over 6 months ago"]
            ),
            "police_report_filed": LegalSchemaField(
                name="police_report_filed",
                field_type="boolean",
                required=True
            ),
            "evidence_available": LegalSchemaField(
                name="evidence_available",
                field_type="array",
                required=False,
                options=["Photos of injuries", "Text messages", "Emails", "Voicemails", "Witness statements", "Medical records", "Police reports", "Security footage", "None"]
            ),
            "current_living_situation": LegalSchemaField(
                name="current_living_situation",
                field_type="string",
                required=True,
                options=["Still living together", "Separated - Safe location", "In shelter", "Staying with friends/family", "Homeless", "Other"]
            ),
            "minor_children_involved": LegalSchemaField(
                name="minor_children_involved",
                field_type="boolean",
                required=True
            ),
            "weapons_involved": LegalSchemaField(
                name="weapons_involved",
                field_type="boolean",
                required=True
            ),
            "existing_orders": LegalSchemaField(
                name="existing_orders",
                field_type="string",
                required=True,
                options=["No existing orders", "Active restraining order", "Expired order", "Criminal protective order", "Order in another state"]
            ),
            "court_hearing_scheduled": LegalSchemaField(
                name="court_hearing_scheduled",
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
            "immediate_danger",  # HIGHEST PRIORITY
            "role_in_case",
            "current_living_situation",
            "most_recent_incident",
            "types_of_abuse",
            "weapons_involved",
            "relationship_to_respondent",
            "order_type_needed",
            "minor_children_involved",
            "police_report_filed",
            "existing_orders",
            "evidence_available",
            "court_hearing_scheduled",
            "legal_representation",
            "urgency_factors"
        ]
        
    def get_schema_name(self) -> str:
        """Get the schema section name."""
        return "restraining_orders"
        
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the current state using Llama 4."""
        try:
            case_info = state.get("case_info", {})
            user_input = state.get("user_text", "")
            chat_history = state.get("chat_history", [])
            
            # Check if initial consultation
            if user_input == "START_SPECIALIZED_CONSULTATION":
                # Initialize restraining orders section if not exists
                if self.get_schema_name() not in case_info:
                    case_info[self.get_schema_name()] = {}
                    
                # Immediately ask about safety
                return {
                    "question": "I want to help ensure your safety. Are you currently in immediate danger?",
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
                    {"role": "system", "content": "You are a restraining order specialist with a safety-first approach. Follow the instructions carefully and respond ONLY with the JSON format specified."},
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
                order_info = result.get("extracted_info", {}).get("restraining_orders", {})
                
                # If immediate danger, set urgency
                if order_info.get("immediate_danger") is True:
                    result["urgent_action_needed"] = True
                    result["safety_resources"] = [
                        "Call 911 immediately if in danger",
                        "National Domestic Violence Hotline: 1-800-799-7233",
                        "Text START to 88788 for Crisis Text Line",
                        "Create a safety plan"
                    ]
                    if "urgency_factors" not in order_info:
                        order_info["urgency_factors"] = []
                    if "Immediate danger" not in order_info["urgency_factors"]:
                        order_info["urgency_factors"].append("Immediate danger")
                        
                # If weapons involved, set urgency
                if order_info.get("weapons_involved") is True:
                    if "urgency_factors" not in order_info:
                        order_info["urgency_factors"] = []
                    if "Weapons involved" not in order_info["urgency_factors"]:
                        order_info["urgency_factors"].append("Weapons involved")
                        
                # If recent incident, set urgency
                if order_info.get("most_recent_incident") in ["Within 24 hours", "Within 1 week"]:
                    if "urgency_factors" not in order_info:
                        order_info["urgency_factors"] = []
                    if "Recent incident" not in order_info["urgency_factors"]:
                        order_info["urgency_factors"].append("Recent incident")
                        
                return result
            else:
                logger.error("No valid response format found")
                return self._get_fallback_response(case_info)
                
        except Exception as e:
            logger.error(f"Error in RestrainingOrdersAgent: {str(e)}")
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
            "immediate_danger": f"Are {person_ref} currently in immediate danger?",
            "role_in_case": f"What is {person_ref}r role in seeking this restraining order? For example: 'Petitioner/Victim', 'Respondent', 'Protected Party', 'Attorney', 'Other'",
            "order_type_needed": f"What type of protective order do {person_ref} need? For example: 'Emergency Protective Order', 'Temporary Restraining Order', 'Permanent Restraining Order', 'Civil Harassment Order', 'Workplace Violence Order', 'Elder Abuse Order', 'Not Sure'",
            "relationship_to_respondent": f"What is {person_ref}r relationship to the person {person_ref} need protection from? For example: 'Spouse/Partner', 'Ex-Spouse/Ex-Partner', 'Dating/Dated', 'Family Member', 'Roommate', 'Neighbor', 'Co-worker', 'Stranger', 'Other'",
            "types_of_abuse": f"What types of abuse or harassment have occurred? You can select multiple: 'Physical Violence', 'Threats', 'Stalking', 'Harassment', 'Sexual Abuse', 'Financial Abuse', 'Emotional/Psychological', 'Property Damage', 'Cyber Harassment'",
            "most_recent_incident": f"When did the most recent incident occur? For example: 'Within 24 hours', 'Within 1 week', 'Within 1 month', 'Within 6 months', 'Over 6 months ago'",
            "police_report_filed": f"Have {person_ref} filed a police report?",
            "evidence_available": f"What evidence do {person_ref} have? You can select multiple: 'Photos of injuries', 'Text messages', 'Emails', 'Voicemails', 'Witness statements', 'Medical records', 'Police reports', 'Security footage', 'None'",
            "current_living_situation": f"What is {person_ref}r current living situation? For example: 'Still living together', 'Separated - Safe location', 'In shelter', 'Staying with friends/family', 'Homeless', 'Other'",
            "minor_children_involved": f"Are there minor children involved who need protection?",
            "weapons_involved": f"Have weapons been involved or threatened?",
            "existing_orders": f"Are there any existing protective orders? For example: 'No existing orders', 'Active restraining order', 'Expired order', 'Criminal protective order', 'Order in another state'",
            "court_hearing_scheduled": f"Is there a court hearing already scheduled?",
            "legal_representation": f"Do {person_ref} have an attorney for this restraining order matter?",
            "urgency_factors": f"Are there any other urgent safety concerns? (e.g., escalating violence, specific threats, upcoming contact)"
        }
        
        return questions.get(field_name, f"Could you provide information about {field_name}?")
        
    def _get_safety_resources(self) -> Dict[str, Any]:
        """Get safety resources for restraining order cases."""
        return {
            "hotlines": [
                {"name": "National Domestic Violence Hotline", "number": "1-800-799-7233"},
                {"name": "Crisis Text Line", "number": "Text START to 88788"},
                {"name": "Emergency Services", "number": "911"}
            ],
            "resources": [
                "Local domestic violence shelter",
                "Safety planning resources",
                "Legal aid organizations",
                "Victim advocacy services"
            ],
            "immediate_actions": [
                "Get to a safe location",
                "Call 911 if in immediate danger",
                "Document all incidents",
                "Save all evidence",
                "Consider emergency protective order"
            ]
        }