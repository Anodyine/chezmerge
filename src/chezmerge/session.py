import json
import shutil
from pathlib import Path

from .git_ops import GitHandler


class MergeSessionManager:
    VERSION = 1

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path.resolve()
        self.git_dir = self.repo_path / ".git"
        self.session_dir = self.git_dir / "chezmerge-session"
        self.manifest_path = self.session_dir / "manifest.json"

    def has_session(self) -> bool:
        return self.manifest_path.exists()

    def start(self, base_submodule_sha: str):
        if self.has_session():
            return

        manifest = {
            "version": self.VERSION,
            "base_submodule_sha": base_submodule_sha,
        }
        self._write_manifest(manifest)

    def cleanup(self):
        if self.session_dir.exists():
            shutil.rmtree(self.session_dir)

    def record_path(self, git: GitHandler, path: str):
        # Kept as a no-op so the merge flow can continue to mark session activity
        # without maintaining per-path rollback state.
        if not self.has_session():
            raise RuntimeError("Cannot record path without an active chezmerge session")

    def abort(self, git: GitHandler):
        manifest = self._read_manifest()
        if not manifest:
            return False

        git.restore_repo_to_head()
        git.clean_untracked_files()
        git.checkout_submodule(manifest["base_submodule_sha"])
        git.sync_submodule_to_index()
        self.cleanup()
        return True

    def _read_manifest(self) -> dict | None:
        return self._read_manifest_file(self.manifest_path)

    def _read_manifest_file(self, path: Path) -> dict | None:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_manifest(self, manifest: dict):
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
