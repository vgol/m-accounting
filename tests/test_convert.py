from pathlib import Path

import pytest

from app.convert.pdf_to_json import convert_directory


@pytest.mark.skip(reason="Requires real PDFs and docling backends; integration test")
def test_convert_directory(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "data"
    input_dir.mkdir()
    # Placeholders: in real test, add a small PDF fixture here
    # (Skipping until fixtures are available.)
    converted = convert_directory(input_dir, output_dir)
    assert converted == []
