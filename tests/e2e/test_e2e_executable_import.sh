#!/bin/bash
set -e

# --- Configuration ---
TEST_ROOT="/tmp/chezmerge-test-executable-import"
REMOTE_REPO="$TEST_ROOT/upstream.git"
MAINTAINER_DIR="$TEST_ROOT/maintainer"
USER_DIR="$TEST_ROOT/local-chezmoi"
PROJECT_ROOT=$(pwd)

# Colors
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}=== Setting up Test Environment (Executable Import) ===${NC}"
rm -rf "$TEST_ROOT"
mkdir -p "$TEST_ROOT"

# 1. Setup Upstream
echo "Creating local upstream repo..."
git init --bare "$REMOTE_REPO"

git clone "$REMOTE_REPO" "$MAINTAINER_DIR"
cd "$MAINTAINER_DIR"

mkdir -p dotfiles/.local/bin
echo '#!/usr/bin/env sh' > dotfiles/.local/bin/cleanup.sh
echo 'echo cleanup' >> dotfiles/.local/bin/cleanup.sh
chmod +x dotfiles/.local/bin/cleanup.sh

git add .
git commit -m "Initial commit with executable script"
git push origin HEAD
cd "$PROJECT_ROOT"

# 2. Initialize via chezmerge
echo -e "${GREEN}=== Testing executable import mapping ===${NC}"
uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
    --repo "$REMOTE_REPO" \
    --source "$USER_DIR" \
    --inner-path "dotfiles"

# 3. Verify mapping to executable_ naming
TARGET="$USER_DIR/dot_local/bin/executable_cleanup.sh"
LEGACY="$USER_DIR/dot_local/bin/cleanup.sh"

if [ -f "$TARGET" ]; then
    echo -e "${GREEN}SUCCESS: executable_ path created.${NC}"
else
    echo "FAILURE: expected $TARGET"
    echo "Contents of $USER_DIR:"
    ls -R "$USER_DIR"
    exit 1
fi

if [ -f "$LEGACY" ]; then
    echo "FAILURE: non-prefixed executable file should not exist: $LEGACY"
    exit 1
fi

if grep -q "echo cleanup" "$TARGET"; then
    echo -e "${GREEN}SUCCESS: Content verified.${NC}"
else
    echo "FAILURE: Content mismatch in $TARGET"
    exit 1
fi

echo -e "${GREEN}=== Executable Import Test Passed ===${NC}"
