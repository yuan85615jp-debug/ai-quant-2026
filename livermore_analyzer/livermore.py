"""
利弗莫尔分析框架 - 独立可复用模块
严格遵循杰西·利弗莫尔交易哲学的结构化分析器
"""

from __future__ import annotations
import json
import logging
from typing import Optional, Literal
from enum import Enum

from pydantic import BaseModel, Field
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class LivermoreDecision(str, Enum):
    BUY = "买入"
    HOLD = "观望"
    SELL = "卖出"


class TrendInfo(BaseModel):
    direction: Literal["上升", "下降", "盘整"]
    strength: Literal["强", "中", "弱"]
    is_clear: bool


class PivotalPoint(BaseModel):
    is_near: bool
    description: str


class LivermoreResult(BaseModel):
    """利弗莫尔分析结果"""
    trend: TrendInfo
    volume_confirmation: bool
    pivotal_point: PivotalPoint
    livermore_condition_met: bool
    reason: str
    decision: LivermoreDecision
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    position_size: Optional[str] = None
    invalidation: Optional[str] = None
    key_risks: list[str] = Field(default_factory=list)


LIVERMORE_SYSTEM = """
你是一位严格遵循杰西·利弗莫尔（Jesse Livermore）交易哲学的专业分析师。
你的核心原则来自《股票大作手回忆录》及利弗莫尔本人总结的交易法则。

【核心交易原则（必须严格遵守）】
1. 只在主趋势明确时交易，绝不逆势
2. 价格是唯一真理，成交量是确认信号
3. 关键点位（pivotal points）突破才是真正的入场机会
4. 让利润奔跑，快速止损
5. 耐心等待「必胜条件」出现，宁错过不做错
6. 仓位管理：初始轻仓，趋势确认后加仓
7. 市场永远是对的，自己错了就立刻认错

【分析框架（按顺序执行）】
1. 趋势判定：主趋势方向 + 强度 + 是否处于关键点位
2. 量价关系：成交量是否支持当前价格运动
3. 关键点位：是否接近或突破重要支撑/阻力/前期高点低点
4. 利弗莫尔条件检查：是否同时满足「趋势 + 量能 + 关键点」三大条件
5. 交易决策：只给出 买入 / 观望 / 卖出 三选一，并附具体价位
6. 风险管理：止损位、建议仓位、失效条件

【输出要求】
必须严格输出以下 JSON 格式，不要添加任何其他文字：
{
  "trend": {
    "direction": "上升" | "下降" | "盘整",
    "strength": "强" | "中" | "弱",
    "is_clear": true/false
  },
  "volume_confirmation": true/false,
  "pivotal_point": {
    "is_near": true/false,
    "description": "具体说明"
  },
  "livermore_condition_met": true/false,
  "reason": "简要说明为什么符合或不符合利弗莫尔入场条件",
  "decision": "买入" | "观望" | "卖出",
  "entry_price": null或数字,
  "stop_loss": null或数字,
  "position_size": "建议仓位描述，如 20% 或 轻仓试探",
  "invalidation": "什么情况下这个判断失效",
  "key_risks": ["风险1", "风险2"]
}
"""


