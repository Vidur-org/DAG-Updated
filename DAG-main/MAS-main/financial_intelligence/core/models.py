from pydantic import BaseModel
from typing import List, Optional, Dict


class Entity(BaseModel):
    name: str
    ticker: str
    type: str  # stock | index | country


class Requirements(BaseModel):
    company_fundamentals: bool
    market_prices: bool
    macro_data: bool
    news: bool


class PlannerOutput(BaseModel):
    entities: List[Entity]
    region: str
    requirements: Requirements
    time_context: str
    error: Optional[str]
