import numpy as np
from typing import Dict, Any

from config.logger_setup import setup_logger

logger = setup_logger("math_tools")

def calculate_kelly(win_rate: float, win_loss_ratio: float, trading_fee_pct: float, api_cost_fixed: float, capital: float) -> float:
    """
    Calculate the optimal Kelly Criterion fraction, adjusted for trading fees and fixed API costs.
    
    Args:
        win_rate (float): Probability of a winning trade (0.0 to 1.0)
        win_loss_ratio (float): The ratio of average win amount to average loss amount.
        trading_fee_pct (float): Trading fee as a percentage applied per trade (e.g., 0.001 for 0.1%).
        api_cost_fixed (float): The fixed cost of the API calls per trade in $.
        capital (float): Current total trading capital.
        
    Returns:
        float: The optimal fraction of capital to risk per trade (e.g. 0.05 for 5%).
    """
    # Adjust win_loss_ratio by subtracting fees from the win and adding fees to the loss
    # Also subtracting fixed API cost relative to an assumed standardized bet size.
    # To simplify mathematically, we calculate the effective return.
    
    # Let W be average win size before fees, L be average loss size before fees
    # Effective Win = W - W * trading_fee_pct - api_cost_fixed
    # Effective Loss = L + L * trading_fee_pct + api_cost_fixed
    
    # Because Kelly formula is K = p - (1-p) / (Effective_Win / Effective_Loss)
    # We estimate based on the given ratio (assuming L = 1 unit)
    
    # Approximated adjusted ratio `b`
    effective_win = win_loss_ratio * (1 - trading_fee_pct) - (api_cost_fixed / capital if capital > 0 else 0)
    effective_loss = 1 * (1 + trading_fee_pct) + (api_cost_fixed / capital if capital > 0 else 0)
    
    if effective_loss <= 0 or effective_win <= 0:
        return 0.0
        
    b = effective_win / effective_loss
    p = win_rate
    q = 1.0 - p
    
    if b <= 0:
        return 0.0
        
    kelly_fraction = max(0.0, p - (q / b))
    logger.info(f"Calculated Kelly: p={win_rate:.2f}, R={win_loss_ratio:.2f}, adj_b={b:.2f} -> {kelly_fraction:.4f}")
    
    # Half-Kelly is often used in practice for safety, but we strictly return full Kelly here.
    return kelly_fraction


def target_decomposer(target_capital: float, current_capital: float, remaining_days: int) -> Dict[str, Any]:
    """
    Automatically breaks down the net profit target into daily required returns 
    based on the current progress and remaining days.
    
    Args:
        target_capital (float): The ultimate goal (e.g., $30B).
        current_capital (float): Currently available capital.
        remaining_days (int): Days left to reach the target.
        
    Returns:
        Dict: Contains daily required multiplier, target profit for the next day, etc.
    """
    if remaining_days <= 0:
        return {
            "required_daily_growth_rate": 0.0,
            "next_day_target": target_capital if current_capital < target_capital else current_capital,
            "status": "Time expired or Target reached"
        }
    
    if current_capital >= target_capital:
        return {
            "required_daily_growth_rate": 0.0,
            "next_day_target": current_capital,
            "status": "Target already reached"
        }
        
    if current_capital <= 0:
        raise ValueError("Current capital must be greater than 0 to calculate CDGR.")
        
    # Calculate Required Compound Daily Growth Rate (CDGR)
    # Target = Current * (1 + r)^n => r = (Target/Current)^(1/n) - 1
    required_rate = (target_capital / current_capital) ** (1.0 / remaining_days) - 1.0
    
    next_day_target = current_capital * (1.0 + required_rate)
    next_day_profit_req = next_day_target - current_capital
    
    return {
        "required_daily_growth_rate": required_rate,
        "next_day_target": next_day_target,
        "next_day_profit_required": next_day_profit_req,
        "status": "On track"
    }


def monte_carlo_simulation(initial_capital: float, target_capital: float, 
                           win_rate: float, win_loss_ratio: float, 
                           trades_per_day: int, days: int, 
                           iterations: int = 1_000_000) -> float:
    """
    Run Monte Carlo simulations to forecast the probability of hitting the final target 
    (e.g., $30B) given market variation.
    
    Args:
        initial_capital (float): Starting capital.
        target_capital (float): Goal capital.
        win_rate (float): Estimated probability of winning.
        win_loss_ratio (float): Average win vs average loss.
        trades_per_day (int): Approximate number of trades per day.
        days (int): Number of trading days.
        iterations (int): Number of simulation paths (default 1,000,000 requests by user).
        
    Returns:
        float: Probability (0.0 to 1.0) of reaching or exceeding the target capital.
    """
    total_trades = trades_per_day * days
    
    # For performance on 1M iterations, we use vectorized numpy operations.
    # We will simulate the number of wins in 'total_trades' using Binomial distribution.
    wins = np.random.binomial(total_trades, win_rate, size=iterations)
    losses = total_trades - wins
    
    # Instead of an arbitrary fixed risk, we calculate the Kelly fraction
    # to dynamically use leverage that mathematically maximizes growth rate.
    # K = W - (1-W)/R
    kelly_fraction = win_rate - ( (1.0 - win_rate) / win_loss_ratio )
    if kelly_fraction <= 0:
        return 0.0 # If kelly is negative or 0, we can't mathematically reach the goal
        
    # We use a fraction of Kelly (e.g. Full Kelly or Half Kelly). 
    # For a high-growth target, we might need Full Kelly.
    risk_per_trade = kelly_fraction
    
    win_multiplier = 1.0 + (risk_per_trade * win_loss_ratio)
    loss_multiplier = 1.0 - risk_per_trade
    
    # Final capital for each simulation path:
    # Final = Initial * (win_multiplier ^ wins) * (loss_multiplier ^ losses)
    final_capitals = initial_capital * (win_multiplier ** wins) * (loss_multiplier ** losses)
    
    # Count how many simulations reached the target
    successes = np.sum(final_capitals >= target_capital)
    
    probability = successes / iterations
    logger.info(f"Monte Carlo simulation (1M) results: {successes} successes -> {probability*100:.2f}% probability of $30B.")
    return float(probability)
