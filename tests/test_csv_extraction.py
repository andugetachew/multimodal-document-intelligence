from app.services.extraction.csv_extractor import extract_csv_text


def test_extract_simple_csv(tmp_path):
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("Name,Age,City\nAndualem,25,Addis Ababa\n", encoding="utf-8")

    result = extract_csv_text(str(csv_path))

    assert "Name | Age | City" in result
    assert "Andualem | 25 | Addis Ababa" in result


def test_extract_csv_with_multiple_rows(tmp_path):
    csv_path = tmp_path / "multi.csv"
    csv_path.write_text(
        "Product,Price\nWidget,10.00\nGadget,20.00\n", encoding="utf-8"
    )

    result = extract_csv_text(str(csv_path))
    lines = result.split("\n")

    assert len(lines) == 3
    assert "Widget | 10.00" in result
    assert "Gadget | 20.00" in result


def test_extract_empty_csv_returns_empty_string(tmp_path):
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("", encoding="utf-8")

    result = extract_csv_text(str(csv_path))

    assert result == ""