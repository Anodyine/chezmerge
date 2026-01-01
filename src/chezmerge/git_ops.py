import subprocess
import shutil
from pathlib import Path
from typing import Optional

class GitHandler:
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path.resolve()
        self.workspace = self.repo_path / ".merge_workspace"

    def run_git(self, args: list[str], cwd: Optional[Path] = None) -> str:
        """Executes a git command."""
        target_cwd = cwd if cwd else self.repo_path
        result = subprocess.run(
            ["git"] + args, 
            cwd=target_cwd, 
            capture_output=True, 
            text=True, 
            check=True
        )
        return result.stdout.strip()

    def is_initialized(self) -> bool:
        return (self.workspace / "base").exists() and (self.workspace / "latest").exists()

    def init_workspace(self, remote_url: str):
        """Sets up the .merge_workspace with base and latest submodules."""
        self.workspace.mkdir(exist_ok=True)
        
        # Ensure main repo is initialized
        if not (self.repo_path / ".git").exists():
            self.run_git(["init"])

        # We use git clones instead of submodules for the MVP to avoid 
        # complex submodule registration issues in the user's repo.
        # This keeps the workspace ephemeral.
        print(f"Cloning {remote_url} into workspace...")
        
        for name in ["base", "latest"]:
            target = self.workspace / name
            if target.exists():
                shutil.rmtree(target)
            self.run_git(["clone", remote_url, name], cwd=self.workspace)

    def fetch_latest(self):
        """Updates the 'latest' clone to the newest upstream commit."""
        self.run_git(["pull", "--rebase"], cwd=self.workspace / "latest")

    def get_head_rev(self, name: str) -> str:
        """Gets the HEAD SHA for one of the workspace clones."""
        return self.run_git(["rev-parse", "HEAD"], cwd=self.workspace / name)

    def get_file_content(self, source: str, path: str) -> str:
        """
        Reads file content. 
        source: 'base', 'latest', or 'local'
        """
        if source == 'local':
            p = self.repo_path / path
            return p.read_text() if p.exists() else ""
        
        # For base/latest, read from the clone
        repo_dir = self.workspace / source
        try:
            return self.run_git(["show", f"HEAD:{path}"], cwd=repo_dir)
        except subprocess.CalledProcessError:
            return ""

    def get_changed_files_between_clones(self, inner_path: str = "") -> list[str]:
        """
        Compares 'base' and 'latest' clones and returns changed filenames.
        Filters by inner_path if provided.
        """
        latest_cwd = self.workspace / "latest"
        base_cwd = self.workspace / "base"
        base_sha = self.run_git(["rev-parse", "HEAD"], cwd=base_cwd)
        
        try:
            # Diff HEAD against the base SHA
            # Note: This assumes 'latest' has the history.
            output = self.run_git(["diff", "--name-only", base_sha, "HEAD"], cwd=latest_cwd)
            files = [line.strip() for line in output.splitlines() if line.strip()]
            
            if inner_path:
                # Filter files that start with inner_path
                filtered = []
                for f in files:
                    if f.startswith(inner_path):
                        filtered.append(f)
                return filtered
            return files
        except subprocess.CalledProcessError:
            return []

    def update_base_pointer(self):
        """Fast-forwards base to match latest."""
        latest_sha = self.get_head_rev("latest")
        base_cwd = self.workspace / "base"
        self.run_git(["fetch", "origin"], cwd=base_cwd)
        self.run_git(["reset", "--hard", latest_sha], cwd=base_cwd)
