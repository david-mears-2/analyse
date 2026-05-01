#!/usr/bin/env python3
"""Swap the embedded datasets block in index.html with sweeper CSV output.

This script supports two operations:

1. apply   - import datasets from a sweeper-style directory and make them active
2. restore - restore the archived original embedded datasets block

On first apply, the current active datasets and dataSourceMeta blocks are preserved
inside index.html as a JavaScript block comment so the original data can be restored
later without needing a second file.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


DEFAULT_SOURCE_DIR = "~/projects/jameel-institute/sweeper"
DEFAULT_HTML_PATH = "index.html"
DEFAULT_ARCHIVE_LABEL = "Thursday 30th April"
EXPECTED_COLUMNS = [
    "response_id",
    "response_label",
    "pathogen_id",
    "pathogen_label",
    "log_slope",
    "step_multiplier",
    "step_pct_change",
    "cost_none_3sf",
    "cost_low_3sf",
    "cost_medium_3sf",
    "cost_high_3sf",
    "run_none",
    "run_low",
    "run_medium",
    "run_high",
]
TIER_ORDER = {"default": 0, "mid": 1, "max": 2}
CSV_NAME_RE = re.compile(
    r"^(?P<country>[a-z]{3})-(?P<tier>default|mid|max)-hosp(?P<capacity>\d+)-"
    r"vaccine-log-slopes-by-response\.csv$"
)
ACTIVE_BLOCK_RE = re.compile(
    r"const datasets = \[.*?\];\n\nconst dataSourceMeta = \{.*?\};\n\n(?=const datasetsById = )",
    re.DOTALL,
)
ARCHIVE_RE = re.compile(
    r"/\*\nBEGIN ARCHIVED EMBEDDED DATA: (?P<label>[^\n]+)\n"
    r"(?P<body>.*?)\n"
    r"END ARCHIVED EMBEDDED DATA: (?P=label)\n\*/\n\n",
    re.DOTALL,
)


@dataclass(frozen=True)
class SourceDataset:
    country_code: str
    country_label: str
    tier: str
    hospital_capacity: str
    rows: list[dict[str, object]]

    @property
    def dataset_id(self) -> str:
        return f"{self.country_code}:{self.tier}:hosp{self.hospital_capacity}"

    def to_embedded_dict(self) -> dict[str, object]:
        return {
            "id": self.dataset_id,
            "country_code": self.country_code,
            "country_label": self.country_label,
            "behaviour": self.tier,
            "hospital_capacity": self.hospital_capacity,
            "rows": self.rows,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Swap the embedded datasets in index.html with sweeper CSV output, or "
            "restore the archived original embedded data."
        )
    )
    parser.add_argument(
        "command",
        choices=["apply", "restore"],
        help="Use 'apply' to import sweeper data, or 'restore' to reactivate the archived original data.",
    )
    parser.add_argument(
        "--html-path",
        default=DEFAULT_HTML_PATH,
        help=f"Path to the HTML file that contains the embedded datasets (default: {DEFAULT_HTML_PATH}).",
    )
    parser.add_argument(
        "--source-dir",
        default=DEFAULT_SOURCE_DIR,
        help=(
            "Directory containing sweeper CSV artifacts and metadata.json "
            f"(default: {DEFAULT_SOURCE_DIR})."
        ),
    )
    parser.add_argument(
        "--archive-label",
        default=DEFAULT_ARCHIVE_LABEL,
        help=(
            "Label to attach to the archived original embedded data block when "
            f"running apply for the first time (default: {DEFAULT_ARCHIVE_LABEL!r})."
        ),
    )
    return parser.parse_args()


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return path.read_text()


def write_text(path: Path, content: str) -> None:
    path.write_text(content)


def load_country_labels(source_dir: Path) -> dict[str, str]:
    metadata_path = source_dir / "metadata.json"
    payload = json.loads(read_text(metadata_path))
    data = payload.get("data", payload)
    parameters = {parameter["id"]: parameter for parameter in data["parameters"]}
    return {
        option["id"].lower(): option["label"]
        for option in parameters["country"]["options"]
    }


def load_model_version(source_dir: Path) -> str:
    metadata_path = source_dir / "metadata.json"
    payload = json.loads(read_text(metadata_path))
    data = payload.get("data", payload)
    model_version = data.get("modelVersion")
    if not isinstance(model_version, str) or not model_version:
        raise ValueError(f"metadata.json did not contain a usable modelVersion in {metadata_path}")
    return model_version


def parse_csv_rows(path: Path) -> list[dict[str, object]]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    if reader.fieldnames != EXPECTED_COLUMNS:
        raise ValueError(f"Unexpected CSV columns in {path}: {reader.fieldnames}")
    parsed_rows: list[dict[str, object]] = []
    seen_keys: set[tuple[str, str]] = set()
    for row in rows:
        key = (row["response_id"], row["pathogen_label"])
        if key in seen_keys:
            raise ValueError(f"Duplicate response/pathogen row {key} in {path}")
        seen_keys.add(key)
        parsed_rows.append(
            {
                "response_id": row["response_id"],
                "response_label": row["response_label"],
                "pathogen_label": row["pathogen_label"],
                "log_slope": float(row["log_slope"]),
                "costs": [
                    int(row["cost_none_3sf"]),
                    int(row["cost_low_3sf"]),
                    int(row["cost_medium_3sf"]),
                    int(row["cost_high_3sf"]),
                ],
            }
        )
    if not parsed_rows:
        raise ValueError(f"No rows found in {path}")
    return parsed_rows


def load_source_datasets(source_dir: Path) -> list[SourceDataset]:
    country_labels = load_country_labels(source_dir)
    datasets: list[SourceDataset] = []
    for csv_path in sorted(source_dir.glob("*-hosp*-vaccine-log-slopes-by-response.csv")):
        match = CSV_NAME_RE.match(csv_path.name)
        if not match:
            continue
        country_code = match.group("country")
        tier = match.group("tier")
        hospital_capacity = match.group("capacity")
        country_label = country_labels.get(country_code)
        if country_label is None:
            raise ValueError(f"No country label found for {country_code!r} in metadata.json")
        datasets.append(
            SourceDataset(
                country_code=country_code,
                country_label=country_label,
                tier=tier,
                hospital_capacity=hospital_capacity,
                rows=parse_csv_rows(csv_path),
            )
        )
    if not datasets:
        raise ValueError(f"No matching sweeper CSVs found in {source_dir}")
    validate_country_tiers(datasets)
    return sorted(
        datasets,
        key=lambda dataset: (
            dataset.country_code,
            TIER_ORDER[dataset.tier],
            int(dataset.hospital_capacity),
        ),
    )


def validate_country_tiers(datasets: list[SourceDataset]) -> None:
    expected_keys_by_country: dict[str, set[tuple[str, str]]] = {}
    for dataset in datasets:
        keys = {
            (row["response_id"], row["pathogen_label"])
            for row in dataset.rows
        }
        if dataset.country_code not in expected_keys_by_country:
            expected_keys_by_country[dataset.country_code] = keys
            continue
        expected_keys = expected_keys_by_country[dataset.country_code]
        if keys != expected_keys:
            missing = sorted(expected_keys - keys)
            extra = sorted(keys - expected_keys)
            raise ValueError(
                "Tier mismatch for "
                f"{dataset.country_code}: missing={missing} extra={extra}"
            )


def build_active_block(datasets: list[SourceDataset], source_dir: Path) -> str:
    embedded_datasets = [dataset.to_embedded_dict() for dataset in datasets]
    model_version = load_model_version(source_dir)
    imported_at = datetime.now(ZoneInfo("Europe/London")).strftime("%Y-%m-%d %H:%M %Z")
    source_directory = str(source_dir.resolve())
    details_html = (
        "Data imported <code>"
        + html.escape(imported_at)
        + "</code> from <code>"
        + html.escape(source_directory)
        + "</code>; model version = <code>"
        + html.escape(model_version)
        + "</code>."
    )
    data_source_meta = {
        "kind": "imported",
        "importedAt": imported_at,
        "sourceDirectory": source_directory,
        "modelVersion": model_version,
        "detailsHtml": details_html,
    }
    datasets_json = json.dumps(embedded_datasets, indent=2)
    metadata_json = json.dumps(data_source_meta, indent=2)
    return f"const datasets = {datasets_json};\n\nconst dataSourceMeta = {metadata_json};\n\n"


def extract_active_block(html_text: str, start_index: int = 0) -> str:
    match = ACTIVE_BLOCK_RE.search(html_text, start_index)
    if match is None:
        raise ValueError("Could not locate active datasets/dataSourceMeta block in HTML")
    return match.group(0)


def build_archive_comment(label: str, active_block: str) -> str:
    archived_body = active_block.rstrip()
    return (
        "/*\n"
        f"BEGIN ARCHIVED EMBEDDED DATA: {label}\n"
        f"{archived_body}\n"
        f"END ARCHIVED EMBEDDED DATA: {label}\n"
        "*/\n\n"
    )


def apply_swap(html_path: Path, source_dir: Path, archive_label: str) -> None:
    html_text = read_text(html_path)
    archive_match = ARCHIVE_RE.search(html_text)
    active_block = extract_active_block(
        html_text,
        archive_match.end() if archive_match is not None else 0,
    )
    new_active_block = build_active_block(load_source_datasets(source_dir), source_dir)
    if archive_match is None:
        replacement = build_archive_comment(archive_label, active_block) + new_active_block
        updated_html = html_text.replace(active_block, replacement, 1)
    else:
        updated_html = html_text.replace(active_block, new_active_block, 1)
    write_text(html_path, updated_html)


def restore_swap(html_path: Path) -> None:
    html_text = read_text(html_path)
    archive_match = ARCHIVE_RE.search(html_text)
    if archive_match is None:
        raise ValueError("No archived embedded data block found in HTML")
    active_block = extract_active_block(html_text, archive_match.end())
    archived_body = archive_match.group("body").strip() + "\n\n"
    updated_html = html_text.replace(archive_match.group(0) + active_block, archived_body, 1)
    write_text(html_path, updated_html)


def main() -> int:
    args = parse_args()
    html_path = Path(args.html_path)
    if args.command == "apply":
        apply_swap(
            html_path=html_path,
            source_dir=Path(args.source_dir).expanduser(),
            archive_label=args.archive_label,
        )
        print(f"Applied sweeper data from {Path(args.source_dir).expanduser()} to {html_path}")
        return 0
    restore_swap(html_path=html_path)
    print(f"Restored archived embedded data in {html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
