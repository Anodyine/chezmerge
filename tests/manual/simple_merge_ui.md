# QA Plan: UI & Workflow Verification

## Objective
Verify that the Textual TUI correctly renders the 4-way merge state, allows editing, and persists changes across a multi-file workflow.

## Prerequisites
1.  Ensure you are in the project root.
2.  Ensure `uv` is installed.

## Test Steps

### 1. Launch the Application
Run the application using `uv`:
```bash
uv run src/chezmerge/main.py
```

### 2. Verify Screen 1: `.bashrc`
*   **Check Layout**: You should see a 3x2 grid.
    *   **Top Left (Theirs)**: Should show `alias ll='ls -la'` and `alias gs='git status'`.
    *   **Top Center (Base)**: Should show `alias ll='ls -l'`.
    *   **Top Right (Ours)**: Should show `alias gc='git commit'`.
    *   **Bottom (Template)**: Should be editable.
*   **Action**: 
    1.  Click into the bottom "Template" pane.
    2.  Edit the text to include both changes:
        ```bash
        alias ll='ls -la'
        alias gs='git status'
        # My custom alias
        alias gc='git commit'
        ```
    3.  Press `Ctrl+S` to save and continue.

### 3. Verify Screen 2: `.config/nvim/init.vim`
*   **Check Transition**: The title should update to `Merging [2/2]: .config/nvim/init.vim`.
*   **Check Content**:
    *   **Template Pane**: Should show `colorscheme {{ .theme }}` (verifying template logic is preserved).
*   **Action**:
    1.  Add `set relativenumber` to the Template pane.
    2.  Press `Ctrl+S`.

### 4. Verify Output
*   The application should exit.
*   The terminal should print the "Final Content" for both files.
*   **Pass Criteria**: The printed output matches the edits you made in steps 2 and 3.
