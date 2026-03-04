#!/bin/bash
set -e

# --- Configuration ---
TEST_ROOT="/tmp/chezmerge-test-symlink-import"
REMOTE_REPO="$TEST_ROOT/upstream.git"
MAINTAINER_DIR="$TEST_ROOT/maintainer"
USER_DIR="$TEST_ROOT/local-chezmoi"
PROJECT_ROOT=$(pwd)

# Colors
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}=== Setting up Test Environment (Symlink Import) ===${NC}"
rm -rf "$TEST_ROOT"
mkdir -p "$TEST_ROOT"

# 1. Setup Upstream
echo "Creating local upstream repo..."
git init --bare "$REMOTE_REPO"

git clone "$REMOTE_REPO" "$MAINTAINER_DIR"
cd "$MAINTAINER_DIR"

mkdir -p dotfiles/.config/app
echo "target-content" > dotfiles/.config/app/target.txt
ln -s target.txt dotfiles/.config/app/link.txt

git add .
git commit -m "Initial commit with symlink"
git push origin master
cd "$PROJECT_ROOT"

# 2. Initialize via chezmerge
echo -e "${GREEN}=== Testing symlink import mapping ===${NC}"
uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
    --repo "$REMOTE_REPO" \
    --source "$USER_DIR" \
    --inner-path "dotfiles"

# 3. Verify mapping to symlink_ naming
TARGET="$USER_DIR/dot_config/app/symlink_link.txt"
LEGACY="$USER_DIR/dot_config/app/link.txt"

if [ -f "$TARGET" ]; then
    echo -e "${GREEN}SUCCESS: symlink_ path created.${NC}"
else
    echo "FAILURE: expected $TARGET"
    echo "Contents of $USER_DIR:"
    ls -R "$USER_DIR"
    exit 1
fi

if [ -f "$LEGACY" ]; then
    echo "FAILURE: raw symlink filename should not exist: $LEGACY"
    exit 1
fi

if grep -q "^target.txt$" "$TARGET"; then
    echo -e "${GREEN}SUCCESS: Symlink target content verified.${NC}"
else
    echo "FAILURE: Symlink target content mismatch in $TARGET"
    echo "Actual content:"
    cat "$TARGET"
    exit 1
fi

echo -e "${GREEN}=== Symlink Import Test Passed ===${NC}"
