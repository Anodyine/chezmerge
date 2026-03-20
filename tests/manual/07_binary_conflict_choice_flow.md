# 07 Binary Conflict Choice Flow

## Objective
Verify the dedicated binary-conflict choice workflow.

This covers:
* `k` keeps the current local binary file.
* `t` replaces the local binary file with the upstream version.
* Binary conflicts use a dedicated choice screen instead of aborting the merge immediately.

## Prerequisites
* `uv` installed.
* `git` installed.
* **Set the Tool Path**:
  ```bash
  export TOOL_REPO="$HOME/repos/chezmerge"
  ```

## 1. Setup Test Environment
Run the following block to create a local upstream repo, initialize chezmerge, and create a binary conflict.

```bash
# 1. Clean previous runs
rm -rf /tmp/qa-07
mkdir -p /tmp/qa-07
export QA_ROOT="/tmp/qa-07"

# 2. Create upstream
git init --bare "$QA_ROOT/upstream.git"
git clone "$QA_ROOT/upstream.git" "$QA_ROOT/maintainer"

# 3. Create initial binary file
cd "$QA_ROOT/maintainer"
python - <<'PY'
from pathlib import Path
Path("wallpaper.jpg").write_bytes(bytes([0x00, 0x01, 0x02, 0x03, 0xFF]))
PY
git add wallpaper.jpg
git commit -m "Base binary wallpaper"
git push origin master

# 4. Initialize local chezmoi source
cd "$QA_ROOT"
uv run --directory "$TOOL_REPO" -m chezmerge.main \
  --repo "$QA_ROOT/upstream.git" \
  --source "$QA_ROOT/local"

git -C "$QA_ROOT/local" add .
git -C "$QA_ROOT/local" commit -m "Baseline import"

# 5. Change upstream binary
cd "$QA_ROOT/maintainer"
python - <<'PY'
from pathlib import Path
Path("wallpaper.jpg").write_bytes(bytes([0x10, 0x11, 0x12, 0x13, 0xFF]))
PY
git add wallpaper.jpg
git commit -m "Update upstream binary"
git push

# 6. Change local binary differently
python - <<PY
from pathlib import Path
Path("$QA_ROOT/local/wallpaper.jpg").write_bytes(bytes([0x20, 0x21, 0x22, 0x23, 0xFF]))
PY
git -C "$QA_ROOT/local" add .
git -C "$QA_ROOT/local" commit -m "Customize local binary"
```

## 2. Test Keep My Version (`k`)
Run chezmerge:

```bash
uv run --directory "$TOOL_REPO" -m chezmerge.main \
  --repo "$QA_ROOT/upstream.git" \
  --source "$QA_ROOT/local"
```

**Verification:**
1. A binary-conflict choice screen appears.
2. Press `k`.
3. Chezmerge should continue the run instead of aborting immediately.
4. Verify the local file still has the local bytes:
   ```bash
   python - <<PY
   from pathlib import Path
   print(list(Path("$QA_ROOT/local/wallpaper.jpg").read_bytes()))
   PY
   ```

**Expected Output:**
```text
[32, 33, 34, 35, 255]
```

## 3. Test Take Their Version (`t`)
Reset to the pre-merge state:

```bash
uv run --directory "$TOOL_REPO" -m chezmerge.main \
  --source "$QA_ROOT/local" \
  --undo-last
```

Run chezmerge again:

```bash
uv run --directory "$TOOL_REPO" -m chezmerge.main \
  --repo "$QA_ROOT/upstream.git" \
  --source "$QA_ROOT/local"
```

At the binary-conflict choice screen, press `t`.

**Verification:**
```bash
python - <<PY
from pathlib import Path
print(list(Path("$QA_ROOT/local/wallpaper.jpg").read_bytes()))
PY
```

**Expected Output:**
```text
[16, 17, 18, 19, 255]
```
