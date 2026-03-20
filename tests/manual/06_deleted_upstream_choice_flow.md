# 06 Deleted Upstream Choice Flow

## Objective
Verify the dedicated deleted-upstream choice workflow.

This covers:
* `k` keeps the local file as reference and does not re-prompt for the same file later in the same run.
* `d` deletes the local file to match upstream.
* `l` opens the inspection editor first.
* `Ctrl+q` from the inspection editor returns to the `k / d / l` choice screen instead of resolving the file.

## Prerequisites
* `uv` installed.
* `git` installed.
* **Set the Tool Path**:
  ```bash
  export TOOL_REPO="$HOME/repos/chezmerge"
  ```

## 1. Setup Test Environment
Run the following block to create a local upstream repo, initialize chezmerge, and create a delete-vs-modified conflict.

```bash
# 1. Clean previous runs
rm -rf /tmp/qa-06
mkdir -p /tmp/qa-06
export QA_ROOT="/tmp/qa-06"

# 2. Create upstream
git init --bare "$QA_ROOT/upstream.git"
git clone "$QA_ROOT/upstream.git" "$QA_ROOT/maintainer"

# 3. Create initial state
cd "$QA_ROOT/maintainer"
mkdir -p .config/hypr/scripts
cat <<'EOF' > .config/hypr/scripts/wallpaper-restore.sh
#!/usr/bin/env bash
cachefile="$HOME/.cache/current_wallpaper"
wallpaper=$(cat "$cachefile")
echo "$wallpaper"
EOF
git add .
git commit -m "Base wallpaper restore script"
git push origin master

# 4. Initialize local chezmoi source
cd "$QA_ROOT"
uv run --directory "$TOOL_REPO" -m chezmerge.main \
  --repo "$QA_ROOT/upstream.git" \
  --source "$QA_ROOT/local"

git -C "$QA_ROOT/local" add .
git -C "$QA_ROOT/local" commit -m "Baseline import"

# 5. Create local customization
cat <<'EOF' > "$QA_ROOT/local/dot_config/hypr/scripts/executable_wallpaper-restore.sh"
#!/usr/bin/env bash
cachefile="$HOME/.cache/current_wallpaper"
persistedwallpaper="$HOME/.config/ml4w/settings/current-wallpaper"

if [ -f "$persistedwallpaper" ]; then
    wallpaper=$(cat "$persistedwallpaper")
else
    wallpaper=$(cat "$cachefile")
fi

echo "$wallpaper"
EOF
git -C "$QA_ROOT/local" add .
git -C "$QA_ROOT/local" commit -m "Add persisted wallpaper fallback"

# 6. Delete upstream file
cd "$QA_ROOT/maintainer"
git rm .config/hypr/scripts/wallpaper-restore.sh
git commit -m "Delete wallpaper restore upstream"
git push
```

## 2. Test Keep (`k`)
Run chezmerge:

```bash
uv run --directory "$TOOL_REPO" -m chezmerge.main \
  --repo "$QA_ROOT/upstream.git" \
  --source "$QA_ROOT/local"
```

**Verification:**
1. A deleted-upstream choice screen appears instead of the normal merge editor.
2. Press `k`.
3. Chezmerge should continue the run.
4. The same deleted file should **not** be shown again later in the same run.
5. Verify the file still exists:
   ```bash
   cat "$QA_ROOT/local/dot_config/hypr/scripts/executable_wallpaper-restore.sh"
   ```

## 3. Test Inspect Then Quit (`l`, then `Ctrl+q`)
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

**Verification:**
1. At the deleted-upstream choice screen, press `l`.
2. The inspection editor opens.
3. Press `Ctrl+q` in the inspection editor.
4. You should return to the deleted-upstream choice screen.
5. The file should not be resolved yet.

## 4. Test Inspect Then Keep (`l`, edit, then `Ctrl+s`)
From the choice screen:

1. Press `l` again.
2. Make a visible edit in the file, such as appending:
   ```bash
   # reviewed
   ```
3. Press `Ctrl+s`.
4. You should return to the deleted-upstream choice screen in the reviewed state.
5. Press `k`.

**Verification:**
```bash
tail -n 3 "$QA_ROOT/local/dot_config/hypr/scripts/executable_wallpaper-restore.sh"
```

You should see the edit you made during inspection.

## 5. Test Delete (`d`)
Reset one more time:

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

At the deleted-upstream choice screen, press `d`.

**Verification:**
```bash
test ! -e "$QA_ROOT/local/dot_config/hypr/scripts/executable_wallpaper-restore.sh" && echo "deleted"
```

Expected output:

```text
deleted
```
