#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status

# --- Configuration ---
TEST_ROOT="/tmp/chezmerge-test-env"
REMOTE_REPO="$TEST_ROOT/upstream.git"
MAINTAINER_DIR="$TEST_ROOT/maintainer"
USER_DIR="$TEST_ROOT/local-chezmoi"
PROJECT_ROOT=$(pwd)

# Colors for output
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Setting up Test Environment ===${NC}"
rm -rf "$TEST_ROOT"
mkdir -p "$TEST_ROOT"

# 1. Setup "Upstream" (Bare Repo + Initial Commit)
echo "Creating local upstream repo..."
git init --bare "$REMOTE_REPO"

# Create initial content
git clone "$REMOTE_REPO" "$MAINTAINER_DIR"
cd "$MAINTAINER_DIR"
echo "alias ll='ls -l'" > .bashrc
echo "set number" > .vimrc
git add .
git commit -m "Initial commit"
git push origin master
cd "$PROJECT_ROOT"

# 2. Test Initialization
echo -e "${GREEN}=== Testing Initialization ===${NC}"
uv run src/chezmerge/main.py \
    --repo "$REMOTE_REPO" \
    --source "$USER_DIR"

# Verify Init
if [ -f "$USER_DIR/dot_bashrc" ]; then
    echo "SUCCESS: dot_bashrc created."
else
    echo "FAILURE: dot_bashrc missing."
    exit 1
fi

# 3. Create Divergence
echo -e "${GREEN}=== Creating Divergence ===${NC}"

# A. Update Upstream (Theirs)
cd "$MAINTAINER_DIR"
echo "alias gs='git status'" >> .bashrc
git commit -am "Add git alias"
git push
cd "$PROJECT_ROOT"

# B. Update Local (Ours)
echo "# My local customization" >> "$USER_DIR/dot_bashrc"

# 4. Test Update (Dry Run)
echo -e "${GREEN}=== Testing Update Detection (Dry Run) ===${NC}"
OUTPUT=$(uv run src/chezmerge/main.py \
    --repo "$REMOTE_REPO" \
    --source "$USER_DIR" \
    --dry-run)

echo "$OUTPUT"

# Verify Conflict Detection
if echo "$OUTPUT" | grep -q "dot_bashrc"; then
    echo -e "${GREEN}SUCCESS: Conflict detected in dot_bashrc.${NC}"
else
    echo "FAILURE: Expected conflict in dot_bashrc not found."
    exit 1
fi

echo -e "${GREEN}=== All Tests Passed ===${NC}"
