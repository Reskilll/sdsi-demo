# KnoxFlow: Autonomous Agentic Team Email & SLA Monitoring System

> **Hackathon Edition** &bull; **Zero External Dependencies** &bull; **JSON Data Fabric** &bull; **Deterministic Anti-Hallucination Guardrails** &bull; **Automated Unit Testing Suite**

KnoxFlow is an autonomous, mission-critical agentic email monitoring and response intelligence platform built for engineering, IT, and operations managers and individual contributors. It eliminates the bystander effect, prevents SLA breaches, and guarantees zero AI hallucinations.

---

## 🌟 Executive Summary & Key Highlights

1. **Zero External Dependencies**:
   - Runs instantly on native Node.js (`node server.js` or `npm start`).
   - Zero `npm install` requirements, zero native compilation, zero external database setup.
2. **Transparent JSON Data Fabric**:
   - Team Roster with Skills & Experience: [`data/team.json`](data/team.json)
   - Verified Incident Knowledge Base: [`data/historical_kb.json`](data/historical_kb.json)
   - Inbound Email & SLA Master Store: [`data/emails.json`](data/emails.json)
   - Benchmark Dataset for Instant Reset: [`data/emails.benchmark.json`](data/emails.benchmark.json)
3. **Manager SLA & Workload Cockpit**:
   - Real-time SLA compliance rate, pending aging countdowns, breach alerts, and turnaround metrics.
   - **Skill-Based Resource Intelligence**: View verified skill profiles (`Kubernetes`, `VPN & Networking`, `PostgreSQL`, `SecOps`, `ITSM`) directly on team cards.
   - **Smart Re-assignment Studio**: Suggests best-fit engineers based on skill overlap (`⭐️ Skill Match`) and real-time workload queue pressure.
4. **Employee Response Studio**:
   - Personal action queue prioritized dynamically by SLA urgency.
   - **Deterministic Historical Response Drafting**: Populates verified procedural drafts with zero hallucination.
   - Captures solution categories and resolution details with one-click indexing into institutional KB.
5. **Interactive 5-Page Presentation Pitch Deck**:
   - Accessible live at `http://localhost:3000/presentation.html` with a comprehensive **Technical FAQ & Architecture Appendix**.
6. **Automated Unit Testing & Security Evaluation**:
   - Comprehensive native test runner (`npm test` / `node test/unit.test.js`) testing all 5 sub-agent suites with 100% pass rate.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph Ingestion["Email Ingestion Pipeline"]
        RawEmail[Incoming Mail / Simulation Engine] --> Ingest[Perception Agent]
        Ingest --> Classifier[Agentic Classifier]
    end

    subgraph Decision["Deterministic Agentic Core"]
        Classifier -->|Informational| GeneralInfo[Mark General Info / No SLA]
        Classifier -->|Actionable Task| TaskEngine[Determine Task Type & SLA Runway]
        TaskEngine --> HistMatcher[Historical KB Matcher]
        HistMatcher -->|Verified Precedent Found| GenDraft[Populate Verified Historical Draft\nBadge: 100% Historical Sourced]
        HistMatcher -->|No Precedent / Zero-Day| SuppressDraft[Flag: Manual Investigation Required\nAI Speculation Strictly Suppressed]
    end

    subgraph MultiRecipient["Multi-Recipient Ownership Resolver"]
        TaskEngine --> RecipientResolver{Resolve Single Owner}
        RecipientResolver -->|Direct Salutation| NamedAssignee[Greeting Priority: 'Hi Sarah']
        RecipientResolver -->|Skill Match| SkillAssignee[Domain Fit: Sarah=VPN, David=SQL]
        RecipientResolver -->|Queue Load| LoadAssignee[Workload Balancer: Fewest Tasks]
    end

    subgraph Views["Dual Role Cockpits"]
        NamedAssignee --> ManagerView[Manager Cockpit: Aging, Skills & Re-assignment]
        SkillAssignee --> ManagerView
        LoadAssignee --> EmployeeView[Employee Cockpit: Personal Queue & Response Studio]
    end

    subgraph Storage["JSON Data Fabric"]
        TeamDB[(data/team.json)]
        KB[(data/historical_kb.json)]
        EmailsDB[(data/emails.json)]
    end

    Ingest -.-> EmailsDB
    HistMatcher <--> KB
    RecipientResolver <--> TeamDB
    ManagerView -.-> EmailsDB
    EmployeeView -.-> EmailsDB
