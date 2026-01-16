# 04 Auto Merge Capability

## Objective
Verify that `chezmerge` correctly handles non-conflicting changes (clean merges). 
When changes occur in different parts of a file, the tool should automatically combine them 
in the "Template" pane without generating conflict markers (`<<<<<<<`).

## Prerequisites
*   `uv` installed.
*   `git` installed.
*   **Set the Tool Path**:
    ```bash
    export TOOL_REPO="$HOME/repos/chezmerge"
    ```

## 1. Setup Test Environment
Run the following block in your terminal to create a fresh environment with a clean merge scenario.

```bash
# 1. Clean up
rm -rf /tmp/qa-04
mkdir -p /tmp/qa-04
export QA_ROOT="/tmp/qa-04"

# 2. Create Upstream
git init --bare "$QA_ROOT/upstream.git"
git clone "$QA_ROOT/upstream.git" "$QA_ROOT/maintainer"

# 3. Create Initial State
# We need enough lines so changes don't overlap contextually
cd "$QA_ROOT/maintainer"
cat <<EOF > config.conf
line 1: default
line 2: default
line 3: default
line 4: default
line 5: default
line 6: default
line 7: default
line 8: default
EOF
git add config.conf
git commit -m "Base: Initial config"
git push origin master

# 4. Initialize User (Local)
# This simulates the user running 'chezmerge init' or first run
cd "$QA_ROOT"
uv run --directory "$TOOL_REPO" -m chezmerge.main \
    --repo "$QA_ROOT/upstream.git" \
    --source "$QA_ROOT/local"

# 5. Create Divergence

# A. Upstream (Theirs) - Change the BOTTOM
cd "$QA_ROOT/maintainer"
sed -i 's/line 8: default/line 8: UPSTREAM_CHANGE/' config.conf
git commit -am "Upstream: Changed bottom"
git push

# B. Local (Ours) - Change the TOP
# Note: Since the upstream file is 'config.conf' (no leading dot), it remains 'config.conf'.
sed -i 's/line 1: default/line 1: LOCAL_CHANGE/' "$QA_ROOT/local/config.conf"
```

## 2. Execute Test
Run the tool pointing to the test environment:

```bash
uv run --directory "$TOOL_REPO" -m chezmerge.main \
    --repo "$QA_ROOT/upstream.git" \
    --source "$QA_ROOT/local"
```

## 3. Execution Verification
**Crucially**, the TUI should **NOT** launch. Since the changes are non-conflicting, the tool should merge them automatically and exit.

**Expected CLI Output:**
```text
Fetching upstream changes...
Detected 1 changed files upstream.
Auto-merging config.conf (AUTO_MERGEABLE)...
All changes merged automatically.
```

## 4. File Content Verification
Verify the file content on disk to ensure both changes were applied:

```bash
cat "$QA_ROOT/local/config.conf"
```

**Expected Output:**
```text
line 1: LOCAL_CHANGE
line 2: default
line 3: default
line 4: default
line 5: default
line 6: default
line 7: default
line 8: UPSTREAM_CHANGE
```

## 6. Idempotency Check
Run the tool one last time:
```bash
uv run --directory "$TOOL_REPO" -m chezmerge.main \
    --repo "$QA_ROOT/upstream.git" \
    --source "$QA_ROOT/local"
```
**Expected Output:**
`No upstream changes detected.`
