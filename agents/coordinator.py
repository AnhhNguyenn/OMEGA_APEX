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
    news_report: str
    scout_report: str
    macro_report: str
    whale_report: str
    analyst_report: str
    skeptic_report: str
    judge_verdict: str
    round_number: int  # Max 3 rounds
    final_decision: Dict[str, Any]


def scout_node(state: AgentState):
    """
    Scout (Gemini Flash): Gathers & summarizes raw data and LIVE NEWS.
    """
    logger.info(f"[Round {state['round_number']}] Scout is analyzing raw data and live news...")
    prompt = f"Summarize this market data and correlate it with the recent news context simply:\nMARKET: {state.get('market_data', '')}\nLIVE NEWS: {state.get('news_report', 'No news.')}"
    
    response = completion(
        model="gemini/gemini-1.5-flash",
        messages=[{"role": "user", "content": prompt}]
    )
    return {"scout_report": response.choices[0].message.content if hasattr(response, 'choices') else response}


def macro_node(state: AgentState):
    """
    Macro Agent: Assesses global economic conditions.
    """
    logger.info(f"[Round {state['round_number']}] Macro Agent checking economic weather...")
    macro_data = state.get("macro_report", "No macro data provided.")
    response = completion(
        model="gemini/gemini-1.5-flash",
        messages=[{"role": "user", "content": f"Summarize this macro economic data and its potential impact on Crypto: {macro_data}"}]
    )
    return {"macro_report": response.choices[0].message.content if hasattr(response, 'choices') else response}


def whale_node(state: AgentState):
    """
    Whale Tracker: Analyzes on-chain large movements.
    """
    logger.info(f"[Round {state['round_number']}] Whale Tracker scanning for leviathans...")
    whale_data = state.get("whale_report", "No whale data provided.")
    response = completion(
        model="gemini/gemini-1.5-flash",
        messages=[{"role": "user", "content": f"Analyze this whale transaction data for buy/sell pressure: {whale_data}"}]
    )
    return {"whale_report": response.choices[0].message.content if hasattr(response, 'choices') else response}


def analyst_node(state: AgentState):
    """
    Analyst (DeepSeek-V3): Finds mathematical/structural patterns.
    """
    logger.info(f"[Round {state['round_number']}] Analyst is finding patterns...")
    prompt = f"Analyze patterns based on:\nScout: {state.get('scout_report', '')}\nMacro: {state.get('macro_report', '')}\nWhale: {state.get('whale_report', '')}"
    response = completion(
        model="deepseek/deepseek-chat",
        messages=[{"role": "user", "content": prompt}]
    )
    return {"analyst_report": response.choices[0].message.content if hasattr(response, 'choices') else response}


def skeptic_node(state: AgentState):
    """
    Skeptic (Claude Sonnet / DeepSeek): Try to invalidate the analyst's thesis.
    """
    logger.info(f"[Round {state['round_number']}] Skeptic is challenging the thesis...")
    response = completion(
        model="deepseek/deepseek-chat", 
        messages=[{"role": "user", "content": f"Debunk this analysis: {state.get('analyst_report', '')}"}]
    )
    return {"skeptic_report": response.choices[0].message.content if hasattr(response, 'choices') else response}


def judge_node(state: AgentState):
    """
    Judge (DeepSeek-R1): The final decider after considering all arguments.
    """
    logger.info(f"[Round {state['round_number']}] Judge is evaluating...")
    
    prompt = f"""
    Review the debate for symbol {state.get('market_data', 'UNKNOWN')[:15]}:
    Scout (Technicals): {state.get('scout_report', '')}
    Macro (Economy): {state.get('macro_report', '')}
    Whale (On-chain): {state.get('whale_report', '')}
    Analyst (Bull/Bear Thesis): {state.get('analyst_report', '')}
    Skeptic (Risks): {state.get('skeptic_report', '')}
    
    Is there a consensus to trade? Overrule technicals if Macro or Whale signals are highly dangerous. 
    Respond EXACTLY with JSON: {{"decision": "BUY"|"SELL"|"HOLD", "confidence": 0-100, "reason": "Short explanation"}}
    """
    
    response = completion(
        model="deepseek/deepseek-reasoner",
        messages=[{"role": "user", "content": prompt}]
    )
    
    content = response.choices[0].message.content if hasattr(response, 'choices') else response
    try:
        verdict_dict = json.loads(content)
    except:
        verdict_dict = {"decision": "HOLD", "confidence": 0, "reason": "Failed to parse judge response."}

    logger.info(f"Judge decided: {verdict_dict.get('decision')} (Confidence: {verdict_dict.get('confidence')}%)")
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
        db.log_agent_debate(str(state.get("market_data", "UNKNOWN_SYMBOL"))[:10], dict(state))
    except Exception as e:
        logger.error(f"Failed to log debate to DB: {e}", exc_info=True)
        
    if decision == "HOLD" and round_number < 3:
        logger.warning(f"Consensus not reached or HOLD decided (Round {round_number}). Looping to NEXT_ROUND...")
        return "NEXT_ROUND"
    else:
        logger.info(f"Debate finalized. Consensus: {decision} with {confidence}% confidence.")
        return "END"


def increment_round(state: AgentState):
    return {"round_number": state.get("round_number", 0) + 1}


# Build LangGraph
builder = StateGraph(AgentState)

builder.add_node("Scout", scout_node)
builder.add_node("Macro", macro_node)
builder.add_node("Whale", whale_node)
builder.add_node("Analyst", analyst_node)
builder.add_node("Skeptic", skeptic_node)
builder.add_node("Judge", judge_node)
builder.add_node("RoundCounter", increment_round)

# Parallel execution for data gathering (Scout, Macro, Whale) -> Analyst
builder.add_edge(START, "Scout")
builder.add_edge(START, "Macro")
builder.add_edge(START, "Whale")

builder.add_edge(["Scout", "Macro", "Whale"], "Analyst")
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
# Reset nodes on new round
builder.add_edge("RoundCounter", "Scout")
builder.add_edge("RoundCounter", "Macro")
builder.add_edge("RoundCounter", "Whale")

brain_orchestrator = builder.compile()

# For Testing
if __name__ == "__main__":
    initial_state = {
        "market_data": "BTC Price: $65000, Vol: 1.2B, Social sentiment: Greedy",
        "macro_report": "CPI at 3.1%, Fed pausing rates.",
        "whale_report": "1000 BTC moved to Coinbase.",
        "round_number": 1
    }
    logger.info("Starting Multi-Agent Brain Local Test...")
    result = brain_orchestrator.invoke(initial_state)
    logger.info(f"FINAL DEBATE OUTCOME: {result.get('final_decision')}")
