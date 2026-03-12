#!/bin/bash
# Test all Upwork Agent components

PROJECT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_PATH"

echo "🧪 Testing Upwork Autonomous Agent..."
echo "Project: $PROJECT_PATH"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

test_count=0
passed=0
failed=0

run_test() {
    local name=$1
    local cmd=$2
    
    test_count=$((test_count + 1))
    echo -e "${YELLOW}[Test $test_count]${NC} $name..."
    
    if eval "$cmd" > /tmp/test_output.log 2>&1; then
        echo -e "${GREEN}✅ PASSED${NC}: $name"
        passed=$((passed + 1))
    else
        echo -e "${RED}❌ FAILED${NC}: $name"
        echo "Output: $(cat /tmp/test_output.log | tail -5)"
        failed=$((failed + 1))
    fi
    echo ""
}

# Tests
run_test "Database initialization" "python src/db_init.py"
run_test "Database schema exists" "sqlite3 db/jobs.sqlite '.tables' | grep -q 'jobs'"
run_test "Scraper import" "python -c 'import src.scraper'"
run_test "Evaluator import" "python -c 'import src.evaluator'"
run_test "Bidder import" "python -c 'import src.bidder'"
run_test "Tracker import" "python -c 'import src.tracker'"
run_test "Config file exists" "test -f config/upwork_config.json"
run_test "Requirements installed" "python -c 'import playwright; import anthropic'"
run_test "Logs directory writable" "touch logs/test.log && rm logs/test.log"

echo ""
echo "📊 Test Results:"
echo "  Total: $test_count"
echo -e "  ${GREEN}Passed: $passed${NC}"
if [ $failed -gt 0 ]; then
    echo -e "  ${RED}Failed: $failed${NC}"
fi
echo ""

if [ $failed -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed${NC}"
    exit 1
fi
