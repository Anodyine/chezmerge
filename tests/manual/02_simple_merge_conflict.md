# 02 Simple Merge Conflict

## Objective
Verify that the TUI correctly displays conflicting changes from Upstream and Local, allows the user to manually edit the result, and saves the merged content to the local file.

## Prerequisites
*   `uv` installed.
*   `git` installed.

## 1. Setup Test Environment
Run the following block in your terminal to create a fresh environment with a guaranteed conflict.

```bash
# 1. Clean up
rm -rf /tmp/qa-02
mkdir -p /tmp/qa-02
export QA_ROOT="/tmp/qa-02"

# 2. Create Upstream
git init --bare "$QA_ROOT/upstream.git"
git clone "$QA_ROOT/upstream.git" "$QA_ROOT/maintainer"

# 3. Create Initial State
cd "$QA_ROOT/maintainer"
echo "alias ll='ls -l'" > .bashrc
git add .
git commit -m "Initial commit"
git push origin master

# 4. Initialize User (Local)
cd "$QA_ROOT"
# Run your tool to init

export TOOL_REPO="~/repos/chezmerge"
uv run $OLDPWD/src/chezmerge/main.py --repo "$QA_ROOT/upstream.git" --source "$QA_ROOT/local"

# 5. Create Conflict
# Upstream adds a line
cd "$QA_ROOT/maintainer"
echo "alias gs='git status'" >> .bashrc
git commit -am "Upstream: Add git alias"
git push

# Local adds a DIFFERENT line
echo "# Local: Custom alias" >> "$QA_ROOT/local/dot_bashrc"
```

## 2. Execute Test
Run the tool from your project root:

```bash
uv run src/chezmerge/main.py --repo "/tmp/qa-02/upstream.git" --source "/tmp/qa-02/local"
```

## 3. TUI Verification Steps
The TUI should launch. Verify the following:

1.  **Layout**: You see three panes (Theirs, Result/Template, Ours).
2.  **Theirs (Left/Top)**: Shows `alias gs='git status'`.
3.  **Ours (Right/Bottom)**: Shows `# Local: Custom alias`.
4.  **Result (Center)**: Shows the current local content (or a raw conflict marker if we implemented that, but currently it defaults to "Ours").

## 4. Interaction Steps
1.  Click or navigate to the **Result/Template** pane.
2.  Edit the text to look like this (combining both):
    ```bash
    alias ll='ls -l'
    alias gs='git status'
    # Local: Custom alias
    ```
3.  Press `Ctrl+S` (or your defined Save keybinding).

## 5. Verification
The app should exit. Verify the file content on disk:

```bash
cat /tmp/qa-02/local/dot_bashrc
```

**Expected Output:**
```text
alias ll='ls -l'
alias gs='git status'
# Local: Custom alias
```

## 6. Idempotency Check
Run the tool one last time:
```bash
uv run src/chezmerge/main.py --repo "/tmp/qa-02/upstream.git" --source "/tmp/qa-02/local"
```
**Expected Output:**
`No upstream changes detected.`
