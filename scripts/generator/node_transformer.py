from collections import defaultdict, Counter
from typing import Any, List, Dict, Literal, Type
from dataclasses import dataclass, asdict
from scripts.generator.lexer import TokenType, Lexer
from scripts.generator.parser import (
    Node,
    ArrayNode,
    ValueNode,
    ObjectNode,
    # CommentNode,
    KeyValueNode,
    ComparisonNode,
    EffectBlockNode,
    KeywordBlockNode,
    TriggerBlockNode,
    Parser,
)
import json


@dataclass
class TransformedString:
    value: str


@dataclass
class TransformedConstant:
    value: str


@dataclass
class TransformedPercentage:
    value: int | float
    percentage_sign: Literal["%", "%%"]


@dataclass
class TransformedDate:
    value: str


@dataclass
class TransformedComparison:
    left: str | int | float | bool | TransformedString | TransformedConstant | TransformedPercentage
    operator: Literal[">", "<", ">=", "<=", "!=", "="]
    right: str | int | float | bool | TransformedString | TransformedConstant | TransformedPercentage


class TransformedJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        # if isinstance(obj, (TransformedString, TransformedConstant, TransformedDate, TransformedComparison)):
        #     return asdict(obj)
        if isinstance(obj, TransformedString):
            return f"string({obj.value})"
        elif isinstance(obj, TransformedConstant):
            return f"constant({obj.value})"
        elif isinstance(obj, TransformedComparison):
            return f"comparison({obj.left} {obj.operator} {obj.right})"
        elif isinstance(obj, TransformedDate):
            return f"date({obj.value})"
        elif isinstance(obj, TransformedPercentage):
            return f"percentage({obj.value * 100}{obj.percentage_sign})"
        return super().default(obj)


