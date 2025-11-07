"""Utilities for converting parsed tech data back into Clausewitz script."""

from __future__ import annotations

from typing import Any, List

from scripts.generator.hoi4.tech import TechCollection
from scripts.generator.node_transformer import (
    TransformedComparison,
    TransformedConstant,
    TransformedDate,
    TransformedPercentage,
    TransformedString,
)


class BaseGenerator:
    def __init__(self, indent: str = "\t"):
        self.indent = indent

    def generate(self) -> str:
        raise NotImplementedError

    def write(self, path: str) -> str:
        output = self.generate()
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(output)
        return path


class _ClausewitzFormatter:
    def __init__(self, indent: str = "\t"):
        self.indent = indent

    def block(self, name: str | None, value: dict[str, Any], level: int = 0) -> List[str]:
        header = f"{self._indent(level)}{name + ' = ' if name else ''}{{"
        lines = [header]
        for key, child in value.items():
            lines.extend(self.entry(key, child, level + 1))
        lines.append(f"{self._indent(level)}}}")
        return lines

    def entry(self, key: str, value: Any, level: int) -> List[str]:
        if isinstance(value, dict):
            return self.block(key, value, level)
        if isinstance(value, list):
            return self._list(key, value, level)
        if isinstance(value, TransformedComparison):
            left = self._format_scalar(value.left)
            right = self._format_scalar(value.right)
            left_key = left if left != key else key
            return [f"{self._indent(level)}{left_key} {value.operator} {right}"]
        return [f"{self._indent(level)}{key} = {self._format_scalar(value)}"]

    def _list(self, key: str, value: list[Any], level: int) -> List[str]:
        if not value:
            return [f"{self._indent(level)}{key} = {{}}"]
        if all(isinstance(item, dict) for item in value):
            lines: List[str] = []
            for item in value:
                lines.extend(self.block(key, item, level))
            return lines
        lines = [f"{self._indent(level)}{key} = {{"]
        for item in value:
            lines.append(f"{self._indent(level + 1)}{self._format_scalar(item)}")
        lines.append(f"{self._indent(level)}}}")
        return lines

    def _format_scalar(self, value: Any) -> str:
        if isinstance(value, TransformedString):
            return f'"{self._escape(value.value)}"'
        if isinstance(value, TransformedConstant):
            return value.value
        if isinstance(value, TransformedDate):
            return value.value
        if isinstance(value, TransformedPercentage):
            percentage = value.value * 100
            percentage_str = ("{:.0f}".format(percentage) if percentage.is_integer() else str(percentage))
            return f"{percentage_str}{value.percentage_sign}"
        if isinstance(value, bool):
            return "yes" if value else "no"
        if isinstance(value, float):
            return ("{:.6f}".format(value)).rstrip("0").rstrip(".")
        if value is None:
            return "0"
        return str(value)

    def _indent(self, level: int) -> str:
        return self.indent * level

    def _escape(self, text: str) -> str:
        return text.replace("\"", "\\\"")


class TechCollectionGenerator(BaseGenerator):
    def __init__(self, tech_collection: TechCollection, indent: str = "\t"):
        super().__init__(indent=indent)
        self.tech_collection = tech_collection
        self.formatter = _ClausewitzFormatter(indent)

    def generate(self) -> str:
        technologies = self.tech_collection.raw_technologies
        lines = self.formatter.block("technologies", technologies, level=0)
        return "\n".join(lines) + "\n"
