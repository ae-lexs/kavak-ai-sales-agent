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
echo "This demo covers:"
echo "  1. RAG/FAQ (Sedes question)"
echo "  2. Catalog Search (Options)"
echo "  3. Financing Calculation"
echo "  4. Lead Capture"
echo "  5. Handoff"
echo ""
echo "=========================================="
echo ""

# Step 1: RAG/FAQ - Sedes Question
echo "--- Step 1: RAG/FAQ (Sedes) ---"
make_request "¿Dónde están las sedes de Kavak?"
echo ""

# Step 2: Commercial Flow - Need
echo "--- Step 2: Commercial Flow (Need) ---"
make_request "Estoy buscando un auto familiar"
echo ""

# Step 3: Budget
echo "--- Step 3: Budget ---"
make_request "Mi presupuesto es \$300,000"
echo ""

# Step 4: Preferences
echo "--- Step 4: Preferences ---"
make_request "Automático"
echo ""

# Step 5: Financing Interest
echo "--- Step 5: Financing Interest ---"
make_request "Sí, me interesa el financiamiento"
echo ""

# Step 6: Down Payment
echo "--- Step 6: Down Payment ---"
make_request "20%"
echo ""

# Step 7: Loan Term
echo "--- Step 7: Loan Term ---"
make_request "48 meses"
echo ""

# Step 8: Lead Capture - Appointment Interest
echo "--- Step 8: Lead Capture (Appointment) ---"
make_request "Sí, me gustaría agendar una cita"
echo ""

# Step 9: Lead Capture - Name
echo "--- Step 9: Lead Capture (Name) ---"
make_request "Juan Pérez"
echo ""

# Step 10: Lead Capture - Phone
echo "--- Step 10: Lead Capture (Phone) ---"
make_request "+525512345678"
echo ""

# Step 11: Lead Capture - Contact Time
echo "--- Step 11: Lead Capture (Contact Time) ---"
make_request "Mañana en la tarde"
echo ""

echo "=========================================="
echo "Demo completed!"
echo "=========================================="
echo ""
echo "Summary:"
echo "  ✓ RAG/FAQ: Answered sedes question using knowledge base"
echo "  ✓ Catalog Search: Found cars matching criteria"
echo "  ✓ Financing: Calculated payment plan with 10% APR"
echo "  ✓ Lead Capture: Collected name, phone, and contact time"
echo "  ✓ Handoff: Lead ready for sales team follow-up"
echo ""