```

---

## 🧪 Automated Unit Testing & Security Evaluation

KnoxFlow features a built-in, zero-dependency automated unit test suite and security evaluation framework designed for hackathon judges and technical evaluators.

### Run Automated Tests
```bash
npm test
# Or natively:
node test/unit.test.js
```

### Test Suite Coverage (15/15 Passed):
* 🧪 **Suite 1: Classification Agent (Intent & Prioritization)**:
  * Classifies broadcast notifications as `General Information` (no SLA clock).
  * Classifies network incidents as `P1 Critical (2h SLA)` under `Access & Network`.
  * Classifies permission requests as `P2 High (4h SLA)` under `Access Request`.
  * Evaluates urgency modifiers (`emergency`, `urgent`) to dynamically elevate SLA priority.
* 🧪 **Suite 2: Strict Anti-Hallucination Guardrail & Historical Matcher**:
  * Automatically populates verified procedural draft *strictly* when historical ticket exists ($\ge 0.50$ score).
  * **Strictly suppresses drafts** for novel/unseen zero-day bugs to eliminate generative hallucinations.
  * Suppresses drafts for informational notices.
* 🧪 **Suite 3: Dynamic SLA & Aging Engine**:
  * Precision elapsed aging calculation against reference clock.
  * Correct status thresholding: `Within SLA` (Green), `Approaching Breach` (Amber at $\ge 75\%$), and `Breached SLA` (Red).
* 🧪 **Suite 4: Multi-Recipient Identification & Resource Skill Routing**:
  * Skill affinity scoring (routes Database issues to David Kim).
  * Direct salutation detection (`Hi Sarah` / `@alex.m`).
* 🧪 **Suite 5: Security Guardrails & Data Sanitization**:
  * Safe string interpolation preventing script injection / XSS.
  * Immutable audit trails across email reassignments.
  * Data Fabric schema integrity verification (`team.json`, `historical_kb.json`, `emails.json`).

---

## 🛡️ Enterprise Security Guardrails & Governance

| Guardrail Layer | Implementation | Purpose |
| :--- | :--- | :--- |
| **Strict Anti-Hallucination Gate** | Mathematical similarity threshold ($\ge 0.50$) against `historical_kb.json` | Ensures employees never send fabricated terminal commands or incorrect technical procedures. |
| **Single Owner Accountability** | 5-step recipient resolution matrix (`Greeting` $\rightarrow$ `To/Cc` $\rightarrow$ `Skill` $\rightarrow$ `Workload`) | Eliminates the enterprise *Bystander Effect*; guarantees a single engineer is on the hook for SLA. |
| **Immutable Audit Logging** | `reassignment_log: []` array on every email object | Tracks every manager escalation: timestamp, previous assignee, new assignee, and explicit manager rationale. |
| **Human-in-the-Loop Studio** | Verification & edit step in Employee Studio | No automated email is ever dispatched blindly; engineers must inspect and confirm drafts. |
| **Input Sanitization** | Regex-isolated template interpolation | Prevents injection of malicious payloads into outbound responses. |
| **State Reset & Idempotence** | Benchmark reset endpoint (`POST /api/reset`) | Restores system to pristine evaluation benchmark state at any moment. |

---

## ⚡ Quick Start Guide (Under 30 Seconds)

### Prerequisites
- Node.js (v18+) installed.

### 1. Launch the Server
```bash
node server.js
# Or
npm start
```

### 2. Access the Application
* **Live Operational Dashboard**: Open [http://localhost:3000](http://localhost:3000)
* **5-Page Pitch Deck & FAQ Appendix**: Open [http://localhost:3000/presentation.html](http://localhost:3000/presentation.html)

---

## 💡 Live Hackathon Demo Walkthrough

### Scenario A: Manager Skill-Based Re-assignment & SLA Mitigation
1. Open [http://localhost:3000](http://localhost:3000) in **Manager Cockpit** mode.
2. Observe the team cards: each teammate displays verified skills (e.g. *Sarah Connor: VPN & Networking, Kubernetes*).
3. Find an aging ticket (e.g. `EML-2026-001` or `EML-2026-002`).
4. Click **Re-assign** &rarr; Notice how the modal highlights candidate engineers with **`⭐️ (Skill Match)`** and displays their live queue load.
5. Select the recommended specialist and click **Confirm Re-assignment**.
6. Observe the immediate workload recalculation and recorded audit trail.

### Scenario B: Zero-Hallucination Response Studio
1. Toggle to **Employee Cockpit** at the top bar.
2. Select **Sarah Connor** from the profile dropdown.
3. Open `EML-2026-001` (VPN Gateway Timeout).
4. Click **Review & Respond** to launch the **Email Response Studio**.
5. Click **Apply Historical Response Draft** &rarr; The verified resolution category (`Gateway Failover & DNS Cache Flush`), verified resolution details, and step-by-step procedure are auto-populated from `KB-101`.
6. Click **Send Response & Log Resolution** &rarr; The ticket is resolved, turnaround time recorded, and SLA compliance updated.

### Scenario C: Simulating New Inbound Emails Live
1. Click **Simulate Inbound Email** in the top navigation.
2. Select an internal employee or external client from the **Sender (From)** dropdown.
3. Select an assignee or choose **🤖 AI Smart Agent Routing**.
4. Test demo presets:
   - **VPN Gateway Timeout**: Triggers verified match with `KB-101`.
   - **Unseen K8s Memory Leak**: Demonstrates automated draft suppression for novel incidents.
   - **Firmware Upgrade Notice**: Categorized as `General Information` without initiating an SLA clock.
5. Click **Ingest & Process with Agent** &rarr; The newly synthesized ticket is instantly visible at the top of the grid with a smooth highlight pulse!

---

## ❓ Frequently Asked Technical Questions (FAQ Appendix)

#### Q1: How does KnoxFlow identify ownership when an email is sent to multiple people in `To` / `Cc`?
KnoxFlow applies a **5-step deterministic matrix**:
1. **Salutation & Mention Priority**: If the email starts with *"Hi Sarah"* or *"@alex.m"*, that person is given 100% priority.
2. **Field Hierarchy**: Direct `To` recipients take precedence over `Cc` observers.
3. **Skill Affinity Scoring**: Compares the email incident profile against verified skills in `team.json`.
4. **Queue Workload Balancer**: Breaks ties by routing to the engineer with the fewest pending tasks.
5. **Owner vs Collaborator**: A single owner is assigned the SLA target, while other recipients are flagged as *Collaborators* to prevent duplicate work.

#### Q2: What is the future roadmap for using LLMs and where do they fit?
KnoxFlow follows a **Bimodal Hybrid Architecture**: deterministic agents enforce SLAs and security guardrails, while LLMs provide cognitive depth across 5 high-impact areas:
* **Deep Semantic Parsing**: Multilingual translation, multi-intent ticket splitting, and urgency nuance detection.
* **Grounded RAG with Vector DBs**: Generates natural, tailored responses strictly anchored to verified runbooks without altering technical facts.
* **Zero-Day Incident SRE Co-Pilot**: Synthesizes internal investigation checklists and debug commands for unverified zero-day bugs.
* **Codebase Skill Routing**: Cross-references error stack traces directly with engineers' recent Git commits.
* **Automated RCA Generation**: Automatically drafts Root Cause Analysis post-mortem reports when SLA breaches occur.

#### Q3: How is Zero AI Hallucination mathematically guaranteed?
Auto-drafts are triggered **strictly if and only if** keyword coverage and task type match a verified historical ticket in `historical_kb.json` with a confidence score $\ge 0.50$. For zero-day or unverified incidents, generative invention is **100% suppressed**, forcing human investigation and review.

---

## 📁 Repository Structure

```
d:\KnoxFlow\
├── agent/
│   ├── classifier.js         # Heuristic & NLP perception agent
│   ├── historicalMatcher.js  # Strict deterministic historical solution matcher
│   ├── slaTracker.js         # Aging, SLA runways, turnaround calculations
│   └── index.js              # Agent pipeline orchestrator
├── data/
│   ├── emails.json           # Inbound emails & thread state (JSON store)
│   ├── historical_kb.json    # Verified incident resolutions & draft templates
│   ├── team.json             # Team directory, skills matrix & profiles
│   └── emails.benchmark.json # Initial benchmark state for one-click resets
├── public/
│   ├── app.js                # Frontend SPA controller & reactivity
│   ├── index.html            # Manager & Employee dual-cockpit interface
│   ├── presentation.html     # 5-Page Hackathon Pitch Deck & FAQ Appendix
│   └── styles.css            # Custom CSS & light/dark theme tokens
├── test/
│   └── unit.test.js          # Automated unit testing & security evaluation suite
├── .gitignore                # Clean publishing ignore rules
├── package.json              # Zero-dependency package manifest (npm start, npm test)
├── server.js                 # Native Node.js HTTP server & REST API
└── README.md                 # Complete documentation & evaluator guide
```

---

## ⚖️ License & Evaluation
Built for the **SDSI Agentic AI Digithon 2026**. KnoxFlow is open-source under the MIT License. Zero external dependencies required.
