"""
Response formatting utilities for consistent, readable AI responses
"""
import re
from typing import List, Dict, Any

def format_response(text: str) -> str:
    """
    Apply consistent formatting to AI responses
    """
    # Ensure proper paragraph spacing
    text = re.sub(r'\n{3,}', '\n\n', text)  # Replace multiple newlines with double
    
    # Ensure bullet points are properly formatted
    text = re.sub(r'^[-*]\s+', '• ', text, flags=re.MULTILINE)
    
    # Ensure numbered lists are properly formatted
    text = re.sub(r'^(\d+)\.\s*', r'\1. ', text, flags=re.MULTILINE)
    
    # Trim whitespace
    text = text.strip()
    
    return text

def create_formatted_list(items: List[str], ordered: bool = False) -> str:
    """
    Create a properly formatted list
    """
    if not items:
        return ""
    
    if ordered:
        return "\n".join([f"{i+1}. {item}" for i, item in enumerate(items)])
    else:
        return "\n".join([f"• {item}" for item in items])

def highlight_important_terms(text: str, terms: List[str]) -> str:
    """
    Bold important terms in the text
    """
    for term in terms:
        # Case-insensitive replacement
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        text = pattern.sub(f"**{term}**", text)
    
    return text

def create_section(title: str, content: str) -> str:
    """
    Create a formatted section with title
    """
    return f"**{title}**\n{content}"

def format_legal_steps(steps: List[Dict[str, str]]) -> str:
    """
    Format legal process steps in a clear, scannable way
    
    Args:
        steps: List of dicts with 'title' and 'description' keys
    """
    formatted_steps = []
    
    for i, step in enumerate(steps, 1):
        title = step.get('title', f'Step {i}')
        description = step.get('description', '')
        formatted_steps.append(f"{i}. **{title}**\n   {description}")
    
    return "\n\n".join(formatted_steps)

def format_options(options: List[Dict[str, str]]) -> str:
    """
    Format multiple options for user choice
    
    Args:
        options: List of dicts with 'title' and 'description' keys
    """
    formatted_options = []
    
    for option in options:
        title = option.get('title', '')
        description = option.get('description', '')
        if description:
            formatted_options.append(f"• **{title}**: {description}")
        else:
            formatted_options.append(f"• **{title}**")
    
    return "\n".join(formatted_options)

def ensure_readable_length(text: str, max_paragraphs: int = 4) -> str:
    """
    Ensure response isn't too long by limiting paragraphs
    """
    paragraphs = text.split('\n\n')
    
    if len(paragraphs) > max_paragraphs:
        # Keep first max_paragraphs-1 and add a summary
        kept_paragraphs = paragraphs[:max_paragraphs-1]
        kept_paragraphs.append("*[Response condensed for readability]*")
        return '\n\n'.join(kept_paragraphs)
    
    return text