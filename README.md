# Chezmerge

**The intelligent merge assistant for Chezmoi users.**

[![Built with Textual](https://img.shields.io/badge/Built%20with-Textual-000000.svg)](https://github.com/Textualize/textual)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

Keeping your dotfiles in sync with an upstream repository (like [ML4W](https://github.com/mylinuxforwork/dotfiles) or [Folke's dots](https://github.com/folke/dot)) is difficult. When you customize your setup, you diverge from the source. When the upstream author updates their code, standard `git merge` often fails or overwrites your hard work—especially when dealing with Chezmoi templates.

**Chezmerge** solves this by providing a dedicated **Terminal User Interface (TUI)** to visualize, edit, and resolve conflicts between your local customizations and upstream updates.

---

## ✨ Features

* **Visual Merge Resolution:** See exactly what changed across upstream, base, and local panes, including upstream deletions.
* **Template Awareness:** Understands `chezmoi` file naming conventions (`dot_`, `private_`, `executable_`) and maps templates to the same target path as upstream dotfiles.
* **Smart Analysis:** Automatically detects safe updates versus complex conflicts, including non-overlapping changes inside template source files.
* **External Editor Integration:** * Seamlessly open the current merge in **Neovim**, **Vim**, or **Vi**.
    * **Neovim Special:** Launches a custom 4-pane split layout designed specifically for merging.
* **Safety First:** Operates on git objects and a local submodule in `.chezmerge-upstream`. Your actual source files are only updated once you explicitly save a merge.

---

## 🚀 Installation

Because Chezmerge is currently in development, you install it by cloning the source and installing it as a local tool.

### 1. Prerequisites
* **Python 3.10+**
* **Git**
* **uv** (Recommended) or **pip**

### 2. Clone and Install
Cloning the repository allows you to install the package in "editable" mode or as a global tool.

```bash
# Clone the repository
git clone https://github.com/anodyine/chezmerge.git
cd chezmerge

# Install as a global tool using uv (Recommended)
uv tool install .
```
OR
```bash
git clone https://github.com/anodyine/chezmerge.git
cd chezmerge

# OR install via pip
pip install .
```
> [!TIP]
> **Why uv?** Using `uv tool install` creates an isolated virtual environment for Chezmerge so its dependencies won't conflict with other Python projects on your system.

---

## 🛠 Usage & Quick Start

### 1. Navigate to your chezmoi source directory
You must run Chezmerge from the root of your Chezmoi source:
```bash
cd $(chezmoi source-path)
```

### 2. Run Chezmerge
Chezmerge has two phases:

**First run (initialize workspace):**
```bash
chezmerge --repo https://github.com/mylinuxforwork/dotfiles.git --inner-path dotfiles
```

**Subsequent runs (fetch + merge upstream updates):**
```bash
chezmerge --inner-path dotfiles
```

> [!NOTE]
> `--repo` is only required on first run when `.chezmerge-upstream` does not exist yet.

**Common Options:**
* `--inner-path <path>`: Use this when dotfiles are in a subdirectory of the upstream repo (for ML4W, use `--inner-path dotfiles`).
* `--dry-run`: Simulate merge logic without writing files or committing.
* `--abort`: Throw away the current uncommitted chezmerge session and reset the repo back to the pre-merge state.
* `--undo-last`: Revert the most recent committed chezmerge merge by creating a new git commit.

Chezmerge requires a clean working tree before starting a merge. Commit, stash, or discard any pending changes first. The exception is `--abort`, which is specifically meant to recover an in-progress chezmerge session.

### 3. The Merge Process
1.  **Analysis:** Chezmerge fetches upstream changes into `.chezmerge-upstream` and compares them to your local files.
2.  **Auto-Merge:** Files you haven't touched are updated automatically. If a local `.tmpl` file and an upstream raw dotfile render to the same target, Chezmerge will also merge non-overlapping changes into the template source automatically.
3.  **Conflict Resolution:** If both you and upstream changed the same part of a file, or if upstream deleted a file you modified locally, the TUI opens. For templates, this means you only drop into manual resolution when the template source cannot be merged safely.
4.  **Finalize:** Once all conflicts are resolved, Chezmerge stages merged files, advances the `.chezmerge-upstream` submodule pointer, and auto-commits with:
```bash
chore(chezmerge): Merge upstream changes
```
## 🧠 How It Works

Chezmerge uses a **3-way merge strategy** to determine how to handle every file. It compares three versions of every file:

1.  **Base:** The state of the file from the last time you synced (the current commit of the submodule).
2.  **Theirs:** The new version from the upstream repository.
3.  **Ours:** Your current local version.



Based on the differences, it assigns one of the following scenarios:

### 🟢 Automatic Actions (No User Intervention)

* **Safe Update (`AUTO_UPDATE`):**
    * *Logic:* You haven't changed the file (`Ours == Base`), but upstream has (`Theirs != Base`).
    * *Action:* Chezmerge automatically updates your file to match upstream.
* **Keep Local (`AUTO_KEEP`):**
    * *Logic:* You customized the file (`Ours != Base`), but upstream hasn't touched it (`Theirs == Base`).
    * *Action:* Chezmerge keeps your custom version.
* **Already Synced (`ALREADY_SYNCED`):**
    * *Logic:* Your file is already identical to the upstream version.
    * *Action:* Skipped.
* **Auto-Mergeable (`AUTO_MERGEABLE`):**
    * *Logic:* Both you and upstream changed the file, but in different places. Git can resolve this mathematically without conflicts.
    * *Action:* Chezmerge applies the merge automatically.
    * *Template behavior:* This also applies when your local file is a Chezmoi template. Chezmerge merges the upstream change into the raw `.tmpl` source so your template logic is preserved.

### 🔴 Manual Intervention (Opens TUI)

* **Conflict (`CONFLICT`):**
    * *Logic:* Both you and upstream changed the same lines of code. Git cannot resolve this automatically.
    * *Action:* Opens the **Interactive TUI** so you can manually edit the result.
* **Deletion Conflict (`DELETION_CONFLICT`):**
    * *Logic:* Upstream deleted the file, but you changed it locally since the last sync.
    * *Action:* Opens the merge UI so you can either keep the file as reference for later repair or delete it to match upstream.
* **Template Divergence (`TEMPLATE_DIVERGENCE`):**
    * *Logic:* The file is a Chezmoi template (`.tmpl`), and both your template source and upstream changed in a way that cannot be merged automatically.
    * *Action:* Chezmerge opens the TUI so you can resolve the conflict in the raw template source while still seeing the upstream, base, and rendered local context.

### What Template Users Should Expect

When a maintainer updates `.bashrc` upstream and your local source contains `dot_bashrc.tmpl`, Chezmerge treats them as the same target file.

* If upstream changed lines that do not overlap with your template edits, Chezmerge merges the upstream changes directly into `dot_bashrc.tmpl`.
* If upstream changed the same logical section as your template logic, Chezmerge stops and opens the merge UI or your configured external editor.
* The editable result is always the raw template source, never the rendered output, so template tags like `{{ ... }}` are preserved.

---

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
| `Ctrl+d` | **Delete To Match Upstream** for delete-vs-modified conflicts. Choose this when you want to align with upstream and drop your local copy. |
| `Ctrl+s` | **Save & Next**. For delete-vs-modified conflicts, this keeps the file as reference or lets you adapt it, but it does not guarantee upstream still invokes it. |
| `Ctrl+q` | **Quit** the application. |

For upstream deletion conflicts, Chezmerge intentionally does **not** treat “keep” as “fully resolved behavior.”

* Choose **Save & Next** when you want to preserve your local customization as reference material, especially if you plan to manually reconnect it later or use an LLM agent to migrate the behavior into the new upstream structure.
* Choose **Delete To Match Upstream** when you believe the upstream deletion reflects the new desired behavior and you do not need the old customization anymore.

---

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

* **Navigation:** Use `Ctrl+w` + `h/j/k/l` to move between splits.
* **Editing:** Edit the bottom window.
* **Finish:** Save and quit (`:wq`). The content will be loaded back into the TUI.

---

## 📂 Project Structure

* `src/chezmerge/ui.py`: The Textual TUI implementation.
* `src/chezmerge/logic.py`: The 3-way merge decision engine.
* `src/chezmerge/git_ops.py`: Git command wrappers and workspace management.
* `src/chezmerge/paths.py`: Utilities for normalizing Chezmoi paths (handling `dot_`, `private_` prefixes).

---

## ⚠️ Important Note on Submodules

Chezmerge uses a Git submodule to track the upstream repository. This means the upstream state is explicitly versioned within your dotfiles repository. When you complete a merge, Chezmerge will stage the updated submodule pointer for you to commit.
