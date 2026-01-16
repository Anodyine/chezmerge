import sys
import argparse
import subprocess
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

def render_chezmoi_template(content: str) -> str:
    """
    Renders the given template content using 'chezmoi execute-template'.
    Returns the rendered string, or the original content if rendering fails.
    """
    try:
        result = subprocess.run(
            ["chezmoi", "execute-template"],
            input=content,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return content

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
        # Import from the submodule
        import_upstream(git.upstream_path, local_path, args.inner_path)
        
        print("Initialization complete. You can now run 'chezmoi apply'.")
        return

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
        if scenario == MergeScenario.CONFLICT and not is_tmpl:
            success, result = git.attempt_merge(base_content, ours_content, theirs_content)
            if success:
                scenario = MergeScenario.AUTO_MERGEABLE
                merged_content = result
        
        if scenario == MergeScenario.ALREADY_SYNCED:
            continue

        if scenario in (MergeScenario.AUTO_UPDATE, MergeScenario.AUTO_MERGEABLE):
            if args.dry_run:
                print(f"  - {str(local_file)} [{scenario.name}]")
            else:
                print(f"Auto-merging {rel_target_path} ({scenario.name})...")
                dest = local_path / str(local_file)
                # For AUTO_UPDATE, theirs_content is the target. 
                # For AUTO_MERGEABLE, merged_content is the target.
                content_to_write = merged_content if scenario == MergeScenario.AUTO_MERGEABLE else theirs_content
                dest.write_text(content_to_write)
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

    if not merge_items:
        print("All changes merged automatically.")
        if not args.dry_run:
            git.update_base_pointer()
            git.commit("chore(chezmerge): Merge upstream changes")
            print("Merge complete. Changes committed.")
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
            git.stage_file(item.path)
            print(f"Updated {item.path}")
        
        # Update base pointer so we don't process these again
        git.update_base_pointer()
        git.commit("chore(chezmerge): Merge upstream changes")
        print("Merge complete. Changes committed.")

if __name__ == "__main__":
    run()
