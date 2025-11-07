"""Node definitions for the v2 Clausewitz intermediate representation."""

from typing import Literal
from pydantic import BaseModel, Field


ClausewitzScalar = str | int | float | bool


class ClausewitzComparison(BaseModel):
    left: ClausewitzScalar
    operator: Literal[">", "<", ">=", "<=", "!=", "="]
    right: ClausewitzScalar


class ClausewitzList(BaseModel):
    values: list["ClausewitzValue"] = Field(default_factory=list)


class ClausewitzEntry(BaseModel):
    key: str
    value: "ClausewitzValue"


class ClausewitzBlock(BaseModel):
    entries: list[ClausewitzEntry] = Field(default_factory=list)

    def add_entry(self, key: str, value: "ClausewitzValue") -> None:
        self.entries.append(ClausewitzEntry(key=key, value=value))


ClausewitzValue = ClausewitzScalar | ClausewitzComparison | ClausewitzList | ClausewitzBlock
