import json
from pathlib import Path

from docling.document_converter import DocumentConverter


def convert_pdf_to_json(input_pdf_path: str | Path, output_json_path: str | Path) -> Path:
    input_path = Path(input_pdf_path)
    output_path = Path(output_json_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    converter = DocumentConverter()
    result = converter.convert_single(str(input_path))
    document_dict = result.document.export_to_dict()
    output_path.write_text(json.dumps(document_dict, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def convert_directory(input_dir: str | Path, output_dir: str | Path) -> list[Path]:
    in_dir = Path(input_dir)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    converted: list[Path] = []
    for pdf in in_dir.glob("*.pdf"):
        out_path = out_dir / (pdf.stem + ".json")
        converted.append(convert_pdf_to_json(pdf, out_path))
    return converted
