# QA Plan 2: End-to-End Workflow (HTTPS)

## Objective
Verify the full lifecycle using a real public repository via HTTPS. This tests the "Init" phase with real network cloning and the "Update" phase by simulating upstream activity.

## Prerequisites
1.  `uv` installed.
2.  `git` installed.
3.  A spare directory to act as the "Local Chezmoi Repo".

## Test Steps

### 1. Test Initialization (HTTPS)
We will use a popular, simple dotfiles repository (e.g., `mathiasbynens/dotfiles`) to test the cloning and import process.

```bash
# 1. Prepare Local Directory (Ensure it is empty)
rm -rf /tmp/local-chezmoi

# 2. Run Initialization
# We use a specific inner path because this repo puts files in the root
uv run src/chezmerge/main.py \
  --repo https://github.com/mathiasbynens/dotfiles.git \
  --source /tmp/local-chezmoi
```

**Verification:**
*   Check `/tmp/local-chezmoi`.
*   It should contain "chezmoified" files like `dot_bash_profile`, `dot_gitconfig`, etc.
*   It should contain `.merge_workspace/base` and `.merge_workspace/latest`.

### 2. Simulate Divergence (The "Merge" Scenario)
Since we cannot push to the public `mathiasbynens/dotfiles` repo, we will simulate an upstream update by manually modifying the `latest` clone in our workspace.

**A. Simulate Upstream Change (Theirs)**
```bash
# Go into the 'latest' workspace clone
cd /tmp/local-chezmoi/.merge_workspace/latest

# Create a fake upstream change
echo "# Upstream alias update" >> .bash_profile
git commit -am "Simulate upstream update"

# Return to root
cd -
```

**B. Create Local Change (Ours)**
```bash
# Edit the local chezmoi source file
echo "# My local customization" >> /tmp/local-chezmoi/dot_bash_profile
```

### 3. Test Update Workflow
Run `chezmerge` again. It should fetch (which will be a no-op or safe rebase) and then detect the divergence between `base` and our modified `latest`.

```bash
uv run src/chezmerge/main.py \
  --repo https://github.com/mathiasbynens/dotfiles.git \
  --source /tmp/local-chezmoi
```

**Verification:**
1.  **TUI Launch**: The TUI should appear for `.bash_profile`.
2.  **Context**:
    *   **Theirs**: Should show `# Upstream alias update`.
    *   **Ours**: Should show `# My local customization`.
3.  **Action**:
    *   Edit the **Template** pane to combine them.
    *   Press `Ctrl+S`.
4.  **Result**:
    *   App exits.
    *   Check `/tmp/local-chezmoi/dot_bash_profile`. It should contain both lines.
    *   Run the command again. It should say "No upstream changes detected".
```
