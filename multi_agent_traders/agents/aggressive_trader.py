from .base_trader import BaseTrader
from prompts.aggressive import AGGRESSIVE_SYSTEM


class AggressiveTrader(BaseTrader):
    name = "激进交易员"
    system_prompt = AGGRESSIVE_SYSTEM
