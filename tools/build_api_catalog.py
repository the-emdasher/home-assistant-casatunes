#!/usr/bin/env python3
"""Generate a sanitized Markdown catalog from CasaTunes resource documents."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _escape(value: object | None) -> str:
    """Make a value safe for a compact Markdown table cell."""
    if value is None:
        return ""
    return " ".join(str(value).replace("|", "\\|").split())


def _load_resources(source: Path) -> list[dict[str, Any]]:
    resources: list[dict[str, Any]] = []
    for path in sorted(source.glob("*.json")):
        with path.open(encoding="utf-8") as handle:
            document = json.load(handle)
        if (
            not isinstance(document, dict)
            or not {
                "resourcePath",
                "apis",
                "models",
            }
            <= document.keys()
        ):
            continue
        resources.append(document)
    if not resources:
        raise ValueError(f"No JSON resource documents found in {source}")
    return resources


def _render(resources: list[dict[str, Any]]) -> str:
    operation_count = sum(
        len(api.get("operations", []))
        for resource in resources
        for api in resource["apis"]
    )

    lines = [
        "# CasaTunes REST API catalog",
        "",
        (
            f"Generated from {len(resources)} machine-readable resource documents "
            f"containing {operation_count} operations. The server address is "
            "intentionally omitted."
        ),
        "",
        (
            "> Important: CasaTunes supports state-changing operations through GET "
            "requests. Treat method names as documentation, not as a safety boundary."
        ),
        "",
        "## Resource summary",
        "",
        "| Resource | Paths | Operations | Models |",
        "| --- | ---: | ---: | ---: |",
    ]

    for resource in resources:
        operations = sum(len(api.get("operations", [])) for api in resource["apis"])
        lines.append(
            "| {resource} | {paths} | {operations} | {models} |".format(
                resource=_escape(resource["resourcePath"]),
                paths=len(resource["apis"]),
                operations=operations,
                models=len(resource["models"]),
            )
        )

    for resource in resources:
        lines.extend(
            [
                "",
                f"## `{_escape(resource['resourcePath'])}`",
                "",
                "| Method | Path | Summary | Parameters | Response |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for api in resource["apis"]:
            for operation in api.get("operations", []):
                parameters = ", ".join(
                    name
                    for parameter in operation.get("parameters", [])
                    if (name := parameter.get("name", ""))
                )
                row_template = (
                    "| "
                    + " | ".join(
                        (
                            "{method}",
                            "`{path}`",
                            "{summary}",
                            "{parameters}",
                            "`{response}`",
                        )
                    )
                    + " |"
                )
                lines.append(
                    row_template.format(
                        method=_escape(operation.get("httpMethod")),
                        path=_escape(api.get("path")),
                        summary=_escape(
                            operation.get("summary") or operation.get("notes")
                        ),
                        parameters=_escape(parameters),
                        response=_escape(operation.get("responseClass")),
                    )
                )

    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="Directory containing resource JSON")
    parser.add_argument("output", type=Path, help="Markdown file to create")
    args = parser.parse_args()

    resources = _load_resources(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(_render(resources), encoding="utf-8")


if __name__ == "__main__":
    main()
