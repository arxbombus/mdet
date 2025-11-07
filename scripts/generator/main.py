from scripts.generator.lexer import Lexer
from scripts.generator.parser import Parser
from scripts.generator.hoi4.tech import TechCollection


def run_parser_test():
    tech_group = TechCollection(
        "scripts/generator/technologies.txt",
        parser_manager_config={"lexer_config": {"enable_logger": False}, "parser_config": {"enable_logger": False}},
    )
    from pprint import pprint

    # pprint(tech_group.techs)


if __name__ == "__main__":
    run_parser_test()
