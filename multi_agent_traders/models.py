"""
多智能体交易员系统 - 数据模型
使用 Pydantic 强制结构化输出，确保下游可自动化处理
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class TradeDirection(str, Enum):
    LONG = "做多"
    SHORT = "做空"
    HOLD = "观望"


class TraderOpinion(BaseModel):
    """单个交易员的分析结果"""
    trader_name: str = Field(..., description="交易员名称")
    direction: TradeDirection = Field(..., description="交易方向")
    confidence: float = Field(..., ge=0.0, le=1.0, description="决策置信度 0-1")
    entry_price: Optional[float] = Field(None, description="建议入场价")
    stop_loss: Optional[float] = Field(None, description="止损价")
    take_profit: Optional[float] = Field(None, description="止盈价")
    position_size: Optional[float] = Field(None, ge=0.0, le=1.0, description="建议仓位比例 0-1")
    key_reasons: List[str] = Field(default_factory=list, description="核心理由")
    risks: List[str] = Field(default_factory=list, description="主要风险")
    raw_analysis: str = Field(default="", description="原始分析文本（可选）")


class FinalDecision(BaseModel):
    """决策者综合后的最终决策"""
    overall_direction: TradeDirection = Field(..., description="综合交易方向")
    consensus_score: float = Field(..., ge=0.0, le=1.0, description="交易员意见一致性 0-1")
    recommended_entry: Optional[float] = Field(None, description="建议入场价")
    recommended_stop: Optional[float] = Field(None, description="建议止损价")
    recommended_target: Optional[float] = Field(None, description="建议目标价")
    position_suggestion: str = Field(..., description="仓位与执行建议")
    trader_opinions: List[TraderOpinion] = Field(default_factory=list)
    synthesis: str = Field(..., description="综合分析论述")
    risk_warnings: List[str] = Field(default_factory=list, description="风险提示")


class MarketData(BaseModel):
    """标准化市场数据输入"""
    stock_code: str
    stock_name: Optional[str] = None
    close: float
    change_pct: Optional[float] = None
    volume: Optional[float] = None
    turnover_rate: Optional[float] = None
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    ma60: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None
    rsi: Optional[float] = None
    k: Optional[float] = None
    d: Optional[float] = None
    j: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    recent_high: Optional[float] = None
    recent_low: Optional[float] = None
    volume_ratio: Optional[float] = None
    extra: dict = Field(default_factory=dict, description="其他扩展字段")
