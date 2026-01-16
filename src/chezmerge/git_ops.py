import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import Optional

class GitHandler:
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path.resolve()
        self.upstream_path = self.repo_path / ".chezmerge-upstream"

    def run_git(self, args: list[str], cwd: Optional[Path] = None, strip: bool = True) -> str:
        """Executes a git command."""
        target_cwd = cwd if cwd else self.repo_path
        try:
            result = subprocess.run(
                ["git"] + args, 
                cwd=target_cwd, 
                capture_output=True, 
                text=True, 
                check=True
            )
            return result.stdout.strip() if strip else result.stdout
        except subprocess.CalledProcessError as e:
            print(f"Git command failed: git {' '.join(args)}")
            print(f"CWD: {target_cwd}")
            print(f"Error: {e.stderr}")
            raise

    def is_initialized(self) -> bool:
        """Checks if the upstream submodule is initialized."""
        return (self.upstream_path / ".git").exists()

    def init_workspace(self, remote_url: str):
        """Sets up the .chezmerge-upstream submodule."""
        # Ensure main repo is initialized
        if not (self.repo_path / ".git").exists():
            self.run_git(["init"])
        
        print(f"Adding submodule {remote_url}...")
        rel_path = str(self.upstream_path.relative_to(self.repo_path))
        
        # Use -c protocol.file.allow=always to bypass security restriction for local paths during clone
        self.run_git(["-c", "protocol.file.allow=always", "submodule", "add", remote_url, rel_path])

        # Configure the submodule to allow file protocol for future fetches
        self.run_git(["config", "protocol.file.allow", "always"], cwd=self.upstream_path)

    def fetch_latest(self):
        """Updates the submodule's remote tracking branch."""
        self.run_git(["fetch", "origin"], cwd=self.upstream_path)

    def get_head_rev(self, ref: str = "HEAD") -> str:
        """Gets the SHA for a ref in the submodule."""
        return self.run_git(["rev-parse", ref], cwd=self.upstream_path)

    def get_file_content(self, source: str, path: str) -> str:
        """
        Reads file content. 
        source: 'base', 'latest', or 'local'
        """
        if source == 'local':
            p = self.repo_path / path
            return p.read_text() if p.exists() else ""
        
        # For base/latest, read from the submodule
        # 'base' is the currently checked out commit in the submodule
        # 'latest' is the remote HEAD
        ref = "HEAD" if source == "base" else "origin/HEAD"
        try:
            return self.run_git(["show", f"{ref}:{path}"], cwd=self.upstream_path, strip=False)
        except subprocess.CalledProcessError:
            return ""

    def get_upstream_changes(self, inner_path: str = "") -> list[str]:
        """
        Compares submodule HEAD and origin/HEAD and returns changed filenames.
        """
        try:
            output = self.run_git(["diff", "--name-only", "HEAD", "origin/HEAD"], cwd=self.upstream_path)
            files = [line.strip() for line in output.splitlines() if line.strip()]
            
            if inner_path:
                filtered = [f for f in files if f.startswith(inner_path)]
                return filtered
            return files
        except subprocess.CalledProcessError:
            return []

    def update_base_pointer(self):
        """Updates the submodule to match origin/HEAD and stages it in the main repo."""
        latest_sha = self.get_head_rev("origin/HEAD")
        self.run_git(["checkout", latest_sha], cwd=self.upstream_path)
        
        rel_path = str(self.upstream_path.relative_to(self.repo_path))
        self.run_git(["add", rel_path])

    def stage_file(self, path: str):
        """Stages a file in the main repository."""
        self.run_git(["add", path])

    def commit(self, message: str):
        """Commits staged changes."""
        self.run_git(["commit", "-m", message])

    def attempt_merge(self, base: str, ours: str, theirs: str) -> tuple[bool, str]:
        """
        Attempts a 3-way merge using 'git merge-file'.
        Returns (success, merged_content).
        """
        with tempfile.NamedTemporaryFile(mode='w+', delete=True) as f_base, \
             tempfile.NamedTemporaryFile(mode='w+', delete=True) as f_ours, \
             tempfile.NamedTemporaryFile(mode='w+', delete=True) as f_theirs:
            
            f_base.write(base)
            f_ours.write(ours)
            f_theirs.write(theirs)
            
            f_base.flush()
            f_ours.flush()
            f_theirs.flush()

            # git merge-file -p <current> <base> <other>
            # -p sends result to stdout, returns 0 on success, positive on conflict
            res = subprocess.run(
                ["git", "merge-file", "-p", f_ours.name, f_base.name, f_theirs.name],
                capture_output=True,
                text=True
            )
            
            return (res.returncode == 0, res.stdout)
