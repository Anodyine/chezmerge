#!/bin/bash

# Configuration
TEST_DIR="tests/e2e"
FAILED=0

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "=== Starting E2E Regression Suite ==="

# Iterate over all .sh files in the e2e directory
for script in "$TEST_DIR"/*.sh; do
    # Check if file exists (in case glob matches nothing)
    [ -e "$script" ] || continue
    
    test_name=$(basename "$script")
    
    echo -e "\n${GREEN}--------------------------------------------------${NC}"
    echo -e "${GREEN}Running $test_name...${NC}"
    echo -e "${GREEN}--------------------------------------------------${NC}"
    
    # Run the test script
    if bash "$script"; then
        echo -e "${GREEN}PASS: $test_name${NC}"
    else
        echo -e "${RED}FAIL: $test_name${NC}"
        FAILED=1
    fi
done

echo -e "\n${GREEN}--------------------------------------------------${NC}"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed successfully.${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed.${NC}"
    exit 1
fi
