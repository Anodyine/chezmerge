import shutil
from pathlib import Path
from .paths import chezmoify_path

def import_upstream(source_dir: Path, target_dir: Path, inner_path: str = ""):
    """
    Copies files from source_dir (upstream) to target_dir (local),
    applying chezmoi naming conventions.
    """
    print(f"Importing from {source_dir} to {target_dir}...")
    
    # Adjust source root if inner_path is used
    root = source_dir / inner_path if inner_path else source_dir
    
    if not root.exists():
        raise FileNotFoundError(f"Upstream path {root} does not exist")

    for item in root.rglob("*"):
        if item.is_file() and ".git" not in item.parts:
            # Get path relative to the root (e.g. .config/nvim/init.vim)
            rel_path = item.relative_to(root)
            
            # Convert to chezmoi path (e.g. dot_config/nvim/init.vim)
            chez_path = chezmoify_path(str(rel_path))
            
            dest = target_dir / chez_path
            
            # Create parent dirs
            dest.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy content
            shutil.copy2(item, dest)
            print(f"  Created: {chez_path}")
