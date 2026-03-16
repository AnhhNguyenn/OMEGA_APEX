from typing import TypedDict, Annotated, List, Dict, Any
from langgraph.graph import StateGraph, START, END
from litellm import completion
import json
import os
from dotenv import load_dotenv
from config.logger_setup import setup_logger

logger = setup_logger("coordinator")

load_dotenv()

# Define the Graph State
class AgentState(TypedDict):
    market_data: str
    scout_report: str
    analyst_report: str
    skeptic_report: str
    judge_verdict: str
    round_number: int  # Max 3 rounds
    final_decision: Dict[str, Any]

def scout_node(state: AgentState):
    """
    Scout (Gemini Flash): Gathers & summarizes raw data.
    """
    logger.info(f"[Round {state['round_number']}] Scout is analyzing raw data...")
    # Litellm call using gemini
    response = completion(
        model="gemini/gemini-1.5-flash",
        messages=[{"role": "user", "content": f"Summarize this market data simply: {state['market_data']}"}]
    )
    return {"scout_report": response.choices[0].message.content if hasattr(response, 'choices') else response}


def analyst_node(state: AgentState):
    """
    Analyst (DeepSeek-V3): Finds mathematical/structural patterns.
    """
    logger.info(f"[Round {state['round_number']}] Analyst is finding patterns...")
    response = completion(
        model="deepseek/deepseek-chat", # deepseek-v3 equivalent typically
        messages=[{"role": "user", "content": f"Analyze patterns based on: {state['scout_report']}"}]
    )
    return {"analyst_report": response.choices[0].message.content if hasattr(response, 'choices') else response}


def skeptic_node(state: AgentState):
    """
    Skeptic (Claude Sonnet / DeepSeek): Try to invalidate the analyst's thesis.
    """
    logger.info(f"[Round {state['round_number']}] Skeptic is challenging the thesis...")
    response = completion(
        model="deepseek/deepseek-chat", 
        messages=[{"role": "user", "content": f"Debunk this analysis: {state['analyst_report']}"}]
    )
    return {"skeptic_report": response.choices[0].message.content if hasattr(response, 'choices') else response}


def judge_node(state: AgentState):
    """
    Judge (DeepSeek-R1): The final decider after considering all arguments.
    """
    logger.info(f"[Round {state['round_number']}] Judge is evaluating...")
    
    prompt = f"""
    Review the debate:
    Scout: {state['scout_report']}
    Analyst: {state['analyst_report']}
    Skeptic: {state['skeptic_report']}
    Is there a consensus to trade? Respond with JSON: {{"decision": "BUY"|"SELL"|"HOLD", "confidence": 0-100}}
    """
    
    response = completion(
        model="deepseek/deepseek-reasoner", # R1 logic model
        messages=[{"role": "user", "content": prompt}]
    )
    
    content = response.choices[0].message.content if hasattr(response, 'choices') else response
    try:
        verdict_dict = json.loads(content)
    except:
        verdict_dict = {"decision": "HOLD", "confidence": 0}

    return {"judge_verdict": content, "final_decision": verdict_dict}


def debate_router(state: AgentState) -> str:
    """
    Route according to consensus and round count.
    """
    decision = state.get("final_decision", {}).get("decision", "HOLD")
    confidence = state.get("final_decision", {}).get("confidence", 0)
    round_number = state.get("round_number", 0)

    try:
        from data.db_manager import DatabaseManager
        db = DatabaseManager()
        db.log_agent_debate(state.get("market_data", "UNKNOWN_SYMBOL")[:10], state)
    except Exception as e:
        logger.error(f"Failed to log debate to DB: {e}", exc_info=True)
        
    if decision == "HOLD" and round_number < 3:
        logger.warning(f"Consensus not reached or HOLD decided (Round {round_number}). Looping to NEXT_ROUND...")
        return "NEXT_ROUND"
    else:
        logger.info(f"Debate finalized. Consesus: {decision} with {confidence}% confidence.")
        return "END"


def increment_round(state: AgentState):
    return {"round_number": state["round_number"] + 1}


# Build LangGraph
builder = StateGraph(AgentState)

builder.add_node("Scout", scout_node)
builder.add_node("Analyst", analyst_node)
builder.add_node("Skeptic", skeptic_node)
builder.add_node("Judge", judge_node)
builder.add_node("RoundCounter", increment_round)

builder.add_edge(START, "Scout")
builder.add_edge("Scout", "Analyst")
builder.add_edge("Analyst", "Skeptic")
builder.add_edge("Skeptic", "Judge")

# Conditional edges from Judge
builder.add_conditional_edges(
    "Judge",
    debate_router,
    {
        "END": END,
        "NEXT_ROUND": "RoundCounter"
    }
)
builder.add_edge("RoundCounter", "Scout")

brain_orchestrator = builder.compile()

# For Testing
if __name__ == "__main__":
    initial_state = {
        "market_data": "BTC Price: $65000, Vol: 1.2B, Social sentiment: Greedy",
        "round_number": 1
    }
    logger.info("Starting Multi-Agent Brain Local Test...")
    # NOTE: Run requires API Keys in .env to call litellm properly, 
    # but mock_response allows local dry-run.
    result = brain_orchestrator.invoke(initial_state)
    logger.info(f"FINAL DEBATE OUTCOME: {result['final_decision']}")
