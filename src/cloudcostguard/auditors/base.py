"""
Base Auditor interface and WasteItem representation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class WasteItem:
    resource_id: str
    resource_type: str              # e.g., "EBS Volume", "Elastic IP", "EC2 Instance", "Snapshot", "Load Balancer"
    region: str
    name: str = "N/A"
    status: str = "Idle"
    details: str = ""
    age_days: Optional[int] = None
    estimated_monthly_waste: float = 0.0
    recommendation: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    action_taken: str = "Audit Only"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "region": self.region,
            "name": self.name,
            "status": self.status,
            "details": self.details,
            "age_days": self.age_days,
            "estimated_monthly_waste": self.estimated_monthly_waste,
            "recommendation": self.recommendation,
            "tags": self.tags,
            "action_taken": self.action_taken,
        }


class BaseAuditor(ABC):
    """Abstract base class for all resource auditors."""

    def __init__(self, session=None, config=None):
        self.session = session
        self.config = config

    @abstractmethod
    def audit(self, region: str) -> List[WasteItem]:
        """Audit a specific AWS region and return a list of wasted resources."""
        pass

    @abstractmethod
    def mock_audit(self, region: str) -> List[WasteItem]:
        """Generate realistic synthetic waste findings for demo and testing without AWS credentials."""
        pass
