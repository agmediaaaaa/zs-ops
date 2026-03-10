# ICP Training — Outbound GTM & Lead Development

SOP / Operational Playbook

This combines:

- **Lead list development workflow**
- **GTM research workflow**
- **Signal-based targeting**
- **Offer discovery**
- **Outbound campaign creation**

The goal is to turn it into a **repeatable outbound engine**, not just isolated tactics.

---

## Objective

Create **highly targeted outbound campaigns** by systematically:

1. Researching the market
2. Identifying buying situations
3. Mapping ICP segments
4. Building qualified lead lists
5. Creating stealth offers
6. Launching signal-based outbound campaigns
7. Iterating messaging through market feedback

---

# Phase 1 — Market Intelligence & GTM Research

## Purpose

Understand the market deeply enough to identify **where demand actually emerges**.

This prevents random outbound and allows targeting **real buying situations**.

---

## Step 1 — Company Capability Analysis

Analyze the company internally.

Document:

### Core Offer

- Services / product offerings
- Delivery process
- Technology stack
- Infrastructure
- Unique capabilities

### Commercial Model

- Pricing structure
- Revenue model
- Contract structure
- Customer lifetime value

### Operational Constraints

- Delivery capacity
- Hiring limitations
- Implementation complexity
- Onboarding requirements

### Outcome Mapping

Translate capabilities into **business outcomes**.

Example:

| Capability          | Outcome                  |
| ------------------- | ------------------------ |
| Automation platform | Reduces operational cost |
| Recruiting service  | Faster hiring            |
| AI infrastructure  | Faster deployment        |

**Goal:** Understand **what business problem the company actually solves.**

---

## Step 2 — Market Landscape Analysis

Map the structure of the market.

### Identify

- Total Addressable Market
- Growth trends
- Market maturity
- Regulatory constraints
- Competitive density

### Segment the Market

Define:

- Industries
- Company size tiers
- Technology adoption levels
- Geographic markets

---

## Step 3 — Buyer Psychology Analysis

Understand how buyers think.

### Identify

**Common objections:**

- Cost
- Switching risk
- Internal resistance
- Implementation complexity

**Emotional drivers:**

- Risk reduction
- Career protection
- Speed of results
- Cost savings

**Internal politics** — Identify:

- Decision makers
- Influencers
- Blockers

Example:

| Role | Incentive                  |
| ---- | -------------------------- |
| CFO  | Cost control               |
| CTO  | Infrastructure reliability |
| COO  | Operational efficiency     |

---

# Phase 2 — Buying Situation Mapping

Instead of targeting static ICPs, identify **dynamic buying situations**.

Demand rarely exists continuously — it appears during **business transitions**.

---

## Step 4 — Define Buying Situations

Identify **8–12 situations** where demand spikes.

### 1. Rapid Hiring

**Problem:** Company needs infrastructure to support growth.

**Signals:**

- New job postings
- HR expansion
- Team growth announcements

---

### 2. Funding Events

**Problem:** Investor pressure to scale quickly.

**Signals:**

- Series A/B/C funding
- Investor press releases
- Hiring spikes

---

### 3. Leadership Change

**Problem:** New leaders restructure operations.

**Signals:**

- New CTO
- New CRO
- New VP operations

---

### 4. Technology Adoption

**Problem:** New systems require supporting infrastructure.

**Signals:**

- New software stack
- Integrations
- Developer hiring

---

### 5. Operational Bottlenecks

**Problem:** Existing systems can't scale.

**Signals:**

- Hiring DevOps
- Hiring operations roles
- Hiring analysts

---

# Phase 3 — Targeting Signal Identification

Each buying situation should map to **observable signals**.

Signals allow **predictive outbound targeting**.

---

## Signal Categories

### Hiring Signals

Search job descriptions for:

- Tools
- Technologies
- Problems

Example:

Job description contains: `LangChain`, `LLM`, `Agentic workflows`  
→ indicates **AI infrastructure demand**

---

### Technology Signals

Detect stack usage.

Examples: AWS, Azure, HubSpot, Salesforce.

Tools: BuiltWith, StoreLeads, Clay enrichment.

---

### Company Signals

Examples: Funding, expansion, acquisitions, product launches.

---

### Behavior Signals

Examples: LinkedIn posts about AI, conference attendance, community participation, GitHub activity.

---

# Phase 4 — ICP Segmentation

Avoid generic ICP definitions. Instead define **Segmented ICPs**.

---

## ICP Structure

### TAM

Everyone who could use the product.

Example: All SaaS companies.

---

### ICP

Best-fit buyers.

Example: SaaS companies — 50–500 employees, funded, selling B2B.

---

### Segments

Sub-groups inside ICP.

Example:

| Segment            | Description           |
| ------------------ | --------------------- |
| Series A startups  | Early growth          |
| Series B companies | Scaling               |
| Enterprise         | Mature infrastructure |

Each segment needs **different messaging**.

---

# Phase 5 — Lead List Development

## Overview

Lead list building has **four stages**:

1. Research
2. Company sourcing
3. Contact scraping
4. Qualification & enrichment

---

## Step 5 — TAM Mapping

Use AI to identify **all possible industries** that could use the service.

Prompt example: *"List all industries that could use [service]"*

### Base Requirements

Define:

