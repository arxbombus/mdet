import json
from dataclasses import asdict

from scripts.generator.hoi4.tech import TechCollection


def run_parser_test():
    tech_group = TechCollection(
        "scripts/generator/technologies.txt",
        parser_manager_config={"lexer_config": {"enable_logger": False}, "parser_config": {"enable_logger": False}},
    )
    techs_dict = {name: asdict(tech) for name, tech in tech_group.techs.items()}
    json_output = json.dumps(techs_dict, indent=2)
    out_path = "out.json"
    with open(out_path, "w", encoding="utf-8") as outfile:
        outfile.write(json_output)
    print(json_output)


if __name__ == "__main__":
    run_parser_test()
