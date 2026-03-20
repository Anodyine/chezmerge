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
        self.snapshots_dir = self.session_dir / "snapshots"
        self.manifest_path = self.session_dir / "manifest.json"

    def has_session(self) -> bool:
        return self.manifest_path.exists()

    def start(self, base_submodule_sha: str):
        if self.has_session():
            return

        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "version": self.VERSION,
            "base_submodule_sha": base_submodule_sha,
            "paths": {},
            "order": [],
        }
        self._write_manifest(manifest)

    def cleanup(self):
        if self.session_dir.exists():
            shutil.rmtree(self.session_dir)

    def record_path(self, git: GitHandler, path: str):
        manifest = self._read_manifest()
        if not manifest:
            raise RuntimeError("Cannot record path without an active chezmerge session")

        if path in manifest["paths"]:
            return

        target = self.repo_path / path
        snapshot_name = None
        worktree_exists = target.exists()
        worktree_mode = None

        if worktree_exists:
            snapshot_name = f"{len(manifest['order']):04d}.snapshot"
            snapshot_path = self.snapshots_dir / snapshot_name
            snapshot_path.write_bytes(target.read_bytes())
            worktree_mode = target.stat().st_mode & 0o777

        index_entry = git.get_index_entry(path)
        entry = {
            "path": path,
            "worktree_exists": worktree_exists,
            "worktree_mode": worktree_mode,
            "snapshot": snapshot_name,
            "index_mode": index_entry["mode"] if index_entry else None,
            "index_sha": index_entry["sha"] if index_entry else None,
        }
        manifest["paths"][path] = entry
        manifest["order"].append(path)
        self._write_manifest(manifest)

    def abort(self, git: GitHandler):
        manifest = self._read_manifest()
        if not manifest:
            return False

        for path in reversed(manifest["order"]):
            entry = manifest["paths"][path]
            self._restore_worktree_path(entry)

        for path in manifest["order"]:
            entry = manifest["paths"][path]
            git.restore_index_entry(path, entry["index_mode"], entry["index_sha"])

        git.set_submodule_pointer(manifest["base_submodule_sha"])
        self.cleanup()
        return True

    def _restore_worktree_path(self, entry: dict):
        path = self.repo_path / entry["path"]
        if entry["worktree_exists"]:
            path.parent.mkdir(parents=True, exist_ok=True)
            snapshot = self.snapshots_dir / entry["snapshot"]
            path.write_bytes(snapshot.read_bytes())
            if entry["worktree_mode"] is not None:
                path.chmod(entry["worktree_mode"])
            return

        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()

        self._prune_empty_parents(path.parent)

    def _prune_empty_parents(self, start: Path):
        repo_root = self.repo_path
        current = start
        while current != repo_root and current.exists():
            try:
                current.rmdir()
            except OSError:
                break
            current = current.parent

    def _read_manifest(self) -> dict | None:
        if not self.manifest_path.exists():
            return None
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def _write_manifest(self, manifest: dict):
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
