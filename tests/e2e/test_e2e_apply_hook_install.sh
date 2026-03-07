#!/bin/bash
set -e

TEST_ROOT="/tmp/chezmerge-test-apply-hook"
REMOTE_REPO="$TEST_ROOT/upstream.git"
MAINTAINER_DIR="$TEST_ROOT/maintainer"
USER_DIR="$TEST_ROOT/local-chezmoi"
PROJECT_ROOT=$(pwd)
HOOK_FILE="$USER_DIR/run_after_15-chezmerge-sync-submodule.sh.tmpl"
MARKER="# Managed by chezmerge: submodule sync hook"

GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}=== Setting up Test Environment (Apply Hook Install) ===${NC}"
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

if [ ! -f "$HOOK_FILE" ]; then
    echo "FAILURE: Expected apply hook file was not created."
    exit 1
fi

if ! grep -q "$MARKER" "$HOOK_FILE"; then
    echo "FAILURE: Apply hook marker not found."
    cat "$HOOK_FILE"
    exit 1
fi

if ! grep -q 'submodule update --init --recursive .chezmerge-upstream' "$HOOK_FILE"; then
    echo "FAILURE: Apply hook does not contain minimal submodule update command."
    cat "$HOOK_FILE"
    exit 1
fi

echo -e "${GREEN}=== Verifying Non-Chezmerge Hook Is Preserved ===${NC}"
cat > "$HOOK_FILE" <<'EOF'
#!/usr/bin/env bash
echo "custom user hook"
EOF

uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
    --repo "$REMOTE_REPO" \
    --source "$USER_DIR"

if ! grep -q 'custom user hook' "$HOOK_FILE"; then
    echo "FAILURE: Non-chezmerge hook should not have been overwritten."
    cat "$HOOK_FILE"
    exit 1
fi

echo -e "${GREEN}=== Verifying Chezmerge-Managed Hook Is Updated ===${NC}"
cat > "$HOOK_FILE" <<'EOF'
#!/usr/bin/env bash
# Managed by chezmerge: submodule sync hook
echo "old hook content"
EOF

uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
    --repo "$REMOTE_REPO" \
    --source "$USER_DIR"

if ! grep -q 'submodule update --init --recursive .chezmerge-upstream' "$HOOK_FILE"; then
    echo "FAILURE: Chezmerge-managed hook was not refreshed."
    cat "$HOOK_FILE"
    exit 1
fi

echo -e "${GREEN}SUCCESS: Apply hook install/update behavior is correct.${NC}"
