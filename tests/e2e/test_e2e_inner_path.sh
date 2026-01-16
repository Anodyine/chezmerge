#!/bin/bash
set -e

# --- Configuration ---
TEST_ROOT="/tmp/chezmerge-test-inner-path"
REMOTE_REPO="$TEST_ROOT/upstream.git"
MAINTAINER_DIR="$TEST_ROOT/maintainer"
USER_DIR="$TEST_ROOT/local-chezmoi"
PROJECT_ROOT=$(pwd)

# Colors
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}=== Setting up Test Environment (Inner Path) ===${NC}"
rm -rf "$TEST_ROOT"
mkdir -p "$TEST_ROOT"

# 1. Setup Upstream with Inner Path
echo "Creating local upstream repo..."
git init --bare "$REMOTE_REPO"

git clone "$REMOTE_REPO" "$MAINTAINER_DIR"
cd "$MAINTAINER_DIR"

# Create structure:
# /
# ├── dotfiles/
# │   └── .bashrc
# ├── setup/
# │   └── install.sh
# └── README.md

mkdir dotfiles
mkdir setup
echo "alias ll='ls -l'" > dotfiles/.bashrc
echo "echo 'Installing...'" > setup/install.sh
echo "# My Dotfiles" > README.md

git add .
git commit -m "Initial commit with inner path structure"
git push origin master
cd "$PROJECT_ROOT"

# 2. Test Initialization with --inner-path
echo -e "${GREEN}=== Testing Initialization with --inner-path ===${NC}"
uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
    --repo "$REMOTE_REPO" \
    --source "$USER_DIR" \
    --inner-path "dotfiles"

# 3. Verify Results
echo "Verifying import..."

# Check if dot_bashrc exists in the root of USER_DIR (chezmoi source)
# It should be flattened/mapped from dotfiles/.bashrc -> dot_bashrc
if [ -f "$USER_DIR/dot_bashrc" ]; then
    echo -e "${GREEN}SUCCESS: dot_bashrc created from inner path.${NC}"
else
    echo "FAILURE: dot_bashrc missing."
    echo "Contents of $USER_DIR:"
    ls -R "$USER_DIR"
    exit 1
fi

# Check content
if grep -q "alias ll" "$USER_DIR/dot_bashrc"; then
    echo -e "${GREEN}SUCCESS: Content verified.${NC}"
else
    echo "FAILURE: Content mismatch."
    exit 1
fi

# Ensure files outside inner-path were NOT imported
# We check for README.md (root) or setup/install.sh
if [ -f "$USER_DIR/README.md" ] || [ -f "$USER_DIR/setup/install.sh" ]; then
    echo "FAILURE: Files outside inner-path were imported."
    echo "Contents of $USER_DIR:"
    ls -R "$USER_DIR"
    exit 1
fi

echo -e "${GREEN}=== Inner Path Test Passed ===${NC}"
