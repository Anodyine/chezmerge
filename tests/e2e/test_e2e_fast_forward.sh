#!/bin/bash
set -e

# --- Configuration ---
TEST_ROOT="/tmp/chezmerge-test-ff"
REMOTE_REPO="$TEST_ROOT/upstream.git"
MAINTAINER_DIR="$TEST_ROOT/maintainer"
USER_DIR="$TEST_ROOT/local-chezmoi"
PROJECT_ROOT=$(pwd)

# Colors
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}=== Setting up Test Environment (Fast Forward) ===${NC}"
rm -rf "$TEST_ROOT"
mkdir -p "$TEST_ROOT"

# 1. Setup Upstream
echo "Creating local upstream repo..."
git init --bare "$REMOTE_REPO"

# Create initial content
git clone "$REMOTE_REPO" "$MAINTAINER_DIR"
cd "$MAINTAINER_DIR"
echo "version 1" > .config
git add .
git commit -m "Initial commit"
git push origin master
cd "$PROJECT_ROOT"

# 2. Initialize Local
echo -e "${GREEN}=== Initializing Local ===${NC}"
uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
    --repo "$REMOTE_REPO" \
    --source "$USER_DIR"

# Verify Init
if grep -q "version 1" "$USER_DIR/dot_config"; then
    echo "Init successful."
else
    echo "FAILURE: dot_config missing or incorrect."
    exit 1
fi

# 3. Update Upstream (Theirs) - No local changes
echo -e "${GREEN}=== Updating Upstream ===${NC}"
cd "$MAINTAINER_DIR"
echo "version 2" > .config
git commit -am "Update config"
git push
cd "$PROJECT_ROOT"

# 4. Run Update
echo -e "${GREEN}=== Running Update ===${NC}"
# This should apply the change automatically without UI
uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
    --repo "$REMOTE_REPO" \
    --source "$USER_DIR"

# 5. Verify Update
echo -e "${GREEN}=== Verifying Update ===${NC}"
if grep -q "version 2" "$USER_DIR/dot_config"; then
    echo -e "${GREEN}SUCCESS: dot_config updated to version 2.${NC}"
else
    echo "FAILURE: dot_config was not updated."
    if [ -f "$USER_DIR/dot_config" ]; then
        echo "Current content:"
        cat "$USER_DIR/dot_config"
    else
        echo "File does not exist."
    fi
    exit 1
fi
