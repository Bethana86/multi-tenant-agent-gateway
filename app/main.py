from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os

from app.security_pipeline import CloudArmor, ModelArmor
from app.agent_platform import AgentRuntime
from app.governance import GovernanceTower

app = FastAPI(title="GCP Multi-Tenant Agent Security Gateway")

# Paths for static files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Ensure static directory exists
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Request Model
class QueryRequest(BaseModel):
    query: str
    tenant_id: str
    enable_cloud_armor: bool = True
    enable_model_armor: bool = True

@app.get("/")
def read_root():
    index_path = os.path.join(TEMPLATES_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h2>Templates not loaded yet. Antigravity is compiling files...</h2>")

@app.post("/api/query")
async def run_query(req: QueryRequest, request: Request):
    # Simulated Ingress credentials & IP from request / Mock IAP
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "Unknown browser")
    user_email = "be*******@gmail.com" # Mocked IAP Authenticated User
    
    # 1. Cloud Armor Ingress Check
    if req.enable_cloud_armor:
        cloud_armor_res = CloudArmor.inspect_request(client_ip, user_agent, req.query)
    else:
        cloud_armor_res = {"allowed": True, "reason": "Cloud Armor Disabled", "policy_rule": "rule-disabled"}
        
    if not cloud_armor_res["allowed"]:
        # Blocked immediately
        log_entry = GovernanceTower.log_event(
            client_ip=client_ip,
            user_email=user_email,
            tenant_id=req.tenant_id,
            query=req.query,
            cloud_armor_res=cloud_armor_res
        )
        return {
            "status": "BLOCKED_BY_CLOUD_ARMOR",
            "cloud_armor": cloud_armor_res,
            "model_armor_prompt": None,
            "agent_trace": None,
            "agent_response": None,
            "model_armor_response": None,
            "audit_log": log_entry
        }
        
    # 2. Model Armor Prompt Check
    if req.enable_model_armor:
        model_armor_prompt_res = ModelArmor.scan_prompt(req.query)
    else:
        model_armor_prompt_res = {
            "blocked": False,
            "injection_score": 0.0,
            "jailbreak_detected": False,
            "pii_detected": False,
            "pii_entities": [],
            "original_prompt": req.query,
            "sanitized_prompt": req.query,
            "block_reason": "Model Armor Disabled"
        }
        
    if model_armor_prompt_res["blocked"]:
        # Blocked by Prompt Scanner
        log_entry = GovernanceTower.log_event(
            client_ip=client_ip,
            user_email=user_email,
            tenant_id=req.tenant_id,
            query=req.query,
            cloud_armor_res=cloud_armor_res,
            model_armor_res=model_armor_prompt_res
        )
        return {
            "status": "BLOCKED_BY_MODEL_ARMOR",
            "cloud_armor": cloud_armor_res,
            "model_armor_prompt": model_armor_prompt_res,
            "agent_trace": None,
            "agent_response": None,
            "model_armor_response": None,
            "audit_log": log_entry
        }
        
    # 3. Agent Platform Runtime (Vertex AI / BigQuery / SQLite MCP Server)
    query_to_run = model_armor_prompt_res["sanitized_prompt"] # Run sanitized prompt
    agent = AgentRuntime(tenant_id=req.tenant_id, project_id="beth-e38b7")
    agent_res = agent.execute_query(query_to_run)
    
    # 4. Model Armor Response Check
    if req.enable_model_armor:
        model_armor_response_res = ModelArmor.scan_response(agent_res["response"])
    else:
        model_armor_response_res = {
            "leaked_data_types": [],
            "original_response": agent_res["response"],
            "sanitized_response": agent_res["response"],
            "safe": True
        }
        
    # Log the complete cycle
    log_entry = GovernanceTower.log_event(
        client_ip=client_ip,
        user_email=user_email,
        tenant_id=req.tenant_id,
        query=req.query,
        cloud_armor_res=cloud_armor_res,
        model_armor_res=model_armor_prompt_res,
        agent_res=agent_res,
        response_armor_res=model_armor_response_res
    )
    
    return {
        "status": "ALLOWED",
        "cloud_armor": cloud_armor_res,
        "model_armor_prompt": model_armor_prompt_res,
        "agent_trace": {
            "agent_name": agent_res["agent_name"],
            "thinking": agent_res["thinking_trace"],
            "tool_calls": agent_res["tool_calls"]
        },
        "agent_response": model_armor_response_res["sanitized_response"],
        "model_armor_response": model_armor_response_res,
        "audit_log": log_entry
    }

@app.get("/api/logs")
def get_audit_logs():
    return GovernanceTower.get_logs()

@app.get("/api/stats")
def get_dashboard_stats():
    return GovernanceTower.get_stats()

@app.post("/api/reset")
def reset_governance_data():
    GovernanceTower._logs = []
    GovernanceTower._stats = {
        "total_requests": 0,
        "total_blocks": 0,
        "cloud_armor_blocks": 0,
        "model_armor_blocks": 0,
        "pii_redacted_count": 0,
        "total_tokens_input": 0,
        "total_tokens_output": 0,
        "total_cost_usd": 0.0,
        "mcp_tool_calls_count": 0,
        "avg_mcp_duration_ms": 0.0
    }
    GovernanceTower._mcp_durations = []
    return {"status": "RESET_SUCCESSFUL"}
