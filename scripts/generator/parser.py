from typing import Any, Dict, List, Literal, Optional, NotRequired, TypedDict
from dataclasses import dataclass
from scripts.generator.lexer import Token, TokenType, Lexer
from scripts.generator.utils import resolve_config
from scripts.generator.logger import Logger


class ParseException(Exception):
    def __init__(self, message: str, token: Optional[Token] = None):
        self.message = message
        self.token = token
        if token:
            message = f"{message} at line {token.line}, column {token.column}" + f", {token=}"
        super().__init__(message)


@dataclass
class Node:
    pass


@dataclass(init=False)
class ValueNode(Node):
    value: str | int | float | bool
    type: TokenType

    def __init__(self, token: Token):
        self.value = token.value
        self.type = token.token_type


@dataclass
class KeyValueNode(Node):
    key: ValueNode
    value: ValueNode


@dataclass
class ComparisonNode(Node):
    left: ValueNode
    operator: Literal[">", "<", ">=", "<=", "!=", "="]
    right: ValueNode


@dataclass
class CommentNode(Node):
    value: str


@dataclass
class ObjectNode(Node):
    context: ValueNode
    children: List[Any]

    def add_child(self, value: Any):
        self.children.append(value)

    def insert_child(self, value: Any):
        self.children.insert(0, value)


@dataclass
class ArrayNode(Node):
    context: ValueNode
    elements: List[ValueNode]


@dataclass
class EffectBlockNode(ObjectNode):
    pass


@dataclass
class KeywordBlockNode(ObjectNode):
    pass


@dataclass
class TriggerBlockNode(ObjectNode):
    pass


class ParserConfig(TypedDict):
    parse: NotRequired[bool]
    strip_comments: NotRequired[bool]
    enable_logger: NotRequired[bool]


class ParserConfigRequired(TypedDict):
    parse: bool
    strip_comments: bool
    enable_logger: bool


DEFAULT_CONFIG: ParserConfigRequired = {"parse": True, "strip_comments": True, "enable_logger": True}


