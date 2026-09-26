from .base_trader import BaseTrader
from prompts.senior import SENIOR_SYSTEM


class SeniorTrader(BaseTrader):
    name = "资深交易员"
    system_prompt = SENIOR_SYSTEM
