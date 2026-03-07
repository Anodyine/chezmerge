#!/bin/bash
set -e

TEST_ROOT="/tmp/chezmerge-test-git-hooks"
REMOTE_REPO="$TEST_ROOT/upstream.git"
MAINTAINER_DIR="$TEST_ROOT/maintainer"
USER_DIR="$TEST_ROOT/local-chezmoi"
PROJECT_ROOT=$(pwd)
HOOK_DIR="$USER_DIR/.githooks"
POST_MERGE_HOOK="$HOOK_DIR/post-merge"
POST_REWRITE_HOOK="$HOOK_DIR/post-rewrite"
MARKER="# Managed by chezmerge: pull submodule sync hook"

GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}=== Setting up Test Environment (Git Hook Install) ===${NC}"
rm -rf "$TEST_ROOT"
mkdir -p "$TEST_ROOT"

git init --bare "$REMOTE_REPO"

git clone "$REMOTE_REPO" "$MAINTAINER_DIR"
cd "$MAINTAINER_DIR"
echo "alias ll='ls -l'" > .bashrc
git add .
git commit -m "Initial commit"
git push origin HEAD
cd "$PROJECT_ROOT"

echo -e "${GREEN}=== Running First Chezmerge Sync ===${NC}"
uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
    --repo "$REMOTE_REPO" \
    --source "$USER_DIR"

if [ ! -f "$POST_MERGE_HOOK" ] || [ ! -f "$POST_REWRITE_HOOK" ]; then
    echo "FAILURE: Expected git hooks were not created."
    ls -la "$HOOK_DIR" || true
    exit 1
fi

if ! grep -q "$MARKER" "$POST_MERGE_HOOK"; then
    echo "FAILURE: post-merge marker not found."
    cat "$POST_MERGE_HOOK"
    exit 1
fi

if ! grep -q "$MARKER" "$POST_REWRITE_HOOK"; then
    echo "FAILURE: post-rewrite marker not found."
    cat "$POST_REWRITE_HOOK"
    exit 1
fi

if ! grep -q 'submodule update --init --recursive .chezmerge-upstream' "$POST_MERGE_HOOK"; then
    echo "FAILURE: post-merge hook does not contain minimal submodule update command."
    cat "$POST_MERGE_HOOK"
    exit 1
fi

if ! grep -q 'submodule update --init --recursive .chezmerge-upstream' "$POST_REWRITE_HOOK"; then
    echo "FAILURE: post-rewrite hook does not contain minimal submodule update command."
    cat "$POST_REWRITE_HOOK"
    exit 1
fi

if [ ! -x "$POST_MERGE_HOOK" ] || [ ! -x "$POST_REWRITE_HOOK" ]; then
    echo "FAILURE: Hook files are not executable."
    ls -la "$HOOK_DIR"
    exit 1
fi

HOOKS_PATH=$(git -C "$USER_DIR" config --local --get core.hooksPath || true)
if [ "$HOOKS_PATH" != ".githooks" ]; then
    echo "FAILURE: core.hooksPath should be .githooks, got '$HOOKS_PATH'."
    exit 1
fi

echo -e "${GREEN}=== Verifying Non-Chezmerge Hook Is Preserved ===${NC}"
cat > "$POST_MERGE_HOOK" <<'EOF'
#!/usr/bin/env bash
echo "custom user hook"
EOF
chmod +x "$POST_MERGE_HOOK"

uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
    --repo "$REMOTE_REPO" \
    --source "$USER_DIR"

if ! grep -q 'custom user hook' "$POST_MERGE_HOOK"; then
    echo "FAILURE: Non-chezmerge post-merge hook should not have been overwritten."
    cat "$POST_MERGE_HOOK"
    exit 1
fi

echo -e "${GREEN}=== Verifying Chezmerge-Managed Hook Is Updated ===${NC}"
cat > "$POST_REWRITE_HOOK" <<'EOF'
#!/usr/bin/env bash
# Managed by chezmerge: pull submodule sync hook
echo "old hook content"
EOF
chmod +x "$POST_REWRITE_HOOK"

git -C "$USER_DIR" config --local core.hooksPath .git/hooks

uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
    --repo "$REMOTE_REPO" \
    --source "$USER_DIR"

if ! grep -q 'submodule update --init --recursive .chezmerge-upstream' "$POST_REWRITE_HOOK"; then
    echo "FAILURE: Chezmerge-managed post-rewrite hook was not refreshed."
    cat "$POST_REWRITE_HOOK"
    exit 1
fi

HOOKS_PATH=$(git -C "$USER_DIR" config --local --get core.hooksPath || true)
if [ "$HOOKS_PATH" != ".githooks" ]; then
    echo "FAILURE: core.hooksPath was not restored to .githooks."
    exit 1
fi

echo -e "${GREEN}SUCCESS: Git hook install/update behavior is correct.${NC}"
