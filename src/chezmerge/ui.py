import shutil
import subprocess
import tempfile
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Grid, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Static, TextArea

from .logic import MergeItem, MergeScenario


class DeletionConflictChoiceApp(App[str | None]):
    CSS = """
    Screen {
        align: center middle;
    }

    #dialog {
        width: 92;
        max-width: 92;
        padding: 1 2;
        border: solid $primary;
        background: $surface;
    }

    #actions {
        width: 100%;
        height: auto;
        align-horizontal: center;
        margin-top: 1;
    }

    Button {
        min-width: 18;
        margin: 0 1;
    }

    .hint {
        color: $text-muted;
        margin-top: 1;
    }
    """

    BINDINGS = [
        ("k", "keep_choice", "Keep"),
        ("d", "delete_choice", "Delete"),
        ("l", "look_choice", "Take A Look"),
        ("escape", "cancel_choice", "Quit"),
    ]

    def __init__(self, item: MergeItem):
        super().__init__()
        self.item = item

    def compose(self) -> ComposeResult:
        if self.item.deletion_reviewed:
            title = "Deleted Upstream: Keep What You Saved Or Delete It"
            body = (
                "You reviewed this file already.\n\n"
                "Keep: preserve what you just saved as reference for later adaptation.\n"
                "Delete: remove it to match upstream if you decided you do not need it.\n\n"
                "Keeping it will not automatically restore behavior if upstream no longer calls it."
            )
        else:
            title = "Deleted Upstream: Choose What To Do"
            body = (
                "Upstream deleted this file, but you changed it locally.\n\n"
                "Keep: preserve it as reference for later adaptation. This probably will not fix the behavior automatically.\n"
                "Delete: remove it if you know you do not need your local changes anymore.\n"
                "Take a look: inspect or edit it first if you want to refresh your memory before deciding."
            )

        yield Vertical(
            Static(title),
            Static(self.item.path, classes="hint"),
            Static(body),
            Horizontal(
                Button("Keep", id="keep", variant="primary"),
                Button("Delete", id="delete", variant="error"),
                Button("Take A Look", id="look"),
                id="actions",
            ),
            Static("Keys: K keep, D delete, L take a look, Esc quit", classes="hint"),
            id="dialog",
        )

    def on_mount(self) -> None:
        self.sub_title = self.item.path
        self.query_one("#keep", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.exit(event.button.id)

    def action_keep_choice(self) -> None:
        self.exit("keep")

    def action_delete_choice(self) -> None:
        self.exit("delete")

    def action_look_choice(self) -> None:
        self.exit("look")

    def action_cancel_choice(self) -> None:
        self.exit(None)


class BinaryConflictChoiceApp(App[str | None]):
    CSS = DeletionConflictChoiceApp.CSS

    BINDINGS = [
        ("k", "keep_choice", "Keep Mine"),
        ("t", "take_choice", "Take Theirs"),
        ("escape", "cancel_choice", "Quit"),
    ]

    def __init__(self, item: MergeItem):
        super().__init__()
        self.item = item

    def compose(self) -> ComposeResult:
        body = (
            "Upstream and local both changed this binary file.\n\n"
            "Keep my version: preserve your current local file.\n"
            "Take their version: replace your local file with the upstream copy.\n\n"
            "Chezmerge cannot open this binary file in the text merge editor."
        )

        yield Vertical(
            Static("Binary Conflict: Choose What To Do"),
            Static(self.item.path, classes="hint"),
            Static(body),
            Horizontal(
                Button("Keep My Version", id="keep", variant="primary"),
                Button("Take Their Version", id="take", variant="warning"),
                id="actions",
            ),
            Static("Keys: K keep mine, T take theirs, Esc quit", classes="hint"),
            id="dialog",
        )

    def on_mount(self) -> None:
        self.sub_title = self.item.path
        self.query_one("#keep", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.exit(event.button.id)

    def action_keep_choice(self) -> None:
        self.exit("keep")

    def action_take_choice(self) -> None:
        self.exit("take")

    def action_cancel_choice(self) -> None:
        self.exit(None)


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
        ("ctrl+s", "save_merge", "Keep / Save"),
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+c", "copy", "Copy"),
        ("ctrl+v", "paste", "Paste"),
        ("ctrl+t", "cycle_focus", "Cycle Pane"),
        ("ctrl+m", "edit_external", "Vim/External Editor"),
    ]

    def __init__(
        self,
        items: list[MergeItem],
        external_editor: str | None = None,
        deletion_inspect_mode: bool = False,
    ):
        super().__init__()
        self.items = items
        self.current_index = 0
        self.external_editor = external_editor
        self.deletion_inspect_mode = deletion_inspect_mode

    def action_copy(self):
        widget = self.screen.focused
        if isinstance(widget, TextArea):
            self.copy_to_clipboard(widget.selected_text)
            self.notify("Copied to clipboard")

    def action_paste(self):
        widget = self.screen.focused
        if isinstance(widget, TextArea) and not widget.read_only:
            self.paste_from_clipboard(lambda text: widget.replace_selection(text) if text else None)

    def action_cycle_focus(self):
        order = ["theirs", "base", "ours", "template"]
        current = self.screen.focused

        next_id = "template"
        if current and current.id in order:
            idx = order.index(current.id)
            next_id = order[(idx + 1) % len(order)]

        self.query_one(f"#{next_id}").focus()

    def action_edit_external(self) -> None:
        item = self.items[self.current_index]
        if self.external_editor:
            editor = shutil.which(self.external_editor) or self.external_editor
        else:
            editor = shutil.which("nvim") or shutil.which("vim") or shutil.which("vi")

        if not editor:
            self.notify("No editor found", severity="error")
            return

        theirs = self.query_one("#theirs", TextArea).text
        base = self.query_one("#base", TextArea).text
        ours = self.query_one("#ours", TextArea).text
        template_widget = self.query_one("#template", TextArea)
        template = item.template.content if item.scenario == MergeScenario.DELETION_CONFLICT else template_widget.text

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            result_file = tmp_path / "MERGE_RESULT.txt"
            theirs_file = tmp_path / "theirs.txt"
            base_file = tmp_path / "base.txt"
            ours_file = tmp_path / "ours.txt"

            result_file.write_text(template)
            theirs_file.write_text(theirs)
            base_file.write_text(base)
            ours_file.write_text(ours)

            cmd = [editor]
            if "nvim" in Path(editor).name:
                vim_script = tmp_path / "layout.vim"
                script_content = [
                    "highlight DiffAddGreen ctermbg=Green guibg=Green ctermfg=Black guifg=Black",
                    "highlight DiffTextGreen ctermbg=Green guibg=Green ctermfg=Black guifg=Black",
                    "highlight DiffAddRed ctermbg=Red guibg=Red ctermfg=Black guifg=Black",
                    "highlight DiffTextRed ctermbg=Red guibg=Red ctermfg=Black guifg=Black",
                    "highlight DiffChangeNone ctermbg=None guibg=None",
                    "highlight DiffDeleteRed ctermbg=Red guibg=Red ctermfg=Black guifg=Black",
                    "highlight DiffDeleteGreen ctermbg=Green guibg=Green ctermfg=Black guifg=Black",
                    f"topleft split {base_file} | set readonly",
                    f"vertical leftabove split {theirs_file} | set readonly",
                    "diffthis",
                    "set winhighlight=DiffAdd:DiffAddGreen,DiffChange:DiffChangeNone,DiffText:DiffTextGreen,DiffDelete:DiffDeleteRed",
                    "wincmd l",
                    "diffthis",
                    "set winhighlight=DiffAdd:DiffAddRed,DiffChange:DiffChangeNone,DiffText:DiffTextRed,DiffDelete:DiffDeleteGreen",
                    f"vertical rightbelow split {ours_file} | set readonly",
                    "diffthis",
                    "set winhighlight=DiffAdd:DiffAddGreen,DiffChange:DiffChangeNone,DiffText:DiffTextGreen,DiffDelete:DiffDeleteRed",
                    "wincmd j",
                ]
                vim_script.write_text("\n".join(script_content))
                cmd.append(str(result_file))
                cmd.extend(["-S", str(vim_script)])
            else:
                cmd.extend(["-p", str(result_file), str(theirs_file), str(base_file), str(ours_file)])

            with self.suspend():
                exit_code = subprocess.call(cmd)

            if result_file.exists():
                new_content = result_file.read_text()
                item.template.content = new_content

                if self.external_editor and exit_code == 0:
                    template_widget.text = new_content
                    self.action_save_merge()
                else:
                    template_widget.text = new_content
                    self.notify("Returned from external editor")

    def action_quit(self) -> None:
        self.exit(None)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Grid(
            TextArea(id="theirs", read_only=True, classes="pane"),
            TextArea(id="base", read_only=True, classes="pane"),
            TextArea(id="ours", read_only=True, classes="pane"),
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

        def set_pane(id, title, content):
            widget = self.query_one(f"#{id}", TextArea)
            widget.text = content
            widget.border_title = title

        theirs_title = "Theirs (Upstream)"
        base_title = "Base (Ancestor)"
        ours_title = "Ours (Local)"
        template_title = f"Template (Editable): {item.path}"
        if item.scenario == MergeScenario.DELETION_CONFLICT:
            theirs_title = "Theirs (Deleted Upstream)"
            base_title = "Base (Last Synced)"
            ours_title = "Ours (Current Local)"
            template_title = f"Inspect As Reference: {item.path}"

        set_pane("theirs", theirs_title, item.theirs.content)
        set_pane("base", base_title, item.base.content)
        set_pane("ours", ours_title, item.ours.content)

        template_widget = self.query_one("#template", TextArea)
        template_widget.text = item.template.content
        template_widget.border_title = template_title
        template_widget.read_only = False
        template_widget.focus()

        if item.scenario == MergeScenario.DELETION_CONFLICT:
            self.notify("Review or edit this file, then press Ctrl+s to keep it as reference.")

        if self.external_editor and (
            item.scenario != MergeScenario.DELETION_CONFLICT or self.deletion_inspect_mode
        ):
            self.call_later(self.action_edit_external)

    def action_save_merge(self):
        if self.current_index < len(self.items):
            item = self.items[self.current_index]
            item.template.content = self.query_one("#template", TextArea).text
            item.delete_on_save = False

        self.current_index += 1
        self.load_current_item()
