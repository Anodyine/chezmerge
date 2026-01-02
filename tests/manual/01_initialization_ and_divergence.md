# QA Plan 2: End-to-End Workflow (Local Repo)

## Objective
Verify the full lifecycle using a local git repository. This simulates a remote upstream without requiring network access or GitHub credentials.

## Prerequisites
1.  `uv` installed.
2.  `git` installed.

## Test Steps

### 1. Setup "Upstream" Repository
We will create a "bare" git repository to act as the server, and a "maintainer" folder to push changes to it.

1.  **Clean previous runs**:
    ```bash
    rm -rf /tmp/qa-upstream.git /tmp/qa-maintainer /tmp/qa-local
    ```

2.  **Create the "Server"**:
    ```bash
    git init --bare /tmp/qa-upstream.git
    ```

3.  **Configure "Maintainer" and Initial Commit**:
    ```bash
    git clone /tmp/qa-upstream.git /tmp/qa-maintainer
    cd /tmp/qa-maintainer
    
    # Create basic files
    echo "alias ll='ls -l'" > .bashrc
    echo "set number" > .vimrc
    
    git add .
    git commit -m "Initial commit"
    git push origin master
    ```

### 2. Test Initialization (The User)
Now act as the user installing these dotfiles.

1.  **Run Initialization**:
    ```bash
    # Run from your project root
    uv run src/chezmerge/main.py \
      --repo /tmp/qa-upstream.git \
      --source /tmp/qa-local
    ```

**Verification:**
*   Check `/tmp/qa-local`.
*   It should contain `dot_bashrc` and `dot_vimrc`.
*   It should contain `.merge_workspace/base` and `.merge_workspace/latest`.

### 3. Create Divergence (The "Merge" Scenario)

**A. Update Upstream (Theirs)**
Act as the maintainer pushing an update.
```bash
cd /tmp/qa-maintainer
echo "alias gs='git status'" >> .bashrc
git commit -am "Add git alias"
git push
```

**B. Update Local (Ours)**
Act as the user customizing their files.
```bash
# Edit the local chezmoi source file
echo "# My local customization" >> /tmp/qa-local/dot_bashrc
```

### 4. Test Update Workflow
Run `chezmerge` again. It should fetch the new commits from the local "upstream" and detect the conflict.

```bash
# Run from your project root
uv run src/chezmerge/main.py \
  --repo /tmp/qa-upstream.git \
  --source /tmp/qa-local
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
    *   Check `/tmp/qa-local/dot_bashrc`. It should contain the combined content.
    *   Run the command again. It should say "No upstream changes detected".
```
