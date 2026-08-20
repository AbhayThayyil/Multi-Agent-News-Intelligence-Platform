from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class TimelineEntry(BaseModel):
    date: datetime
    event: str = Field(min_length=1)
    source_title: str = Field(min_length=1)
    source_url: HttpUrl | None = None


class Timeline(BaseModel):
    entries: list[TimelineEntry]


class ExtractedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=0)
    event: str = Field(min_length=1)


class TimelineExtractionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[ExtractedEvent]
