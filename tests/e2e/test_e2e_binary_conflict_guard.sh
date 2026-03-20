#!/bin/bash
set -e

TEST_ROOT="/tmp/chezmerge-test-binary-conflict"
REMOTE_REPO="$TEST_ROOT/upstream.git"
MAINTAINER_DIR="$TEST_ROOT/maintainer"
USER_DIR="$TEST_ROOT/local-chezmoi"
PROJECT_ROOT=$(pwd)

GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}=== Setting up Test Environment (Binary Conflict Guard) ===${NC}"
rm -rf "$TEST_ROOT"
mkdir -p "$TEST_ROOT"

git init --bare "$REMOTE_REPO"
git clone "$REMOTE_REPO" "$MAINTAINER_DIR"
cd "$MAINTAINER_DIR"

python - <<'PY'
from pathlib import Path
Path("wallpaper.jpg").write_bytes(bytes([0x00, 0x01, 0x02, 0xFF, 0x0A]))
PY

git add wallpaper.jpg
git commit -m "Initial binary commit"
git push origin HEAD
cd "$PROJECT_ROOT"

echo -e "${GREEN}=== Initializing Local ===${NC}"
uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
  --repo "$REMOTE_REPO" \
  --source "$USER_DIR"

git -C "$USER_DIR" add .
git -C "$USER_DIR" commit -m "Baseline import" >/dev/null

echo -e "${GREEN}=== Creating Binary Divergence ===${NC}"
cd "$MAINTAINER_DIR"
python - <<'PY'
from pathlib import Path
Path("wallpaper.jpg").write_bytes(bytes([0x10, 0x11, 0x12, 0xFF, 0x0A]))
PY
git add wallpaper.jpg
git commit -m "Update binary upstream"
git push origin HEAD
cd "$PROJECT_ROOT"

python - <<PY
from pathlib import Path
Path("$USER_DIR/wallpaper.jpg").write_bytes(bytes([0x20, 0x21, 0x22, 0xFF, 0x0A]))
PY
git -C "$USER_DIR" commit -am "Customize binary locally" >/dev/null

echo -e "${GREEN}=== Running Update (Dry Run) ===${NC}"
OUTPUT=$(uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
  --source "$USER_DIR" \
  --dry-run)

echo "$OUTPUT"

if echo "$OUTPUT" | grep -q "manual resolution before advancing base pointer"; then
  echo "FAILURE: Binary conflicts should now enter the merge flow instead of aborting immediately"
  exit 1
fi

if ! echo "$OUTPUT" | grep -q "wallpaper.jpg \\[BINARY_CONFLICT\\]"; then
  echo "FAILURE: Expected binary conflict to be surfaced as a merge item"
  exit 1
fi

echo -e "${GREEN}SUCCESS: Binary conflicts are routed into the beginner-friendly choice flow.${NC}"
