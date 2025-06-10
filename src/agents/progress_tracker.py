"""
Progress Tracker Agent for Love & Law Backend
Tracks user milestones and schedules event-based check-ins
# TODO: This agent needs to be integrated with the Therapeutic Engine workflow
"""

import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

from .base import BaseAgent
from ..models.conversation import TurnState
from ..models.user import UserProfile
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MilestoneCategory(Enum):
    """Categories of legal milestones"""
    INFORMATION_GATHERING = "information_gathering"
    DOCUMENTATION = "documentation"
    FILING = "filing"
    LEGAL_PROCESS = "legal_process"
    RESOLUTION = "resolution"
    POST_RESOLUTION = "post_resolution"


@dataclass
class Milestone:
    """Represents a legal milestone"""
    id: str
    name: str
    category: MilestoneCategory
    description: str
    prerequisites: List[str] = None
    triggers: List[str] = None  # Keywords/facts that indicate milestone
    follow_up_days: Optional[int] = None  # Days until check-in
    
    def __post_init__(self):
        if self.prerequisites is None:
            self.prerequisites = []
        if self.triggers is None:
            self.triggers = []


# Milestone catalog for divorce proceedings
DIVORCE_MILESTONES = [
    # Information Gathering
    Milestone(
        id="initial_consultation",
        name="Initial Consultation Completed",
        category=MilestoneCategory.INFORMATION_GATHERING,
        description="User has discussed their situation and goals",
        triggers=["discussed situation", "shared story", "explained problem"],
        follow_up_days=3
    ),
    Milestone(
        id="financial_info_gathered",
        name="Financial Information Gathered",
        category=MilestoneCategory.INFORMATION_GATHERING,
        description="User has provided basic financial information",
        triggers=["income", "assets", "debts", "property", "finances"],
        follow_up_days=7
    ),
    Milestone(
        id="children_info_gathered",
        name="Children Information Gathered",
        category=MilestoneCategory.INFORMATION_GATHERING,
        description="User has provided information about children",
        triggers=["children", "custody", "child support", "parenting"],
        prerequisites=["initial_consultation"]
    ),
    
    # Documentation
    Milestone(
        id="documents_checklist_created",
        name="Documents Checklist Created",
        category=MilestoneCategory.DOCUMENTATION,
        description="User has received list of required documents",
        triggers=["what documents", "paperwork needed", "forms required"],
        prerequisites=["initial_consultation"],
        follow_up_days=5
    ),
    Milestone(
        id="key_documents_gathered",
        name="Key Documents Gathered",
        category=MilestoneCategory.DOCUMENTATION,
        description="User has gathered essential documents",
        triggers=["gathered documents", "have paperwork", "collected forms"],
        prerequisites=["documents_checklist_created"],
        follow_up_days=14
    ),
    
    # Filing
    Milestone(
        id="attorney_matched",
        name="Attorney Matched",
        category=MilestoneCategory.FILING,
        description="User has been matched with suitable attorneys",
        triggers=["lawyer matched", "attorney options", "legal representation"],
        prerequisites=["initial_consultation"],
        follow_up_days=3
    ),
    Milestone(
        id="attorney_contacted",
        name="Attorney Contacted",
        category=MilestoneCategory.FILING,
        description="User has contacted an attorney",
        triggers=["contacted lawyer", "spoke to attorney", "hired lawyer"],
        prerequisites=["attorney_matched"],
        follow_up_days=7
    ),
    Milestone(
        id="petition_filed",
        name="Petition Filed",
        category=MilestoneCategory.FILING,
        description="Divorce petition has been filed",
        triggers=["filed petition", "submitted papers", "filed for divorce"],
        prerequisites=["attorney_contacted", "key_documents_gathered"],
        follow_up_days=30
    ),
    
    # Legal Process
    Milestone(
        id="served_papers",
        name="Papers Served",
        category=MilestoneCategory.LEGAL_PROCESS,
        description="Spouse has been served divorce papers",
        triggers=["served papers", "spouse received", "papers delivered"],
        prerequisites=["petition_filed"],
        follow_up_days=21
    ),
    Milestone(
        id="temporary_orders",
        name="Temporary Orders Established",
        category=MilestoneCategory.LEGAL_PROCESS,
        description="Temporary custody/support orders in place",
        triggers=["temporary orders", "interim agreement", "temporary custody"],
        prerequisites=["petition_filed"],
        follow_up_days=30
    ),
    Milestone(
        id="mediation_scheduled",
        name="Mediation Scheduled",
        category=MilestoneCategory.LEGAL_PROCESS,
        description="Mediation session has been scheduled",
        triggers=["mediation scheduled", "mediation date", "mediator meeting"],
        prerequisites=["served_papers"],
        follow_up_days=14
    ),
    
    # Resolution
    Milestone(
        id="settlement_reached",
        name="Settlement Agreement Reached",
        category=MilestoneCategory.RESOLUTION,
        description="Parties have reached a settlement agreement",
        triggers=["settlement reached", "agreement made", "terms agreed"],
        prerequisites=["mediation_scheduled"],
        follow_up_days=30
    ),
    Milestone(
        id="final_decree",
        name="Final Decree Issued",
        category=MilestoneCategory.RESOLUTION,
        description="Divorce has been finalized by the court",
        triggers=["divorce final", "decree issued", "officially divorced"],
        prerequisites=["settlement_reached"],
        follow_up_days=90
    ),
    
    # Post-Resolution
    Milestone(
        id="post_divorce_checklist",
        name="Post-Divorce Checklist Completed",
        category=MilestoneCategory.POST_RESOLUTION,
        description="User has completed post-divorce tasks",
        triggers=["name change", "beneficiary update", "new accounts"],
        prerequisites=["final_decree"],
        follow_up_days=180
    ),
]

