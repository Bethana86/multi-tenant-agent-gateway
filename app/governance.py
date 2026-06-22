import datetime
import json
from typing import Dict, Any, List

class GovernanceTower:
    """Manages central security audit logs, anomaly alarms, token counts, and cost metrics."""
    
    # Pricing configuration
    PRICE_MODEL_ARMOR_PER_SCAN = 0.001       # $0.001 per prompt check
    PRICE_GEMINI_INPUT_PER_1K = 0.000125      # $0.000125 per 1,000 input tokens
    PRICE_GEMINI_OUTPUT_PER_1K = 0.000375     # $0.000375 per 1,000 output tokens
    
    _logs: List[Dict[str, Any]] = []
    
    _stats = {
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
    
    _mcp_durations: List[float] = []

    @classmethod
    def log_event(cls, 
                  client_ip: str, 
                  user_email: str, 
                  tenant_id: str, 
                  query: str, 
                  cloud_armor_res: Dict[str, Any], 
                  model_armor_res: Dict[str, Any] = None, 
                  agent_res: Dict[str, Any] = None,
                  response_armor_res: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Processes a full request cycle, registers an audit log, 
        and updates performance/security metrics.
        """
        timestamp = datetime.datetime.utcnow().isoformat() + "Z"
        cls._stats["total_requests"] += 1
        
        # Calculate tokens & pricing
        input_tokens = 0
        output_tokens = 0
        gemini_cost = 0.0
        model_armor_cost = 0.0
        
        status = "ALLOWED"
        block_reason = ""
        
        # 1. Check Cloud Armor status
        if not cloud_armor_res["allowed"]:
            status = "BLOCKED_BY_CLOUD_ARMOR"
            block_reason = cloud_armor_res["reason"]
            cls._stats["total_blocks"] += 1
            cls._stats["cloud_armor_blocks"] += 1
            
        # 2. Check Model Armor status (if request passed Cloud Armor)
        elif model_armor_res:
            model_armor_cost = cls.PRICE_MODEL_ARMOR_PER_SCAN
            if model_armor_res["blocked"]:
                status = "BLOCKED_BY_MODEL_ARMOR"
                block_reason = model_armor_res["block_reason"]
                cls._stats["total_blocks"] += 1
                cls._stats["model_armor_blocks"] += 1
            
            if model_armor_res["pii_detected"]:
                cls._stats["pii_redacted_count"] += 1
                
            # If agent ran (allowed request)
            if not model_armor_res["blocked"] and agent_res:
                # Estimate token counts
                input_tokens = len(query.split()) * 4 + 150  # base prompt + system instructions estimate
                output_tokens = len(agent_res["response"].split()) * 4
                
                cls._stats["total_tokens_input"] += input_tokens
                cls._stats["total_tokens_output"] += output_tokens
                
                # Calculate cost
                gemini_cost = (
                    (input_tokens / 1000.0 * cls.PRICE_GEMINI_INPUT_PER_1K) + 
                    (output_tokens / 1000.0 * cls.PRICE_GEMINI_OUTPUT_PER_1K)
                )
                
                # Update MCP Tool metrics
                for tc in agent_res.get("tool_calls", []):
                    cls._stats["mcp_tool_calls_count"] += 1
                    # Extract duration from trace log if matches pattern: 'Time: 0.123s'
                    try:
                        time_part = tc["log"].split("Time: ")[1].split("s")[0]
                        duration_ms = float(time_part) * 1000.0
                        cls._mcp_durations.append(duration_ms)
                    except Exception:
                        pass
        
        total_cost = model_armor_cost + gemini_cost
        cls._stats["total_cost_usd"] = round(cls._stats["total_cost_usd"] + total_cost, 6)
        
        # Calculate average MCP duration
        if cls._mcp_durations:
            cls._stats["avg_mcp_duration_ms"] = round(sum(cls._mcp_durations) / len(cls._mcp_durations), 2)
            
        # Compile structured audit log entry
        log_entry = {
            "timestamp": timestamp,
            "client_ip": client_ip,
            "user_email": user_email,
            "tenant_id": tenant_id,
            "query": query,
            "status": status,
            "block_reason": block_reason,
            "cloud_armor_rule": cloud_armor_res["policy_rule"],
            "model_armor": {
                "injection_score": model_armor_res.get("injection_score", 0.0) if model_armor_res else 0.0,
                "jailbreak_detected": model_armor_res.get("jailbreak_detected", False) if model_armor_res else False,
                "pii_redacted": model_armor_res.get("pii_detected", False) if model_armor_res else False,
                "redacted_prompt": model_armor_res.get("sanitized_prompt", query) if model_armor_res else query
            } if model_armor_res else None,
            "agent_performance": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": round(total_cost, 6),
                "tool_calls": agent_res.get("tool_calls", []) if agent_res else []
            } if agent_res else None,
            "response_security": {
                "leaks_found": response_armor_res.get("leaked_data_types", []) if response_armor_res else [],
                "sanitized": response_armor_res.get("safe", True) if response_armor_res else True
            } if response_armor_res else None
        }
        
        cls._logs.insert(0, log_entry)
        
        # Keep logs list size capped to last 100 entries
        if len(cls._logs) > 100:
            cls._logs.pop()
            
        return log_entry

    @classmethod
    def get_logs(cls) -> List[Dict[str, Any]]:
        return cls._logs

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        # Return a copy to prevent mutation
        return {**cls._stats}
