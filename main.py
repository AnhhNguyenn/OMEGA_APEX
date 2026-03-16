from fastapi import FastAPI
import uvicorn
import yaml
import os

from agents.coordinator import brain_orchestrator, AgentState

ASCII_LOGO = """
██████╗ ███╗   ███╗███████╗ ██████╗  █████╗      █████╗ ██████╗ ███████╗██╗  ██╗
██╔═══██╗████╗ ████║██╔════╝██╔════╝ ██╔══██╗    ██╔══██╗██╔══██╗██╔════╝╚██╗██╔╝
██║   ██║██╔████╔██║█████╗  ██║  ███╗███████║    ███████║██████╔╝█████╗   ╚███╔╝ 
██║   ██║██║╚██╔╝██║██╔══╝  ██║   ██║██╔══██║    ██╔══██║██╔═══╝ ██╔══╝   ██╔██╗ 
╚██████╔╝██║ ╚═╝ ██║███████╗╚██████╔╝██║  ██║    ██║  ██║██║     ███████╗██╔╝ ██╗
 ╚═════╝ ╚═╝     ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝    ╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝
                                [ MARKET PREDATOR V1.0 ]
"""

app = FastAPI(title="OMEGA APEX", description="Hyper-Growth Trading System API")

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {"capital": 0, "target_goal": 0, "timeframe_days": 0}

@app.on_event("startup")
async def startup_event():
    print(ASCII_LOGO)
    config = load_config()
    print(f"System Initialized. Capital constraint: ${config.get('capital')}")

@app.get("/")
def read_root():
    return {"status": "OMEGA APEX is running", "version": "1.0"}

@app.post("/trigger_analysis")
def trigger_analysis(symbol: str):
    """
    Manually trigger the LangGraph multi-agent debate for a given symbol.
    """
    # Mocking fetching data via CCXT
    initial_state = {
        "market_data": f"{symbol} Price: Latest. High volume spike detected. Sentiments normal.",
        "round_number": 1
    }
    
    # Run Graph
    result = brain_orchestrator.invoke(initial_state)
    
    return {
        "symbol": symbol,
        "recommendation": result.get("final_decision"),
        "total_rounds": result.get("round_number")
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
