#!/bin/bash
set -e

# --- Configuration ---
TEST_ROOT="/tmp/chezmerge-test-local-only"
REMOTE_REPO="$TEST_ROOT/upstream.git"
MAINTAINER_DIR="$TEST_ROOT/maintainer"
USER_DIR="$TEST_ROOT/local-chezmoi"
PROJECT_ROOT=$(pwd)

# Colors
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}=== Setting up Test Environment (Local Changes Only) ===${NC}"
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

# 3. Modify Local (Ours)
echo -e "${GREEN}=== Modifying Local File ===${NC}"
echo "version 1 modified" > "$USER_DIR/dot_config"

# 4. Run Update (No Upstream Changes)
echo -e "${GREEN}=== Running Update ===${NC}"
OUTPUT=$(uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
    --repo "$REMOTE_REPO" \
    --source "$USER_DIR")

echo "$OUTPUT"

# 5. Verify Behavior
if echo "$OUTPUT" | grep -q "No upstream changes detected"; then
    echo -e "${GREEN}SUCCESS: Correctly detected no upstream changes.${NC}"
else
    echo "FAILURE: Should have reported no upstream changes."
    exit 1
fi

# 6. Verify Local Changes Persist
if grep -q "version 1 modified" "$USER_DIR/dot_config"; then
    echo -e "${GREEN}SUCCESS: Local changes preserved.${NC}"
else
    echo "FAILURE: Local changes were lost."
    if [ -f "$USER_DIR/dot_config" ]; then
        echo "Current content:"
        cat "$USER_DIR/dot_config"
    fi
    exit 1
fi
