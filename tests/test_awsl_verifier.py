from pathlib import Path

from awsl.verifier import verify


def test_deepresearch_sample():
    verify(Path("awsl/deepresearch.awsl"))
