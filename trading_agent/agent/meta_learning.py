"""
Meta-learning system
The agent learns how to learn - optimizing its own learning process
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List
import numpy as np
from claude_agent_sdk import AssistantMessage, TextBlock


class MetaLearningSystem:
    """
    Meta-learning: The agent learns how to optimize its own learning

    This system analyzes performance across different timeframes
    and adjusts learning parameters accordingly
    """

    def __init__(self, database, strategy_manager):
        """
        Initialize meta-learning system

        Args:
            database: Database instance
            strategy_manager: AutonomousStrategyManager instance
        """
        self.database = database
        self.strategy_manager = strategy_manager

    async def analyze_and_evolve(self, client) -> Dict[str, Any]:
        """
        Main evolution cycle - analyze performance and adjust parameters

        Args:
            client: ClaudeSDKClient for agent reasoning

        Returns:
            Evolution results
        """
        # Analyze performance across timeframes
        short_term = self._analyze_timeframe("short")
        medium_term = self._analyze_timeframe("medium")
        long_term = self._analyze_timeframe("long")

        # Ask Claude to analyze and suggest improvements
        analysis_prompt = f"""
        Analyze your own trading performance and learning process:

        SHORT-TERM PERFORMANCE (7 days):
        {self._format_performance(short_term)}

        MEDIUM-TERM PERFORMANCE (30 days):
        {self._format_performance(medium_term)}

        LONG-TERM PERFORMANCE (90 days):
        {self._format_performance(long_term)}

        CURRENT PARAMETERS:
        {self._format_parameters()}

        Tasks:
        1. Evaluate if your confidence calibration is accurate
           (Are high-confidence trades actually performing better?)

        2. Assess if your learning rate is appropriate
           (Are you adapting too quickly or too slowly?)

        3. Analyze strategy performance
           (Which strategies are working? Which should be retired?)

        4. Recommend parameter adjustments
           (Should thresholds be raised/lowered? Why?)

        5. Identify patterns in wins vs losses
           (Market conditions, trade types, confidence levels)

        Be critical and objective. Suggest specific parameter changes with reasoning.
        Use update_strategy_parameters tool to make adjustments.
        """

        await client.query(analysis_prompt)

        insights = []
        response_text = ""
        async for message in client.receive_response():
            # Collect insights from Claude's analysis
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        response_text += block.text

        # Parse insights from response
        if response_text:
            insights.append({
                "timestamp": datetime.utcnow(),
                "analysis": response_text,
                "metrics": {
                    "short_term": short_term,
                    "medium_term": medium_term,
                    "long_term": long_term
                }
            })

        return {
            "short_term": short_term,
            "medium_term": medium_term,
            "long_term": long_term,
            "insights": insights
        }

    def _analyze_timeframe(self, timeframe: str) -> Dict[str, Any]:
        """
        Analyze performance for a specific timeframe

        Args:
            timeframe: "short", "medium", or "long"

        Returns:
            Performance metrics
        """
        trades = self.database.get_trades_by_timeframe(timeframe)
        closed_trades = [t for t in trades if t.status == "closed" and t.pnl is not None]

        if not closed_trades:
            return {
                "timeframe": timeframe,
                "total_trades": 0,
                "message": "No closed trades in this timeframe"
            }

        # Calculate metrics
        total_pnl = sum(t.pnl for t in closed_trades)
        wins = [t for t in closed_trades if t.pnl > 0]
        losses = [t for t in closed_trades if t.pnl < 0]

        win_rate = len(wins) / len(closed_trades)
        avg_win = np.mean([t.pnl for t in wins]) if wins else 0
        avg_loss = np.mean([t.pnl for t in losses]) if losses else 0

        # Confidence calibration analysis
        confidence_accuracy = self._analyze_confidence_calibration(closed_trades)

        # Strategy performance breakdown
        strategy_performance = self._analyze_strategy_performance(closed_trades)

        return {
            "timeframe": timeframe,
            "total_trades": len(closed_trades),
            "total_pnl": total_pnl,
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": abs(avg_win / avg_loss) if avg_loss != 0 else float('inf'),
            "confidence_accuracy": confidence_accuracy,
            "strategy_performance": strategy_performance
        }

    def _analyze_confidence_calibration(self, trades: List) -> Dict[str, Any]:
        """
        Analyze if confidence scores are well-calibrated

        High-confidence trades should have better outcomes

        Args:
            trades: List of Trade objects

        Returns:
            Calibration analysis
        """
        # Group trades by confidence buckets
        high_conf = [t for t in trades if t.confidence and t.confidence >= 0.8]
        med_conf = [t for t in trades if t.confidence and 0.6 <= t.confidence < 0.8]
        low_conf = [t for t in trades if t.confidence and t.confidence < 0.6]

        def calc_win_rate(trade_list):
            if not trade_list:
                return 0.0
            wins = sum(1 for t in trade_list if t.pnl > 0)
            return wins / len(trade_list)

        return {
            "high_confidence": {
                "count": len(high_conf),
                "win_rate": calc_win_rate(high_conf),
                "avg_pnl": np.mean([t.pnl for t in high_conf]) if high_conf else 0
            },
            "medium_confidence": {
                "count": len(med_conf),
                "win_rate": calc_win_rate(med_conf),
                "avg_pnl": np.mean([t.pnl for t in med_conf]) if med_conf else 0
            },
            "low_confidence": {
                "count": len(low_conf),
                "win_rate": calc_win_rate(low_conf),
                "avg_pnl": np.mean([t.pnl for t in low_conf]) if low_conf else 0
            },
            "is_well_calibrated": calc_win_rate(high_conf) > calc_win_rate(low_conf)
        }

    def _analyze_strategy_performance(self, trades: List) -> Dict[str, Dict[str, Any]]:
        """
        Analyze performance by strategy

        Args:
            trades: List of Trade objects

        Returns:
            Performance by strategy
        """
        strategies = {}

        for trade in trades:
            if not trade.strategy_name:
                continue

            if trade.strategy_name not in strategies:
                strategies[trade.strategy_name] = {
                    "trades": [],
                    "total_pnl": 0,
                    "wins": 0,
                    "losses": 0
                }

            strategies[trade.strategy_name]["trades"].append(trade)
            strategies[trade.strategy_name]["total_pnl"] += trade.pnl

            if trade.pnl > 0:
                strategies[trade.strategy_name]["wins"] += 1
            elif trade.pnl < 0:
                strategies[trade.strategy_name]["losses"] += 1

        # Calculate rates
        for strategy_name, data in strategies.items():
            total = len(data["trades"])
            data["win_rate"] = data["wins"] / total if total > 0 else 0
            data["avg_pnl"] = data["total_pnl"] / total if total > 0 else 0

        return strategies

    def _format_performance(self, perf: Dict[str, Any]) -> str:
        """Format performance data for Claude"""
        if perf.get("total_trades", 0) == 0:
            return "No trades in this timeframe"

        output = f"""
