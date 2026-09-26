"""
决策者：并行收集多交易员意见并综合
"""

from __future__ import annotations
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from models import FinalDecision, TraderOpinion, MarketData, TradeDirection
from agents.base_trader import BaseTrader
from prompts.decision_maker import DECISION_MAKER_SYSTEM

logger = logging.getLogger(__name__)


class DecisionMaker:
    def __init__(
        self,
        traders: List[BaseTrader],
        client: OpenAI,
        model: str = "deepseek-reasoner",
        max_workers: int = 3,
    ):
        self.traders = traders
        self.client = client
        self.model = model
        self.max_workers = max_workers

    def _collect_opinions(self, market_data: MarketData) -> List[TraderOpinion]:
        opinions: List[TraderOpinion] = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_trader = {
                executor.submit(trader.analyze, market_data): trader
                for trader in self.traders
            }
            for future in as_completed(future_to_trader):
                trader = future_to_trader[future]
                try:
                    opinion = future.result()
                    opinions.append(opinion)
                except Exception as e:
                    logger.error(f"{trader.name} 执行异常: {e}")
                    opinions.append(
                        TraderOpinion(
                            trader_name=trader.name,
                            direction=TradeDirection.HOLD,
                            confidence=0.0,
                            key_reasons=[f"执行异常: {e}"],
                            risks=["该交易员结果不可用"],
                        )
                    )
        return opinions

    def _build_synthesis_prompt(self, opinions: List[TraderOpinion], market_data: MarketData) -> str:
        parts = [
            f"股票代码：{market_data.stock_code}",
            f"最新收盘价：{market_data.close}",
            "",
            "【各位交易员意见】",
        ]
        for op in opinions:
            parts.append(f"\n--- {op.trader_name} ---")
            parts.append(f"方向：{op.direction.value}")
            parts.append(f"置信度：{op.confidence:.2f}")
            parts.append(f"入场价：{op.entry_price}")
            parts.append(f"止损：{op.stop_loss}")
            parts.append(f"止盈：{op.take_profit}")
            parts.append(f"仓位：{op.position_size}")
            parts.append(f"理由：{op.key_reasons}")
            parts.append(f"风险：{op.risks}")
        parts.append("\n请综合以上意见，给出最终决策。严格按 JSON 格式输出。")
        return "\n".join(parts)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _synthesize(self, opinions: List[TraderOpinion], market_data: MarketData) -> FinalDecision:
        user_prompt = self._build_synthesis_prompt(opinions, market_data)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": DECISION_MAKER_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        data = json.loads(response.choices[0].message.content)

        direction_raw = data.get("overall_direction") or data.get("direction") or "观望"
        try:
            overall_direction = TradeDirection(direction_raw)
        except ValueError:
            overall_direction = TradeDirection.HOLD

        return FinalDecision(
            overall_direction=overall_direction,
            consensus_score=float(data.get("consensus_score", 0.5)),
            recommended_entry=data.get("recommended_entry"),
            recommended_stop=data.get("recommended_stop"),
            recommended_target=data.get("recommended_target"),
            position_suggestion=data.get("position_suggestion") or "",
            trader_opinions=opinions,
            synthesis=data.get("synthesis") or "",
            risk_warnings=data.get("risk_warnings") or [],
        )

    def run(self, market_data: MarketData) -> FinalDecision:
        logger.info(f"开始多智能体分析: {market_data.stock_code}")
        opinions = self._collect_opinions(market_data)
        decision = self._synthesize(opinions, market_data)
        logger.info(
            f"最终决策: {decision.overall_direction.value}, "
            f"一致性={decision.consensus_score:.2f}"
        )
        return decision
