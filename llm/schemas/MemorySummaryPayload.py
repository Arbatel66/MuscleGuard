from typing import Optional

from pydantic import BaseModel, Field


class MemorySummaryPayload(BaseModel):
    summary: list[str] = Field(description="对话历史的要点列表，每个要点是一句话")
    title: Optional[str] = Field(
        default=None,
        description="对话主题的简短标题（可选）"
    )
    key_facts: list[str] = Field(default_factory=list)
    injuries: list[str] = Field(default_factory=list)
    preferences: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    next_focus: list[str] = Field(default_factory=list)