- Company size
- Location
- Industry
- Revenue proxy (employees)

These define the **TAM filter layer**.

---

## Step 6 — ICP Definition

Analyze:

- CRM data
- Closed deals
- Sales call transcripts

Identify:

- Best industries
- Common team structures
- Common tech stacks
- Buying triggers

---

## Step 7 — Segment Definition

Combine: **Industry + Persona + Situation**

Example segments:

| Segment              | Persona         |
| -------------------- | --------------- |
| Manufacturing firms  | COO             |
| Fintech startups     | CTO             |
| Healthcare providers | Director of Ops |

Each segment becomes a **separate campaign.**

---

# Phase 6 — Company Sourcing

Companies can be sourced from **three types of databases**.

---

## 1. Online Directories

Used for **niche industries**.

Examples: Association directories, Google Maps, certification lists.

Tools: Instant Data Scraper, PhantomBuster.

---

## 2. Industry Databases

Higher quality data.

| Platform   | Purpose             |
| ---------- | ------------------- |
| Crunchbase | Funding signals     |
| BuiltWith  | Tech stack          |
| StoreLeads | Ecommerce           |
| ZoomInfo   | Enterprise contacts |

---

## 3. Prospecting Platforms

Bulk list building.

Example: Apollo, AI Arc. Good for **large-scale outbound lists**.

---

# Phase 7 — Contact Sourcing

Find decision makers.

### Title filters

Example: Head of Engineering, VP Operations, CTO, Director Marketing.

### Keyword search

Generate title variations with AI.

Example prompt: *"Generate job titles related to Head of AI."*

### Contact scraping

Use: Apollo, Clay, AI Arc, Phantombuster.

---

# Phase 8 — Data Qualification

Qualify companies **before enriching contacts**.

Reason: Prevents wasting enrichment credits.

---

## Company Qualification

Example checks:

- Correct industry
- Company size
- Technology usage
- Relevant services

Use: Claygent, Serper, Apify, GPT analysis.

---

## Data Verification

Fix incorrect data points: employee count, industry classification, location.

Tools: LeadMagic, Clay enrichment.

---

# Phase 9 — Contact Enrichment

Once companies are qualified: run **waterfall enrichment**.

Sequence:

1. Email
2. Phone
3. LinkedIn
4. Company data

Tools: Prospeo, Icypeas, LeadMagic.

---

# Phase 10 — Data Verification

Verify contact data.

Examples: Email verification, phone validation.

Goal: Ensure high deliverability.

---

# Phase 11 — Stealth Offer Creation

A **stealth offer** is a unique mechanism that differentiates the solution.

Examples:

| Mechanism              | Promise                |
| ---------------------- | ---------------------- |
| Speed advantage        | Fastest deployment     |
| Risk reduction         | No infrastructure risk |
| Cost advantage         | Cheaper scaling        |
| Operational simplicity | Fewer tools required   |

---

## How to Discover Stealth Offers

Analyze: Sales calls, objections, competitor weaknesses.

Find: **Unique capability → market outcome.**

Example:

| Capability                | Stealth offer         |
| ------------------------- | ---------------------- |
| Durable agents            | Lossless AI agents    |
| Serverless infrastructure | Deploy without DevOps |

---

# Phase 12 — Campaign Creation

Each campaign must include:

1. Segment
2. Buying situation
3. Stealth offer
4. Targeting signals
5. Messaging

---

## Campaign Structure

Example:

| Element | Example        |
| ------- | -------------- |
| Segment | AI startups   |
| Signal  | Hiring ML engineers |
| Offer   | Deploy agents faster |
| Message angle | "Skip infrastructure build." |

---

# Phase 13 — Messaging Strategy

Cold email messaging must:

1. Reference the situation
2. Diagnose the problem
3. Introduce the mechanism
4. Propose the outcome

Structure:

```
Observation → Problem → Mechanism → Outcome → CTA
```

Example:

- **Observation:** "Noticed you're hiring AI engineers."
- **Problem:** "Most teams spend months building infrastructure."
- **Mechanism:** "We built the deployment layer."
- **Outcome:** "Ship agents instantly."

---

# Phase 14 — Campaign Testing

Test multiple offers simultaneously.

Example: 10 segments × 4 offers each = **40 campaigns**.

Measure: Reply rate, positive responses, meeting rate.

---

# Phase 15 — Offer Optimization

After testing:

- Identify winning offer, winning segment, winning signal.
- Scale those campaigns.

---

# Phase 16 — Feedback Loop

Feed results back into:

- Offer library
- Campaign knowledge base
- Targeting signals

Build internal documentation.

This creates a **self-improving GTM system**.

---

# Final System Architecture

Full workflow:

```
Market Research
    ↓
Buying Situation Mapping
    ↓
Signal Identification
    ↓
ICP Segmentation
    ↓
Lead List Development
    ↓
Data Qualification
    ↓
Contact Enrichment
    ↓
Campaign Creation
    ↓
Outbound Testing
    ↓
Offer Optimization
    ↓
Knowledge Base
```

---

# Key Principle

**Outbound works best when targeting situations, not personas.**

| Bad targeting                    | Good targeting                              |
| -------------------------------- | ------------------------------------------- |
| "Send emails to CTOs."           | "Send emails to CTOs hiring AI engineers."  |
