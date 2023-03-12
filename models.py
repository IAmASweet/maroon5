from typing import Optional, List
from pydantic import AnyHttpUrl
from sqlmodel import Field, SQLModel, JSON, Column


class ChannelBase(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    link: AnyHttpUrl = Field(unique=True)
    channel_id: int = Field(unique=True)
    keywords: List[str] = Field(sa_column=Column(JSON))
