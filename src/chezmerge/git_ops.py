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

    def is_submodule_registered(self) -> bool:
        """Checks if the upstream submodule is tracked by the parent repository."""
        rel_path = str(self.upstream_path.relative_to(self.repo_path))
        result = subprocess.run(
            ["git", "submodule", "status", "--", rel_path],
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )
        return result.returncode == 0 and bool(result.stdout.strip())

    def get_configured_upstream_url(self) -> Optional[str]:
        """Reads the upstream URL for this submodule from .gitmodules if present."""
        gitmodules = self.repo_path / ".gitmodules"
        if not gitmodules.exists():
            return None

        rel_path = str(self.upstream_path.relative_to(self.repo_path))
        try:
            paths_output = self.run_git(
                ["config", "-f", ".gitmodules", "--get-regexp", r"^submodule\..*\.path$"],
                cwd=self.repo_path,
                strip=False
            )
        except subprocess.CalledProcessError:
            return None

        for line in paths_output.splitlines():
            if not line.strip():
                continue
            key, _, value = line.partition(" ")
            if value.strip() != rel_path:
                continue
            url_key = f"{key.rsplit('.path', 1)[0]}.url"
            try:
                url = self.run_git(["config", "-f", ".gitmodules", "--get", url_key], cwd=self.repo_path)
            except subprocess.CalledProcessError:
                return None
            return url.strip() or None

        return None

    def init_workspace(self, remote_url: str):
        """Sets up the .chezmerge-upstream submodule."""
        # Ensure main repo is initialized
        if not (self.repo_path / ".git").exists():
            self.run_git(["init"])
        rel_path = str(self.upstream_path.relative_to(self.repo_path))

        if self.is_submodule_registered():
            print(f"Initializing existing submodule at {rel_path}...")
            self.run_git(["-c", "protocol.file.allow=always", "submodule", "update", "--init", rel_path])
        else:
            print(f"Adding submodule {remote_url}...")
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

    def get_upstream_changes(self, inner_path: str = "") -> list[tuple[str, str]]:
        """
        Compares submodule HEAD and origin/HEAD and returns (status, path) pairs.
        """
        try:
            output = self.run_git(["diff", "--name-status", "HEAD", "origin/HEAD"], cwd=self.upstream_path)
            changes: list[tuple[str, str]] = []
            for line in output.splitlines():
                if not line.strip():
                    continue
                parts = line.split("\t")
                status = parts[0].strip()
                if not status:
                    continue

                # For rename/copy, use destination path (the last path field).
                if len(parts) >= 3 and status[0] in ("R", "C"):
                    path = parts[-1].strip()
                elif len(parts) >= 2:
                    path = parts[1].strip()
                else:
                    continue

                if path:
                    changes.append((status[0], path))

            if inner_path:
                filtered = [(status, path) for status, path in changes if path.startswith(inner_path)]
                return filtered
            return changes
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
