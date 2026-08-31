from dataclasses import dataclass, field
from typing import List, Set, Optional, Dict, Any
from enum import Enum

class FileClassification(str, Enum):
    PURE_CONFIRMED = "Pure Confirmed"
    PURE_UNREADY = "Pure Unready"
    MIXED = "Mixed (Requires Review)"
    UNKNOWN = "Unclassified"

@dataclass
class UnmergedCommit:
    sha: str
    author: str
    email: str
    timestamp: int
    message: str
    files: List[str] = field(default_factory=list)

@dataclass
class FileDivergence:
    path: str
    insertions: int
    deletions: int
    authors: Set[str] = field(default_factory=set)
    commits: List[str] = field(default_factory=list)
    classification: FileClassification = FileClassification.UNKNOWN

    @property
    def is_multi_author(self) -> bool:
        return len(self.authors) > 1

@dataclass
class DiscoveryResult:
    current_branch: str
    prod_branch: str
    merge_base: str
    commits: List[UnmergedCommit] = field(default_factory=list)
    files: List[FileDivergence] = field(default_factory=list)
    author_map: Dict[str, List[str]] = field(default_factory=dict)
    author_files_map: Dict[str, Set[str]] = field(default_factory=dict)

@dataclass
class AuditContext:
    branch: str
    prod_branch: str
    backup_branch: Optional[str]
    commit_sha: Optional[str]
    confirmed_authors: Set[str] = field(default_factory=set)
    unready_authors: Set[str] = field(default_factory=set)
    pure_reverted_files: List[str] = field(default_factory=list)
    mixed_resolved_files: List[str] = field(default_factory=list)

    @property
    def total_restored(self) -> int:
        return len(self.pure_reverted_files) + len(self.mixed_resolved_files)
