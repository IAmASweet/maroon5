from typing import Optional, List
from pydantic import AnyHttpUrl
from sqlalchemy import BigInteger
from sqlmodel import Field, SQLModel, JSON, Column


class ChannelBase(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    link: AnyHttpUrl = Field(unique=True)
    channel_id: Optional[int] = Field(unique=True, sa_column=Column(BigInteger()))
    keywords: List[str] = Field(sa_column=Column(JSON))