# Custody milestones
CUSTODY_MILESTONES = [
    Milestone(
        id="custody_info_gathered",
        name="Custody Information Gathered",
        category=MilestoneCategory.INFORMATION_GATHERING,
        description="Basic custody arrangement preferences collected",
        triggers=["custody type", "parenting schedule", "shared custody"],
        follow_up_days=3
    ),
    Milestone(
        id="parenting_plan_drafted",
        name="Parenting Plan Drafted",
        category=MilestoneCategory.DOCUMENTATION,
        description="Created detailed parenting plan",
        triggers=["parenting plan", "custody schedule", "visitation plan"],
        prerequisites=["custody_info_gathered"],
        follow_up_days=7
    ),
    Milestone(
        id="custody_petition_filed",
        name="Custody Petition Filed",
        category=MilestoneCategory.FILING,
        description="Filed custody petition with court",
        triggers=["filed custody", "custody petition", "custody papers"],
        prerequisites=["parenting_plan_drafted"],
        follow_up_days=30
    ),
]

# Child support milestones
CHILD_SUPPORT_MILESTONES = [
    Milestone(
        id="financial_disclosure_complete",
        name="Financial Disclosure Complete",
        category=MilestoneCategory.DOCUMENTATION,
        description="Completed financial disclosure forms",
        triggers=["income disclosed", "financial forms", "pay stubs submitted"],
        follow_up_days=7
    ),
    Milestone(
        id="support_calculation_done",
        name="Support Calculation Completed",
        category=MilestoneCategory.DOCUMENTATION,
        description="Child support amount calculated",
        triggers=["support calculated", "payment amount", "support formula"],
        prerequisites=["financial_disclosure_complete"],
        follow_up_days=3
    ),
    Milestone(
        id="support_order_filed",
        name="Support Order Filed",
        category=MilestoneCategory.FILING,
        description="Child support order filed with court",
        triggers=["support order", "filed for support", "support petition"],
        prerequisites=["support_calculation_done"],
        follow_up_days=30
    ),
]


