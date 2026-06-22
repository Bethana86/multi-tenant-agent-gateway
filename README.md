# GCP Multi-Tenant Agentic Security Gateway (MAG)

A high-fidelity, secure multi-tenant routing hub and Generative AI security gateway built on Google Cloud. This application implements the exact architecture required to securely route and sanitize enterprise requests directed to tenant agent runtimes using **Cloud Armor**, **Model Armor**, and **Model Context Protocol (MCP)** secure datastores.

---

## 🏗️ Architecture Design

The system implements a secure, audited routing topology structured across three main architectural sections:

```
[Client Request]
       │
       ▼
┌────────────────────────────────────────────────────────┐
│ 1. Routing Hub (Ingress Portal)                        │
│    ├── External Application Load Balancer              │
│    ├── Cloud Armor (IP Filter, SQLi, XSS checks)       │
│    └── Model Armor (Jailbreak, PII, Injection Scan)   │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼ (Sanitized Prompt)
┌───────────────────────┴────────────────────────────────┐
│ 2. Isolated Tenant Runtimes                            │
│    ├── Tenant A Project (Fusion AI Metrics)            │
│    │    └── MCP Server ──► BigQuery (fusion_ai)        │
│    ├── Tenant B Project (FinCorp Stock Trends)         │
│    │    └── MCP Server ──► SQLite (fincorp.db)         │
│    └── Model Armor Output Scanner (Egress Masking)     │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼ (Audit Log Telemetry)
┌───────────────────────┴────────────────────────────────┐
│ 3. Central Governance & Security Tower                 │
│    ├── Cloud Logging Audit Logs (Structured JSON)      │
│    ├── Real-time Threat Chart (Chart.js)               │
│    └── Gemini API Token & Model Armor Cost Tracker     │
└────────────────────────────────────────────────────────┘
```

1. **Ingress Gateway (Routing Hub)**: Implements Cloud Load Balancing ingress, Cloud Armor (blocking network threats), and Model Armor (scanning and sanitizing prompt injections, jailbreaks, and PII before hitting the routing portal).
2. **Tenant Runtimes**: Isolated project boundaries representing distinct tenants. Runtimes call Gemini models (via Vertex AI) and retrieve data securely through **MCP Servers** querying BigQuery (`fusion_ai` dataset) and local databases. Outgoing agent responses are scanned by Model Armor for data leaks before delivery.
3. **Governance Tower**: Aggregates all security policy violations, audit trails, and cost estimators for centralized corporate compliance.

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.11.x
- Google Cloud SDK authenticated with access to Vertex AI and BigQuery datasets.

### Installation
1. Clone this repository to your local workspace.
2. Initialize and activate a virtual environment:
   ```powershell
   py -m venv .venv
   .venv\Scripts\activate
   ```
3. Install required packages:
   ```powershell
   pip install -r requirements.txt
   ```
4. Initialize the Tenant B SQLite database:
   ```powershell
   py init_db.py
   ```

### Running the Server
Launch the FastAPI gateway server:
```powershell
py -m uvicorn app.main:app --reload --port 8000
```
Open your browser and navigate to **[http://localhost:8000](http://localhost:8000)**.

---

## 📂 Project Structure

```
├── app/
│   ├── static/
│   │   ├── app.js            # Frontend state, animations, and chart renderers
│   │   └── styles.css        # Premium dark glassmorphic CSS styling
│   ├── templates/
│   │   └── index.html        # Main dashboard markup
│   ├── agent_platform.py     # Tenant Runtimes & MCP Server database queries
│   ├── governance.py         # Logs aggregation and cost calculation
│   ├── main.py               # FastAPI backend routes
│   └── security_pipeline.py  # Cloud Armor & Model Armor semantic regex filters
├── fincorp.db                # SQLite database for Tenant B (initialized at startup)
├── init_db.py                # Database population script
├── requirements.txt          # Library dependencies
├── test_gateway.py           # Automated unit test suite
└── README.md
```

---

## 🧪 Running Verification Tests
To run the automated verification suite to ensure all security controls (SQLi blocking, semantic bypass blocks, and RAG retrievals) are functional:
```powershell
py test_gateway.py
```
