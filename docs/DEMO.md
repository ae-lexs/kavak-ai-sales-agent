# Kavak AI Sales Agent - Demo Guide

This guide provides a complete demo script for presenting the Kavak AI Sales Agent, including both WhatsApp (Twilio) and API-based demonstrations.

## Table of Contents

1. [Twilio WhatsApp Sandbox Setup](#twilio-whatsapp-sandbox-setup)
2. [3-Minute WhatsApp Demo Script](#3-minute-whatsapp-demo-script)
3. [API Demo Script](#api-demo-script)
4. [What to Highlight](#what-to-highlight)

---

## Twilio WhatsApp Sandbox Setup

### Quick Setup Summary

1. **Prerequisites:**
   - Twilio account (sign up at https://www.twilio.com/try-twilio)
   - WhatsApp Sandbox access (automatically enabled for new accounts)
   - Public HTTPS URL (use ngrok/localtunnel for local development)

2. **Local Development Setup:**
   ```bash
   # Terminal 1: Start the application
   make dev
   
   # Terminal 2: Expose with tunnel (choose one)
   ngrok http 8000
   # OR
   localtunnel --port 8000
   # OR
   cloudflared tunnel --url http://localhost:8000
   ```

3. **Twilio Console Configuration:**
   - Go to https://console.twilio.com
   - Navigate to **Messaging** → **Try it out** → **Send a WhatsApp message**
   - In "When a message comes in" field, enter:
     ```
     https://your-tunnel-url.ngrok.io/channels/whatsapp/webhook
     ```
   - Set HTTP method to **POST**
   - Click **Save**

4. **Environment Variables:**
   ```bash
   # Optional: Enable signature validation in production
   TWILIO_VALIDATE_SIGNATURE=false  # true for production
   TWILIO_IDEMPOTENCY_ENABLED=true  # Prevents duplicate replies
   REDIS_URL=redis://localhost:6379/0
   ```

5. **Test Connection:**
   - Send "Hola" to your Twilio Sandbox number (shown in console)
   - You should receive a Spanish response from the agent

---

## 3-Minute WhatsApp Demo Script

### Timeline: ~3 minutes

**Goal:** Demonstrate RAG (FAQ), catalog search, financing calculation, lead capture, and persistence.

### Step-by-Step Messages (Send in Spanish via WhatsApp)

#### **Step 1: RAG/FAQ - Sedes Question** (30 seconds)
**Send:** `¿Dónde están las sedes de Kavak?`

**Expected Response:** Agent responds with information about Kavak locations (15 sedes, 13 centros de inspección) using RAG from knowledge base.

**What to Highlight:**
- ✅ **RAG (Retrieval-Augmented Generation)**: Agent retrieves information from knowledge base
- ✅ **No Hallucination**: All information comes from controlled sources
- ✅ **Spanish-only output**: Professional, natural responses

---

#### **Step 2: Commercial Flow - Need & Budget** (45 seconds)
**Send:** `Estoy buscando un auto familiar`

**Expected Response:** Agent asks about budget.

**Send:** `Mi presupuesto es $300,000`

**Expected Response:** Agent asks about preferences (transmission, fuel type, etc.).

**What to Highlight:**
- ✅ **Guided Conversation**: Agent controls the flow and asks necessary questions
- ✅ **State Persistence**: Conversation state is saved (Postgres + Redis cache)
- ✅ **Step-by-step progression**: Agent enforces flow order

---

#### **Step 3: Catalog Search - Options** (30 seconds)
**Send:** `Automático`

**Expected Response:** Agent shows 1-3 car recommendations from catalog with prices and brief descriptions.

**What to Highlight:**
- ✅ **Catalog Search**: Agent searches CSV catalog based on criteria (family car, $300k budget, automatic)
- ✅ **Personalized Recommendations**: Results match user's needs and budget
- ✅ **Real Data**: All cars and prices come from actual catalog

---

#### **Step 4: Financing Calculation** (45 seconds)
**Send:** `Sí, me interesa el financiamiento`

**Expected Response:** Agent asks about down payment.

**Send:** `20%`

**Expected Response:** Agent asks about loan term (36, 48, 60, or 72 months).

**Send:** `48 meses`

**Expected Response:** Agent calculates and displays financing plan:
- Monthly payment
- Total interest
- Total amount
- Using fixed 10% annual interest rate

**What to Highlight:**
- ✅ **Deterministic Calculation**: Fixed rules (10% APR, 36-72 months, 10% min down payment)
- ✅ **Real-time Calculation**: Instant financing simulation
- ✅ **Transparent Terms**: Clear breakdown of costs

---

#### **Step 5: Lead Capture** (30 seconds)
**Expected Response:** Agent asks if user wants to schedule an appointment.

**Send:** `Sí, me gustaría agendar una cita`

**Expected Response:** Agent asks for name.

**Send:** `Juan Pérez`

**Expected Response:** Agent asks for phone number.

**Send:** `+525512345678`

**Expected Response:** Agent asks for preferred contact time.

**Send:** `Mañana en la tarde`

**Expected Response:** Agent confirms lead capture and provides next steps.

**What to Highlight:**
- ✅ **Lead Capture**: Complete contact information collection
- ✅ **Data Persistence**: Lead saved to database (Postgres)
- ✅ **Handoff Ready**: Lead ready for sales team follow-up

---

### Demo Tips

1. **Timing:** Pause 2-3 seconds between messages to simulate natural conversation
2. **Show Logs:** If presenting with terminal visible, show structured logs with cache hits/misses
3. **Highlight Architecture:** Mention Clean Architecture, cache-aside pattern, idempotency
4. **Error Handling:** If time permits, show graceful handling of invalid inputs
5. **Reset:** To restart, send "reset" or "reiniciar"

---

## API Demo Script

For API-based demos, use the `scripts/demo.sh` script:

```bash
# Run the demo script
./scripts/demo.sh

# Or with custom base URL
BASE_URL=http://localhost:8000 ./scripts/demo.sh
```

The script covers the complete flow:
1. **Sedes FAQ** → RAG demonstration
2. **Options** → Catalog search
3. **Financing** → Calculation with user inputs
4. **Lead Capture** → Complete contact collection
5. **Handoff** → Lead ready for sales team

---

## What to Highlight

### Architecture Highlights

1. **Clean Architecture**
   - Clear separation: Domain → Application → Adapters → Infrastructure
   - Dependency inversion: Business logic independent of frameworks
   - Easy to test and maintain

2. **Cache-Aside Pattern**
   - Redis cache for conversation state
   - Postgres as source of truth
   - Cache hits reduce database load
   - Logs show `state_cache_hit` and `state_cache_miss`

3. **Idempotency**
   - Redis-based idempotency for Twilio webhook
   - Prevents duplicate replies on retries
   - Uses MessageSid for deduplication

4. **RAG (Retrieval-Augmented Generation)**
   - Knowledge base retrieval for FAQ questions
   - No hallucinations - all info from controlled sources
   - Optional LLM for natural language generation

### Feature Highlights

1. **RAG/FAQ** (Step 1)
   - Retrieves information from knowledge base
   - Answers questions about Kavak services, locations, benefits
   - Grounded in factual documents

2. **Catalog Search** (Step 3)
   - Searches CSV catalog based on user criteria
   - Filters by need, budget, preferences
   - Returns personalized recommendations

3. **Financing Calculator** (Step 4)
   - Deterministic calculation with fixed rules
   - 10% annual interest rate
   - Flexible terms (36-72 months)
   - Minimum 10% down payment

4. **Lead Capture** (Step 5)
   - Collects name, phone, preferred contact time
   - Persists to database
   - Ready for sales team handoff

5. **Persistence**
   - Conversation state persists across sessions
   - Postgres for durability
   - Redis cache for performance
   - Leads stored for follow-up

### Technical Highlights

- **Spanish-only user output**: All responses in Spanish
- **English code/logs**: Codebase and logs in English
- **Structured logging**: JSON-like logs with session_id, turn_id, component
- **Error handling**: Graceful degradation, no user-facing errors
- **Test coverage**: Comprehensive unit and golden tests

---

## Troubleshooting

### WhatsApp Not Responding
- Check tunnel is running and URL is correct
- Verify webhook URL in Twilio console
- Check application logs for errors
- Ensure Redis is running (for idempotency)

### API Demo Fails
- Verify application is running: `curl http://localhost:8000/health`
- Check database connection (if using Postgres)
- Review application logs

### Cache Not Working
- Verify Redis is running: `redis-cli ping`
- Check `STATE_CACHE=redis` in environment
- Review cache hit/miss logs

---

## Next Steps After Demo

1. **Show Code Structure**: Walk through Clean Architecture layers
2. **Show Tests**: Demonstrate test coverage and golden tests
3. **Show Logs**: Highlight structured logging and observability
4. **Show Configuration**: Explain environment variables and flexibility
5. **Q&A**: Address questions about scalability, deployment, extensions
