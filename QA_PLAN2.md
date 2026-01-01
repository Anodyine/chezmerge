# QA Plan 2: End-to-End Workflow

## Objective
Verify the full lifecycle: Initialization from an upstream repo, "chezmoification" of files, and handling subsequent updates via the TUI.

## Prerequisites
1.  `uv` installed.
2.  `git` installed.
3.  A spare directory to act as the "Upstream Repo".
4.  A spare directory to act as the "Local Chezmoi Repo".

## Test Steps

### 1. Setup Simulation Environment
Run these commands in your terminal to create the testbed:

```bash
# 1. Create the "Upstream" Repo
mkdir -p /tmp/upstream-dots/dots
cd /tmp/upstream-dots
git init
# Create a basic config
echo "alias ll='ls -l'" > dots/.bashrc
echo "set number" > dots/.vimrc
git add .
git commit -m "Initial upstream commit"

# 2. Prepare Local Directory (Ensure it is empty)
rm -rf /tmp/local-chezmoi
```

### 2. Test Initialization
Run `chezmerge` to initialize the local repo from the upstream.

```bash
# Run from your project root
uv run src/chezmerge/main.py \
  --repo /tmp/upstream-dots \
  --inner-path dots \
  --source /tmp/local-chezmoi
```

**Verification:**
*   Check `/tmp/local-chezmoi`.
*   It should contain `dot_bashrc` and `dot_vimrc`.
*   It should contain `.merge_workspace/base` and `.merge_workspace/latest`.

### 3. Simulate Divergence (The "Merge" Scenario)

**A. Update Upstream (Theirs)**
```bash
cd /tmp/upstream-dots
echo "alias gs='git status'" >> dots/.bashrc
git add dots/.bashrc
git commit -m "Add git alias"
```

**B. Update Local (Ours)**
```bash
# Edit the local file manually
echo "# My local customization" >> /tmp/local-chezmoi/dot_bashrc
```

### 4. Test Update Workflow
Run `chezmerge` again. It should detect the changes.

```bash
uv run src/chezmerge/main.py \
  --repo /tmp/upstream-dots \
  --inner-path dots \
  --source /tmp/local-chezmoi
```

**Verification:**
1.  **TUI Launch**: The TUI should appear.
2.  **Context**:
    *   **Theirs**: Should show the new `alias gs`.
    *   **Ours**: Should show `# My local customization`.
3.  **Action**:
    *   Edit the **Template** pane to combine them:
        ```bash
        alias ll='ls -l'
        alias gs='git status'
        # My local customization
        ```
    *   Press `Ctrl+S`.
4.  **Result**:
    *   App exits.
    *   Check `/tmp/local-chezmoi/dot_bashrc`. It should contain the combined content.
    *   Run the command again. It should say "No upstream changes detected" (because the base pointer was updated).
```
