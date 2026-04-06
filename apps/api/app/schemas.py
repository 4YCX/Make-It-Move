from typing import Literal
from pydantic import BaseModel, Field


ActionLiteral = Literal["up", "down", "left", "right", "idle"]
AgentSpeedLiteral = Literal["slow", "normal", "fast"]
ObstacleDensityLiteral = Literal["loose", "medium", "tight"]


class MatchSettingsPayload(BaseModel):
    agentSpeed: AgentSpeedLiteral = "slow"
    obstacleDensity: ObstacleDensityLiteral = "medium"
    layoutTransform: bool = False


class CreateMatchRequest(BaseModel):
    settings: MatchSettingsPayload = Field(default_factory=MatchSettingsPayload)


class CreateMatchResponse(BaseModel):
    matchId: str


class ActionPayload(BaseModel):
    action: ActionLiteral


class PlayerActionMessage(BaseModel):
    type: Literal["PLAYER_ACTION"]
    payload: ActionPayload
