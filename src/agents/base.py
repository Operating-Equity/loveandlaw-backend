from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from src.models.conversation import TurnState
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BaseAgent(ABC):
    """Base class for all agents in the Therapeutic Engine"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = get_logger(f"agent.{name}")
    
    @abstractmethod
    async def process(self, state: TurnState, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the current turn state and return updates
        
        Args:
            state: Current turn state
            context: Additional context (user profile, conversation history, etc.)
            
        Returns:
            Dictionary of state updates
        """
        pass
    
    async def __call__(self, state: TurnState, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make agent callable"""
        context = context or {}
        self.logger.info(f"Processing turn {state.turn_id}")
        
        try:
            result = await self.process(state, context)
            self.logger.info(f"Completed processing turn {state.turn_id}")
            return result
        except Exception as e:
            self.logger.error(f"Error processing turn {state.turn_id}: {e}")
            raise