"""Builders that convert transformed trees into ClausewitzDocuments."""

from __future__ import annotations

from typing import Any

from scripts.generator.node_transformer import (
    TransformedComparison,
    TransformedConstant,
    TransformedDate,
    TransformedPercentage,
    TransformedString,
)

from .document import ClausewitzDocument
from .nodes import ClausewitzBlock, ClausewitzComparison, ClausewitzList, ClausewitzValue
from .schema import DocumentSchema, KeyRule


class ClausewitzBuilder:
    def __init__(self, schema: DocumentSchema):
        self.schema = schema

    def build(self, tree: dict[str, Any]) -> ClausewitzDocument:
        if self.schema.root_key not in tree:
            raise ValueError(f"Root key '{self.schema.root_key}' not present in tree")
        root_value = tree[self.schema.root_key]
        if not isinstance(root_value, dict):
            raise TypeError("Root value must be a mapping")
        block = self._convert_block(root_value, path=[self.schema.root_key], rule=self.schema.root_rule)
        return ClausewitzDocument(schema=self.schema, root=block)

    def _convert_block(self, obj: dict[str, Any], path: list[str], rule: KeyRule | None) -> ClausewitzBlock:
        block = ClausewitzBlock()
        for key, value in obj.items():
            child_path = [*path, key]
            child_rule = rule.child(key) if rule else None
            normalized_value = self._convert_value(value, child_path, child_rule)
            block.add_entry(key, normalized_value)
        return block

    def _convert_value(self, value: Any, path: list[str], rule: KeyRule | None) -> ClausewitzValue:
        if isinstance(value, dict):
            return self._convert_block(value, path, rule)
        if isinstance(value, list):
            return self._convert_list(value, path, rule)
        if isinstance(value, TransformedComparison):
            return ClausewitzComparison(
                left=self._convert_scalar(value.left),
                operator=value.operator,
                right=self._convert_scalar(value.right),
            )
        return self._convert_scalar(value)

    def _convert_list(self, items: list[Any], path: list[str], rule: KeyRule | None) -> ClausewitzList:
        list_node = ClausewitzList()
        for idx, value in enumerate(items):
            child_path = [*path, str(idx)]
            list_node.values.append(self._convert_value(value, child_path, rule))
        return list_node

    def _convert_scalar(self, value: Any) -> ClausewitzValue:
        if isinstance(value, (TransformedString, TransformedConstant, TransformedPercentage, TransformedDate)):
            return value
        if isinstance(value, list):  # catch unexpected lists
            return ClausewitzList(values=[self._convert_scalar(v) for v in value])
        return value


__all__ = ["ClausewitzBuilder"]
