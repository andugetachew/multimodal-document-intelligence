import csv


def extract_csv_text(file_path: str) -> str:
    rows = []

    with open(file_path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        for row in reader:
            rows.append(" | ".join(cell.strip() for cell in row))

    return "\n".join(rows).strip()