"""Simple syntax verifier for AWsl files."""
from pathlib import Path
import sys

from lark import Lark, UnexpectedInput


def load_grammar() -> str:
    grammar_path = Path(__file__).with_name("awsl.bnf")
    return grammar_path.read_text()


def verify(path: Path) -> None:
    grammar = load_grammar()
    parser = Lark(grammar, start="workflow")
    text = path.read_text()
    parser.parse(text)


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python verifier.py <file.awsl>")
        raise SystemExit(1)

    file_path = Path(sys.argv[1])
    try:
        verify(file_path)
    except UnexpectedInput as exc:
        print(f"Syntax error: {exc}")
        raise SystemExit(1)
    print("Syntax OK")


if __name__ == "__main__":
    main()