class Parser:
    def __init__(self, tokens: List[Token], config: Optional[ParserConfig] = None):
        self.config = resolve_config(config or {}, DEFAULT_CONFIG)
        self.logger = Logger(config={"name": "Parser Logger", "is_enabled": self.config["enable_logger"]}).logger
        self.logger.info("Parser initialized")
        if self.config["strip_comments"]:
            self.tokens = self._strip_comments(tokens)
            self.logger.debug("Comments stripped from tokens")
        self.position = 0
        if self.config["parse"]:
            self.parsed_tree = self.parse_tokens()
            self.logger.debug("Tokens parsed into AST")

    def _strip_comments(self, tokens: List[Token]) -> List[Token]:
        return [token for token in tokens if token.token_type != TokenType.COMMENT]

    @property
    def prev_token(self) -> Token:
        return self.lookahead(-1)

    @property
    def current_token(self) -> Token:
        return self.tokens[self.position]

    @property
    def next_token(self) -> Token:
        return self.lookahead()

    def lookahead(self, distance: int = 1) -> Token:
        if 0 <= self.position + distance < len(self.tokens):
            return self.tokens[self.position + distance]
        return Token(TokenType.EOF, None, self.current_token.line, self.current_token.column)

    def advance(self, steps: int = 1) -> None:
        self.logger.debug(f"Advancing {steps} step(s) from position {self.position}")
        self.position = min(self.position + steps, len(self.tokens))

    def expect(self, expected_type: TokenType | List[TokenType], expected_value: Optional[Any] = None):
        if not isinstance(expected_type, list):
            expected_type = [expected_type]
        if self.current_token.token_type not in expected_type:
            raise ParseException(
                f"Expected token type {expected_type}, but got {self.current_token.token_type}",
                self.current_token,
            )
        elif expected_value and self.current_token.value != expected_value:
            raise ParseException(
                f"Expected token value {expected_value}, but got {self.current_token.value}",
                self.current_token,
            )

    def consume(self, expected_type: TokenType | List[TokenType], expected_value: Optional[Any] = None) -> Token:
        current_token = self.current_token
        self.expect(expected_type=expected_type, expected_value=expected_value)
        self.advance()
        self.logger.info(f"Consumed token {current_token}")
        return current_token

    def _get_identifier_type(self) -> Literal["value", "object", "key_value_pair", "comparison"]:
        current_token = self.current_token
        next_token = self.next_token
        next_next_token = self.lookahead(2)
        self.expect(
            [
                TokenType.IDENTIFIER,
                TokenType.CONSTANT,
                TokenType.KEYWORD,
                TokenType.SCOPE,
                TokenType.MODIFIER,
                TokenType.EFFECT,
                TokenType.TRIGGER,
                TokenType.VARIABLE,
            ]
        )
        if next_token.token_type == TokenType.OPEN_BRACE or (
            next_token.value == "=" and next_next_token.token_type == TokenType.OPEN_BRACE
        ):
            return "object"
        elif next_token.token_type == TokenType.OPERATOR:
            if next_token.value == "=":
                if next_next_token.token_type in {
                    TokenType.IDENTIFIER,
                    TokenType.NUMBER_LITERAL,
                    TokenType.PERCENTAGE_LITERAL,
                    TokenType.STRING_LITERAL,
                    TokenType.BOOLEAN,
                    TokenType.CONSTANT,
                    TokenType.DATE_LITERAL,
                    TokenType.SCOPE,
                    TokenType.MODIFIER,
                    TokenType.EFFECT,
                    TokenType.VARIABLE,
                }:
                    return "key_value_pair"
                else:
                    return "value"
            else:
                return "comparison"
        return "value"

    def parse_tokens(self):
        root_token = Token(TokenType.ROOT, "root", 0, 0)
        root_value_node = ValueNode(root_token)
        node = ObjectNode(context=root_value_node, children=[])
        while self.current_token.token_type != TokenType.EOF:
            # res = self._parse()
            # self.logger.debug(f"Parsed token {res}")
            node.add_child(self._parse())
        return node

    def _parse(self):
        current_token = self.current_token
        current_token_type = current_token.token_type
        if current_token_type in {
            TokenType.STRING_LITERAL,
            TokenType.NUMBER_LITERAL,
            TokenType.PERCENTAGE_LITERAL,
            TokenType.BOOLEAN,
            # TokenType.CONSTANT,
            TokenType.DATE_LITERAL,
        }:
            return self._parse_value()
        elif current_token_type in {
            TokenType.IDENTIFIER,
            TokenType.CONSTANT,
            TokenType.KEYWORD,
            TokenType.SCOPE,
            TokenType.MODIFIER,
            TokenType.EFFECT,
            TokenType.TRIGGER,
            TokenType.VARIABLE,
        }:
            identifier_type = self._get_identifier_type()
            match identifier_type:
                case "object":
                    context = current_token
                    self.consume(
                        [
                            TokenType.IDENTIFIER,
                            TokenType.CONSTANT,
                            TokenType.KEYWORD,
                            TokenType.SCOPE,
                            TokenType.MODIFIER,
                            TokenType.EFFECT,
                            TokenType.TRIGGER,
                            # TokenType.VARIABLE,
                        ]
                    )
                    if self.current_token.token_type == TokenType.OPEN_BRACE:
                        return self._parse_object(context=context)
                    self.consume(TokenType.OPERATOR, "=")
                    return self._parse_object(context=context)
                case "key_value_pair":
                    return self._parse_key_value_pair()
                case "value":
                    return self._parse_value()
                case "comparison":
                    return self._parse_comparison()
        else:
            raise ParseException(f"Unexpected token type {current_token_type}", current_token)

    def _parse_value(self):
        current_token = self.current_token
        current_token_type = current_token.token_type
        if current_token_type == TokenType.STRING_LITERAL:
            return ValueNode(self.consume(TokenType.STRING_LITERAL))
        elif current_token_type == TokenType.NUMBER_LITERAL:
            return ValueNode(self.consume(TokenType.NUMBER_LITERAL))
        elif current_token_type == TokenType.PERCENTAGE_LITERAL:
            return ValueNode(self.consume(TokenType.PERCENTAGE_LITERAL))
        elif current_token_type == TokenType.BOOLEAN:
            return ValueNode(self.consume(TokenType.BOOLEAN))
        elif current_token_type == TokenType.CONSTANT:
            return ValueNode(self.consume(TokenType.CONSTANT))
        elif current_token_type == TokenType.DATE_LITERAL:
            return ValueNode(self.consume(TokenType.DATE_LITERAL))
        elif current_token_type == TokenType.IDENTIFIER:
            return ValueNode(self.consume(TokenType.IDENTIFIER))
        elif current_token_type == TokenType.VARIABLE:
            return ValueNode(self.consume(TokenType.VARIABLE))
        else:
            raise ParseException(f"Unexpected token type {current_token_type}", current_token)

    def _parse_comparison(self):
        left = self._parse_value()
        operator = self.consume(TokenType.OPERATOR)
        right = self._parse_value()
        return ComparisonNode(left=left, operator=operator.value, right=right)

    def _parse_key_value_pair(self):
        key = ValueNode(
            self.consume(
                [
                    TokenType.IDENTIFIER,
                    TokenType.CONSTANT,
                    TokenType.KEYWORD,
                    TokenType.SCOPE,
                    # TokenType.MODIFIER,
                    TokenType.EFFECT,
                    TokenType.TRIGGER,
                    TokenType.VARIABLE,
                ]
            )
        )
        self.consume(TokenType.OPERATOR, "=")
        value = self._parse_value()
        return KeyValueNode(key=key, value=value)

    def _parse_object(self, context: Token):
        self.consume(TokenType.OPEN_BRACE)
        context_type = context.token_type
        if context_type == TokenType.EFFECT:
            node = EffectBlockNode(context=ValueNode(context), children=[])
        elif context_type == TokenType.KEYWORD:
            node = KeywordBlockNode(context=ValueNode(context), children=[])
        elif context_type == TokenType.TRIGGER:
            node = TriggerBlockNode(context=ValueNode(context), children=[])
        else:
            node = ObjectNode(context=ValueNode(context), children=[])
        while self.current_token.token_type != TokenType.CLOSE_BRACE:
            node.add_child(self._parse())
        self.consume(TokenType.CLOSE_BRACE)
        # convert to array if all values are ValueNodes
        if all(isinstance(value, ValueNode) for value in node.children):
            elements = [value for value in node.children]
            return ArrayNode(context=ValueNode(context), elements=elements)
        # converts all key-value pairs in TriggerNodes to ComparisonNodes
        if isinstance(node, TriggerBlockNode):
            for i, value in enumerate(node.children):
                if isinstance(value, KeyValueNode):
                    node.children[i] = ComparisonNode(left=value.key, operator="=", right=value.value)
        # goes through the node and finds all key-value pairs with constants as keys.
        # adds an object node called "_constants" with all these key-value pairs
        _constants_node = ObjectNode(context=ValueNode(Token(TokenType.CONSTANT, "_constants", 0, 0)), children=[])
        for i, value in enumerate(node.children):
            if isinstance(value, KeyValueNode) and value.key.type == TokenType.CONSTANT:
                _constants_node.add_child(value)
                node.children = [
                    x
                    for x in node.children
                    if not isinstance(x, KeyValueNode) or isinstance(x, KeyValueNode) and x.key.value != value.key.value
                ]
        if len(_constants_node.children) > 0:
            node.insert_child(_constants_node)
        return node

    def find_by_value_or_type(self, value: Optional[Any] = None, node_type: Optional[type] = None) -> List[Node]:
        results = []

        def search_node(node):
            if value is not None and isinstance(node, ValueNode) and node.value == value:
                results.append(node)
            if node_type is not None and isinstance(node, node_type):
                results.append(node)
            if isinstance(node, ObjectNode):
                for child_node in node.children:
                    search_node(child_node)
            elif isinstance(node, ArrayNode):
                for element in node.elements:
                    search_node(element)
            elif isinstance(node, KeyValueNode):
                search_node(node.key)
                search_node(node.value)
            elif isinstance(node, ComparisonNode):
                search_node(node.left)
                search_node(node.right)

        search_node(self.parsed_tree)
        return results

    def print_tree(self):
        self._print_ast(self.parsed_tree)

    def _print_ast(self, node: Node, indent: int = 0):
        def _get_value(node: Node):
            if isinstance(node, ValueNode):
                if node.type == TokenType.STRING_LITERAL:
                    return f'"{node.value}"'
                elif node.type == TokenType.BOOLEAN:
                    return f"bool({node.value})"
                elif node.type == TokenType.NUMBER_LITERAL:
                    if isinstance(node.value, int):
                        return f"int({node.value})"
                    return f"float({node.value})"
                elif node.type == TokenType.PERCENTAGE_LITERAL:
                    return f"percentage({node.value})"
                elif node.type == TokenType.DATE_LITERAL:
                    return f"date({node.value})"
                return node.value
            else:
                return str(node.context.value)  # type: ignore

        if isinstance(node, EffectBlockNode):
            print(f"{'  ' * indent}EffectBlock: {_get_value(node)}")
            for value in node.children:
                self._print_ast(value, indent + 1)
        elif isinstance(node, KeywordBlockNode):
            print(f"{'  ' * indent}KeywordBlock: {_get_value(node)}")
            for value in node.children:
                self._print_ast(value, indent + 1)
        elif isinstance(node, TriggerBlockNode):
            print(f"{'  ' * indent}TriggerBlock: {_get_value(node)}")
            for value in node.children:
                self._print_ast(value, indent + 1)
        elif isinstance(node, ObjectNode):
            print(f"{'  ' * indent}Object: {_get_value(node)}")
            for value in node.children:
                self._print_ast(value, indent + 1)
        elif isinstance(node, ArrayNode):
            print(f"{'  ' * indent}Array: {_get_value(node)}")
            for element in node.elements:
                self._print_ast(element, indent + 1)
        elif isinstance(node, KeyValueNode):
            key_value = _get_value(node.key)  # Use _get_value for key
            value_value = _get_value(node.value)  # Use _get_value for value
            print(f"{'  ' * indent}KeyValue: {key_value} = {value_value}")
        elif isinstance(node, ComparisonNode):
            left_value = _get_value(node.left)  # Use _get_value for left
            right_value = _get_value(node.right)  # Use _get_value for right
            print(f"{'  ' * indent}Comparison: {left_value} {node.operator} {right_value}")
        elif isinstance(node, ValueNode):
            print(f"{'  ' * indent}Value: {_get_value(node)}")
        elif isinstance(node, CommentNode):
            print(f"{'  ' * indent}Comment: {_get_value(node)}")
        else:
            print(f"{'  ' * indent}Unknown Node Type: {type(node)}")


if __name__ == "__main__":
    try:
        input_text = open("module-eq-parser/parser_v2/technologies_data.txt").read()
    except:
        input_text = open("countrytechtreeview.gui").read()
    lexer = Lexer(input_text, "hoi4", config={"enable_logger": False})
    tokens = lexer.tokenize()
    parser = Parser(tokens, config={"enable_logger": False})
    parser.print_tree()
