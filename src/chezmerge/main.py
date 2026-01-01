import sys
from pathlib import Path

# Logic to handle running this file directly vs as a module
if __name__ == "__main__" and __package__ is None:
    # Add 'src' to sys.path to allow importing 'chezmerge' as a package
    src_path = Path(__file__).resolve().parent.parent
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    from chezmerge.ui import ChezmergeApp
    from chezmerge.logic import MergeItem, FileState, MergeScenario
else:
    from .ui import ChezmergeApp
    from .logic import MergeItem, FileState, MergeScenario

def create_dummy_data():
    """Generates a scenario for UI testing."""
    return [
        MergeItem(
            path=".bashrc",
            base=FileState(content="alias ll='ls -l'", path=".bashrc"),
            theirs=FileState(content="alias ll='ls -la'\nalias gs='git status'", path=".bashrc"),
            ours=FileState(content="alias ll='ls -l'\n# My custom alias\nalias gc='git commit'", path=".bashrc"),
            template=FileState(content="alias ll='ls -l'\n# My custom alias\nalias gc='git commit'", path="dot_bashrc", is_template=True),
            scenario=MergeScenario.CONFLICT
        ),
        MergeItem(
            path=".config/nvim/init.vim",
            base=FileState(content="set number", path="init.vim"),
            theirs=FileState(content="set number\nset relativenumber", path="init.vim"),
            ours=FileState(content="set number\ncolorscheme gruvbox", path="init.vim"),
            template=FileState(content="set number\ncolorscheme {{ .theme }}", path="dot_config/nvim/init.vim", is_template=True),
            scenario=MergeScenario.TEMPLATE_DIVERGENCE
        )
    ]

def run():
    items = create_dummy_data()
    app = ChezmergeApp(items)
    result = app.run()
    
    if result:
        print("\n--- Merge Complete! Results: ---")
        for item in result:
            print(f"\nFile: {item.path}")
            print(f"Final Content:\n{item.template.content}")
            print("-" * 20)

if __name__ == "__main__":
    run()
