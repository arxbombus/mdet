"""CLI for regenerating Clausewitz tech scripts from parsed data."""

from __future__ import annotations

import argparse

from scripts.generator.hoi4.tech import TechCollection
from scripts.generator.generator import TechCollectionGenerator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate HOI4 tech script from parsed data.")
    parser.add_argument(
        "input",
        nargs="?",
        default="scripts/generator/technologies.txt",
        help="Path to the source technologies script.",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Optional output path. Prints to stdout when omitted.",
    )
    parser.add_argument(
        "--indent",
        default="\t",
        help="Indentation characters to use for blocks (default: tab).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tech_collection = TechCollection(
        args.input,
        parser_manager_config={
            "lexer_config": {"enable_logger": False},
            "parser_config": {"enable_logger": False},
        },
    )
    generator = TechCollectionGenerator(tech_collection, indent=args.indent)
    output = generator.generate()
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(output)
    else:
        print(output)


if __name__ == "__main__":
    main()
