from pathlib import Path
from typing import Optional

# Prefixes used by chezmoi to modify file attributes
CHEZMOI_PREFIXES = [
    "private_", "executable_", "exact_", "symlink_", 
    "modify_", "create_", "empty_", "readonly_"
]

def normalize_path(path_str: str) -> str:
    """
    Converts a chezmoi source path (e.g. 'dot_config/private_foo') 
    to the target path (e.g. '.config/foo').
    """
    parts = Path(path_str).parts
    new_parts = []
    for part in parts:
        p = part
        
        # Handle .tmpl suffix
        if p.endswith(".tmpl"):
            p = p[:-5]

        # Iteratively strip prefixes
        while True:
            changed = False
            # Handle 'dot_' specifically as it maps to '.'
            if p.startswith("dot_"):
                p = "." + p[4:]
                changed = True
            
            for prefix in CHEZMOI_PREFIXES:
                if p.startswith(prefix):
                    p = p[len(prefix):]
                    changed = True
            
            if not changed:
                break
        new_parts.append(p)
    return str(Path(*new_parts))

def chezmoify_path(path_str: str) -> str:
    """
    Converts a standard path (e.g. '.config/foo') to a basic chezmoi source path 
    (e.g. 'dot_config/foo').
    Note: This is a basic implementation for the MVP import process.
    """
    parts = Path(path_str).parts
    new_parts = []
    for part in parts:
        if part.startswith("."):
            new_parts.append("dot_" + part[1:])
        else:
            new_parts.append(part)
    return str(Path(*new_parts))

def find_local_match(repo_root: Path, target_rel_path: str) -> Optional[Path]:
    """
    Scans the repo_root to find the local source file that generates the target_rel_path.
    """
    target_path = str(Path(target_rel_path))
    
    # Walk the local repository to find a matching path.
    for candidate in repo_root.rglob("*"):
        if not candidate.is_file():
            continue
        
        # Skip .git and .merge_workspace directories
        if ".git" in candidate.parts or ".merge_workspace" in candidate.parts:
            continue

        rel_candidate = candidate.relative_to(repo_root)
        normalized = normalize_path(str(rel_candidate))
        
        if normalized == target_path:
            return rel_candidate
            
    return None
