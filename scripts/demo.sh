#!/bin/bash

# Demo script for Kavak AI Sales Agent
# Simulates a full happy path conversation in Spanish

set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"
SESSION_ID="demo_session_$(date +%s)"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if jq is available
if command -v jq &> /dev/null; then
    USE_JQ=true
else
    USE_JQ=false
fi

print_message() {
    echo -e "${BLUE}You:${NC} $1"
}

print_response() {
    echo -e "${GREEN}Agent:${NC} $1"
    echo ""
}

print_suggested() {
    echo -e "${YELLOW}Suggested questions:${NC}"
    if [ "$USE_JQ" = true ]; then
        echo "$1" | jq -r '.suggested_questions[]' | sed 's/^/  - /'
    else
        echo "$1" | grep -o '"suggested_questions":\[[^]]*\]' | sed 's/"suggested_questions":\[//;s/\]//;s/"//g;s/,/\n/g' | sed 's/^/  - /'
    fi
    echo ""
}

make_request() {
    local message="$1"
    print_message "$message"
    
    local response
    if [ "$USE_JQ" = true ]; then
        response=$(curl -s -X POST "${BASE_URL}/chat" \
            -H "Content-Type: application/json" \
            -d "{\"session_id\": \"${SESSION_ID}\", \"message\": \"${message}\", \"channel\": \"api\"}")
        
        local reply=$(echo "$response" | jq -r '.reply')
        print_response "$reply"
        print_suggested "$response"
    else
        response=$(curl -s -X POST "${BASE_URL}/chat" \
            -H "Content-Type: application/json" \
            -d "{\"session_id\": \"${SESSION_ID}\", \"message\": \"${message}\", \"channel\": \"api\"}")
        
        local reply=$(echo "$response" | grep -o '"reply":"[^"]*"' | sed 's/"reply":"//;s/"$//')
        print_response "$reply"
        echo -e "${YELLOW}Suggested questions:${NC}"
        echo "$response" | grep -o '"suggested_questions":\[[^]]*\]' | sed 's/"suggested_questions":\[//;s/\]//;s/"//g;s/,/\n/g' | sed 's/^/  - /'
        echo ""
    fi
}

echo "=========================================="
echo "Kavak AI Sales Agent - Demo Conversation"
echo "=========================================="
echo ""

# Step 1: User expresses need
make_request "Estoy buscando un auto familiar"

# Step 2: User provides budget
make_request "Mi presupuesto es \$300,000"

# Step 3: User asks about financing
make_request "Sí, me interesa el financiamiento"

# Step 4: User provides preferences (if needed) or down payment
make_request "Automático"

# Step 5: User provides down payment
make_request "20%"

# Step 6: User provides loan term
make_request "48 meses"

echo "=========================================="
echo "Demo completed!"
echo "=========================================="

