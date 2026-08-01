from typing import Literal

from pydantic import BaseModel, ConfigDict


class ExecutionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: Literal["summary", "timeline"]
    requires_timeline: bool = False
    response_style: Literal["neutral", "technical", "casual"] = "neutral"
