import subprocess
from pathlib import Path
from typing import Optional

class GitHandler:
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path

    def run_git(self, args: list[str]) -> str:
        """Executes a git command in the repo context."""
        result = subprocess.run(
            ["git"] + args, 
            cwd=self.repo_path, 
            capture_output=True, 
            text=True, 
            check=True
        )
        return result.stdout.strip()

    def get_repo_root(self) -> Path:
        """Finds the root of the git repository."""
        out = self.run_git(["rev-parse", "--show-toplevel"])
        return Path(out)

    def ensure_submodules(self):
        """
        Ensures .merge_workspace/base and .merge_workspace/latest exist.
        This will eventually handle the `git submodule add` logic.
        """
        pass

    def get_file_content(self, revision: str, path: str) -> str:
        """
        Reads file content from a specific git revision (e.g., :base/file).
        """
        # Example: git show base:dot_zshrc
        try:
            return self.run_git(["show", f"{revision}:{path}"])
        except subprocess.CalledProcessError:
            return ""
