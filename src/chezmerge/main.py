import sys
import argparse
import subprocess
import os
from pathlib import Path
from typing import Optional

from .logic import MergeItem, FileState, MergeScenario, DecisionEngine
from .git_ops import GitHandler
from .paths import find_local_match, chezmoify_path
from .importer import import_upstream
from .session import MergeSessionManager

def parse_args():
    parser = argparse.ArgumentParser(description="Chezmerge: Intelligent Dotfile Merger")
    parser.add_argument("--repo", help="Upstream git repository URL")
    parser.add_argument("--inner-path", default="", help="Subdirectory inside upstream repo containing dotfiles")
    parser.add_argument("--source", default="~/.local/share/chezmoi", help="Local chezmoi source directory")
    parser.add_argument("--editor", help="External editor to use for merges (e.g. nvim, vim, vi)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate merge logic without launching UI")
    parser.add_argument("--abort", action="store_true", help="Abort the current uncommitted chezmerge session")
    return parser.parse_args()

def render_chezmoi_template(content: str) -> str:
    """
    Renders the given template content using 'chezmoi execute-template'.
    Returns the rendered string, or the original content if rendering fails.

    Note: chezmoi automatically discovers its configuration in standard 
    locations (e.g., ~/.config/chezmoi/chezmoi.toml).
    """
    cmd = ["chezmoi", "execute-template"]

    # Support custom config file via env var, useful for testing and custom setups.
    # By default, chezmoi automatically discovers the config in standard locations.
    config_path = os.environ.get("CHEZMOI_CONFIG")
    if config_path:
        cmd.extend(["--config", config_path])

    try:
        result = subprocess.run(
            cmd,
            input=content,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        # Print warning to stderr so it doesn't break stdout flow but is visible
        print(f"Warning: Template rendering failed: {e.stderr.strip()}", file=sys.stderr)
        return content
    except FileNotFoundError:
        print("Warning: 'chezmoi' executable not found. Cannot render template.", file=sys.stderr)
        return content

def import_new_upstream_file(git: GitHandler, rel_target_path: str, upstream_file: str) -> Optional[str]:
    """Imports a newly-added upstream file and returns the staged local relative path."""
    mode = git.get_file_mode("origin/HEAD", upstream_file)
    is_symlink = mode == "120000"
    is_executable = mode == "100755"
    dest_rel = chezmoify_path(rel_target_path, executable=is_executable, symlink=is_symlink)

    content = git.get_file_content("latest", upstream_file)
    if is_symlink and content and not content.endswith("\n"):
        # chezmoi stores symlink targets as file content with trailing newline.
        content = f"{content}\n"

    git.write_local_file(dest_rel, content)
    git.stage_file(dest_rel)
    return dest_rel

def run():
    args = parse_args()
    local_path = Path(args.source).expanduser().resolve()
    
    if not local_path.exists():
        print(f"Creating local directory: {local_path}")
        local_path.mkdir(parents=True, exist_ok=True)

    git = GitHandler(local_path)
    session = MergeSessionManager(local_path)

    if args.abort:
        if session.abort(git):
            print("Aborted chezmerge session and restored recorded paths.")
        else:
            print("No active chezmerge session found.")
        return

    if session.has_session():
        print("An uncommitted chezmerge session is already in progress.")
        print("Run 'chezmerge --abort' to roll it back before starting a new merge.")
        return
    
    # 1. Initialization Phase
    if not git.is_initialized():
        submodule_was_registered = git.is_submodule_registered()
        repo_url = args.repo or git.get_configured_upstream_url()
        if not repo_url:
            print("Error: First run requires --repo <url> (or a .gitmodules entry for .chezmerge-upstream)")
            sys.exit(1)

        if not args.repo:
            print(f"Using submodule URL from .gitmodules: {repo_url}")

        print("Initializing Chezmerge Workspace...")
        git.init_workspace(repo_url)
        git.ensure_pull_hooks()

        # If the submodule already existed in .gitmodules but was not initialized,
        # this is not a true first run. Continue to update/merge flow to preserve
        # local modifications and present conflicts as needed.
        if not submodule_was_registered:
            print("Performing initial import...")
            # Import from the submodule
            import_upstream(git.upstream_path, local_path, args.inner_path)

            print("Initialization complete. You can now run 'chezmoi apply'.")
            return
    else:
        git.ensure_pull_hooks()

    # 2. Update Phase
    print("Fetching upstream changes...")
    git.fetch_latest()
    
    # Identify changed files between base and latest
    changed_files = git.get_upstream_changes(args.inner_path)
    
    if not changed_files:
        print("No upstream changes detected.")
        return

    print(f"Detected {len(changed_files)} changed files upstream.")
    
    merge_items = []
    engine = DecisionEngine()
    session_started = False
    base_submodule_sha = git.get_head_rev("HEAD")
    
    unresolved_missing: list[str] = []

    normalized_inner = args.inner_path.strip("/")
    inner_prefix = f"{normalized_inner}/" if normalized_inner else ""

    def to_inner_relative(upstream_path: str) -> Optional[str]:
        if not normalized_inner:
            return upstream_path
        if upstream_path == normalized_inner:
            return ""
        if upstream_path.startswith(inner_prefix):
            return upstream_path[len(inner_prefix):]
        return None

    def ensure_session_started():
        nonlocal session_started
        if not session_started:
            session.start(base_submodule_sha)
            session_started = True

    def record_path_before_change(path: str):
        ensure_session_started()
        session.record_path(git, path)

    for change_type, upstream_file, source_upstream_file in changed_files:
        if change_type == "R":
            old_upstream_file = source_upstream_file
            new_upstream_file = upstream_file

            if not old_upstream_file:
                unresolved_missing.append(new_upstream_file)
                print(f"Missing rename source metadata for {new_upstream_file}; manual resolution required.")
                continue

            rel_old_target = to_inner_relative(old_upstream_file)
            rel_new_target = to_inner_relative(new_upstream_file)

            local_old = find_local_match(local_path, rel_old_target) if rel_old_target is not None else None
            local_new = find_local_match(local_path, rel_new_target) if rel_new_target is not None else None

            # Rename moved out of managed scope -> treat as deletion.
            if rel_old_target is not None and rel_new_target is None:
                if not local_old:
                    unresolved = rel_old_target or old_upstream_file
                    print(f"Missing local counterpart for {unresolved} (R->out); manual resolution required.")
                    unresolved_missing.append(unresolved)
                    continue

                base_content = git.get_file_content("base", old_upstream_file)
                raw_local_content = git.get_file_content("local", str(local_old))
                if raw_local_content == base_content:
                    if args.dry_run:
                        print(f"  - {str(local_old)} [AUTO_DELETE]")
                    else:
                        print(f"Auto-deleting {rel_old_target} (upstream renamed outside inner path)...")
                        record_path_before_change(str(local_old))
                        old_abs = local_path / str(local_old)
                        if old_abs.exists():
                            old_abs.unlink()
                        if git.is_path_tracked(str(local_old)):
                            git.stage_file(str(local_old))
                    continue

                print(f"Rename conflict: {rel_old_target} -> {new_upstream_file} (local file modified)")
                unresolved_missing.append(f"{rel_old_target} -> {new_upstream_file}")
                continue

            # Rename moved into managed scope -> treat as addition.
            if rel_old_target is None and rel_new_target is not None:
                if local_new:
                    latest_content = git.get_file_content("latest", new_upstream_file)
                    raw_local_new = git.get_file_content("local", str(local_new))
                    if raw_local_new == latest_content:
                        continue
                    unresolved = rel_new_target or new_upstream_file
                    print(f"Existing local file for renamed upstream path {unresolved}; manual resolution required.")
                    unresolved_missing.append(unresolved)
                    continue

                if args.dry_run:
                    mode = git.get_file_mode("origin/HEAD", new_upstream_file)
                    is_symlink = mode == "120000"
                    is_executable = mode == "100755"
                    dest_rel = chezmoify_path(rel_new_target, executable=is_executable, symlink=is_symlink)
                    print(f"  - {dest_rel} [AUTO_IMPORT]")
                else:
                    mode = git.get_file_mode("origin/HEAD", new_upstream_file)
                    is_symlink = mode == "120000"
                    is_executable = mode == "100755"
                    dest_rel = chezmoify_path(rel_new_target, executable=is_executable, symlink=is_symlink)
                    record_path_before_change(dest_rel)
                    staged_path = import_new_upstream_file(git, rel_new_target, new_upstream_file)
                    print(f"Auto-importing renamed upstream file {new_upstream_file} -> {staged_path}")
                continue

            # Rename wholly outside scope should not appear, but ignore safely if it does.
            if rel_old_target is None and rel_new_target is None:
                continue

            # Standard in-scope rename.
            if not local_old:
                unresolved = rel_old_target or old_upstream_file
                print(f"Missing local counterpart for {unresolved} (R); manual resolution required.")
                unresolved_missing.append(unresolved)
                continue

            base_old_content = git.get_file_content("base", old_upstream_file)
            raw_local_old_content = git.get_file_content("local", str(local_old))
            if raw_local_old_content != base_old_content:
                old_display = rel_old_target or old_upstream_file
                new_display = rel_new_target or new_upstream_file
                print(f"Rename conflict: {old_display} -> {new_display} (local file modified)")
                unresolved_missing.append(f"{old_display} -> {new_display}")
                continue

            mode = git.get_file_mode("origin/HEAD", new_upstream_file)
            is_symlink = mode == "120000"
            is_executable = mode == "100755"
            new_local_rel = chezmoify_path(rel_new_target, executable=is_executable, symlink=is_symlink)
            latest_new_content = git.get_file_content("latest", new_upstream_file)
            if is_symlink and latest_new_content and not latest_new_content.endswith("\n"):
                latest_new_content = f"{latest_new_content}\n"

            old_local_rel = str(local_old)
            old_abs = local_path / old_local_rel
            new_abs = local_path / new_local_rel

            if args.dry_run:
                print(f"  - {old_local_rel} -> {new_local_rel} [AUTO_RENAME]")
                continue

            # If destination already exists with unexpected content, require manual handling.
            if new_abs.exists() and new_abs != old_abs:
                current_new_content = git.get_file_content("local", new_local_rel)
                if current_new_content != latest_new_content:
                    old_display = rel_old_target or old_upstream_file
                    new_display = rel_new_target or new_upstream_file
                    print(f"Rename conflict: destination exists for {old_display} -> {new_display}; manual resolution required.")
                    unresolved_missing.append(f"{old_display} -> {new_display}")
                    continue

            print(f"Auto-renaming {rel_old_target} -> {rel_new_target}...")
            record_path_before_change(old_local_rel)
            if new_local_rel != old_local_rel:
                record_path_before_change(new_local_rel)
            if old_abs.exists() and new_abs != old_abs:
                new_abs.parent.mkdir(parents=True, exist_ok=True)
                old_abs.rename(new_abs)

            git.write_local_file(new_local_rel, latest_new_content)
            git.stage_file(new_local_rel)
            if new_local_rel != old_local_rel:
                if git.is_path_tracked(old_local_rel):
                    git.stage_file(old_local_rel)
            continue

        # upstream_file is relative to repo root (e.g. 'dots/.bashrc')
        # We need the path relative to the inner_path for matching
        rel_target_path = upstream_file
        if normalized_inner:
            if upstream_file.startswith(inner_prefix):
                rel_target_path = upstream_file[len(inner_prefix):]
            elif upstream_file == normalized_inner:
                rel_target_path = ""
            
        # Find local match
        local_file = find_local_match(local_path, rel_target_path)
        
        if not local_file:
            if change_type == "A":
                if args.dry_run:
                    mode = git.get_file_mode("origin/HEAD", upstream_file)
                    is_symlink = mode == "120000"
                    is_executable = mode == "100755"
                    dest_rel = chezmoify_path(rel_target_path, executable=is_executable, symlink=is_symlink)
                    print(f"  - {dest_rel} [AUTO_IMPORT]")
                else:
                    mode = git.get_file_mode("origin/HEAD", upstream_file)
                    is_symlink = mode == "120000"
                    is_executable = mode == "100755"
                    dest_rel = chezmoify_path(rel_target_path, executable=is_executable, symlink=is_symlink)
                    record_path_before_change(dest_rel)
                    staged_path = import_new_upstream_file(git, rel_target_path, upstream_file)
                    print(f"Auto-importing new upstream file {rel_target_path} -> {staged_path}")
                continue
            if change_type == "D":
                # If upstream deleted a file and we no longer have a local source entry
                # that maps to it, the desired state (absence) is already satisfied.
                print(f"Skipping {rel_target_path} (upstream deleted, local counterpart already absent).")
                continue

            unresolved = rel_target_path or upstream_file
            print(f"Missing local counterpart for {unresolved} ({change_type}); manual resolution required.")
            unresolved_missing.append(unresolved)
            continue

        if change_type == "D":
            base_content = git.get_file_content("base", upstream_file)
            raw_local_content = git.get_file_content("local", str(local_file))

            # Safe auto-delete only when local content still matches base.
            if raw_local_content == base_content:
                if args.dry_run:
                    print(f"  - {str(local_file)} [AUTO_DELETE]")
                else:
                    print(f"Auto-deleting {rel_target_path} (upstream deleted, local unchanged)...")
                    record_path_before_change(str(local_file))
                    dest = local_path / str(local_file)
                    if dest.exists():
                        dest.unlink()
                    if git.is_path_tracked(str(local_file)):
                        git.stage_file(str(local_file))
                continue

            print(f"Deletion conflict: {rel_target_path} (upstream deleted, local file modified)")
            print("  Keeping the local file preserves it as reference only; upstream may no longer invoke it.")
            is_tmpl = str(local_file).endswith(".tmpl")
            ours_content = raw_local_content
            if is_tmpl:
                ours_content = render_chezmoi_template(raw_local_content)

            merge_items.append(MergeItem(
                path=str(local_file),
                base=FileState(base_content, rel_target_path),
                theirs=FileState("", rel_target_path),
                ours=FileState(ours_content, str(local_file)),
                template=FileState(raw_local_content, str(local_file), is_template=is_tmpl),
                scenario=MergeScenario.DELETION_CONFLICT
            ))
            continue

        # Gather 4-way state
        # Base: Content from 'base' clone
        base_content = git.get_file_content("base", upstream_file)
        # Theirs: Content from 'latest' clone
        theirs_content = git.get_file_content("latest", upstream_file)
        
        # Ours: Content from local disk
        raw_local_content = git.get_file_content("local", str(local_file))
        
        is_tmpl = str(local_file).endswith(".tmpl")

        # If it's a template, try to render it for the "Ours" view (comparison context)
        ours_content = raw_local_content
        if is_tmpl:
            ours_content = render_chezmoi_template(raw_local_content)
        
        # Template view always needs the raw source for editing
        template_content = raw_local_content
        
        base_state = FileState(base_content, rel_target_path)
        theirs_state = FileState(theirs_content, rel_target_path)
        ours_state = FileState(ours_content, str(local_file))
        template_state = FileState(template_content, str(local_file), is_template=is_tmpl)
        
        scenario = engine.analyze(base_state, theirs_state, ours_state, template_state)
        
        merged_content = None
        if scenario == MergeScenario.CONFLICT:
            merge_ours_content = template_content if is_tmpl else ours_content
            success, result = git.attempt_merge(base_content, merge_ours_content, theirs_content)
            if success:
                scenario = MergeScenario.AUTO_MERGEABLE
                merged_content = result
            elif is_tmpl:
                scenario = MergeScenario.TEMPLATE_DIVERGENCE
        
        if scenario == MergeScenario.ALREADY_SYNCED:
            continue

        if scenario in (MergeScenario.AUTO_UPDATE, MergeScenario.AUTO_MERGEABLE):
            if args.dry_run:
                print(f"  - {str(local_file)} [{scenario.name}]")
            else:
                print(f"Auto-merging {rel_target_path} ({scenario.name})...")
                record_path_before_change(str(local_file))
                # For AUTO_UPDATE, theirs_content is the target.
                # For AUTO_MERGEABLE, merged_content is the target.
                content_to_write = merged_content if scenario == MergeScenario.AUTO_MERGEABLE else theirs_content
                
                if content_to_write is None:
                    raise RuntimeError(f"Unexpected None content for {scenario.name}")

                git.write_local_file(str(local_file), content_to_write)
                git.stage_file(str(local_file))
            continue

        merge_items.append(MergeItem(
            path=str(local_file),
            base=base_state,
            theirs=theirs_state,
            ours=ours_state,
            template=template_state,
            scenario=scenario
        ))

    if unresolved_missing:
        print(f"{len(unresolved_missing)} path(s) require manual resolution before advancing base pointer:")
        for path in unresolved_missing:
            print(f"  - {path}")
        print("Aborting without commit to avoid dropping upstream changes.")
        return

    if not merge_items:
        print("All changes merged automatically.")
        if not args.dry_run:
            ensure_session_started()
            git.update_base_pointer()
            git.commit("chore(chezmerge): Merge upstream changes")
            session.cleanup()
            print("Merge complete. Changes committed.")
        return

    # Handle Dry Run
    if args.dry_run:
        print(f"Dry Run: {len(merge_items)} files require merging.")
        for item in merge_items:
            print(f"  - {item.path} [{item.scenario.name}]")
        return

    # Launch UI
    from .ui import ChezmergeApp
    app = ChezmergeApp(merge_items, external_editor=args.editor)
    results = app.run()
    
    if results:
        print("Applying changes to local files...")
        for item in results:
            if item.delete_on_save:
                record_path_before_change(item.path)
                dest = local_path / item.path
                if dest.exists():
                    dest.unlink()
                git.stage_file(item.path)
                print(f"Deleted {item.path}")
                continue

            # Write the template content back to the local file
            record_path_before_change(item.path)
            git.write_local_file(item.path, item.template.content)
            git.stage_file(item.path)
            print(f"Updated {item.path}")
        
        # Update base pointer so we don't process these again
        ensure_session_started()
        git.update_base_pointer()
        git.commit("chore(chezmerge): Merge upstream changes")
        session.cleanup()
        print("Merge complete. Changes committed.")

if __name__ == "__main__":
    run()