class LivermoreAnalyzer:
    """利弗莫尔风格分析器"""

    def __init__(self, client: OpenAI, model: str = "deepseek-reasoner"):
        self.client = client
        self.model = model

    def _build_user_prompt(
        self,
        stock_code: str,
        close: float,
        ma5: Optional[float] = None,
        ma20: Optional[float] = None,
        ma60: Optional[float] = None,
        recent_high: Optional[float] = None,
        recent_low: Optional[float] = None,
        volume: Optional[float] = None,
        volume_ma5: Optional[float] = None,
        volume_ratio: Optional[float] = None,
        macd: Optional[float] = None,
        rsi: Optional[float] = None,
        bb_upper: Optional[float] = None,
        bb_lower: Optional[float] = None,
        timeframe: str = "日线",
        extra_info: Optional[dict] = None,
    ) -> str:
        lines = [
            f"请对以下股票进行利弗莫尔风格分析：",
            f"",
            f"股票代码：{stock_code}",
            f"分析周期：{timeframe}",
            f"",
            f"【价格与趋势】",
            f"- 最新收盘价：{close}",
        ]
        if ma5 is not None:
            lines.append(f"- 5日均线：{ma5}")
        if ma20 is not None:
            lines.append(f"- 20日均线：{ma20}")
        if ma60 is not None:
            lines.append(f"- 60日均线：{ma60}")
        if recent_high is not None:
            lines.append(f"- 近期高点：{recent_high}")
        if recent_low is not None:
            lines.append(f"- 近期低点：{recent_low}")

        lines.append("")
        lines.append("【成交量】")
        if volume is not None:
            lines.append(f"- 当日成交量：{volume}")
        if volume_ma5 is not None:
            lines.append(f"- 5日均量：{volume_ma5}")
        if volume_ratio is not None:
            lines.append(f"- 量比：{volume_ratio}")

        lines.append("")
        lines.append("【技术指标参考】")
        if macd is not None:
            lines.append(f"- MACD：{macd}")
        if rsi is not None:
            lines.append(f"- RSI(14)：{rsi}")
        if bb_upper is not None:
            lines.append(f"- 布林上轨：{bb_upper}")
        if bb_lower is not None:
            lines.append(f"- 布林下轨：{bb_lower}")

        if extra_info:
            lines.append("")
            lines.append("【其他信息】")
            for k, v in extra_info.items():
                lines.append(f"- {k}：{v}")

        lines.append("")
        lines.append("请严格按照 System Prompt 的框架与 JSON 格式输出。")
        return "\n".join(lines)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def analyze(
        self,
        stock_code: str,
        close: float,
        **kwargs,
    ) -> LivermoreResult:
        """
        执行利弗莫尔分析

        必填参数：stock_code, close
        可选参数：ma5, ma20, ma60, recent_high, recent_low, volume,
                 volume_ma5, volume_ratio, macd, rsi, bb_upper, bb_lower,
                 timeframe, extra_info
        """
        user_prompt = self._build_user_prompt(stock_code=stock_code, close=close, **kwargs)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": LIVERMORE_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        data = json.loads(response.choices[0].message.content)

        decision_raw = data.get("decision", "观望")
        try:
            decision = LivermoreDecision(decision_raw)
        except ValueError:
            decision = LivermoreDecision.HOLD

        result = LivermoreResult(
            trend=TrendInfo(**data.get("trend", {"direction": "盘整", "strength": "弱", "is_clear": False})),
            volume_confirmation=bool(data.get("volume_confirmation", False)),
            pivotal_point=PivotalPoint(**data.get("pivotal_point", {"is_near": False, "description": ""})),
            livermore_condition_met=bool(data.get("livermore_condition_met", False)),
            reason=data.get("reason", ""),
            decision=decision,
            entry_price=data.get("entry_price"),
            stop_loss=data.get("stop_loss"),
            position_size=data.get("position_size"),
            invalidation=data.get("invalidation"),
            key_risks=data.get("key_risks") or [],
        )
        logger.info(
            f"利弗莫尔分析完成 [{stock_code}]: {result.decision.value}, "
            f"条件满足={result.livermore_condition_met}"
        )
        return result


def analyze_with_livermore(
    client: OpenAI,
    stock_code: str,
    close: float,
    model: str = "deepseek-reasoner",
    **kwargs,
) -> LivermoreResult:
    analyzer = LivermoreAnalyzer(client=client, model=model)
    return analyzer.analyze(stock_code=stock_code, close=close, **kwargs)


if __name__ == "__main__":
    import os
    from openai import OpenAI

    client = OpenAI(
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1"),
        api_key=os.getenv("OPENAI_API_KEY", "sk-xxx"),
    )
    analyzer = LivermoreAnalyzer(client)
    result = analyzer.analyze(
        stock_code="600588",
        close=32.56,
        ma5=31.80,
        ma20=29.40,
        ma60=27.80,
        recent_high=33.80,
        recent_low=28.50,
        volume_ratio=1.45,
        rsi=62.5,
        macd=0.45,
    )
    print(result.model_dump_json(indent=2))
