# 03 Template Logic Preservation

## Objective
Verify that the TUI correctly handles `chezmoi` templates. Specifically, ensure that the user edits the **template source** (with `{{ ... }}` logic) while seeing the **rendered** context from Upstream and Local.

## Prerequisites
*   `uv` installed.
*   `git` installed.
*   **Set the Tool Path**:
    ```bash
    export TOOL_REPO="$HOME/repos/chezmerge"
    ```

## 1. Setup Test Environment
Run the following block to create a scenario where a local template needs to incorporate an upstream change.

```bash
# 1. Clean up
rm -rf /tmp/qa-03
mkdir -p /tmp/qa-03
export QA_ROOT="/tmp/qa-03"

# 2. Create Upstream
git init --bare "$QA_ROOT/upstream.git"
git clone "$QA_ROOT/upstream.git" "$QA_ROOT/maintainer"

# 3. Create Initial State
cd "$QA_ROOT/maintainer"
echo "alias ll='ls -l'" > .bashrc
git add .
git commit -m "Initial commit"
git push origin master

# 4. Initialize User (Local) with a Template
cd "$QA_ROOT"
uv run --directory "$TOOL_REPO" -m chezmerge.main \
    --repo "$QA_ROOT/upstream.git" \
    --source "$QA_ROOT/local"

# Convert .bashrc to a template locally
cd "$QA_ROOT/local"
mv dot_bashrc dot_bashrc.tmpl
echo "alias ll='ls -{{ .ls_flags }}'" > dot_bashrc.tmpl
# Note: In a real chezmoi repo, .ls_flags would be in a data file. 
# For this test, we are verifying the TUI presents the .tmpl file for editing.

# 5. Create Upstream Change
cd "$QA_ROOT/maintainer"
echo "alias gs='git status'" >> .bashrc
git commit -am "Upstream: Add git alias"
git push
```

## 2. Execute Test
Run the tool:

```bash
uv run --directory "$TOOL_REPO" -m chezmerge.main \
    --repo "$QA_ROOT/upstream.git" \
    --source "$QA_ROOT/local"
```

## 3. TUI Verification Steps
1.  **Identify File**: The title should indicate it is merging `dot_bashrc.tmpl`.
2.  **Theirs (Context)**: Should show the rendered upstream version:
    ```bash
    alias ll='ls -l'
    alias gs='git status'
    ```
3.  **Ours (Context)**: Should show your local rendered version (if the engine supports rendering) or the previous base.
4.  **Template (Editor)**: **CRITICAL**: This pane must show the raw template logic:
    ```bash
    alias ll='ls -{{ .ls_flags }}'
    ```

## 4. Interaction Steps
1.  In the **Template** pane, manually add the new alias while preserving the template tag:
    ```bash
    alias ll='ls -{{ .ls_flags }}'
    alias gs='git status'
    ```
2.  Press `Ctrl+S` to save.

## 5. Verification
The app should exit. Verify the file content on disk:

```bash
cat /tmp/qa-03/local/dot_bashrc.tmpl
```

**Expected Output:**
```text
alias ll='ls -{{ .ls_flags }}'
alias gs='git status'
```

**Pass Criteria**: The template logic `{{ .ls_flags }}` was preserved and not replaced by the literal `l` from the upstream/rendered views.
