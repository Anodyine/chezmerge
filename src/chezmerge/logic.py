from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

class MergeScenario(Enum):
    ALREADY_SYNCED = auto()  # Yours == Theirs
    AUTO_UPDATE = auto()     # Yours == Base, Theirs != Base
    AUTO_KEEP = auto()       # Yours != Base, Theirs == Base
    CONFLICT = auto()        # Yours != Base, Theirs != Base
    AUTO_MERGEABLE = auto()  # Conflict resolved automatically by git
    TEMPLATE_DIVERGENCE = auto() # Template logic detected, requires manual review

@dataclass
class FileState:
    content: str
    path: str
    is_template: bool = False

class DecisionEngine:
    def analyze(self, base: FileState, theirs: FileState, ours: FileState, template: FileState) -> MergeScenario:
        """
        Determines the merge strategy based on the 4-way state.
        """
        # 1. Check for Template Safety
        if template.is_template:
            # If it's a template, we almost always want to show the UI 
            # unless the update is identical to what we already have.
            if ours.content == theirs.content:
                return MergeScenario.ALREADY_SYNCED
            return MergeScenario.TEMPLATE_DIVERGENCE

        # 2. Standard 3-way merge logic for raw files
        if ours.content == theirs.content:
            return MergeScenario.ALREADY_SYNCED
        
        if ours.content == base.content and theirs.content != base.content:
            return MergeScenario.AUTO_UPDATE
            
        if ours.content != base.content and theirs.content == base.content:
            return MergeScenario.AUTO_KEEP
            
        return MergeScenario.CONFLICT

@dataclass
class MergeItem:
    """Represents the complete merge state for a single file."""
    path: str
    base: FileState
    theirs: FileState
    ours: FileState
    template: FileState
    scenario: MergeScenario = MergeScenario.CONFLICT