Trades: {perf['total_trades']}
Total P&L: ${perf['total_pnl']:.2f}
Win Rate: {perf['win_rate']:.1%}
Average Win: ${perf['avg_win']:.2f}
Average Loss: ${perf['avg_loss']:.2f}
Profit Factor: {perf['profit_factor']:.2f}

Confidence Calibration:
  High Confidence (>80%): {perf['confidence_accuracy']['high_confidence']['count']} trades, {perf['confidence_accuracy']['high_confidence']['win_rate']:.1%} win rate
  Medium Confidence (60-80%): {perf['confidence_accuracy']['medium_confidence']['count']} trades, {perf['confidence_accuracy']['medium_confidence']['win_rate']:.1%} win rate
  Low Confidence (<60%): {perf['confidence_accuracy']['low_confidence']['count']} trades, {perf['confidence_accuracy']['low_confidence']['win_rate']:.1%} win rate
  Well Calibrated: {'Yes' if perf['confidence_accuracy']['is_well_calibrated'] else 'No'}

Strategy Performance:
"""
        for strategy_name, data in perf.get('strategy_performance', {}).items():
            output += f"  {strategy_name}: {data['win_rate']:.1%} win rate, ${data['avg_pnl']:.2f} avg P&L ({len(data['trades'])} trades)\n"

        return output

    def _format_parameters(self) -> str:
        """Format current parameters for Claude"""
        params = self.strategy_manager.get_all_parameters()

        output = ""
        for name, value in params.items():
            output += f"  {name}: {value}\n"

        return output

    def suggest_threshold_adjustment(
        self,
        confidence_analysis: Dict[str, Any],
        current_threshold: float
    ) -> Dict[str, Any]:
        """
        Suggest threshold adjustment based on confidence calibration

        Args:
            confidence_analysis: Confidence calibration data
            current_threshold: Current auto-trade threshold

        Returns:
            Suggestion dict
        """
        high_conf = confidence_analysis["high_confidence"]
        med_conf = confidence_analysis["medium_confidence"]

        # If high-confidence trades are performing well, can lower threshold
        if high_conf["win_rate"] > 0.7 and high_conf["count"] >= 10:
            suggested = max(0.75, current_threshold - 0.05)
            reason = "High-confidence trades performing well, can be more aggressive"
            confidence = 0.8

        # If high-confidence trades are failing, increase threshold
        elif high_conf["win_rate"] < 0.5 and high_conf["count"] >= 10:
            suggested = min(0.98, current_threshold + 0.05)
            reason = "High-confidence trades underperforming, need to be more selective"
            confidence = 0.9

        # Not enough data or performing as expected
        else:
            suggested = current_threshold
            reason = "Current threshold seems appropriate"
            confidence = 0.5

        return {
            "current_threshold": current_threshold,
            "suggested_threshold": suggested,
            "reason": reason,
            "confidence": confidence,
            "should_change": abs(suggested - current_threshold) > 0.01
        }

    async def periodic_evolution(self, client) -> None:
        """
        Run periodic evolution cycle (e.g., weekly)

        Args:
            client: ClaudeSDKClient
        """
        print("Running periodic evolution cycle...")

        # Analyze and evolve
        results = await self.analyze_and_evolve(client)

        # Log evolution cycle
        insight_data = {
            "insight_type": "evolution_cycle",
            "description": "Completed periodic meta-learning evolution",
            "confidence": 0.8,
            "supporting_data": results,
            "action_taken": "Analyzed performance and adjusted parameters",
            "status": "active"
        }
        self.database.save_learning_insight(insight_data)

        print("Evolution cycle complete")