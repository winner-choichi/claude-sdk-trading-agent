"""
Autonomous strategy management system
The agent creates, evolves, and manages its own trading strategies
"""

from datetime import datetime
from typing import Dict, Any, Optional
import json


class AutonomousStrategyManager:
    """
    Manages self-evolving trading strategies

    The agent has full control over:
    - Strategy creation and refinement
    - Risk management parameters
    - Position sizing rules
    - Confidence thresholds
    """

    def __init__(self, database, initial_params: Optional[Dict[str, float]] = None):
        """
        Initialize strategy manager

        Args:
            database: Database instance
            initial_params: Initial parameter values
        """
        self.database = database

        # Default initial parameters (very conservative)
        self.default_params = {
            "auto_trade_confidence_threshold": 0.95,  # Very high initially
            "max_position_size_pct": 10.0,  # Max 10% per position
            "max_portfolio_exposure_pct": 80.0,  # Max 80% invested
            "daily_loss_limit_pct": 2.0,  # Stop if lose 2% in a day
            "min_risk_reward_ratio": 2.0,  # Minimum 2:1 risk/reward
            "learning_aggression": 0.5  # 0=conservative, 1=aggressive
        }

        # Initialize parameters in database
        self._initialize_parameters(initial_params or {})

    def _initialize_parameters(self, custom_params: Dict[str, Any]) -> None:
        """Initialize parameters in database if they don't exist"""

        # Merge defaults with custom
        params = {**self.default_params, **custom_params}

        # Check each parameter - only store numeric parameters
        for name, value in params.items():
            # Skip non-numeric parameters (like learning_rate string)
            if not isinstance(value, (int, float)):
                continue

            existing = self.database.get_parameter(name)
            if existing is None:
                self.database.update_parameter(
                    name=name,
                    value=value,
                    reason="Initial system setup"
                )

    def get_parameter(self, name: str) -> float:
        """Get current parameter value"""
        value = self.database.get_parameter(name)
        return value if value is not None else self.default_params.get(name, 0.0)

    def get_all_parameters(self) -> Dict[str, float]:
        """Get all current parameters"""
        return self.database.get_all_parameters()

    def update_parameter(
        self,
        name: str,
        new_value: float,
        reason: str,
        agent_decision: bool = True
    ) -> None:
        """
        Update a parameter value

        Args:
            name: Parameter name
            new_value: New value
            reason: Explanation for change
            agent_decision: True if agent decided this autonomously
        """
        self.database.update_parameter(name, new_value, reason)

        # Log this as a learning insight if it was autonomous
        if agent_decision:
            insight_data = {
                "insight_type": "parameter_adjustment",
                "description": f"Adjusted {name} to {new_value}",
                "confidence": 0.8,
                "supporting_data": {
                    "parameter": name,
                    "new_value": new_value,
                    "reason": reason
                },
                "action_taken": f"Updated {name}",
                "status": "active"
            }
            self.database.save_learning_insight(insight_data)

    def get_auto_trade_threshold(self) -> float:
        """Get current confidence threshold for auto-trading"""
        return self.get_parameter("auto_trade_confidence_threshold")

    def should_auto_execute(
        self,
        confidence: float,
        recent_performance: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Decide if a trade should auto-execute based on confidence

        Args:
            confidence: Trade confidence (0-1)
            recent_performance: Recent performance metrics

        Returns:
            True if should auto-execute
        """
        threshold = self.get_auto_trade_threshold()

        # Basic threshold check
        if confidence < threshold:
            return False

        # Additional checks based on recent performance
        if recent_performance:
            # If recent win rate is low, be more conservative
            win_rate = recent_performance.get("win_rate", 0.5)
            if win_rate < 0.4:
                # Temporarily increase threshold
                adjusted_threshold = threshold + 0.05
                return confidence >= adjusted_threshold

            # If we're near daily loss limit, pause auto-trading
            daily_pnl_pct = recent_performance.get("daily_pnl_pct", 0)
            loss_limit = self.get_parameter("daily_loss_limit_pct")
            if daily_pnl_pct < -loss_limit * 0.8:  # 80% of limit
                return False

        return True

    def calculate_position_size(
        self,
        symbol: str,
        confidence: float,
        account_value: float,
        current_price: float,
        current_exposure: float = 0.0
    ) -> int:
        """
        Calculate optimal position size

        Args:
            symbol: Stock symbol
            confidence: Trade confidence (0-1)
            account_value: Total account value
            current_price: Current stock price
            current_exposure: Current portfolio exposure (0-1)

        Returns:
            Number of shares to buy
        """
        # Get parameters
        max_position_pct = self.get_parameter("max_position_size_pct") / 100
        max_exposure_pct = self.get_parameter("max_portfolio_exposure_pct") / 100

        # Scale position size with confidence
        # High confidence = larger position (up to max)
        target_pct = max_position_pct * confidence

        # Check if we have room in portfolio
        available_exposure = max_exposure_pct - current_exposure
        if available_exposure <= 0:
            return 0

        # Use the smaller of target and available
        actual_pct = min(target_pct, available_exposure)

        # Calculate shares
        position_value = account_value * actual_pct
        shares = int(position_value / current_price)

        return max(0, shares)

    def evaluate_risk_reward(
        self,
        entry_price: float,
        target_price: float,
        stop_loss: float
    ) -> Dict[str, Any]:
        """
        Evaluate if risk/reward ratio is acceptable

        Args:
            entry_price: Entry price
            target_price: Target profit price
            stop_loss: Stop loss price

        Returns:
            Dict with evaluation results
        """
        potential_gain = target_price - entry_price
        potential_loss = entry_price - stop_loss

        if potential_loss <= 0:
            risk_reward = float('inf')
        else:
            risk_reward = potential_gain / potential_loss

        min_ratio = self.get_parameter("min_risk_reward_ratio")
        is_acceptable = risk_reward >= min_ratio

        return {
            "risk_reward_ratio": risk_reward,
            "potential_gain": potential_gain,
            "potential_loss": potential_loss,
            "is_acceptable": is_acceptable,
            "min_required": min_ratio
        }

    def create_strategy_record(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any]
    ) -> None:
        """
        Record a new strategy

        Args:
            name: Strategy name
            description: Strategy description
            parameters: Strategy parameters
        """
        strategy_data = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "created_at": datetime.utcnow(),
            "status": "active",
            "total_trades": 0
        }

        self.database.save_strategy(strategy_data)

    def update_strategy_performance(
        self,
        strategy_name: str,
        trade_result: Dict[str, Any]
    ) -> None:
        """
        Update strategy performance after a trade

        Args:
            strategy_name: Strategy name
            trade_result: Trade result data
        """
        strategy = self.database.get_strategy(strategy_name)
        if not strategy:
            return

        # Increment trade count
        strategy.total_trades += 1

        # Recalculate metrics (simplified)
        # In production, this would use all historical trades
        self.database.update_strategy_performance(
            name=strategy_name,
            metrics={
                "total_trades": strategy.total_trades,
                "last_used_at": datetime.utcnow()
            }
        )

    def get_system_prompt_context(self) -> str:
        """
        Generate context for Claude's system prompt

        Returns current parameters and performance for the agent to consider
        """
        params = self.get_all_parameters()
        active_strategies = self.database.get_active_strategies()

        context = "=== Current Strategy Parameters ===\n\n"
        context += "You have full control over these parameters and can adjust them based on performance:\n\n"

        for name, value in params.items():
            context += f"- {name}: {value}\n"

        context += "\n=== Active Strategies ===\n\n"
        if active_strategies:
            for strategy in active_strategies:
                context += f"- {strategy.name}: {strategy.description}\n"
                context += f"  Trades: {strategy.total_trades}, "
                if strategy.win_rate:
                    context += f"Win Rate: {strategy.win_rate:.1%}, "
                if strategy.sharpe_ratio:
                    context += f"Sharpe: {strategy.sharpe_ratio:.2f}"
                context += "\n"
        else:
            context += "No active strategies yet. You can create new strategies based on market analysis.\n"

        context += "\n=== Your Capabilities ===\n\n"
        context += "You can:\n"
        context += "1. Adjust your own confidence thresholds based on performance\n"
        context += "2. Create new trading strategies when you identify opportunities\n"
        context += "3. Modify position sizing and risk parameters\n"
        context += "4. Retire underperforming strategies\n"
        context += "5. Change how aggressively you learn from feedback\n\n"
        context += "Make decisions autonomously, but always explain your reasoning.\n"

        return context