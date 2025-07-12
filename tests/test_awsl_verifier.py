from pathlib import Path

from awsl.grammar.verifier import verify


def test_deepresearch_sample():
    verify(Path("awsl/deepresearch.awsl"))
