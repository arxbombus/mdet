"""CLI for parsing and normalizing Millennium Dawn technology files."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from scripts.generator import ClausewitzFormatter, ClausewitzParser, DocumentSchema
from scripts.generator.schemas import technologies_schema

DEFAULT_INPUT_DIR = Path("docs/millennium-dawn/common/technologies")
DEFAULT_OUTPUT_DIR = Path("out/")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Parse Clausewitz technology files and write normalized Millennium Dawn outputs "
            "(matching the formatting used in out/)."
        )
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=str(DEFAULT_INPUT_DIR),
        help="Path to a technology file or directory (defaults to docs/millennium-dawn/common/technologies).",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where normalized files should be written (defaults to out/).",
    )
    parser.add_argument(
        "--indent",
        default="\t",
        help="Indentation characters to use (default: tab).",
    )
    parser.add_argument(
        "--inline-braces",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Inline simple braces/lists when possible (default: enabled).",
    )
    return parser.parse_args()


def collect_inputs(path: Path) -> list[Path]:
    if path.is_dir():
        files = sorted(p for p in path.glob("*.txt") if p.is_file())
        if not files:
            raise FileNotFoundError(f"No .txt files found in directory: {path}")
        return files
    if path.is_file():
        return [path]
    raise FileNotFoundError(f"Input path does not exist: {path}")


def format_document(text: str, formatter: ClausewitzFormatter, schema: DocumentSchema) -> str:
    parser = ClausewitzParser(text, schema=schema)
    document = parser.parse_document()
    lines: list[str] = []
    for entry in document.root.entries:
        lines.extend(formatter.format_entry(entry.key, entry.value, level=0))
    return "\n".join(lines).rstrip() + "\n"


def generate(files: Iterable[Path], output_dir: Path, indent: str, inline_braces: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    formatter = ClausewitzFormatter(indent=indent, inline_braces=inline_braces)
    schema = technologies_schema()
    for source in files:
        text = source.read_text(encoding="utf-8")
        try:
            normalized = format_document(text, formatter, schema)
        except Exception as exc:  # pragma: no cover - surfaced to CLI
            raise RuntimeError(f"Failed to parse {source}") from exc
        destination = output_dir / source.name
        destination.write_text(normalized, encoding="utf-8")
        try:
            display_path = destination.relative_to(Path.cwd())
        except ValueError:
            display_path = destination
        print(f"Wrote {display_path}")


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    files = collect_inputs(input_path)
    generate(files, output_dir, indent=args.indent, inline_braces=args.inline_braces)


if __name__ == "__main__":
    main()
