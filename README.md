# Chezmerge

**The intelligent merge assistant for Chezmoi users.**

[![Built with Textual](https://img.shields.io/badge/Built%20with-Textual-000000.svg)](https://github.com/Textualize/textual)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

Keeping your dotfiles in sync with an upstream repository (like [ML4W](https://github.com/mylinuxforwork/dotfiles) or [Folke's dots](https://github.com/folke/dot)) is difficult. When you customize your setup, you diverge from the source. When the upstream author updates their code, standard `git merge` often fails or overwrites your hard work—especially when dealing with Chezmoi templates.

**Chezmerge** solves this by providing a dedicated **Terminal User Interface (TUI)** to visualize, edit, and resolve conflicts between your local customizations and upstream updates.

---

## ✨ Features

* **Visual 3-Way Merge:** See exactly what changed across three panes (Theirs, Base, Ours).
* **Template Awareness:** Understands `chezmoi` file naming conventions (`dot_`, `private_`, `executable_`).
* **Smart Analysis:** Automatically detects safe updates versus complex conflicts.
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
Point the tool to the upstream repository you want to sync with.
*Example:*
```bash
chezmerge --repo https://github.com/mylinuxforwork/dotfiles.git --inner-path dotfiles
```
 **Common Options:**
* `--inner-path <path>`: If the dotfiles aren't at the repo root (e.g., `--inner-path dotfiles`).
* `--branch <name>`: Sync with a specific branch (defaults to the remote's default branch).
* `--dry-run`: Simulate the process without changing any files.

### 3. The Merge Process
1.  **Analysis:** Chezmerge fetches upstream changes into `.chezmerge-upstream` and compares them to your local files.
2.  **Auto-Merge:** Files you haven't touched are updated automatically.
3.  **Conflict Resolution:** If both you and upstream changed a file, the TUI opens.
4.  **Finalize:** Once all conflicts are resolved, Chezmerge stages the changes. You simply need to commit them:
```bash
git commit -m "chore: sync with upstream via chezmerge"
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

### 🔴 Manual Intervention (Opens TUI)

* **Conflict (`CONFLICT`):**
    * *Logic:* Both you and upstream changed the same lines of code. Git cannot resolve this automatically.
    * *Action:* Opens the **Interactive TUI** so you can manually edit the result.
* **Template Divergence (`TEMPLATE_DIVERGENCE`):**
    * *Logic:* The file is a Chezmoi template (`.tmpl`). Because templates contain logic that generates content, standard text merging is risky.
    * *Action:* Unless the files are identical, Chezmerge treats this as a conflict and opens the TUI. This ensures you can verify that your template logic is preserved correctly.

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
| `Ctrl+s` | **Save & Next**. Saves the current file and moves to the next conflict. |
| `Ctrl+q` | **Quit** the application. |

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