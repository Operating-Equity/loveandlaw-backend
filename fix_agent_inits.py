#!/usr/bin/env python3
"""Fix all agent init calls to include name parameter"""

import os
import re

# Define the mapping of files to class names
agent_files = {
    "src/agents/reflection_agent.py": "ReflectionAgent",
    "src/agents/legal_specialists/family_law.py": "FamilyLawAgent",
    "src/agents/legal_specialists/child_custody.py": "ChildCustodyAgent",
    "src/agents/legal_specialists/guardianship.py": "GuardianshipAgent",
    "src/agents/legal_specialists/divorce_separation.py": "DivorceAndSeparationAgent",
    "src/agents/legal_specialists/domestic_violence.py": "DomesticViolenceAgent",
    "src/agents/legal_specialists/case_general.py": "CaseGeneralAgent",
    "src/agents/legal_specialists/adoption.py": "AdoptionAgent",
    "src/agents/legal_specialists/restraining_orders.py": "RestrainingOrdersAgent",
    "src/agents/legal_specialists/paternity_practice.py": "PaternityPracticeAgent",
    "src/agents/legal_specialists/child_abuse.py": "ChildAbuseAgent",
    "src/agents/legal_specialists/spousal_support.py": "SpousalSupportAgent",
    "src/agents/legal_specialists/property_division.py": "PropertyDivisionAgent",
    "src/agents/legal_specialists/child_support.py": "ChildSupportAgent",
    "src/agents/legal_specialists/base.py": "LegalSpecialistAgent",
    "src/agents/legal_specialists/juvenile_delinquency.py": "JuvenileDelinquencyAgent"
}

for filepath, class_name in agent_files.items():
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Replace super().__init__() with super().__init__(name="ClassName")
        new_content = content.replace(
            "super().__init__()",
            f'super().__init__(name="{class_name}")'
        )
        
        if new_content != content:
            with open(filepath, 'w') as f:
                f.write(new_content)
            print(f"Fixed: {filepath}")
        else:
            print(f"Already fixed or not found: {filepath}")
    else:
        print(f"File not found: {filepath}")

print("Done!")