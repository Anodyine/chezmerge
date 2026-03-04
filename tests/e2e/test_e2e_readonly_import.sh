#!/bin/bash
set -e

# --- Configuration ---
TEST_ROOT="/tmp/chezmerge-test-readonly-import"
USER_DIR="$TEST_ROOT/local-chezmoi"
SOURCE_DIR="$TEST_ROOT/upstream-files"
PROJECT_ROOT=$(pwd)

# Colors
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}=== Setting up Test Environment (Readonly Import) ===${NC}"
rm -rf "$TEST_ROOT"
mkdir -p "$SOURCE_DIR/.config/app" "$USER_DIR"

# 1. Build a local fixture with non-git-tracked mode bits
echo "lock=true" > "$SOURCE_DIR/.config/app/lock.conf"
chmod 444 "$SOURCE_DIR/.config/app/lock.conf"

# 2. Run importer directly so filesystem modes are preserved
echo -e "${GREEN}=== Testing readonly import mapping ===${NC}"
PYTHONPATH="$PROJECT_ROOT/src" python -c \
  "from pathlib import Path; from chezmerge.importer import import_upstream; import_upstream(Path('$SOURCE_DIR'), Path('$USER_DIR'))"

# 3. Verify mapping to readonly_ naming
TARGET="$USER_DIR/dot_config/app/readonly_lock.conf"
LEGACY="$USER_DIR/dot_config/app/lock.conf"

if [ -f "$TARGET" ]; then
    echo -e "${GREEN}SUCCESS: readonly_ path created.${NC}"
else
    echo "FAILURE: expected $TARGET"
    echo "Contents of $USER_DIR:"
    ls -R "$USER_DIR"
    exit 1
fi

if [ -f "$LEGACY" ]; then
    echo "FAILURE: non-prefixed readonly file should not exist: $LEGACY"
    exit 1
fi

if grep -q "lock=true" "$TARGET"; then
    echo -e "${GREEN}SUCCESS: Content verified.${NC}"
else
    echo "FAILURE: Content mismatch in $TARGET"
    exit 1
fi

echo -e "${GREEN}=== Readonly Import Test Passed ===${NC}"
