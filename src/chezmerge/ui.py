from textual.app import App, ComposeResult
from textual.containers import Grid
from textual.widgets import Header, Footer, TextArea
from .logic import MergeItem

class ChezmergeApp(App[list[MergeItem]]):
    CSS = """
    Grid {
        layout: grid;
        grid-size: 3 2;
        grid-rows: 1fr 2fr;
        grid-columns: 1fr 1fr 1fr;
        height: 100%;
    }

    .pane {
        border: solid $secondary;
        height: 100%;
    }

    #template {
        column-span: 3;
        border: solid $primary;
    }
    """

    BINDINGS = [
        ("ctrl+s", "save_merge", "Save & Next"),
        ("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self, items: list[MergeItem]):
        super().__init__()
        self.items = items
        self.current_index = 0

    def compose(self) -> ComposeResult:
        yield Header()
        yield Grid(
            # Top Row: Context (Read Only)
            TextArea(id="theirs", read_only=True, classes="pane"),
            TextArea(id="base", read_only=True, classes="pane"),
            TextArea(id="ours", read_only=True, classes="pane"),
            
            # Bottom Row: Action (Editable)
            TextArea(id="template", classes="pane"),
        )
        yield Footer()

    def on_mount(self):
        self.load_current_item()

    def load_current_item(self):
        if not self.items or self.current_index >= len(self.items):
            self.exit(self.items)
            return

        item = self.items[self.current_index]
        self.sub_title = f"Merging [{self.current_index + 1}/{len(self.items)}]: {item.path}"

        # Helper to set text and title
        def set_pane(id, title, content):
            widget = self.query_one(f"#{id}", TextArea)
            widget.text = content
            widget.border_title = title

        set_pane("theirs", "Theirs (Upstream)", item.theirs.content)
        set_pane("base", "Base (Ancestor)", item.base.content)
        set_pane("ours", "Ours (Local)", item.ours.content)
        
        # Template is special: it gets focus
        template_widget = self.query_one("#template", TextArea)
        template_widget.text = item.template.content
        template_widget.border_title = f"Template (Editable): {item.path}"
        template_widget.focus()

    def action_save_merge(self):
        # Save current state back to the item
        if self.current_index < len(self.items):
            current_content = self.query_one("#template", TextArea).text
            self.items[self.current_index].template.content = current_content

        # Advance
        self.current_index += 1
        self.load_current_item()
