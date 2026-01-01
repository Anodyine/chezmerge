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
