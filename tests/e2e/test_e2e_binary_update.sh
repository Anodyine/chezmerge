#!/bin/bash
set -e

TEST_ROOT="/tmp/chezmerge-test-binary-update"
REMOTE_REPO="$TEST_ROOT/upstream.git"
MAINTAINER_DIR="$TEST_ROOT/maintainer"
USER_DIR="$TEST_ROOT/local-chezmoi"
PROJECT_ROOT=$(pwd)

GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}=== Setting up Test Environment (Binary Update) ===${NC}"
rm -rf "$TEST_ROOT"
mkdir -p "$TEST_ROOT"

git init --bare "$REMOTE_REPO"
git clone "$REMOTE_REPO" "$MAINTAINER_DIR"
cd "$MAINTAINER_DIR"

python - <<'PY'
from pathlib import Path
Path("blob.bin").write_bytes(bytes([0x00, 0x01, 0x02, 0xFF, 0x0A]))
PY

git add blob.bin
git commit -m "Initial binary commit"
git push origin HEAD
cd "$PROJECT_ROOT"

echo -e "${GREEN}=== Initializing Local ===${NC}"
uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
  --repo "$REMOTE_REPO" \
  --source "$USER_DIR"

git -C "$USER_DIR" add .
git -C "$USER_DIR" commit -m "Baseline import" >/dev/null

echo -e "${GREEN}=== Updating Upstream Binary ===${NC}"
cd "$MAINTAINER_DIR"
python - <<'PY'
from pathlib import Path
Path("blob.bin").write_bytes(bytes([0x10, 0x11, 0x12, 0xFF, 0x0A]))
PY
git add blob.bin
git commit -m "Update binary"
git push origin HEAD
cd "$PROJECT_ROOT"

echo -e "${GREEN}=== Running Update ===${NC}"
uv run --directory "$PROJECT_ROOT" -m chezmerge.main \
  --source "$USER_DIR"

python - <<PY
from pathlib import Path
expected = Path("$MAINTAINER_DIR/blob.bin").read_bytes()
actual = Path("$USER_DIR/blob.bin").read_bytes()
if actual != expected:
    raise SystemExit("FAILURE: Binary content mismatch after update")
PY

echo -e "${GREEN}SUCCESS: Binary update handled without decode crash.${NC}"
