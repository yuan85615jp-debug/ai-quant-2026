from .base_trader import BaseTrader
from prompts.institutional import INSTITUTIONAL_SYSTEM


class InstitutionalTrader(BaseTrader):
    name = "机构交易员"
    system_prompt = INSTITUTIONAL_SYSTEM
