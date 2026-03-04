#!/bin/bash
set -e

# --- Configuration ---
TEST_ROOT="/tmp/chezmerge-test-private-import"
USER_DIR="$TEST_ROOT/local-chezmoi"
SOURCE_DIR="$TEST_ROOT/upstream-files"
PROJECT_ROOT=$(pwd)

# Colors
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}=== Setting up Test Environment (Private Import) ===${NC}"
rm -rf "$TEST_ROOT"
mkdir -p "$SOURCE_DIR/.ssh" "$USER_DIR"

# 1. Build a local fixture with non-git-tracked mode bits
echo "dummy-private-key" > "$SOURCE_DIR/.ssh/id_example"
chmod 600 "$SOURCE_DIR/.ssh/id_example"
echo "#!/usr/bin/env sh" > "$SOURCE_DIR/.ssh/id_exec_readonly"
chmod 500 "$SOURCE_DIR/.ssh/id_exec_readonly"

# 2. Run importer directly so filesystem modes are preserved
echo -e "${GREEN}=== Testing private import mapping ===${NC}"
PYTHONPATH="$PROJECT_ROOT/src" python -c \
  "from pathlib import Path; from chezmerge.importer import import_upstream; import_upstream(Path('$SOURCE_DIR'), Path('$USER_DIR'))"

# 3. Verify mapping to private_ naming
TARGET="$USER_DIR/dot_ssh/private_id_example"
LEGACY="$USER_DIR/dot_ssh/id_example"

if [ -f "$TARGET" ]; then
    echo -e "${GREEN}SUCCESS: private_ path created.${NC}"
else
    echo "FAILURE: expected $TARGET"
    echo "Contents of $USER_DIR:"
    ls -R "$USER_DIR"
    exit 1
fi

if [ -f "$LEGACY" ]; then
    echo "FAILURE: non-prefixed private file should not exist: $LEGACY"
    exit 1
fi

if grep -q "dummy-private-key" "$TARGET"; then
    echo -e "${GREEN}SUCCESS: Content verified.${NC}"
else
    echo "FAILURE: Content mismatch in $TARGET"
    exit 1
fi

COMBINED="$USER_DIR/dot_ssh/private_readonly_executable_id_exec_readonly"
if [ -f "$COMBINED" ]; then
    echo -e "${GREEN}SUCCESS: Combined private+readonly+executable prefix verified.${NC}"
else
    echo "FAILURE: expected combined prefix file $COMBINED"
    exit 1
fi

echo -e "${GREEN}=== Private Import Test Passed ===${NC}"
