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

def chezmoify_path(
    path_str: str,
    executable: bool = False,
    private: bool = False,
    readonly: bool = False,
    symlink: bool = False,
) -> str:
    """
    Converts a standard path (e.g. '.config/foo') to a basic chezmoi source path 
    (e.g. 'dot_config/foo').
    Attribute prefixes are applied to the final path component in this order:
    private_ -> readonly_ -> executable_ -> symlink_.
    """
    parts = Path(path_str).parts
    new_parts = []
    for index, part in enumerate(parts):
        if part.startswith("."):
            mapped = "dot_" + part[1:]
        else:
            mapped = part

        if index == len(parts) - 1:
            # Avoid applying duplicate prefixes if source was already chezmoified.
            has_prefix = lambda p: mapped.startswith(p)
            # Prepending in reverse produces the canonical left-to-right order.
            if symlink and not has_prefix("symlink_"):
                mapped = "symlink_" + mapped
            if executable and not has_prefix("executable_"):
                mapped = "executable_" + mapped
            if readonly and not has_prefix("readonly_"):
                mapped = "readonly_" + mapped
            if private and not has_prefix("private_"):
                mapped = "private_" + mapped

        new_parts.append(mapped)
    return str(Path(*new_parts))

def find_local_match(repo_root: Path, target_rel_path: str) -> Optional[Path]:
    """
    Scans the repo_root to find the local source file that generates the target_rel_path.
    Prioritizes .tmpl files if multiple matches exist.
    """
    target_path = str(Path(target_rel_path))
    best_match = None
    
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
            # If we find a template, it is the preferred match. Return immediately.
            if candidate.name.endswith(".tmpl"):
                return rel_candidate
            
            # Otherwise, store it as a candidate and keep looking
            best_match = rel_candidate
            
    return best_match
