# Chezmerge

**The intelligent merge assistant for Chezmoi users.**

Keeping your dotfiles in sync with an upstream repository (like [ML4W](https://github.com/mylinuxforwork/dotfiles) or [Folke's dots](https://github.com/folke/dotfiles)) is difficult. When you customize your setup, you diverge from the source. When the upstream author updates their code, standard `git merge` often fails or overwrites your hard work—especially when dealing with Chezmoi templates.

**Chezmerge** solves this by providing a dedicated **Terminal User Interface (TUI)** to visualize, edit, and resolve conflicts between your local customizations and upstream updates.

## ✨ Features

*   **Visual 3-Way Merge:** See exactly what changed.
    *   **Theirs:** The new upstream version.
    *   **Base:** The common ancestor (what the file looked like before updates).
    *   **Ours:** Your current local version.
    *   **Result:** The editable output template.
*   **Template Awareness:** Understands `chezmoi` file naming conventions (`dot_`, `private_`, `executable_`).
*   **Smart Analysis:** Automatically detects:
    *   Files you haven't touched (Safe to update).
    *   Files you customized but they didn't touch (Safe to keep).
    *   **Conflicts:** Files changed by both parties.
*   **External Editor Integration:**
    *   Seamlessly open the current merge in **Neovim**, **Vim**, or **Vi**.
    *   **Neovim Special:** Opens a custom 4-pane split layout (Theirs/Base/Ours on top, Result on bottom) for a professional merge experience.
*   **Safety First:** Operates on git objects and local clones in a `.merge_workspace`. It does not overwrite your actual source files until you explicitly save the merge.

## 🚀 Installation

Chezmerge is a Python package managed with `uv`.

### Prerequisites
*   Python 3.10+
*   Git
*   (Optional) Neovim or Vim for external editing.

### Installing

Navigate to your project directory and install:

```bash
# Using uv (Recommended)
uv tool install .

# Or using pip
pip install .
```

## 🛠 Usage

1.  **Navigate to your chezmoi source directory:**
    ```bash
    cd $(chezmoi source-path)
    ```

2.  **Run Chezmerge:**
    ```bash
    chezmerge --repo <upstream_git_url>
    ```
    *Example:*
    ```bash
    chezmerge --repo https://github.com/mylinuxforwork/dotfiles.git
    ```
    
    **Options:**
    *   `--dry-run`: Simulate the merge process and print what would happen without changing any files.
    *   `--inner-path <path>`: Specify a subdirectory in the upstream repo if the dotfiles aren't at the root (e.g., `--inner-path dotfiles`).

3.  **The Merge Process:**
    The application will fetch the latest upstream changes into a local workspace (`.merge_workspace`) and analyze them against your local files.

## 🧠 How It Works

Chezmerge uses a **3-way merge strategy** to determine how to handle every file. It compares three versions of every file:
1.  **Base:** The state of the file from the last time you synced.
2.  **Theirs:** The new version from the upstream repository.
3.  **Ours:** Your current local version.

Based on the differences, it assigns one of the following scenarios:

### 🟢 Automatic Actions (No User Intervention)

*   **Safe Update (`AUTO_UPDATE`):**
    *   *Logic:* You haven't changed the file (`Ours == Base`), but upstream has (`Theirs != Base`).
    *   *Action:* Chezmerge automatically updates your file to match upstream.
*   **Keep Local (`AUTO_KEEP`):**
    *   *Logic:* You customized the file (`Ours != Base`), but upstream hasn't touched it (`Theirs == Base`).
    *   *Action:* Chezmerge keeps your custom version.
*   **Already Synced (`ALREADY_SYNCED`):**
    *   *Logic:* Your file is already identical to the upstream version.
    *   *Action:* Skipped.
*   **Auto-Mergeable (`AUTO_MERGEABLE`):**
    *   *Logic:* Both you and upstream changed the file, but in different places. Git can resolve this mathematically without conflicts.
    *   *Action:* Chezmerge applies the merge automatically.

### 🔴 Manual Intervention (Opens TUI)

*   **Conflict (`CONFLICT`):**
    *   *Logic:* Both you and upstream changed the same lines of code. Git cannot resolve this automatically.
    *   *Action:* Opens the **Interactive TUI** so you can manually edit the result.
*   **Template Divergence (`TEMPLATE_DIVERGENCE`):**
    *   *Logic:* The file is a Chezmoi template (`.tmpl`). Because templates contain logic that generates content, standard text merging is risky.
    *   *Action:* Unless the files are identical, Chezmerge treats this as a conflict and opens the TUI. This ensures you can verify that your template logic (variables, conditionals) is preserved correctly against upstream changes.

## 🖥️ The Interactive TUI

When manual intervention is required, the TUI launches with a grid layout:

| Pane | Description |
| :--- | :--- |
| **Theirs (Top Left)** | The file as it exists in the upstream repo (Read-Only). |
| **Base (Top Mid)** | The common ancestor file (Read-Only). |
| **Ours (Top Right)** | Your current local version (Read-Only). |
| **Template (Bottom)** | **The Editable Result.** This is where you construct the final file. |

### Keyboard Shortcuts

| Key | Action |
| :--- | :--- |
| `Ctrl+t` | **Cycle Focus** between the panes. |
| `Ctrl+m` | **Open External Editor** (Vim/Neovim). |
| `Ctrl+s` | **Save & Next**. Saves the current file and moves to the next conflict. |
| `Ctrl+c` | Copy selected text. |
| `Ctrl+v` | Paste text into the Template pane. |
| `Ctrl+q` | Quit the application. |

## 📝 External Editor Workflow

Sometimes the built-in text box isn't enough. Pressing `Ctrl+m` launches your system editor.

### Neovim Users
If `nvim` is detected, Chezmerge opens a specialized layout designed for merging:

```
+-----------------+-----------------+-----------------+
|                 |                 |                 |
|     THEIRS      |      BASE       |      OURS       |
|  (readonly)     |   (readonly)    |   (readonly)    |
|                 |                 |                 |
+-----------------+-----------------+-----------------+
|                                                     |
|                   MERGE RESULT                      |
|                    (Editable)                       |
|                                                     |
+-----------------------------------------------------+
```

*   **Navigation:** Use `Ctrl+w` + `h/j/k/l` to move between splits.
*   **Editing:** Edit the bottom window.
*   **Finish:** Save and quit (`:wq`). The content will be loaded back into the TUI.

### Vim/Vi Users
Opens the four files in separate tabs (`-p` mode). Use `gt` and `gT` to switch tabs.

## 📂 Project Structure

*   `src/chezmerge/`: Source code.
    *   `ui.py`: The Textual TUI implementation.
    *   `logic.py`: The 3-way merge decision engine.
    *   `git_ops.py`: Git command wrappers and workspace management.
    *   `importer.py`: Handles initial import of upstream files.
    *   `paths.py`: Utilities for normalizing Chezmoi paths (handling `dot_`, `private_` prefixes).
*   `dev_logs/`: Development history.

## ⚠️ Important Note on .gitignore

Chezmerge downloads upstream repositories into a local cache directory. Ensure this is ignored in your dotfiles repo to prevent committing the upstream source code.

Add this to your `.gitignore`:
```text
.merge_workspace/
```
