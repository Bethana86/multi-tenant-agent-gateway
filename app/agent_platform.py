import sqlite3
import os
import time
from typing import Dict, Any, List, Tuple
from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPIError

# Path to the Tenant B SQLite Database
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fincorp.db")

class MCPServer:
    """Simulates Model Context Protocol (MCP) server providing secure database access tools."""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        # Initialize BigQuery Client
        try:
            self.bq_client = bigquery.Client(project=self.project_id)
            self.bq_available = True
        except Exception as e:
            print(f"BigQuery Client initialization error: {e}")
            self.bq_available = False

    # --- Tenant A Tools (BigQuery Datastore) ---
    
    def query_historical_forecast(self, limit: int = 5) -> Tuple[List[Dict[str, Any]], str]:
        """Tool: Retrieve historical metrics forecast data from BigQuery."""
        if not self.bq_available:
            return [], "BigQuery Client not available."
        
        query = f"""
            SELECT timestamp, value 
            FROM `{self.project_id}.fusion_ai.historical_metrics_forecast`
            ORDER BY timestamp DESC
            LIMIT {limit}
        """
        try:
            start_time = time.time()
            query_job = self.bq_client.query(query)
            results = list(query_job.result())
            duration = time.time() - start_time
            
            data = [{"timestamp": str(r.timestamp), "value": r.value} for r in results]
            trace_log = f"SQL Execute: SELECT * FROM fusion_ai.historical_metrics_forecast LIMIT {limit} | Time: {duration:.3f}s"
            return data, trace_log
        except Exception as e:
            return [], f"BigQuery Query Error: {str(e)}"

    def list_recent_anomalies(self, limit: int = 5) -> Tuple[List[Dict[str, Any]], str]:
        """Tool: Retrieve metrics anomalies from BigQuery."""
        if not self.bq_available:
            return [], "BigQuery Client not available."
            
        query = f"""
            SELECT timestamp, value 
            FROM `{self.project_id}.fusion_ai.historical_metrics_anomaly`
            ORDER BY timestamp DESC
            LIMIT {limit}
        """
        try:
            start_time = time.time()
            query_job = self.bq_client.query(query)
            results = list(query_job.result())
            duration = time.time() - start_time
            
            data = [{"timestamp": str(r.timestamp), "value": r.value} for r in results]
            trace_log = f"SQL Execute: SELECT * FROM fusion_ai.historical_metrics_anomaly LIMIT {limit} | Time: {duration:.3f}s"
            return data, trace_log
        except Exception as e:
            return [], f"BigQuery Query Error: {str(e)}"

    # --- Tenant B Tools (Local SQLite Datastore) ---
    
    def query_stock_forecast(self, ticker: str) -> Tuple[List[Dict[str, Any]], str]:
        """Tool: Retrieve forecasted stock trends for a ticker from SQLite."""
        ticker = ticker.upper().strip()
        start_time = time.time()
        
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT timestamp, forecast_value, confidence_lower, confidence_upper FROM stock_forecasts WHERE ticker = ? ORDER BY timestamp ASC",
                (ticker,)
            )
            rows = cursor.fetchall()
            conn.close()
            duration = time.time() - start_time
            
            data = [dict(row) for row in rows]
            trace_log = f"SQL Execute: SELECT * FROM stock_forecasts WHERE ticker = '{ticker}' | Time: {duration:.3f}s"
            return data, trace_log
        except Exception as e:
            return [], f"SQLite Query Error: {str(e)}"

    def list_market_news(self, ticker: str) -> Tuple[List[Dict[str, Any]], str]:
        """Tool: Retrieve market news sentiment for a ticker from SQLite."""
        ticker = ticker.upper().strip()
        start_time = time.time()
        
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT headline, sentiment, timestamp FROM market_news WHERE ticker = ? ORDER BY timestamp DESC",
                (ticker,)
            )
            rows = cursor.fetchall()
            conn.close()
            duration = time.time() - start_time
            
            data = [dict(row) for row in rows]
            trace_log = f"SQL Execute: SELECT * FROM market_news WHERE ticker = '{ticker}' | Time: {duration:.3f}s"
            return data, trace_log
        except Exception as e:
            return [], f"SQLite Query Error: {str(e)}"


