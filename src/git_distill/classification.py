from typing import Set, List, Optional
from git_distill.models import DiscoveryResult, FileDivergence, FileClassification

def classify_files(
    discovery: DiscoveryResult,
    confirmed_authors: Optional[Set[str]] = None,
    unready_authors: Optional[Set[str]] = None,
    confirmed_files: Optional[Set[str]] = None,
    unready_files: Optional[Set[str]] = None,
) -> List[FileDivergence]:
    """
    Classifies files based on confirmed/unready authors and optional file-level overrides.
    - Pure Confirmed: touched ONLY by confirmed authors (or in confirmed_files)
    - Pure Unready: touched ONLY by unready authors (or in unready_files)
    - Mixed: touched by BOTH confirmed and unready authors
    """
    confirmed_auth = {a.strip().lower() for a in confirmed_authors} if confirmed_authors else set()
    unready_auth = {a.strip().lower() for a in unready_authors} if unready_authors else set()
    conf_files = {f.strip() for f in confirmed_files} if confirmed_files else set()
    unr_files = {f.strip() for f in unready_files} if unready_files else set()

    for file_div in discovery.files:
        # File-level direct overrides take precedence
        if file_div.path in conf_files:
            file_div.classification = FileClassification.PURE_CONFIRMED
            continue
        if file_div.path in unr_files:
            file_div.classification = FileClassification.PURE_UNREADY
            continue

        file_authors = {a.strip().lower() for a in file_div.authors}

        has_confirmed = bool(file_authors.intersection(confirmed_auth))
        has_unready = bool(file_authors.intersection(unready_auth))

        # If only confirmed is provided, non-confirmed authors are treated as unready
        if confirmed_auth and not unready_auth:
            non_confirmed = file_authors - confirmed_auth
            has_unready = bool(non_confirmed)

        # If only unready is provided, non-unready authors are treated as confirmed
        elif unready_auth and not confirmed_auth:
            non_unready = file_authors - unready_auth
            has_confirmed = bool(non_unready)

        if has_confirmed and has_unready:
            file_div.classification = FileClassification.MIXED
        elif has_confirmed and not has_unready:
            file_div.classification = FileClassification.PURE_CONFIRMED
        elif has_unready and not has_confirmed:
            file_div.classification = FileClassification.PURE_UNREADY
        else:
            # Fallback when no author lists are provided
            if file_div.is_multi_author:
                file_div.classification = FileClassification.MIXED
            else:
                file_div.classification = FileClassification.UNKNOWN

    return discovery.files
