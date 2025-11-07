from typing import Any, Dict, List, Literal, Optional, Set, TypedDict, NotRequired
from enum import Enum, auto
from dataclasses import dataclass
import json
import re
import os
from scripts.generator.utils import resolve_config
from scripts.generator.logger import Logger


class TokenType(Enum):
    STRING_LITERAL = auto()
    NUMBER_LITERAL = auto()
    PERCENTAGE_LITERAL = auto()
    DATE_LITERAL = auto()
    BOOLEAN = auto()
    OPERATOR = auto()
    KEYWORD = auto()
    SCOPE = auto()
    MODIFIER = auto()
    EFFECT = auto()
    TRIGGER = auto()
    VARIABLE = auto()
    # TARGETED_VARIABLE = auto()
    CONSTANT = auto()
    IDENTIFIER = auto()
    OPEN_BRACE = auto()
    CLOSE_BRACE = auto()
    COMMENT = auto()
    ROOT = auto()  # unused in lexer - root of AST tree
    EOF = auto()

    @classmethod
    def get_token_type(cls, type: str):
        for token_type in cls:
            if token_type.name == type:
                return token_type
        raise ValueError(f"Unknown token type: {type}")


@dataclass
class Token:
    token_type: TokenType
    value: Any
    line: int
    column: int


GameType = Literal["hoi4", "stellaris"]

OPERATORS = {">", "<", ">=", "<=", "!=", "=", ":", "?", "@"}


class LexerError(Exception):
    def __init__(self, message, line, column):
        super().__init__(f"Error: {message} at {line}:{column}")
        self.line = line
        self.column = column


class LexerConfig(TypedDict):
    tokenize: NotRequired[bool]
    enable_logger: NotRequired[bool]
    clausewitz_types_path: NotRequired[str]
    game_info_path: NotRequired[str]


class LexerConfigRequired(TypedDict):
    tokenize: bool
    enable_logger: bool
    clausewitz_types_path: str
    game_info_path: str


DEFAULT_CONFIG: LexerConfigRequired = {
    "tokenize": True,
    "enable_logger": True,
    "clausewitz_types_path": "scripts/generator/clausewitz.json",
    "game_info_path": "scripts/generator/hoi4.json",
}


