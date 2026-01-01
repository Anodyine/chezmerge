from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, TextArea
from textual.containers import Container

class ChezmergeApp(App):
    CSS = """
    .grid {
        layout: grid;
        grid-size: 2 2;
        height: 100%;
    }

    #diff_view {
        border: solid green;
    }

    #ours_view {
        border: solid blue;
    }

    #template_editor {
        column-span: 2;
        border: solid red;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(classes="grid"):
            yield Static("Q1: BASE vs THEIRS", id="diff_view")
            yield Static("Q2: OURS (Rendered)", id="ours_view")
            yield TextArea("Q3: TEMPLATE", id="template_editor")
        yield Footer()
