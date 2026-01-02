import sys
import argparse
from pathlib import Path

from .ui import ChezmergeApp
from .logic import MergeItem, FileState, MergeScenario, DecisionEngine
from .git_ops import GitHandler
from .paths import find_local_match, normalize_path
from .importer import import_upstream

def parse_args():
    parser = argparse.ArgumentParser(description="Chezmerge: Intelligent Dotfile Merger")
    parser.add_argument("--repo", help="Upstream git repository URL")
    parser.add_argument("--inner-path", default="", help="Subdirectory inside upstream repo containing dotfiles")
    parser.add_argument("--source", default="~/.local/share/chezmoi", help="Local chezmoi source directory")
    parser.add_argument("--dry-run", action="store_true", help="Simulate merge logic without launching UI")
    return parser.parse_args()

def run():
    args = parse_args()
    local_path = Path(args.source).expanduser().resolve()
    
    if not local_path.exists():
        print(f"Creating local directory: {local_path}")
        local_path.mkdir(parents=True, exist_ok=True)

    git = GitHandler(local_path)
    
    # 1. Initialization Phase
    if not git.is_initialized():
        if not args.repo:
            print("Error: First run requires --repo <url>")
            sys.exit(1)
            
        print("Initializing Chezmerge Workspace...")
        git.init_workspace(args.repo)
        
        print("Performing initial import...")
        # Import from 'base' (which is same as latest initially)
        import_upstream(git.workspace / "base", local_path, args.inner_path)
        
        print("Initialization complete. You can now run 'chezmoi apply'.")
        return

    # 2. Update Phase
    print("Fetching upstream changes...")
    git.fetch_latest()
    
    # Identify changed files between base and latest
    changed_files = git.get_changed_files_between_clones(args.inner_path)
    
    if not changed_files:
        print("No upstream changes detected.")
        return

    print(f"Detected {len(changed_files)} changed files upstream.")
    
    merge_items = []
    engine = DecisionEngine()
    
    for upstream_file in changed_files:
        # upstream_file is relative to repo root (e.g. 'dots/.bashrc')
        # We need the path relative to the inner_path for matching
        rel_target_path = upstream_file
        if args.inner_path and upstream_file.startswith(args.inner_path):
            rel_target_path = upstream_file[len(args.inner_path):].lstrip("/")
            
        # Find local match
        local_file = find_local_match(local_path, rel_target_path)
        
        if not local_file:
            print(f"Skipping {rel_target_path} (not found locally)")
            continue

        # Gather 4-way state
        # Base: Content from 'base' clone
        base_content = git.get_file_content("base", upstream_file)
        # Theirs: Content from 'latest' clone
        theirs_content = git.get_file_content("latest", upstream_file)
        # Ours: Content from local disk (rendered? No, raw source for now)
        ours_content = git.get_file_content("local", str(local_file))
        
        # For MVP, Template is just Ours
        template_content = ours_content
        
        base_state = FileState(base_content, rel_target_path)
        theirs_state = FileState(theirs_content, rel_target_path)
        ours_state = FileState(ours_content, str(local_file))
        template_state = FileState(template_content, str(local_file), is_template=True)
        
        scenario = engine.analyze(base_state, theirs_state, ours_state, template_state)
        
        # For MVP, we only show UI for conflicts or updates, skipping auto-synced
        if scenario != MergeScenario.ALREADY_SYNCED:
            merge_items.append(MergeItem(
                path=str(local_file),
                base=base_state,
                theirs=theirs_state,
                ours=ours_state,
                template=template_state,
                scenario=scenario
            ))

    if not merge_items:
        print("All changes merged automatically.")
        git.update_base_pointer()
        return

    # Handle Dry Run
    if args.dry_run:
        print(f"Dry Run: {len(merge_items)} files require merging.")
        for item in merge_items:
            print(f"  - {item.path} [{item.scenario.name}]")
        return

    # Launch UI
    app = ChezmergeApp(merge_items)
    results = app.run()
    
    if results:
        print("Applying changes to local files...")
        for item in results:
            # Write the template content back to the local file
            dest = local_path / item.path
            dest.write_text(item.template.content)
            print(f"Updated {item.path}")
        
        # Update base pointer so we don't process these again
        git.update_base_pointer()
        print("Merge complete.")

if __name__ == "__main__":
    run()
