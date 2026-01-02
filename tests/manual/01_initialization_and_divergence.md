# 01 Initialization and Divergence

## Objective
Verify the full lifecycle: Initialization, Upstream Updates, and Local Divergence using a local git repository.

## Prerequisites
*   `uv` installed.
*   `git` installed.
*   **Set the Tool Path**:
    ```bash
    export TOOL_REPO="$HOME/repos/chezmerge"
    ```

## Test Steps

### 1. Setup "Upstream" Repository
We will create a "bare" git repository to act as the server, and a "maintainer" folder to push changes to it.

```bash
# 1. Clean previous runs
rm -rf /tmp/qa-01
mkdir -p /tmp/qa-01
export QA_ROOT="/tmp/qa-01"

# 2. Create the "Server"
git init --bare "$QA_ROOT/upstream.git"

# 3. Configure "Maintainer" and Initial Commit
git clone "$QA_ROOT/upstream.git" "$QA_ROOT/maintainer"
cd "$QA_ROOT/maintainer"

# Create basic files
echo "alias ll='ls -l'" > .bashrc
echo "set number" > .vimrc

git add .
git commit -m "Initial commit"
git push origin master
```

### 2. Test Initialization (The User)
Now act as the user installing these dotfiles.

```bash
# Run from anywhere
uv run --directory "$TOOL_REPO" -m chezmerge.main \
  --repo "$QA_ROOT/upstream.git" \
  --source "$QA_ROOT/local"
```

**Verification:**
*   Check `$QA_ROOT/local`.
*   It should contain `dot_bashrc` and `dot_vimrc`.
*   It should contain `.merge_workspace/base` and `.merge_workspace/latest`.

### 3. Create Divergence (The "Merge" Scenario)

**A. Update Upstream (Theirs)**
Act as the maintainer pushing an update.
```bash
cd "$QA_ROOT/maintainer"
echo "alias gs='git status'" >> .bashrc
git commit -am "Add git alias"
git push
```

**B. Update Local (Ours)**
Act as the user customizing their files.
```bash
# Edit the local chezmoi source file
echo "# My local customization" >> "$QA_ROOT/local/dot_bashrc"
```

### 4. Test Update Workflow
Run `chezmerge` again. It should fetch the new commits from the local "upstream" and detect the conflict.

```bash
uv run --directory "$TOOL_REPO" -m chezmerge.main \
  --repo "$QA_ROOT/upstream.git" \
  --source "$QA_ROOT/local"
```

**Verification:**
1.  **TUI Launch**: The TUI should appear for `.bashrc`.
2.  **Context**:
    *   **Theirs**: Should show the new `alias gs`.
    *   **Ours**: Should show `# My local customization`.
3.  **Action**:
    *   Edit the **Template** pane to combine them.
    *   Press `Ctrl+S`.
4.  **Result**:
    *   App exits.
    *   Check `$QA_ROOT/local/dot_bashrc`. It should contain the combined content.
    *   Run the command again. It should say "No upstream changes detected".