class AgentRuntime:
    """Simulates the isolated Tenant Agent Runtime environment invoking Gemini and secure tools."""

    def __init__(self, tenant_id: str, project_id: str):
        self.tenant_id = tenant_id  # 'tenant_a' or 'tenant_b'
        self.project_id = project_id
        self.mcp = MCPServer(project_id)
        
        # Configure prompts and metadata based on tenant id
        if self.tenant_id == "tenant_a":
            self.agent_name = "Fusion AI Operations Assistant"
            self.system_prompt = (
                "You are the Fusion AI Operations Assistant. Your job is to analyze historical metrics forecasts "
                "and anomalies stored in BigQuery, and assist DevOps engineers with system health monitoring."
            )
        else:
            self.agent_name = "FinCorp Advisory Agent"
            self.system_prompt = (
                "You are the FinCorp Stock Advisory Agent. Your job is to analyze stock forecast trends "
                "and news sentiment from the FinCorp database and provide investment market insights."
            )

    def execute_query(self, user_query: str) -> Dict[str, Any]:
        """
        Executes the agent loop:
        1. Analyzes the query
        2. Selects and runs the appropriate tool via MCP
        3. Invokes Gemini (or fallback simulator) to synthesize the response
        """
        thinking_trace = []
        tool_calls = []
        result_data = None
        
        thinking_trace.append(f"System: Initializing Agent Session - Role: {self.agent_name}")
        thinking_trace.append(f"System: Active System Prompt: '{self.system_prompt}'")
        thinking_trace.append(f"Thought: Analyzing user query: '{user_query}'")
        
        query_lower = user_query.lower()
        
        # Tool Selection Logic based on Tenant and keywords
        if self.tenant_id == "tenant_a":
            if "anomaly" in query_lower or "anomalies" in query_lower or "outlier" in query_lower:
                thinking_trace.append("Thought: The user is asking about anomalies. I need to list recent anomalies from BigQuery.")
                thinking_trace.append("Action: Invoke MCP tool 'list_recent_anomalies' with limit=5")
                
                data, log = self.mcp.list_recent_anomalies(limit=5)
                tool_calls.append({"tool": "list_recent_anomalies", "status": "SUCCESS", "log": log})
                result_data = data
                thinking_trace.append(f"Result: Received {len(data)} anomaly data records from BigQuery.")
                
            else:
                thinking_trace.append("Thought: The user is asking about forecasts or metrics. I need to query historical forecasts from BigQuery.")
                thinking_trace.append("Action: Invoke MCP tool 'query_historical_forecast' with limit=5")
                
                data, log = self.mcp.query_historical_forecast(limit=5)
                tool_calls.append({"tool": "query_historical_forecast", "status": "SUCCESS", "log": log})
                result_data = data
                thinking_trace.append(f"Result: Received {len(data)} forecast records from BigQuery.")
                
        else:  # tenant_b
            # Extract ticker symbol
            ticker = "GOOGL" # Default
            for t in ["GOOGL", "AAPL", "MSFT", "AMZN"]:
                if t in user_query.upper():
                    ticker = t
                    break
            
            if "news" in query_lower or "sentiment" in query_lower or "headline" in query_lower:
                thinking_trace.append(f"Thought: User wants news details for ticker {ticker}. I need to check recent market news.")
                thinking_trace.append(f"Action: Invoke MCP tool 'list_market_news' with ticker='{ticker}'")
                
                data, log = self.mcp.list_market_news(ticker)
                tool_calls.append({"tool": "list_market_news", "status": "SUCCESS", "log": log})
                result_data = data
                thinking_trace.append(f"Result: Received {len(data)} news records from the database.")
            else:
                thinking_trace.append(f"Thought: User wants stock forecast/trend for ticker {ticker}.")
                thinking_trace.append(f"Action: Invoke MCP tool 'query_stock_forecast' with ticker='{ticker}'")
                
                data, log = self.mcp.query_stock_forecast(ticker)
                tool_calls.append({"tool": "query_stock_forecast", "status": "SUCCESS", "log": log})
                result_data = data
                thinking_trace.append(f"Result: Received {len(data)} forecast data points for {ticker}.")

        # Generate response using LLM logic
        thinking_trace.append("Thought: Formulating final response based on database results...")
        response_text = self._simulate_gemini_generation(user_query, result_data, ticker=ticker if self.tenant_id == 'tenant_b' else None)
        
        return {
            "agent_name": self.agent_name,
            "thinking_trace": thinking_trace,
            "tool_calls": tool_calls,
            "result_data": result_data,
            "response": response_text
        }

    def _simulate_gemini_generation(self, query: str, data: Any, ticker: str = None) -> str:
        """Simulates Gemini output synthesis from RAG context."""
        time.sleep(0.8) # Simulate generation latency
        
        if self.tenant_id == "tenant_a":
            if "anomaly" in query.lower() or "anomalies" in query.lower():
                if not data:
                    return "No recent system anomalies were found in the database. All systems are stable."
                latest = data[0]
                return (
                    f"Based on the BigQuery database metrics records, the latest system anomaly was detected at "
                    f"**{latest['timestamp']}** with an abnormal metric value of **{latest['value']:.2f}**. "
                    f"The operations log suggests checking the load distribution since this value exceeds the warning threshold."
                )
            else:
                if not data:
                    return "No metrics forecast data is currently loaded in the BigQuery tables."
                latest = data[0]
                return (
                    f"According to the latest historical metric forecasting data from BigQuery, the system metric is forecasted at "
                    f"**{latest['value']:.2f}** for timestamp **{latest['timestamp']}**. "
                    f"The trend indicates steady traffic with no immediate capacity risks detected."
                )
        else:  # tenant_b
            if "news" in query.lower() or "sentiment" in query.lower():
                if not data:
                    return f"No recent news headlines are registered for {ticker}."
                headline = data[0]
                return (
                    f"Here is the latest market news context retrieved for **{ticker}**:\n"
                    f"- **Headline**: \"{headline['headline']}\"\n"
                    f"- **Sentiment**: `{headline['sentiment']}`\n"
                    f"- **Date**: {headline['timestamp']}\n\n"
                    f"Overall, market sentiment remains positive, supporting a favorable outlook."
                )
            else:
                if not data:
                    return f"No stock forecast data is available in the database for ticker {ticker}."
                latest = data[-1]
                initial = data[0]
                direction = "upward" if latest['forecast_value'] > initial['forecast_value'] else "downward"
                return (
                    f"Analyzing the 14-day stock price forecasting data for **{ticker}**:\n"
                    f"- **Current Forecast Value**: ${initial['forecast_value']:.2f} (Interval: ${initial['confidence_lower']:.2f} - ${initial['confidence_upper']:.2f})\n"
                    f"- **Target 14-day Forecast**: ${latest['forecast_value']:.2f} (Interval: ${latest['confidence_lower']:.2f} - ${latest['confidence_upper']:.2f})\n"
                    f"- **Trend**: Showing an overall **{direction}** trend.\n\n"
                    f"This forecast suggest a stable performance over the next two weeks."
                )
