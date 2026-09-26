"""
多智能体交易员系统 - 入口
用法：
    python main.py
    python main.py --code 600588
"""

from __future__ import annotations
import argparse
import logging
import sys
import os

import yaml
from openai import OpenAI

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents import InstitutionalTrader, AggressiveTrader, SeniorTrader
from decision_maker import DecisionMaker
from data_provider import get_demo_market_data
from models import MarketData

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("main")


def load_config(path: str = "config.yaml") -> dict:
    config_path = os.path.join(os.path.dirname(__file__), path)
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_client(api_cfg: dict) -> OpenAI:
    return OpenAI(
        base_url=api_cfg.get("base_url"),
        api_key=api_cfg.get("api_key"),
    )


def main():
    parser = argparse.ArgumentParser(description="多智能体交易员分析系统")
    parser.add_argument("--code", default="600588", help="股票代码")
    parser.add_argument("--config", default="config.yaml", help="配置文件路径")
    args = parser.parse_args()

    config = load_config(args.config)
    client = build_client(config["api"])
    model = config["api"].get("model", "deepseek-reasoner")

    traders = []
    trader_map = {
        "InstitutionalTrader": InstitutionalTrader,
        "AggressiveTrader": AggressiveTrader,
        "SeniorTrader": SeniorTrader,
    }
    for t_cfg in config.get("traders", []):
        if t_cfg.get("enabled", True):
            cls = trader_map.get(t_cfg["class"])
            if cls:
                traders.append(cls(client=client, model=model))

    if not traders:
        logger.error("没有启用任何交易员，请检查 config.yaml")
        return

    dm_cfg = config.get("decision_maker", {})
    decision_maker = DecisionMaker(
        traders=traders,
        client=client,
        model=dm_cfg.get("model", model),
        max_workers=dm_cfg.get("max_workers", 3),
    )

    logger.info(f"获取 {args.code} 市场数据（当前为演示数据）...")
    market_data: MarketData = get_demo_market_data(args.code)

    decision = decision_maker.run(market_data)

    print("\n" + "=" * 60)
    print(f"股票：{market_data.stock_code} {market_data.stock_name or ''}")
    print(f"最新价：{market_data.close}")
    print("=" * 60)
    print(f"\n【最终决策】{decision.overall_direction.value}")
    print(f"一致性评分：{decision.consensus_score:.2f}")
    print(f"建议入场：{decision.recommended_entry}")
    print(f"建议止损：{decision.recommended_stop}")
    print(f"建议目标：{decision.recommended_target}")
    print(f"仓位建议：{decision.position_suggestion}")
    print(f"\n【综合论述】\n{decision.synthesis}")
    print(f"\n【风险提示】")
    for r in decision.risk_warnings:
        print(f"  - {r}")

    print("\n【各交易员明细】")
    for op in decision.trader_opinions:
        print(f"\n  {op.trader_name}: {op.direction.value} (置信度 {op.confidence:.2f})")
        print(f"    入场={op.entry_price} 止损={op.stop_loss} 止盈={op.take_profit} 仓位={op.position_size}")
        print(f"    理由: {op.key_reasons}")
        print(f"    风险: {op.risks}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
