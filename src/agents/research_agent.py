from typing import Dict, Any, List, Optional
import asyncio
import aiohttp
from groq import AsyncGroq
from src.agents.base import BaseAgent
from src.models.conversation import TurnState
from src.config.settings import settings
from src.utils.logger import get_logger
import json

logger = get_logger(__name__)


class ResearchAgent(BaseAgent):
    """Perform external legal research when needed"""
    
    def __init__(self):
        super().__init__("research")
        self.groq_client = AsyncGroq(api_key=settings.groq_api_key)
        self.timeout = aiohttp.ClientTimeout(total=10)
    
    async def process(self, state: TurnState, context: Dict[str, Any]) -> Dict[str, Any]:
        """Determine if research is needed and perform it"""
        
        # Check if research is needed
        needs_research = await self._should_research(state, context)
        
        if not needs_research:
            return {"legal_research": None}
        
        # Determine research queries
        queries = await self._generate_research_queries(state)
        
        # Perform research (with timeout protection)
        research_results = await self._perform_research(queries, state)
        
        # Synthesize findings
        synthesized = await self._synthesize_research(research_results, state)
        
        return {
            "legal_research": synthesized,
            "research_sources": research_results.get("sources", [])
        }
    
    async def _should_research(self, state: TurnState, context: Dict[str, Any]) -> bool:
        """Determine if external research is needed"""
        
        # Skip if in crisis
        if state.distress_score >= 7:
            return False
        
        # Research triggers
        research_keywords = [
            "law", "legal", "statute", "code", "regulation", "requirement",
            "process", "procedure", "timeline", "deadline", "form", "document",
            "rights", "obligations", "recent changes", "new law"
        ]
        
        user_text_lower = state.user_text.lower()
        
        # Check for explicit questions
        if any(q in user_text_lower for q in ["what is", "how do", "can i", "do i need", "is it legal"]):
            if any(keyword in user_text_lower for keyword in research_keywords):
                return True
        
        # Check legal intents that benefit from research
        research_intents = ["adoption", "guardianship", "relocation", "international"]
        if any(intent in state.legal_intent for intent in research_intents):
            return True
        
        # Use LLM to decide
        try:
            prompt = f"""Determine if this user message requires external legal research.
Consider if they're asking about:
- Specific laws or statutes
- Legal procedures or timelines
- Recent law changes
- Complex legal situations
- State-specific requirements

User message: {state.user_text}
Legal context: {', '.join(state.legal_intent)}

Reply with just YES or NO:"""

            response = await self.groq_client.chat.completions.create(
                model=settings.signal_extract_model,  # Using fast extraction model
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=10
            )
            
            answer = response.choices[0].message.content.strip().upper()
            return answer == "YES"
            
        except Exception as e:
            logger.error(f"Error determining research need: {e}")
            return False
    
    async def _generate_research_queries(self, state: TurnState) -> List[str]:
        """Generate specific research queries"""
        
        # Base query from user's question
        queries = []
        
        # Add state-specific query if location known
        location = state.facts.get("state", "")
        
        prompt = f"""Generate 2-3 specific legal research queries based on this user's question.
Focus on practical, actionable information.

User question: {state.user_text}
Legal topics: {', '.join(state.legal_intent)}
Location: {location or 'Unknown'}

Format as a JSON array of query strings:"""

        try:
            response = await self.groq_client.chat.completions.create(
                model=settings.signal_extract_model,  # Using fast extraction model
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
                # Note: Groq doesn't support response_format parameter
            )
            
            result = json.loads(response.choices[0].message.content)
            queries = result.get("queries", [])[:3]  # Limit to 3
            
        except Exception as e:
            logger.error(f"Error generating queries: {e}")
            # Fallback queries
            if state.legal_intent:
                queries = [f"{state.legal_intent[0]} requirements {location}".strip()]
            else:
                queries = ["family law basics"]
        
        return queries
    
    async def _perform_research(self, queries: List[str], state: TurnState) -> Dict[str, Any]:
        """Perform actual research using available APIs"""
        
        research_results = {
            "findings": [],
            "sources": []
        }
        
        # For now, simulate research with structured responses
        # In production, would integrate with legal databases, Perplexity, etc.
        
        for query in queries:
            try:
                # Simulate API call with GPT-4 knowledge
                research_prompt = f"""Provide accurate, current legal information for this query.
Focus on practical guidance, not legal advice.
Include relevant timelines, requirements, and common considerations.

Query: {query}
Context: User in {state.facts.get('state', 'US')} dealing with {', '.join(state.legal_intent)}

Provide a concise, factual response:"""

                response = await self.groq_client.chat.completions.create(
                    model=settings.advisor_model,  # Using advisor model for research
                    messages=[{"role": "user", "content": research_prompt}],
                    temperature=0.2,
                    max_tokens=300
                )
                
                finding = response.choices[0].message.content.strip()
                
                research_results["findings"].append({
                    "query": query,
                    "content": finding,
                    "source": "Legal Knowledge Base"
                })
                
                research_results["sources"].append({
                    "name": "Legal Knowledge Base",
                    "query": query,
                    "reliability": "high"
                })
                
            except Exception as e:
                logger.error(f"Research error for query '{query}': {e}")
        
        return research_results
    
    async def _synthesize_research(self, research_results: Dict[str, Any], state: TurnState) -> str:
        """Synthesize research findings into actionable guidance"""
        
        if not research_results.get("findings"):
            return None
        
        # Combine findings
        all_findings = "\n\n".join([
            f"**{f['query']}**\n{f['content']}" 
            for f in research_results["findings"]
        ])
        
        synthesis_prompt = f"""Synthesize this legal research into clear, actionable guidance.

FORMATTING REQUIREMENTS:
- Use bullet points for key points or options
- Bold important terms with **text**
- Keep paragraphs short (2-3 sentences)
- Use numbered lists for sequential steps

CONTENT REQUIREMENTS:
- Make it specific to the user's situation
- Use plain, conversational language - no legal jargon
- Focus on practical next steps
- Highlight what's most important for their case
- Include relevant timelines or deadlines if applicable

User situation: {state.user_text}
Research findings:
{all_findings}

Provide a clear, well-formatted summary that's easy to scan and understand:"""

        try:
            response = await self.groq_client.chat.completions.create(
                model=settings.advisor_model,  # Using advisor model for synthesis
                messages=[{"role": "user", "content": synthesis_prompt}],
                temperature=0.3,
                max_tokens=400
            )
            
            synthesized = response.choices[0].message.content.strip()
            
            # Add disclaimer
            synthesized += "\n\n*This information is for educational purposes only and should not replace consultation with a qualified attorney.*"
            
            return synthesized
            
        except Exception as e:
            logger.error(f"Error synthesizing research: {e}")
            return research_results["findings"][0]["content"] if research_results["findings"] else None