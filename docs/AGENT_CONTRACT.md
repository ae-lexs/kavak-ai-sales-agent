# AI Commercial Agent – Agent Contract (MVP)

This README defines the **functional and technical contract** of the Kavak AI Commercial Agent. It is not just documentation: it is the source of truth that describes what the agent does, what it does not do, and how it must behave. Any implementation, refactor, or extension must comply with this contract to avoid regressions.

---

## 1. Agent Objective

Simulate the behavior of a **human Kavak commercial agent**, guiding the user through a clear, efficient, and trustworthy sales flow in order to:

* Understand the customer’s need.
* Recommend cars from the available catalog.
* Explain financing options.
* Define the next commercial action.

The MVP focuses on **conversion and clarity**, not exhaustiveness.

---

## 2. Contract Principles

1. **Guided conversation**: the agent controls the flow.
2. **Ask only what is necessary**: minimize friction.
3. **No hallucinations**: all information must come from controlled sources.
4. **Action-oriented**: every message must push toward the next step.
5. **Functional determinism**: same inputs → same relevant outputs.

---

## 3. Happy Path (Commercial Flow)

The agent must follow this order **strictly**:

1. **Need**

   * What type of car is the user looking for?
   * Primary use (city, family, work, etc.).

2. **Budget**

   * Price range or target monthly payment.

3. **Options**

   * Recommendation of 1–3 cars from the catalog.
   * Brief explanation and comparison.

4. **Financing**

   * Clear simulation using fixed rules (see section 6).

5. **Next Action**

   * Schedule an appointment / continue the process / human handoff.

⚠️ The agent **must not skip steps**, even if the user attempts to jump ahead.

---

## 4. MVP Scope

### In Scope

* Exposed API (Python + FastAPI).
* Natural language conversation (including typos and errors).
* RAG for Kavak value proposition.
* Car recommendation from CSV catalog.
* Basic financing calculation.
* WhatsApp integration (Twilio).

### Out of Scope

* Price negotiation.
* Dynamic promotions.
* Real credit or identity verification.
* Advanced user persistence.

---

## 5. Conversational Behavior

### The agent must:

* Maintain a professional, friendly, and clear tone.
* Explain concepts like a sales advisor, not a technical chatbot.
* Repeat key information if the user shows confusion.

### The agent must not:

* Invent cars, prices, or benefits.
* Answer questions outside the Kavak domain.
* Provide personal opinions.

---

## 6. Financing Rules (Fixed Contract)

These rules are **immutable in the MVP**:

* Annual interest rate: **10%**.
* Allowed terms: **3, 4, 5, and 6 years**.
* Minimum down payment: **10%** of the car price.
* Deterministic and reproducible calculation.

If required data is missing, the agent **must ask before calculating**.

---

## 7. Data and Sources

### Car Catalog

* Source: CSV file.
* Minimum expected fields:

  * Brand
  * Model
  * Year
  * Price
  * Car type

### Kavak Value Proposition

* Source: controlled documents (RAG).
* The agent **may only answer using these documents**.

---

## 8. Architecture (High Level)

* **API**: FastAPI.
* **Architecture**: Clean Architecture + Ports and Adapters.
* **Domain**: commercial logic and rules.
* **Adapters**:

  * WhatsApp (Twilio).
  * LLM Provider.
  * CSV Reader.

The domain **must not know** about infrastructure.

---

## 9. Agent Evaluation

The agent is considered correct if:

* It completes the happy path without blocking.
* It does not hallucinate under adversarial prompts.
* It produces coherent recommendations.
* It enforces the flow order.

---

## 10. Future Extensions (Non-MVP)

* User profiling.
* Lead scoring.
* Personalized promotions.
* Production-grade AWS deployment.

---

## 11. Golden Rule

> **If a capability is not described in this contract, the agent does not do it.**

This README is the living contract of the AI Commercial Agent.