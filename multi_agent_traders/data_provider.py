"""
简易数据提供层（示例）
生产环境请替换为可靠的数据源（akshare、tushare、本地数据库等）
"""

from __future__ import annotations
import logging
from typing import Optional
import pandas as pd
import numpy as np

from models import MarketData

logger = logging.getLogger(__name__)

try:
    import pandas_ta as ta
    HAS_PANDAS_TA = True
except ImportError:
    HAS_PANDAS_TA = False
    logger.warning("pandas_ta 未安装，技术指标将使用简易计算")


def _simple_rsi(series: pd.Series, length: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(length).mean()
    avg_loss = loss.rolling(length).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """计算常用技术指标"""
    df = df.copy()
    close = df["close"]
    high = df.get("high", close)
    low = df.get("low", close)

    df["ma5"] = close.rolling(5).mean()
    df["ma10"] = close.rolling(10).mean()
    df["ma20"] = close.rolling(20).mean()
    df["ma60"] = close.rolling(60).mean()

    if HAS_PANDAS_TA:
        try:
            macd_df = ta.macd(close)
            if macd_df is not None:
                df["macd"] = macd_df.iloc[:, 0]
                df["macd_signal"] = macd_df.iloc[:, 1]
                df["macd_hist"] = macd_df.iloc[:, 2]
            df["rsi"] = ta.rsi(close, length=14)
            stoch = ta.stoch(high, low, close)
            if stoch is not None:
                df["k"] = stoch.iloc[:, 0]
                df["d"] = stoch.iloc[:, 1]
                df["j"] = 3 * df["k"] - 2 * df["d"]
            bb = ta.bbands(close, length=20)
            if bb is not None:
                df["bb_upper"] = bb.iloc[:, 0]
                df["bb_middle"] = bb.iloc[:, 1]
                df["bb_lower"] = bb.iloc[:, 2]
        except Exception as e:
            logger.warning(f"pandas_ta 计算部分失败，使用简易方法: {e}")
            df["rsi"] = _simple_rsi(close)
    else:
        df["rsi"] = _simple_rsi(close)

    df["recent_high"] = high.rolling(20).max()
    df["recent_low"] = low.rolling(20).min()
    if "volume" in df.columns:
        df["volume_ma5"] = df["volume"].rolling(5).mean()
        df["volume_ratio"] = df["volume"] / df["volume_ma5"]

    return df


def get_market_data_from_df(df: pd.DataFrame, stock_code: str, stock_name: Optional[str] = None) -> MarketData:
    """从已计算指标的 DataFrame 取最新一行，转为 MarketData"""
    if df.empty:
        raise ValueError("数据为空")
    latest = df.iloc[-1]

    def safe(val):
        if pd.isna(val):
            return None
        return float(val)

    return MarketData(
        stock_code=stock_code,
        stock_name=stock_name,
        close=safe(latest["close"]),
        change_pct=safe(latest.get("change_pct")),
        volume=safe(latest.get("volume")),
        turnover_rate=safe(latest.get("turnover_rate")),
        ma5=safe(latest.get("ma5")),
        ma10=safe(latest.get("ma10")),
        ma20=safe(latest.get("ma20")),
        ma60=safe(latest.get("ma60")),
        macd=safe(latest.get("macd")),
        macd_signal=safe(latest.get("macd_signal")),
        macd_hist=safe(latest.get("macd_hist")),
        rsi=safe(latest.get("rsi")),
        k=safe(latest.get("k")),
        d=safe(latest.get("d")),
        j=safe(latest.get("j")),
        bb_upper=safe(latest.get("bb_upper")),
        bb_middle=safe(latest.get("bb_middle")),
        bb_lower=safe(latest.get("bb_lower")),
        recent_high=safe(latest.get("recent_high")),
        recent_low=safe(latest.get("recent_low")),
        volume_ratio=safe(latest.get("volume_ratio")),
    )


def get_demo_market_data(stock_code: str = "600588") -> MarketData:
    """返回演示用模拟数据，方便直接测试多智能体流程"""
    return MarketData(
        stock_code=stock_code,
        stock_name="用友网络",
        close=32.56,
        change_pct=1.85,
        volume=125.6,
        turnover_rate=1.23,
        ma5=31.80,
        ma10=30.95,
        ma20=29.40,
        ma60=27.80,
        macd=0.45,
        macd_signal=0.32,
        macd_hist=0.13,
        rsi=62.5,
        k=68.2,
        d=61.5,
        j=81.6,
        bb_upper=34.20,
        bb_middle=30.50,
        bb_lower=26.80,
        recent_high=33.80,
        recent_low=28.50,
        volume_ratio=1.45,
        extra={
            "行业": "软件服务",
            "备注": "这是演示数据，实盘请替换为真实行情",
        },
    )
