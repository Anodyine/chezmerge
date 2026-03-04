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
        if ".git" in item.parts:
            continue
        if not (item.is_file() or item.is_symlink()):
            continue

        # Get path relative to the root (e.g. .config/nvim/init.vim)
        rel_path = item.relative_to(root)

        # Match chezmoi add/import attribute naming rules as closely as possible.
        # - executable_: any execute bit set
        # - private_: no group/other bits set
        # - readonly_: owner write bit not set
        # - symlink_: symlink target tracked as file content
        mode = item.lstat().st_mode
        is_symlink = item.is_symlink()
        is_executable = (mode & 0o111) != 0 and not is_symlink
        is_private = (mode & 0o077) == 0 and not is_symlink
        is_readonly = (mode & 0o200) == 0 and not is_symlink
        chez_path = chezmoify_path(
            str(rel_path),
            executable=is_executable,
            private=is_private,
            readonly=is_readonly,
            symlink=is_symlink,
        )
        
        # Check if a template version already exists locally
        # If so, we skip importing the raw file to avoid ambiguity
        dest_tmpl = target_dir / (chez_path + ".tmpl")
        if dest_tmpl.exists():
            print(f"  Skipping {chez_path} (Template exists: {dest_tmpl.name})")
            continue

        dest = target_dir / chez_path
        
        # Create parent dirs
        dest.parent.mkdir(parents=True, exist_ok=True)

        if is_symlink:
            # Chezmoi stores symlink targets as file contents.
            target = item.readlink()
            dest.write_text(f"{target}\n")
        else:
            # Copy content and metadata.
            shutil.copy2(item, dest)
        print(f"  Created: {chez_path}")
