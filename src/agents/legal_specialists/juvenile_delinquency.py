"""Juvenile delinquency specialist agent."""

from typing import Dict, Any, Optional, List
from .base import LegalSpecialistAgent, LegalSchemaField
from ...utils.logger import setup_logger
from groq import Groq
import os
import re
import json

logger = setup_logger(__name__)


class JuvenileDelinquencyAgent(LegalSpecialistAgent):
    """Handles juvenile delinquency case information gathering."""
    
    def __init__(self):
        """Initialize the juvenile delinquency agent."""
        super().__init__()
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.prompt_template = self._load_prompt_template()
        
    def _load_prompt_template(self) -> str:
        """Load the juvenile delinquency prompt template."""
        try:
            with open("/Users/arpanghoshal/loveandlaw-backend/prompts/juvenile_delinquency_agent.prompt", "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading prompt: {e}")
            return ""
            
    def _define_schema_fields(self) -> Dict[str, LegalSchemaField]:
        """Define the schema fields for juvenile delinquency."""
        return {
            "role_in_case": LegalSchemaField(
                name="role_in_case",
                field_type="string",
                required=True,
                options=["Parent/Guardian", "Juvenile", "Relative", "Attorney", "Other"]
            ),
            "juvenile_age": LegalSchemaField(
                name="juvenile_age",
                field_type="integer",
                required=True
            ),
            "offense_type": LegalSchemaField(
                name="offense_type",
                field_type="array",
                required=True,
                options=["Status Offense", "Property Crime", "Drug Offense", "Violent Offense", "Theft", "Vandalism", "Assault", "Weapons Charge", "Traffic Violation", "School-Related", "Other"]
            ),
            "offense_severity": LegalSchemaField(
                name="offense_severity",
                field_type="string",
                required=True,
                options=["Minor Misdemeanor", "Misdemeanor", "Felony", "Unknown"]
            ),
            "arrest_status": LegalSchemaField(
                name="arrest_status",
                field_type="string",
                required=True,
                options=["Not Arrested", "Arrested and Released", "In Detention", "Released to Parents", "Citation Issued"]
            ),
            "prior_record": LegalSchemaField(
                name="prior_record",
                field_type="string",
                required=True,
                options=["No Prior Record", "Prior Warnings", "Prior Diversions", "Prior Adjudications", "Multiple Priors"]
            ),
            "school_status": LegalSchemaField(
                name="school_status",
                field_type="string",
                required=True,
                options=["Enrolled - Good Standing", "Enrolled - Academic Issues", "Enrolled - Behavioral Issues", "Suspended", "Expelled", "Dropped Out", "Graduated"]
            ),
            "court_status": LegalSchemaField(
                name="court_status",
                field_type="string",
                required=True,
                options=["Pre-Filing", "Charges Filed", "Arraignment Scheduled", "Pre-Trial", "Trial Scheduled", "Adjudicated", "Sentencing Phase", "Probation", "Case Closed"]
            ),
            "diversion_eligibility": LegalSchemaField(
                name="diversion_eligibility",
                field_type="string",
                required=True,
                options=["Likely Eligible", "Possibly Eligible", "Not Eligible", "Already in Diversion", "Unknown"]
            ),
            "parent_cooperation": LegalSchemaField(
                name="parent_cooperation",
                field_type="string",
                required=True,
                options=["Fully Cooperative", "Somewhat Cooperative", "Not Cooperative", "Parents Absent", "State Custody"]
            ),
            "substance_abuse_issues": LegalSchemaField(
                name="substance_abuse_issues",
                field_type="boolean",
                required=True
            ),
            "mental_health_concerns": LegalSchemaField(
                name="mental_health_concerns",
                field_type="boolean",
                required=True
            ),
            "legal_representation": LegalSchemaField(
                name="legal_representation",
                field_type="string",
                required=True,
                options=["Private Attorney", "Public Defender", "Court Appointed", "Seeking Attorney", "No Attorney Yet"]
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
            "juvenile_age",
            "arrest_status",  # Immediate concern
            "offense_type",
            "offense_severity",
            "court_status",
            "prior_record",
            "school_status",
            "parent_cooperation",
            "diversion_eligibility",
            "substance_abuse_issues",
            "mental_health_concerns",
            "legal_representation",
            "urgency_factors"
        ]
        
    def get_schema_name(self) -> str:
        """Get the schema section name."""
        return "juvenile_delinquency"
        
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the current state using Llama 4."""
        try:
            case_info = state.get("case_info", {})
            user_input = state.get("user_text", "")
            chat_history = state.get("chat_history", [])
            
            # Check if initial consultation
            if user_input == "START_SPECIALIZED_CONSULTATION":
                # Initialize juvenile delinquency section if not exists
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
                    {"role": "system", "content": "You are a juvenile delinquency specialist. Follow the instructions carefully and respond ONLY with the JSON format specified."},
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
                
                # Apply special handling for juvenile cases
                juvenile_info = result.get("extracted_info", {}).get("juvenile_delinquency", {})
                
                # If juvenile is in detention, set urgency
                if juvenile_info.get("arrest_status") == "In Detention":
                    if "urgency_factors" not in juvenile_info:
                        juvenile_info["urgency_factors"] = []
                    if "Juvenile in detention" not in juvenile_info["urgency_factors"]:
                        juvenile_info["urgency_factors"].append("Juvenile in detention")
                        
                # If serious felony charge
                if juvenile_info.get("offense_severity") == "Felony":
                    if "urgency_factors" not in juvenile_info:
                        juvenile_info["urgency_factors"] = []
                    if "Felony charges" not in juvenile_info["urgency_factors"]:
                        juvenile_info["urgency_factors"].append("Felony charges")
                        
                # If juvenile is very young (under 14)
                age = juvenile_info.get("juvenile_age")
                if age and age < 14:
                    if "urgency_factors" not in juvenile_info:
                        juvenile_info["urgency_factors"] = []
                    if "Very young juvenile" not in juvenile_info["urgency_factors"]:
                        juvenile_info["urgency_factors"].append("Very young juvenile")
                        
                return result
            else:
                logger.error("No valid response format found")
                return self._get_fallback_response(case_info)
                
        except Exception as e:
            logger.error(f"Error in JuvenileDelinquencyAgent: {str(e)}")
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
            "role_in_case": f"What is {person_ref}r role in this juvenile case? For example: 'Parent/Guardian', 'Juvenile', 'Relative', 'Attorney', 'Other'",
            "juvenile_age": f"What is the age of the juvenile involved in the case?",
            "offense_type": f"What type of offense(s) is the juvenile accused of? You can select multiple: 'Status Offense', 'Property Crime', 'Drug Offense', 'Violent Offense', 'Theft', 'Vandalism', 'Assault', 'Weapons Charge', 'Traffic Violation', 'School-Related', 'Other'",
            "offense_severity": f"How serious is the offense? For example: 'Minor Misdemeanor', 'Misdemeanor', 'Felony', 'Unknown'",
            "arrest_status": f"What is the current arrest/detention status? For example: 'Not Arrested', 'Arrested and Released', 'In Detention', 'Released to Parents', 'Citation Issued'",
            "prior_record": f"Does the juvenile have any prior record? For example: 'No Prior Record', 'Prior Warnings', 'Prior Diversions', 'Prior Adjudications', 'Multiple Priors'",
            "school_status": f"What is the juvenile's current school status? For example: 'Enrolled - Good Standing', 'Enrolled - Academic Issues', 'Enrolled - Behavioral Issues', 'Suspended', 'Expelled', 'Dropped Out', 'Graduated'",
            "court_status": f"What is the current status of the case in court? For example: 'Pre-Filing', 'Charges Filed', 'Arraignment Scheduled', 'Pre-Trial', 'Trial Scheduled', 'Adjudicated', 'Sentencing Phase', 'Probation', 'Case Closed'",
            "diversion_eligibility": f"Is the juvenile eligible for a diversion program? For example: 'Likely Eligible', 'Possibly Eligible', 'Not Eligible', 'Already in Diversion', 'Unknown'",
            "parent_cooperation": f"How cooperative are the parents/guardians? For example: 'Fully Cooperative', 'Somewhat Cooperative', 'Not Cooperative', 'Parents Absent', 'State Custody'",
            "substance_abuse_issues": f"Are there any substance abuse issues involved in this case?",
            "mental_health_concerns": f"Are there any mental health concerns that need to be addressed?",
            "legal_representation": f"What is the status of legal representation? For example: 'Private Attorney', 'Public Defender', 'Court Appointed', 'Seeking Attorney', 'No Attorney Yet'",
            "urgency_factors": f"Are there any urgent factors in the case? (e.g., upcoming court dates, detention hearings, school disciplinary proceedings)"
        }
        
        return questions.get(field_name, f"Could you provide information about {field_name}?")