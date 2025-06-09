"""Base class for legal specialist agents."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel
from ...utils.logger import get_logger
from ..base import BaseAgent

logger = get_logger(__name__)


class LegalSchemaField(BaseModel):
    """Definition of a legal schema field."""
    name: str
    field_type: str  # boolean, string, integer, array
    required: bool = True
    options: Optional[List[str]] = None
    depends_on: Optional[Dict[str, Any]] = None  # Field dependencies
    auto_populate: Optional[Dict[str, Any]] = None  # Auto-population rules


class LegalSpecialistAgent(BaseAgent, ABC):
    """Base class for all legal specialist agents."""
    
    def __init__(self, name: str = "LegalSpecialistAgent"):
        """Initialize the legal specialist agent."""
        super().__init__(name=name)
        self.schema_fields = self._define_schema_fields()
        self.priority_order = self._define_priority_order()
        self.state = "initial_analysis"
        
    @abstractmethod
    def _define_schema_fields(self) -> Dict[str, LegalSchemaField]:
        """Define the schema fields for this specialist."""
        pass
        
    @abstractmethod
    def _define_priority_order(self) -> List[str]:
        """Define the order in which fields should be collected."""
        pass
        
    @abstractmethod
    def get_schema_name(self) -> str:
        """Get the name of the schema section (e.g., 'divorce_and_separation')."""
        pass
        
    def _load_prompt_template(self) -> str:
        """Load the prompt template for this specialist."""
        # This would load from the prompts directory
        # For now, return empty string as prompts are loaded dynamically
        return ""
        
    def _extract_from_user_input(self, user_input: str, case_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract information from user input."""
        extracted = {}
        
        # Handle yes/no responses
        if user_input.lower() in ["yes", "yeah", "yep", "y"]:
            extracted["_last_response"] = True
        elif user_input.lower() in ["no", "nope", "nah", "n"]:
            extracted["_last_response"] = False
            
        # Handle indifference
        indifference_patterns = [
            "don't care", "dont care", "whatever", 
            "don't mind", "dont mind", "doesn't matter",
            "doesnt matter", "not sure", "unsure",
            "up to you", "you decide", "any option"
        ]
        if any(pattern in user_input.lower() for pattern in indifference_patterns):
            extracted["_is_indifferent"] = True
            
        return extracted
        
    def _get_missing_fields(self, case_info: Dict[str, Any]) -> List[str]:
        """Get list of missing required fields."""
        schema_data = case_info.get(self.get_schema_name(), {})
        missing = []
        
        for field_name, field_def in self.schema_fields.items():
            if not field_def.required:
                continue
                
            # Check dependencies
            if field_def.depends_on:
                should_skip = False
                for dep_field, dep_value in field_def.depends_on.items():
                    if schema_data.get(dep_field) != dep_value:
                        should_skip = True
                        break
                if should_skip:
                    continue
                    
            # Check if field is missing
            if field_name not in schema_data or schema_data[field_name] is None:
                missing.append(field_name)
                
        return missing
        
    def _apply_auto_population(self, case_info: Dict[str, Any]) -> Dict[str, Any]:
        """Apply auto-population rules to fields."""
        schema_data = case_info.get(self.get_schema_name(), {})
        
        for field_name, field_def in self.schema_fields.items():
            if field_def.auto_populate and field_name not in schema_data:
                for condition_field, condition_value in field_def.auto_populate.items():
                    if schema_data.get(condition_field) == condition_value:
                        # Apply the auto-population rule
                        if "set_value" in field_def.auto_populate:
                            schema_data[field_name] = field_def.auto_populate["set_value"]
                            
        return schema_data
        
    def _get_next_question(self, case_info: Dict[str, Any]) -> Optional[str]:
        """Get the next question to ask based on missing fields."""
        missing_fields = self._get_missing_fields(case_info)
        
        if not missing_fields:
            return None
            
        # Get the highest priority missing field
        for field_name in self.priority_order:
            if field_name in missing_fields:
                return field_name
                
        # If we have missing fields not in priority order, return the first one
        return missing_fields[0] if missing_fields else None
        
    def _validate_response(self, field_name: str, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate a response for a specific field."""
        field_def = self.schema_fields.get(field_name)
        if not field_def:
            return False, f"Unknown field: {field_name}"
            
        # Type validation
        if field_def.field_type == "boolean" and not isinstance(value, bool):
            return False, "Please respond with Yes or No"
            
        if field_def.field_type == "string" and field_def.options:
            if value not in field_def.options:
                return False, f"Please choose from: {', '.join(field_def.options)}"
                
        return True, None
        
    def _format_question(self, field_name: str, case_info: Dict[str, Any]) -> str:
        """Format a question for a specific field."""
        # This would be implemented by each specialist based on their prompt template
        # For now, return a generic question
        return f"Please provide information for {field_name}"
        
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the current state and generate a response."""
        try:
            case_info = state.get("case_info", {})
            user_input = state.get("user_text", "")
            chat_history = state.get("chat_history", [])
            
            # Extract information from user input
            extracted = self._extract_from_user_input(user_input, case_info)
            
            # Check if user is indifferent
            if extracted.get("_is_indifferent"):
                return self._handle_indifference(state)
                
            # Apply auto-population rules
            schema_data = self._apply_auto_population(case_info)
            
            # Get next missing field
            next_field = self._get_next_question(case_info)
            
            if not next_field:
                # All fields collected
                return {
                    "question": None,
                    "current_state": "completed",
                    "extracted_info": {
                        self.get_schema_name(): schema_data
                    }
                }
                
            # Format the question for the next field
            question = self._format_question(next_field, case_info)
            
            return {
                "question": question,
                "current_state": "question_asked",
                "extracted_info": {
                    self.get_schema_name(): schema_data
                }
            }
            
        except Exception as e:
            logger.error(f"Error in {self.__class__.__name__}: {str(e)}")
            return {
                "question": "I apologize, but I encountered an error. Could you please repeat your last response?",
                "current_state": "error",
                "extracted_info": {}
            }
            
    def _handle_indifference(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle indifferent user responses."""
        # This would be customized by each specialist
        return {
            "question": "I understand this might be difficult. Your input helps ensure we find the right attorney for your needs. Could you please provide your preference?",
            "current_state": "question_asked", 
            "extracted_info": state.get("case_info", {}).get(self.get_schema_name(), {})
        }