from typing import List, Optional, NotRequired, TypedDict
from scripts.generator.lexer import Lexer, GameType, LexerConfig
from scripts.generator.parser import Parser, ParserConfig
from scripts.generator.node_transformer import NodeTransformer
from scripts.generator.utils import resolve_config


class ParserManagerConfig(TypedDict):
    # game_type: GameType
    lexer_config: NotRequired[LexerConfig]
    parser_config: NotRequired[ParserConfig]


class ParserManagerConfigRequired(TypedDict):
    lexer_config: LexerConfig
    parser_config: ParserConfig


DEFAULT_CONFIG: ParserManagerConfigRequired = {
    "lexer_config": {},
    "parser_config": {},
}


class ParserManager:
    def __init__(self, path: str, game_type: GameType, config: Optional[ParserManagerConfig] = None):
        # if isinstance(paths, str):
        #     paths = [paths]
        self.config = resolve_config(config or {}, DEFAULT_CONFIG)
        self.paths = path
        self.input = open(path, "r").read()
        self.lexer = Lexer(input=self.input, game_type=game_type, config=self.config["lexer_config"])
        self.parser = Parser(tokens=self.lexer.tokens, config=self.config["parser_config"])
        self.node_transformer = NodeTransformer(self.parser.parsed_tree)
        # self.transformed_tree = self.node_transformer.transformed_tree
