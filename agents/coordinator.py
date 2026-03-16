from typing import TypedDict, Annotated, List, Dict, Any
from langgraph.graph import StateGraph, START, END
from litellm import completion
import json
import os
from dotenv import load_dotenv

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
    print(f"[Round {state['round_number']}] Scout is analyzing raw data...")
    # Litellm call using gemini
    response = completion(
        model="gemini/gemini-1.5-flash",
        messages=[{"role": "user", "content": f"Summarize this market data simply: {state['market_data']}"}],
        mock_response="Scout summary: High volatility detected in BTC. Positive sentiment." # Mocked for no keys
    )
    # Using mock_response string if API keys missing, for robustness
    return {"scout_report": response.choices[0].message.content if hasattr(response, 'choices') else response}


def analyst_node(state: AgentState):
    """
    Analyst (DeepSeek-V3): Finds mathematical/structural patterns.
    """
    print(f"[Round {state['round_number']}] Analyst is finding patterns...")
    response = completion(
        model="deepseek/deepseek-chat", # deepseek-v3 equivalent typically
        messages=[{"role": "user", "content": f"Analyze patterns based on: {state['scout_report']}"}],
        mock_response="Analyst report: Breakout pattern forming. Bullish."
    )
    return {"analyst_report": response.choices[0].message.content if hasattr(response, 'choices') else response}


def skeptic_node(state: AgentState):
    """
    Skeptic (Claude Sonnet / DeepSeek): Try to invalidate the analyst's thesis.
    """
    print(f"[Round {state['round_number']}] Skeptic is challenging the thesis...")
    response = completion(
        model="deepseek/deepseek-chat", 
        messages=[{"role": "user", "content": f"Debunk this analysis: {state['analyst_report']}"}],
        mock_response="Skeptic report: Volume does not support the breakout. Fakeout risk high."
    )
    return {"skeptic_report": response.choices[0].message.content if hasattr(response, 'choices') else response}


def judge_node(state: AgentState):
    """
    Judge (DeepSeek-R1): The final decider after considering all arguments.
    """
    print(f"[Round {state['round_number']}] Judge is evaluating...")
    
    prompt = f"""
    Review the debate:
    Scout: {state['scout_report']}
    Analyst: {state['analyst_report']}
    Skeptic: {state['skeptic_report']}
    Is there a consensus to trade? Respond with JSON: {{"decision": "BUY"|"SELL"|"HOLD", "confidence": 0-100}}
    """
    
    response = completion(
        model="deepseek/deepseek-reasoner", # R1 logic model
        messages=[{"role": "user", "content": prompt}],
        mock_response='{"decision": "HOLD", "confidence": 60}'
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
    
    if confidence >= 85 and decision != "HOLD":
        print(f"-> Strong Consensus reached: {decision} ({confidence}%). Ending debate.")
        return "END"
    
    if state["round_number"] >= 3:
        print(f"-> Debate reached max rounds (3). Forcing final decision.")
        return "END"
        
    print(f"-> Confidence low ({confidence}%) or HOLD. Proceeding to next round.")
    return "NEXT_ROUND"


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
    print("Starting Multi-Agent Brain...")
    # NOTE: Run requires API Keys in .env to call litellm properly, 
    # but mock_response allows local dry-run.
    result = brain_orchestrator.invoke(initial_state)
    print(f"\\nFINAL DEBATE OUTCOME: {result['final_decision']}")
