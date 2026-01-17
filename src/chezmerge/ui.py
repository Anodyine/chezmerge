import os
import shutil
import subprocess
import tempfile
from pathlib import Path

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
        ("ctrl+c", "copy", "Copy"),
        ("ctrl+v", "paste", "Paste"),
        ("ctrl+t", "cycle_focus", "Cycle Pane"),
        ("ctrl+m", "edit_external", "Vim/External Editor"),
    ]

    def __init__(self, items: list[MergeItem], external_editor: str | None = None):
        super().__init__()
        self.items = items
        self.current_index = 0
        self.external_editor = external_editor

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

        # Determine next pane
        next_id = "template"
        if current and current.id in order:
            idx = order.index(current.id)
            next_id = order[(idx + 1) % len(order)]

        self.query_one(f"#{next_id}").focus()

    def action_edit_external(self) -> None:
        """Launch an external editor to handle the merge."""
        if self.external_editor:
            editor = shutil.which(self.external_editor) or self.external_editor
        else:
            editor = shutil.which("nvim") or shutil.which("vim") or shutil.which("vi")

        if not editor:
            self.notify("No editor found", severity="error")
            return

        # Get current content from widgets
        theirs = self.query_one("#theirs", TextArea).text
        base = self.query_one("#base", TextArea).text
        ours = self.query_one("#ours", TextArea).text
        template_widget = self.query_one("#template", TextArea)
        template = template_widget.text

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Define files
            result_file = tmp_path / "MERGE_RESULT.txt"
            theirs_file = tmp_path / "theirs.txt"
            base_file = tmp_path / "base.txt"
            ours_file = tmp_path / "ours.txt"

            # Write content
            result_file.write_text(template)
            theirs_file.write_text(theirs)
            base_file.write_text(base)
            ours_file.write_text(ours)

            # Prepare command
            cmd = [editor]

            # Check if we are using neovim for the custom layout
            if "nvim" in Path(editor).name:
                # Create a vim script to handle layout and highlighting
                # This avoids the "Too many arguments" error with multiple -c flags
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
                    
                    "wincmd j"
                ]
                vim_script.write_text("\n".join(script_content))
                
                # Open result file and source the layout script
                cmd.append(str(result_file))
                cmd.extend(["-S", str(vim_script)])
            else:
                # Fallback for vim/vi: Open in tabs
                cmd.extend(["-p", str(result_file), str(theirs_file), str(base_file), str(ours_file)])

            # Suspend and run editor
            with self.suspend():
                exit_code = subprocess.call(cmd)

            # Read back result
            if result_file.exists():
                new_content = result_file.read_text()
                template_widget.text = new_content

                # If in auto-mode (CLI arg) and editor exited cleanly, save and next immediately
                if self.external_editor and exit_code == 0:
                    self.action_save_merge()
                else:
                    self.notify("Returned from external editor")

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

        # Auto-launch external editor if configured
        if self.external_editor:
            # Use call_later to trigger immediately without waiting for a UI render
            self.call_later(self.action_edit_external)

    def action_save_merge(self):
        # Save current state back to the item
        if self.current_index < len(self.items):
            current_content = self.query_one("#template", TextArea).text
            self.items[self.current_index].template.content = current_content

        # Advance
        self.current_index += 1
        self.load_current_item()
