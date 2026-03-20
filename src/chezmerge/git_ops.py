import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import Optional

class GitHandler:
    PULL_HOOKS_DIR = ".githooks"
    PULL_HOOK_NAMES = ("post-merge", "post-rewrite")
    PULL_HOOK_MARKER = "# Managed by chezmerge: pull submodule sync hook"

    PULL_HOOK_CONTENT = """#!/usr/bin/env bash
set -euo pipefail

# Managed by chezmerge: pull submodule sync hook
# Keep the local submodule worktree aligned with the commit recorded
# in the parent repository after pull/merge/rebase operations.
git submodule update --init --recursive .chezmerge-upstream || true
"""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path.resolve()
        self.upstream_path = self.repo_path / ".chezmerge-upstream"

    def ensure_pull_hooks(self):
        """
        Ensures git pull-related hooks exist and local core.hooksPath points to them.
        If a non-chezmerge hook exists at a managed path, it is left untouched.
        """
        if not (self.repo_path / ".git").exists():
            return

        hooks_dir = self.repo_path / self.PULL_HOOKS_DIR
        hooks_dir.mkdir(parents=True, exist_ok=True)

        for hook_name in self.PULL_HOOK_NAMES:
            hook_path = hooks_dir / hook_name
            self._ensure_managed_hook(hook_path, hook_name)

        self._ensure_hooks_path_config()

    def _ensure_managed_hook(self, hook_path: Path, hook_name: str):
        desired = self.PULL_HOOK_CONTENT

        if hook_path.exists():
            current = hook_path.read_text(encoding="utf-8", errors="surrogateescape")
            if self.PULL_HOOK_MARKER not in current:
                print(
                    f"Warning: {self.PULL_HOOKS_DIR}/{hook_name} exists and is not managed by chezmerge; "
                    "leaving it unchanged."
                )
                return
            if current != desired:
                hook_path.write_text(desired, encoding="utf-8", errors="surrogateescape")
                print(f"Updated {self.PULL_HOOKS_DIR}/{hook_name}")
        else:
            hook_path.write_text(desired, encoding="utf-8", errors="surrogateescape")
            print(f"Installed {self.PULL_HOOKS_DIR}/{hook_name}")

        hook_path.chmod(0o755)

    def _ensure_hooks_path_config(self):
        result = subprocess.run(
            ["git", "config", "--local", "--get", "core.hooksPath"],
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )
        current = result.stdout.strip() if result.returncode == 0 else ""
        if current == self.PULL_HOOKS_DIR:
            return

        self.run_git(["config", "--local", "core.hooksPath", self.PULL_HOOKS_DIR])
        print(f"Configured core.hooksPath={self.PULL_HOOKS_DIR}")

    def run_git(self, args: list[str], cwd: Optional[Path] = None, strip: bool = True, text: bool = True):
        """Executes a git command."""
        target_cwd = cwd if cwd else self.repo_path
        try:
            result = subprocess.run(
                ["git"] + args, 
                cwd=target_cwd, 
                capture_output=True, 
                text=text, 
                check=True
            )
            stdout = result.stdout
            if text:
                return stdout.strip() if strip else stdout
            return stdout
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
            return p.read_bytes().decode("utf-8", errors="surrogateescape") if p.exists() else ""
        
        # For base/latest, read from the submodule
        # 'base' is the currently checked out commit in the submodule
        # 'latest' is the remote HEAD
        ref = "HEAD" if source == "base" else "origin/HEAD"
        try:
            raw = self.run_git(["show", f"{ref}:{path}"], cwd=self.upstream_path, strip=False, text=False)
            return raw.decode("utf-8", errors="surrogateescape")
        except subprocess.CalledProcessError:
            return ""

    def get_file_mode(self, ref: str, path: str) -> Optional[str]:
        """Gets the git mode for a file at ref:path (e.g. 100644, 100755, 120000)."""
        try:
            output = self.run_git(["ls-tree", ref, "--", path], cwd=self.upstream_path, strip=True)
        except subprocess.CalledProcessError:
            return None

        if not output:
            return None

        # Format: "<mode> <type> <sha>\t<path>"
        first_field = output.split()[0] if output.split() else ""
        return first_field or None

    def is_path_tracked(self, path: str) -> bool:
        """Returns True when path exists in git index/history for this repo."""
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", path],
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )
        return result.returncode == 0

    def get_index_entry(self, path: str) -> Optional[dict[str, str]]:
        """Returns the mode and blob SHA stored in the index for path, if present."""
        result = subprocess.run(
            ["git", "ls-files", "--stage", "--", path],
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None

        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) < 4:
                continue
            mode, sha, stage = parts[0], parts[1], parts[2]
            if stage == "0":
                return {"mode": mode, "sha": sha}
        return None

    def get_upstream_changes(self, inner_path: str = "") -> list[tuple[str, str, Optional[str]]]:
        """
        Compares submodule HEAD and origin/HEAD and returns:
        (status, path, source_path)

        For regular statuses (A/M/D), source_path is None.
        For rename/copy statuses (R/C), path is destination and source_path is origin.
        """
        def _in_scope(path: str, normalized_inner: str) -> bool:
            if not normalized_inner:
                return True
            prefix = f"{normalized_inner}/"
            return path == normalized_inner or path.startswith(prefix)

        try:
            output = self.run_git(["diff", "--name-status", "HEAD", "origin/HEAD"], cwd=self.upstream_path)
            changes: list[tuple[str, str, Optional[str]]] = []
            normalized_inner = inner_path.strip("/")
            for line in output.splitlines():
                if not line.strip():
                    continue
                parts = line.split("\t")
                status = parts[0].strip()
                if not status:
                    continue

                kind = status[0]
                if kind in ("R", "C"):
                    if len(parts) < 3:
                        continue
                    source_path = parts[1].strip()
                    dest_path = parts[2].strip()
                    if not source_path or not dest_path:
                        continue
                    if _in_scope(source_path, normalized_inner) or _in_scope(dest_path, normalized_inner):
                        changes.append((kind, dest_path, source_path))
                    continue

                if len(parts) < 2:
                    continue
                path = parts[1].strip()
                if path and _in_scope(path, normalized_inner):
                    changes.append((kind, path, None))

            return changes
        except subprocess.CalledProcessError:
            return []

    def write_local_file(self, path: str, content: str):
        """Writes file content preserving non-UTF8 bytes via surrogateescape."""
        target = self.repo_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content.encode("utf-8", errors="surrogateescape"))

    def update_base_pointer(self):
        """Updates the submodule to match origin/HEAD and stages it in the main repo."""
        latest_sha = self.get_head_rev("origin/HEAD")
        self.set_submodule_pointer(latest_sha)

    def set_submodule_pointer(self, sha: str):
        """Checks out the upstream submodule at sha and stages the submodule pointer."""
        self.run_git(["checkout", sha], cwd=self.upstream_path)
        rel_path = str(self.upstream_path.relative_to(self.repo_path))
        self.run_git(["add", rel_path])

    def stage_file(self, path: str):
        """Stages a file change in the main repository (add/update/delete)."""
        self.run_git(["add", "-A", "--", path])

    def restore_index_entry(self, path: str, mode: Optional[str], sha: Optional[str]):
        """Restores a single index entry to a previously recorded state."""
        if mode and sha:
            self.run_git(["update-index", "--add", "--cacheinfo", f"{mode},{sha},{path}"])
            return

        subprocess.run(
            ["git", "rm", "--cached", "-q", "--ignore-unmatch", "--", path],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=False
        )

    def commit(self, message: str):
        """Commits staged changes."""
        self.run_git(["commit", "-m", message])

    def attempt_merge(self, base: str, ours: str, theirs: str) -> tuple[bool, str]:
        """
        Attempts a 3-way merge using 'git merge-file'.
        Returns (success, merged_content).
        """
        with tempfile.NamedTemporaryFile(mode='wb+', delete=True) as f_base, \
             tempfile.NamedTemporaryFile(mode='wb+', delete=True) as f_ours, \
             tempfile.NamedTemporaryFile(mode='wb+', delete=True) as f_theirs:
            
            f_base.write(base.encode("utf-8", errors="surrogateescape"))
            f_ours.write(ours.encode("utf-8", errors="surrogateescape"))
            f_theirs.write(theirs.encode("utf-8", errors="surrogateescape"))
            
            f_base.flush()
            f_ours.flush()
            f_theirs.flush()

            # git merge-file -p <current> <base> <other>
            # -p sends result to stdout, returns 0 on success, positive on conflict
            res = subprocess.run(
                ["git", "merge-file", "-p", f_ours.name, f_base.name, f_theirs.name],
                capture_output=True
            )
            
            return (res.returncode == 0, res.stdout.decode("utf-8", errors="surrogateescape"))
