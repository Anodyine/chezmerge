from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, TextArea
from textual.containers import Container
from textual.binding import Binding

class ChezmergeApp(App):
    CSS = """
    .grid {
        layout: grid;
        grid-size: 3 2;
        grid-rows: 1fr 1fr;
        height: 100%;
    }

    .panel {
        border: solid $secondary;
        padding: 0 1;
    }

    #view_theirs {
        border-title: "Theirs (Diff vs Base)";
        background: $error 10%;
    }

    #view_base {
        border-title: "Base (Common Ancestor)";
        background: $surface;
    }

    #view_ours {
        border-title: "Ours (Diff vs Base)";
        background: $success 10%;
    }

    #editor {
        column-span: 3;
        border: solid $accent;
        border-title: "Template Editor (Source)";
    }
    """

    BINDINGS = [
        Binding("ctrl+s", "save_merge", "Save & Continue"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        # Dummy Data for Visualization
        dummy_base = "setting_a = 'default'\nsetting_b = 'off'"
        
        dummy_theirs_diff = (
            "--- base\n"
            "+++ theirs\n"
            "@@ -1,2 +1,2 @@\n"
            "-setting_a = 'default'\n"
            "+setting_a = 'upstream_change'\n"
            " setting_b = 'off'"
        )
        
        dummy_ours_diff = (
            "--- base\n"
            "+++ ours\n"
            "@@ -1,2 +1,2 @@\n"
            " setting_a = 'default'\n"
            "-setting_b = 'off'\n"
            "+setting_b = 'local_change'"
        )

        dummy_template = (
            "setting_a = '{{ .upstream_val }}'\n"
            "setting_b = '{{ .local_val }}'"
        )

        yield Header()
        with Container(classes="grid"):
            yield Static(dummy_theirs_diff, id="view_theirs", classes="panel")
            yield Static(dummy_base, id="view_base", classes="panel")
            yield Static(dummy_ours_diff, id="view_ours", classes="panel")
            yield TextArea(dummy_template, language="python", id="editor")
        yield Footer()

    def action_save_merge(self):
        """Handle the save action."""
        # In the future, this will write the editor content to disk
        self.exit(result="saved")
