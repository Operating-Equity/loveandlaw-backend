import re
from typing import Dict, List, Tuple, Optional
from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from groq import AsyncGroq
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PIIRedactionService:
    def __init__(self):
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        self.groq_client = AsyncGroq(api_key=settings.groq_api_key)
        
        # Add custom recognizers for legal-specific PII
        self._add_custom_recognizers()
        
        # Common PII patterns to check
        self.pii_entities = [
            "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "US_SSN",
            "CREDIT_CARD", "US_DRIVER_LICENSE", "LOCATION",
            "DATE_TIME", "MEDICAL_LICENSE", "US_PASSPORT",
            "CASE_NUMBER", "COURT_NAME"  # Custom legal entities
        ]
    
    def _add_custom_recognizers(self):
        """Add custom recognizers for legal-specific PII"""
        
        # Case number pattern
        case_number_pattern = Pattern(
            name="case_number_pattern",
            regex=r"\b\d{2,4}-[A-Z]{2,4}-\d{3,6}\b",
            score=0.8
        )
        case_number_recognizer = PatternRecognizer(
            supported_entity="CASE_NUMBER",
            patterns=[case_number_pattern]
        )
        
        # Court name pattern
        court_patterns = [
            Pattern(name="court_pattern", regex=r"\b(?:Superior|District|Circuit|Family|Probate|Federal)\s+Court\b", score=0.7),
            Pattern(name="court_of_pattern", regex=r"\bCourt of [\w\s]+\b", score=0.7)
        ]
        court_recognizer = PatternRecognizer(
            supported_entity="COURT_NAME",
            patterns=court_patterns
        )
        
        # Add recognizers to analyzer
        self.analyzer.registry.add_recognizer(case_number_recognizer)
        self.analyzer.registry.add_recognizer(court_recognizer)
    
    async def redact_text(self, text: str) -> Tuple[str, Dict[str, List[str]]]:
        """
        Redact PII from text and return redacted text with found entities
        
        Returns:
            Tuple of (redacted_text, found_entities_dict)
        """
        try:
            # Analyze text for PII
            results = self.analyzer.analyze(
                text=text,
                entities=self.pii_entities,
                language='en'
            )
            
            # Group entities by type
            found_entities = {}
            for result in results:
                entity_type = result.entity_type
                entity_text = text[result.start:result.end]
                
                if entity_type not in found_entities:
                    found_entities[entity_type] = []
                found_entities[entity_type].append(entity_text)
            
            # Anonymize the text
            anonymized_result = self.anonymizer.anonymize(
                text=text,
                analyzer_results=results,
                operators={
                    "DEFAULT": OperatorConfig("replace", {"new_value": "[REDACTED]"}),
                    "PERSON": OperatorConfig("replace", {"new_value": "[NAME]"}),
                    "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[EMAIL]"}),
                    "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "[PHONE]"}),
                    "LOCATION": OperatorConfig("replace", {"new_value": "[LOCATION]"}),
                    "CASE_NUMBER": OperatorConfig("replace", {"new_value": "[CASE_NUMBER]"}),
                    "COURT_NAME": OperatorConfig("replace", {"new_value": "[COURT]"})
                }
            )
            
            return anonymized_result.text, found_entities
            
        except Exception as e:
            logger.error(f"Error in PII redaction: {e}")
            # Return original text if redaction fails
            return text, {}
    
    async def redact_with_llm(self, text: str) -> Tuple[str, Dict[str, List[str]]]:
        """
        Use Groq LLM for additional context-aware PII detection
        """
        try:
            prompt = f"""Identify and redact personal information in this text. 
Replace:
- Names with [NAME]
- Emails with [EMAIL]
- Phone numbers with [PHONE]
- Addresses with [ADDRESS]
- SSN with [SSN]
- Case numbers with [CASE_NUMBER]
- Court names with [COURT]
- Dates with [DATE]

Text: {text}

Return ONLY the redacted text, nothing else."""

            response = await self.groq_client.chat.completions.create(
                model=settings.safety_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=1000
            )
            
            redacted_text = response.choices[0].message.content.strip()
            
            # Extract what was redacted by comparing
            found_entities = self._extract_redacted_entities(text, redacted_text)
            
            return redacted_text, found_entities
            
        except Exception as e:
            logger.error(f"Error in LLM-based PII redaction: {e}")
            # Fall back to rule-based redaction
            return await self.redact_text(text)
    
    def _extract_redacted_entities(self, original: str, redacted: str) -> Dict[str, List[str]]:
        """Extract what entities were redacted by comparing texts"""
        entities = {}
        
        # Simple pattern matching to find redacted placeholders
        patterns = {
            "PERSON": r"\[NAME\]",
            "EMAIL_ADDRESS": r"\[EMAIL\]",
            "PHONE_NUMBER": r"\[PHONE\]",
            "LOCATION": r"\[ADDRESS\]|\[LOCATION\]",
            "US_SSN": r"\[SSN\]",
            "CASE_NUMBER": r"\[CASE_NUMBER\]",
            "COURT_NAME": r"\[COURT\]",
            "DATE_TIME": r"\[DATE\]"
        }
        
        for entity_type, pattern in patterns.items():
            if re.search(pattern, redacted):
                if entity_type not in entities:
                    entities[entity_type] = ["[REDACTED]"]  # Placeholder since we don't have original values
        
        return entities
    
    def mask_for_storage(self, text: str, entities: Dict[str, List[str]]) -> str:
        """
        Create a version of text suitable for storage with partial masking
        For example, show only last 4 digits of phone numbers
        """
        masked_text = text
        
        # Custom masking rules for different entity types
        if "PHONE_NUMBER" in entities:
            for phone in entities["PHONE_NUMBER"]:
                if len(phone) >= 4:
                    masked_phone = "***-***-" + phone[-4:]
                    masked_text = masked_text.replace(phone, masked_phone)
        
        if "EMAIL_ADDRESS" in entities:
            for email in entities["EMAIL_ADDRESS"]:
                if "@" in email:
                    parts = email.split("@")
                    if len(parts[0]) > 2:
                        masked_email = parts[0][:2] + "***@" + parts[1]
                        masked_text = masked_text.replace(email, masked_email)
        
        return masked_text


# Global instance
pii_service = PIIRedactionService()