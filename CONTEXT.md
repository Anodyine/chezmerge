# Chezmerge Project Context

## Executive Summary
Chezmerge is a state-aware merge assistant for `chezmoi` users, designed to handle complex updates from upstream dotfile repositories. It transforms the merge process from a manual git chore into a structured, 4-way merge workflow within a Textual TUI.

## Architectural Blueprint

### 1. Core Philosophy
*   **Distribution**: Distributed as a `uv tool`.
*   **State Management**: 
    *   State is stored *inside* the user's chezmoi source repository.
    *   Uses `.merge_workspace/` for temporary file generation.
    *   Uses `.last_external_commit` to track the upstream pointer.
*   **Backend**: 
    *   **Dual-Submodule System**: Manages two git submodules within the user's repo:
        *   `base`: Pinned to the last known good commit (Common Ancestor).
        *   `latest`: The target upstream commit (Theirs).

### 2. The 4-Way Merge Model
Unlike standard 3-way merges, Chezmerge accounts for the `chezmoi` template layer:
1.  **BASE**: Common ancestor (from `base` submodule).
2.  **THEIRS**: Upstream update (from `latest` submodule).
3.  **OURS**: Local rendered config (de-chezmoified).
4.  **TEMPLATE**: The actual source file (`.tmpl`) the user edits.

### 3. Decision Engine
The engine analyzes the 4-way state to automate trivial merges:
*   **Already Synced**: Yours == Theirs → Skip.
*   **Auto-Update**: Yours == Base && Theirs != Base → Update (if safe).
*   **Auto-Keep**: Yours != Base && Theirs == Base → Keep Yours.
*   **Conflict/Template**: Yours != Base && Theirs != Base → **Open TUI**.
*   **Template Safety**: If the target is a template, the engine defaults to the TUI to prevent overwriting logic with raw upstream content.

## User Experience (UX)

### TUI Layout (Textual)
A **3x2 Grid** designed to maximize context:
*   **Top Row (Context)**:
    *   **Left**: `Theirs` (Diff vs Base) - What changed upstream?
    *   **Center**: `Base` (Content) - What was the common starting point?
    *   **Right**: `Ours` (Diff vs Base) - What have I changed locally?
*   **Bottom Row (Action)**:
    *   **Editor**: Full-width editor for the `TEMPLATE` file.

### Workflow
1.  **Launch**: `chezmerge` (auto-detects repo).
2.  **Review**: User sees the 3-pane context and edits the template below.
3.  **Verify**: (Future) "Snap-Back" feature re-renders the template to preview the result in the "Ours" column.
4.  **Commit**: `Ctrl+S` saves the template and advances to the next file.

## Current Status
*   **Scaffolding**: Project structure initialized with `uv` and `pyproject.toml`.
*   **Legacy Code**: Reference logic moved to `reference-project/`.
*   **UI Prototype**: Functional Textual app implementing the 3x2 grid layout with dummy data.
*   **Logic**: Initial data structures (`FileState`, `MergeScenario`) defined.

## Roadmap
1.  **Git Backend**: Implement `git_ops.py` to handle submodule manipulation and file extraction.
2.  **Logic Integration**: Connect the `DecisionEngine` to real git data.
3.  **UI Wiring**: Replace dummy data with real file content and diffs.
4.  **Snap-Back**: Implement the re-rendering loop for immediate feedback.
