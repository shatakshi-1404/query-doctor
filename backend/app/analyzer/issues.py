from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Issue:
    rule_id: str                 # stable machine-readable name, e.g. "LARGE_SEQ_SCAN"
    title: str                   # short heading shown in the UI
    severity: Severity
    node_type: str               # plan node that triggered it
    relation_name: str | None    # table involved, if any
    what_happened: str
    why_it_matters: str
    what_to_investigate: str
    metrics: dict[str, Any] = field(default_factory=dict)  # numbers that back up the claim
