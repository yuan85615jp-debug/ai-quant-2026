"""
交易员基类
"""

from __future__ import annotations
import json
import logging
from typing import Any
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from models import TraderOpinion, MarketData, TradeDirection

logger = logging.getLogger(__name__)


class BaseTrader:
    """所有交易员的基类"""

    name: str = "BaseTrader"
    system_prompt: str = ""

    def __init__(self, client: OpenAI, model: str = "deepseek-reasoner"):
        self.client = client
        self.model = model

    def _build_user_prompt(self, market_data: MarketData) -> str:
        """构建用户提示词，子类可覆盖以增加个性化字段"""
        data = market_data.model_dump(exclude_none=True)
        lines = [f"请对股票 {market_data.stock_code} 进行分析。", "", "【市场数据】"]
        for k, v in data.items():
            if k in ("stock_code", "stock_name", "extra"):
                continue
            lines.append(f"- {k}: {v}")
        if market_data.extra:
            lines.append("【其他信息】")
            for k, v in market_data.extra.items():
                lines.append(f"- {k}: {v}")
        lines.append("")
        lines.append("请严格按照 System Prompt 要求的 JSON 格式输出。")
        return "\n".join(lines)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def analyze(self, market_data: MarketData) -> TraderOpinion:
        """执行分析并返回结构化结果"""
        user_prompt = self._build_user_prompt(market_data)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
            )
            content = response.choices[0].message.content
            data = json.loads(content)

            direction_raw = data.get("direction") or data.get("overall_direction") or "观望"
            try:
                direction = TradeDirection(direction_raw)
            except ValueError:
                direction = TradeDirection.HOLD

            opinion = TraderOpinion(
                trader_name=self.name,
                direction=direction,
                confidence=float(data.get("confidence", 0.5)),
                entry_price=data.get("entry_price"),
                stop_loss=data.get("stop_loss"),
                take_profit=data.get("take_profit"),
                position_size=data.get("position_size"),
                key_reasons=data.get("key_reasons") or data.get("reasons") or [],
                risks=data.get("risks") or [],
                raw_analysis=data.get("raw_analysis") or "",
            )
            logger.info(f"{self.name} 分析完成: {opinion.direction.value}, confidence={opinion.confidence:.2f}")
            return opinion

        except Exception as e:
            logger.error(f"{self.name} 分析失败: {e}")
            return TraderOpinion(
                trader_name=self.name,
                direction=TradeDirection.HOLD,
                confidence=0.0,
                key_reasons=[f"分析过程出现异常: {str(e)}"],
                risks=["模型调用失败，结果不可靠"],
            )