class Lexer:
    def __init__(self, input: str, game_type: GameType, config: Optional[LexerConfig] = None):
        self.input = input
        self.game_type = game_type
        self.config = resolve_config(config or {}, DEFAULT_CONFIG)
        self.logger = Logger(config={"name": "Lexer Logger", "is_enabled": self.config["enable_logger"]}).logger
        self.keywords: Set[str] = set()
        self.modifiers: Set[str] = set()
        self.effects: Set[str] = set()
        self.triggers: Set[str] = set()
        self.repeatable_keys: set[str] = set()
        self._get_base_clausewitz_types()
        self._get_game_specific_types()
        self._start = 0
        self.position = 0
        self.line = 1
        self.column = 1
        self.tokens = []
        if self.config["tokenize"]:
            self.tokenize()

    def _get_base_clausewitz_types(self):
        clausewitz_path = self.config["clausewitz_types_path"]
        with open(clausewitz_path) as f:
            base = json.load(f)
        self.keywords.update(base["keywords"])
        self.triggers.update(base["triggers"])

    def _get_game_specific_types(self):
        game_info_path = self.config["game_info_path"]
        with open(game_info_path) as f:
            game_info = json.load(f)
        self.modifiers.update(game_info["modifiers"])
        self.effects.update(game_info["effects"])
        self.triggers.update(game_info["triggers"])
        self.repeatable_keys = set(game_info.get("repeatable_keys", []))

    @property
    def previous_token(self):
        return self.tokens[-1] if self.tokens else None

    @property
    def has_more_chars(self):
        return self.position < len(self.input)

    @property
    def char(self):
        return self.input[self.position] if self.has_more_chars else "\0"

    @property
    def current_value(self):
        return self.input[self._start : self.position] if self.has_more_chars else self.input[self._start :]

    def _advance(self, steps=1):
        for _ in range(steps):
            if not self.has_more_chars:
                raise LexerError("Attempt to advance beyond end of input", self.line, self.column)
            if self.char == "\n":
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            self.position += 1

    def _consume_while(self, condition):
        while self.has_more_chars and condition(self.char):
            self._advance()

    def _peek(self, steps=1):
        if self.position + steps < len(self.input):
            return self.input[self.position + steps]
        return "\0"

    def _add_token(self, token_type: TokenType, value: Any, line: Optional[int] = None, column: Optional[int] = None):
        self.logger.debug(
            f"Adding token {token_type} with value '{value}' at line {line or self.line}, column {column or self.column}",
        )
        self.tokens.append(Token(token_type, value, line or self.line, max(column or self.column, 1)))

    def _is_whitespace(self, char: str) -> bool:
        return char.isspace() or char == "\n"

    def _is_operator(self, chars: str) -> bool:
        return chars in OPERATORS

    def _get_identifier_token_type(self, chars: str):
        if chars in self.keywords:
            return TokenType.KEYWORD
        elif chars in self.modifiers:
            return TokenType.MODIFIER
        elif chars in self.effects:
            return TokenType.EFFECT
        elif chars in self.triggers:
            return TokenType.TRIGGER
        return TokenType.IDENTIFIER

    def _is_boolean(self, value: str) -> bool:
        return value in {"yes", "no"}

    def _handle_unexpected_char(self):
        char = self.char
        raise LexerError(f"Unexpected character '{char}'", self.line, self.column)

    def tokenize(self):
        try:
            self.logger.info("Starting tokenization")
            while self.has_more_chars:
                char = self.char
                self.logger.debug(
                    f"Processing character '{char}' at position {self.position}, line {self.line}, column {self.column}",
                )
                if self._is_whitespace(char):
                    self._skip_whitespace()
                elif char == "#":
                    self._handle_comments()
                elif char in {"{", "}"}:
                    self._handle_braces()
                elif char in ('"', "'"):
                    self._handle_strings()
                elif char.isdigit() or (char == "-" and self._peek().isdigit()):
                    self._handle_numbers()
                elif self._is_operator(char):
                    self._handle_operator()
                elif char.isalpha() or char in {"_", "-", ".", "@"}:
                    self._handle_identifiers()
                else:
                    self._handle_unexpected_char()
            self._add_token(TokenType.EOF, None)
            self.logger.info("Tokenization complete")
            return self.tokens
        except LexerError as e:
            self.logger.error(e)
            # Handle or propagate the error as needed
        return []

    def _skip_whitespace(self):
        self._consume_while(lambda c: c.isspace())

    def _handle_braces(self):
        if self.char == "{":
            self._add_token(TokenType.OPEN_BRACE, "{")
        elif self.char == "}":
            self._add_token(TokenType.CLOSE_BRACE, "}")
        self._advance()

    def _handle_strings(self):
        self._start = self.position + 1
        quote = self.char
        self._advance()
        self._consume_while(lambda c: c != quote)
        self._add_token(TokenType.STRING_LITERAL, self.current_value)  # strip quotes...I guess
        self._advance()

    def _handle_numbers(self):
        self._start = self.position
        # if self.char == "-" or self.char == "." or self.char == "%":
        if self.char in {"-", "."}:
            self._advance()
        self._consume_while(lambda c: c.isdigit() or c in {".", "%"})
        date_regex = r"\b\d{1,4}\.\d{1,4}\.\d{1,4}\b"
        if re.match(date_regex, self.current_value):
            self._add_token(TokenType.DATE_LITERAL, self.current_value)
        elif "%" in self.current_value:
            self._add_token(TokenType.PERCENTAGE_LITERAL, self.current_value)
        else:
            value = self.current_value
            if "." in value:
                value = float(value)
            else:
                value = int(value)
            self._add_token(TokenType.NUMBER_LITERAL, value)

    def _handle_comments(self):
        if self.char == "#":
            self._start = self.position
            self._consume_while(lambda c: c != "\n")
            self._add_token(TokenType.COMMENT, self.current_value)

    def _handle_operator(self):
        self._start = self.position
        _val = self.current_value + self._peek(1)
        if self.char == "@":
            self._handle_identifiers()
        else:
            if self._is_operator(_val):
                self._advance(2)
                self._add_token(TokenType.OPERATOR, self.current_value)
            else:
                self._advance()
                self._add_token(TokenType.OPERATOR, self.current_value)

    def _handle_identifiers(self):
        self._start = self.position
        if self.char == "@":  # @ should only be handled when it's the first char for TokenTypes.CONSTANT
            self._advance()
        self._consume_while(lambda c: c.isalnum() or c in {"_", "-", "."})
        value = self.current_value
        if self._is_boolean(value):
            self._add_token(TokenType.BOOLEAN, value == "yes")
        elif "@" in value:
            if self.previous_token and self.previous_token.token_type == TokenType.IDENTIFIER:
                self._add_token(TokenType.IDENTIFIER, value)
            else:
                self._add_token(TokenType.CONSTANT, value)
        elif "." in value:
            self._add_token(TokenType.SCOPE, value)
        elif re.match(r"^[a-zA-Z_][a-zA-Z0-9_-]*$", value):
            self._add_token(self._get_identifier_token_type(value), value)
        else:
            self._add_token(TokenType.IDENTIFIER, value)


if __name__ == "__main__":
    # use technologies_data.txt
    input_text = open("countrytechtreeview.gui").read()
    lexer = Lexer(input_text, "hoi4", config={"enable_logger": False})
    tokens = lexer.tokenize()
    # json output
    with open("countrytechtreeview_tokenized.txt", "w+") as file:
        file.writelines([repr(token) + "\n" for token in tokens])