class ProgressTracker(BaseAgent):
    """Tracks user progress through legal milestones and schedules check-ins"""
    
    def __init__(self):
        super().__init__(name="ProgressTracker")
        self.milestone_catalog = {
            "divorce": DIVORCE_MILESTONES,
            "custody": CUSTODY_MILESTONES,
            "child_support": CHILD_SUPPORT_MILESTONES,
        }
    
    async def process(self, turn_state: TurnState, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process turn to detect and update milestones"""
        try:
            # Extract necessary information from turn state
            user_id = turn_state.user_id
            legal_intent = turn_state.legal_intent
            case_info = turn_state.facts
            progress_markers = turn_state.progress_markers
            user_text = turn_state.user_text
            
            # Get user profile from context or create minimal one
            user_profile = context.get("user_profile", {})
            if not user_profile:
                user_profile = {
                    "milestones_completed": [],
                    "user_id": user_id
                }
            
            # Determine relevant milestone set based on legal intent
            relevant_milestones = self._get_relevant_milestones(legal_intent)
            
            # Detect newly completed milestones
            new_milestones = self._detect_milestones(
                turn_state, 
                user_profile,
                relevant_milestones
            )
            
            # Update progress markers and user profile
            updates = {}
            if new_milestones:
                updates = self._update_progress(
                    turn_state,
                    user_profile,
                    new_milestones
                )
                
                # Schedule check-ins for milestones with follow-up
                check_ins = self._schedule_check_ins(new_milestones)
                if check_ins:
                    updates["scheduled_check_ins"] = check_ins
            
            # Calculate overall progress
            progress_info = self._calculate_progress(
                user_profile,
                relevant_milestones
            )
            updates["progress_info"] = progress_info
            
            # Generate progress-based insights
            insights = self._generate_insights(
                user_profile,
                relevant_milestones,
                progress_info
            )
            if insights:
                updates["progress_insights"] = insights
            
            return updates
            
        except Exception as e:
            logger.error(f"ProgressTracker error: {str(e)}")
            return {}
    
    def _get_relevant_milestones(self, legal_intents: List[str]) -> List[Milestone]:
        """Get milestones relevant to user's legal situation"""
        milestones = []
        
        for intent in legal_intents:
            intent_lower = intent.lower()
            
            # Map intents to milestone sets
            if "divorce" in intent_lower:
                milestones.extend(self.milestone_catalog.get("divorce", []))
            elif "custody" in intent_lower:
                milestones.extend(self.milestone_catalog.get("custody", []))
            elif "child support" in intent_lower or "support" in intent_lower:
                milestones.extend(self.milestone_catalog.get("child_support", []))
        
        # Default to divorce milestones if no specific intent
        if not milestones and legal_intents:
            milestones = self.milestone_catalog.get("divorce", [])
        
        return milestones
    
    def _detect_milestones(
        self, 
        turn_state: TurnState, 
        user_profile: Dict[str, Any],
        relevant_milestones: List[Milestone]
    ) -> List[Milestone]:
        """Detect which milestones have been newly completed"""
        new_milestones = []
        
        # Get already completed milestones
        completed_ids = set(user_profile.get("milestones_completed", []))
        
        # Combine user text and facts for trigger detection
        user_text = turn_state.user_text.lower()
        facts = turn_state.facts
        facts_text = " ".join(str(v) for v in facts.values()).lower()
        
        # Also check case_info for relevant information
        case_info = getattr(turn_state, 'case_info', {})
        case_info_text = str(case_info).lower()
        
        full_context = f"{user_text} {facts_text} {case_info_text}"
        
        for milestone in relevant_milestones:
            # Skip if already completed
            if milestone.id in completed_ids:
                continue
            
            # Check prerequisites
            if milestone.prerequisites:
                if not all(prereq in completed_ids for prereq in milestone.prerequisites):
                    continue
            
            # Check triggers
            if milestone.triggers:
                if any(trigger.lower() in full_context for trigger in milestone.triggers):
                    new_milestones.append(milestone)
                    logger.info(f"Detected milestone: {milestone.name}")
        
        return new_milestones
    
    def _update_progress(
        self,
        turn_state: TurnState,
        user_profile: Dict[str, Any],
        new_milestones: List[Milestone]
    ) -> Dict[str, Any]:
        """Update progress markers and user profile"""
        updates = {}
        
        # Update progress markers in turn_state
        new_markers = [m.id for m in new_milestones]
        current_markers = turn_state.progress_markers
        turn_state.progress_markers = list(set(current_markers + new_markers))
        
        # Update milestones in user profile
        current_milestones = user_profile.get("milestones_completed", [])
        user_profile["milestones_completed"] = list(
            set(current_milestones + new_markers)
        )
        
        # Generate celebration messages for new milestones
        celebrations = []
        for milestone in new_milestones:
            celebrations.append({
                "type": "milestone_completed",
                "milestone": milestone.name,
                "category": milestone.category.value,
                "message": f"Great progress! You've completed: {milestone.name}"
            })
        
        updates["milestone_celebrations"] = celebrations
        updates["new_milestones"] = new_markers
        
        return updates
    
    def _schedule_check_ins(self, milestones: List[Milestone]) -> List[Dict[str, Any]]:
        """Schedule follow-up check-ins for milestones"""
        check_ins = []
        
        for milestone in milestones:
            if milestone.follow_up_days:
                check_in_date = datetime.now() + timedelta(days=milestone.follow_up_days)
                check_ins.append({
                    "milestone_id": milestone.id,
                    "milestone_name": milestone.name,
                    "check_in_date": check_in_date.isoformat(),
                    "days_until": milestone.follow_up_days,
                    "check_in_type": "milestone_follow_up",
                    "message": f"Check in on progress since {milestone.name}"
                })
        
        return check_ins
    
    def _calculate_progress(
        self,
        user_profile: Dict[str, Any],
        relevant_milestones: List[Milestone]
    ) -> Dict[str, Any]:
        """Calculate overall progress through legal journey"""
        if not relevant_milestones:
            return {"percentage": 0, "completed": 0, "total": 0}
        
        completed = len(user_profile.get("milestones_completed", []))
        total = len(relevant_milestones)
        percentage = int((completed / total) * 100) if total > 0 else 0
        
        # Calculate progress by category
        category_progress = {}
        for category in MilestoneCategory:
            category_milestones = [m for m in relevant_milestones if m.category == category]
            category_completed = sum(
                1 for m in category_milestones 
                if m.id in user_profile.get("milestones_completed", [])
            )
            if category_milestones:
                category_progress[category.value] = {
                    "completed": category_completed,
                    "total": len(category_milestones),
                    "percentage": int((category_completed / len(category_milestones)) * 100)
                }
        
        return {
            "percentage": percentage,
            "completed": completed,
            "total": total,
            "by_category": category_progress,
            "current_phase": self._determine_current_phase(user_profile, relevant_milestones)
        }
    
    def _determine_current_phase(
        self,
        user_profile: Dict[str, Any],
        relevant_milestones: List[Milestone]
    ) -> str:
        """Determine which phase user is currently in"""
        completed_ids = set(user_profile.get("milestones_completed", []))
        
        # Check phases in order
        for category in [
            MilestoneCategory.INFORMATION_GATHERING,
            MilestoneCategory.DOCUMENTATION,
            MilestoneCategory.FILING,
            MilestoneCategory.LEGAL_PROCESS,
            MilestoneCategory.RESOLUTION,
            MilestoneCategory.POST_RESOLUTION
        ]:
            category_milestones = [m for m in relevant_milestones if m.category == category]
            if category_milestones:
                # If any milestone in this category is not completed, this is current phase
                if not all(m.id in completed_ids for m in category_milestones):
                    return category.value
        
        return MilestoneCategory.POST_RESOLUTION.value
    
    def _generate_insights(
        self,
        user_profile: Dict[str, Any],
        relevant_milestones: List[Milestone],
        progress_info: Dict[str, Any]
    ) -> List[str]:
        """Generate insights about user's progress"""
        insights = []
        completed_ids = set(user_profile.get("milestones_completed", []))
        
        # Insight: Next steps
        next_milestones = self._get_next_available_milestones(
            completed_ids,
            relevant_milestones
        )
        if next_milestones:
            next_names = [m.name for m in next_milestones[:2]]  # Top 2
            insights.append(f"Next steps: {', '.join(next_names)}")
        
        # Insight: Phase progress
        current_phase = progress_info.get("current_phase", "")
        if current_phase and current_phase != MilestoneCategory.POST_RESOLUTION.value:
            phase_data = progress_info["by_category"].get(current_phase, {})
            if phase_data:
                insights.append(
                    f"You're {phase_data['percentage']}% through the {current_phase.replace('_', ' ')} phase"
                )
        
        # Insight: Overall journey
        if progress_info["percentage"] > 0:
            if progress_info["percentage"] < 25:
                insights.append("You're just getting started - take it one step at a time")
            elif progress_info["percentage"] < 50:
                insights.append("You're making good progress through the early stages")
            elif progress_info["percentage"] < 75:
                insights.append("You're over halfway through your legal journey")
            else:
                insights.append("You're in the final stages - stay strong!")
        
        return insights
    
    def _get_next_available_milestones(
        self,
        completed_ids: Set[str],
        relevant_milestones: List[Milestone]
    ) -> List[Milestone]:
        """Get milestones that are available to complete next"""
        available = []
        
        for milestone in relevant_milestones:
            # Skip if already completed
            if milestone.id in completed_ids:
                continue
            
            # Check if prerequisites are met
            if all(prereq in completed_ids for prereq in milestone.prerequisites):
                available.append(milestone)
        
        # Sort by category order
        category_order = {
            MilestoneCategory.INFORMATION_GATHERING: 0,
            MilestoneCategory.DOCUMENTATION: 1,
            MilestoneCategory.FILING: 2,
            MilestoneCategory.LEGAL_PROCESS: 3,
            MilestoneCategory.RESOLUTION: 4,
            MilestoneCategory.POST_RESOLUTION: 5,
        }
        
        available.sort(key=lambda m: category_order.get(m.category, 999))
        
        return available