class NodeTransformer:
    def __init__(self, parsed_tree: ObjectNode, always_list_keys: set[str] | None = None):
        if parsed_tree.context.value != "root":
            raise ValueError("Root node must have 'root' value")
        self.parsed_tree = parsed_tree
        self.always_list_keys: set[str] = set(always_list_keys or [])
        self.transformed_tree = self._convert_object_node(parsed_tree)
        # self._validate_objects_and_arrays(self.transformed_tree)

    def _convert_node(self, node: Node):
        if isinstance(node, ValueNode):
            return self._convert_value_node(node)
        elif isinstance(node, KeyValueNode):
            return self._convert_key_value_node(node)
        elif isinstance(node, ComparisonNode):
            return self._convert_comparison_node(node)
        elif isinstance(node, ArrayNode):
            return self._convert_array_node(node)
        elif isinstance(node, (ObjectNode, EffectBlockNode, KeywordBlockNode, TriggerBlockNode)):
            return self._convert_object_node(node)
        else:
            raise ValueError(f"Unknown node type: {type(node)}")

    def _convert_value_node(self, node: ValueNode):
        type = node.type
        value = node.value
        if type == TokenType.STRING_LITERAL:
            return TransformedString(value)  # type: ignore
        elif type == TokenType.CONSTANT:
            return TransformedConstant(value)  # type: ignore
        elif type == TokenType.PERCENTAGE_LITERAL:
            value = str(value)
            # strip all % from value
            percentage_sign = "%%" if value.endswith("%%") else "%"
            value = float(value.replace(percentage_sign, "")) / 100
            return TransformedPercentage(value, percentage_sign)

        return value

    def _convert_key_value_node(self, node: KeyValueNode):
        return self._convert_node(node.value)

    def _convert_comparison_node(self, node: ComparisonNode):
        left = self._convert_value_node(node.left)
        operator = node.operator
        right = self._convert_value_node(node.right)
        return TransformedComparison(left, operator, right)

    def _convert_array_node(self, node: ArrayNode):
        return [self._convert_node(child) for child in node.elements]

    def _convert_object_node(self, node: ObjectNode | EffectBlockNode | KeywordBlockNode | TriggerBlockNode):
        context = {}
        for child in node.children:
            if isinstance(child, KeyValueNode):
                key = self._convert_value_node(child.key)
                if not isinstance(key, (str, int, float, bool)):
                    key = key.value

                    # if False:
                    # print("OMG")
                    # print(f"key: {key}, value: {child.value}")
                value = self._convert_node(child.value)
                self._store_in_context(context, key, value)
            elif isinstance(child, ComparisonNode):
                comparison = self._convert_comparison_node(child)
                context[comparison.left] = comparison
            elif isinstance(child, ArrayNode):
                key = child.context.value
                if key in context:
                    context[key].append(self._convert_array_node(child))
                else:
                    context[key] = self._convert_array_node(child)
            elif isinstance(child, (ObjectNode, EffectBlockNode, KeywordBlockNode, TriggerBlockNode)):
                key = child.context.value
                value = self._convert_object_node(child)
                self._store_in_context(context, key, value)
        return context

    def _store_in_context(self, context: Dict[Any, Any], key: Any, value: Any):
        if key in self.always_list_keys:
            existing_value = context.get(key)
            if existing_value is None:
                context[key] = [value]
            elif isinstance(existing_value, list):
                existing_value.append(value)
            else:
                context[key] = [existing_value, value]
            return

        if key in context:
            if isinstance(context[key], list):
                context[key].append(value)
            else:
                context[key] = [context[key], value]
        else:
            context[key] = value

    # def _validate_objects_and_arrays(self, node: ObjectNode | Dict[str, Any]):
    #     key_types: Dict[str, List[Type]] = defaultdict(list)

    #     def collect_key_types(sub_node: Any):
    #         if isinstance(sub_node, dict):
    #             for key, value in sub_node.items():
    #                 if isinstance(value, list):
    #                     key_types[key].append(list)
    #                     for item in value:
    #                         collect_key_types(item)
    #                 else:
    #                     key_types[key].append(type(value))
    #                     collect_key_types(value)
    #         elif isinstance(sub_node, list):
    #             for item in sub_node:
    #                 collect_key_types(item)

    #     collect_key_types(node)

    #     # Determine the most common type for each key
    #     common_types = {key: Counter(types).most_common(1)[0][0] for key, types in key_types.items()}

    #     def standardize_types(sub_node: Any):
    #         if isinstance(sub_node, dict):
    #             for key, value in sub_node.items():
    #                 expected_type = common_types[key]
    #                 if isinstance(value, list):
    #                     if expected_type is not list:
    #                         sub_node[key] = self._merge_lists_to_type(value, expected_type)
    #                     else:
    #                         for item in value:
    #                             standardize_types(item)
    #                 else:
    #                     if not isinstance(value, expected_type):
    #                         sub_node[key] = self._convert_to_type(value, expected_type)
    #                     standardize_types(value)
    #         elif isinstance(sub_node, list):
    #             for item in sub_node:
    #                 standardize_types(item)

    #     standardize_types(node)

    # def _merge_lists_to_type(self, values: List[Any], expected_type: Type) -> Any:
    #     merged = []
    #     for value in values:
    #         if isinstance(value, list):
    #             merged.extend(value)
    #         else:
    #             merged.append(value)
    #     if expected_type is dict:
    #         result = {}
    #         for item in merged:
    #             result.update(item)
    #         return result
    #     return merged

    # def _convert_to_type(self, value: Any, expected_type: Type) -> Any:
    #     # Conversion logic. For simplicity, we convert only basic types here.
    #     if expected_type is list:
    #         return [value]
    #     if expected_type is dict:
    #         return {"value": value}
    #     return value  # For other types, return the value as-is

    def toJSON(self, path: str):
        with open(path, "w+") as file:
            json.dump(self.transformed_tree, file, cls=TransformedJSONEncoder, indent=4)


if __name__ == "__main__":
    input_text = open("countrytechtreeview.gui").read()
    lexer = Lexer(input_text, "hoi4", config={"enable_logger": False})
    tokens = lexer.tokenize()
    parser = Parser(tokens, config={"enable_logger": False})
    # parser.print_tree()
    node_transformer = NodeTransformer(parser.parsed_tree, always_list_keys=lexer.repeatable_keys)
    node_transformer.toJSON("countrytechtreeview_transformed.json")
