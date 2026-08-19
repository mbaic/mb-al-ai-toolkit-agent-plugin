#!/usr/bin/env python3
"""Test scripts/validate.py against packages that carry one deliberate defect each.

The validator stands in for a test suite in this repository, so the validator
itself needs one. Testing only the real package tests the happy path, and the
happy path is not where a manifest repository fails.

Each case below is a real failure this package has met or could meet, and every
one of them is silent at runtime: the client loads what it can, skips what it
cannot read, and reports nothing. The `mcp_http` case is the defect that shipped
in version 1.0.0.

Each case is built in a temporary directory from the live plugin, so a version
bump or a new component never makes these tests stale.

Usage:
    python3 tests/run.py

Exits 0 when every case gives the expected verdict, 1 otherwise.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)
PLUGIN_SRC = os.path.join(REPO_ROOT, "plugins", "bc-al-toolkit")
VALIDATOR = os.path.join(REPO_ROOT, "scripts", "validate.py")

MCP_REL = os.path.join("plugins", "bc-al-toolkit", "mcp.json")
MARKET_REL = os.path.join(".github", "plugin", "marketplace.json")


def write(base: str, rel: str, text: str) -> None:
    with open(os.path.join(base, rel), "w", encoding="utf-8") as handle:
        handle.write(text)


def edit_json(base: str, rel: str, mutate) -> None:
    path = os.path.join(base, rel)
    with open(path, encoding="utf-8") as handle:
        doc = json.load(handle)
    mutate(doc)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(doc, handle, indent=2)


# ---------------------------------------------------------------- the defects

def mcp_no_schema(base):
    edit_json(base, MCP_REL, lambda d: d.pop("$schema", None))


def mcp_http(base):
    edit_json(base, MCP_REL, lambda d: d["mcpServers"]["microsoft-learn"].update(type="http"))


def mcp_top_level_field(base):
    edit_json(base, MCP_REL, lambda d: d.update(servers={}))


def mcp_wrong_variant_field(base):
    edit_json(base, MCP_REL, lambda d: d["mcpServers"]["microsoft-learn"].update(command="node"))


def mcp_unreviewed_server(base):
    edit_json(
        base,
        MCP_REL,
        lambda d: d["mcpServers"].update(
            {"some-other": {"type": "streamable-http", "url": "https://example.invalid/mcp"}}
        ),
    )


def skill_name_mismatch(base):
    skills = os.path.join(base, "plugins", "bc-al-toolkit", "skills")
    os.rename(os.path.join(skills, "al-code-review"), os.path.join(skills, "al-review"))


def version_drift(base):
    edit_json(base, MARKET_REL, lambda d: d["plugins"][0].update(version="9.9.9"))


def docs_disagree(base):
    write(base, "README.md", '# Fixture\n\nThe transport is `"type": "sse"`.\n')


CASES = [
    (mcp_no_schema, "mcp.json declares no $schema"),
    (mcp_http, "mcp.json uses transport 'http', which the specification does not define"),
    (mcp_top_level_field, "mcp.json declares a top-level field outside the closed schema"),
    (mcp_wrong_variant_field, "an http server declares 'command', which belongs to stdio"),
    (mcp_unreviewed_server, "an MCP server is not on the reviewed read-only list"),
    (skill_name_mismatch, "a skill folder name differs from the name in its frontmatter"),
    (version_drift, "the marketplace and plugin versions disagree"),
    (docs_disagree, "the documentation names a transport the package does not use"),
]


def build(tmp: str, name: str) -> str:
    """Copy the live plugin into a self-contained one-plugin marketplace."""
    base = os.path.join(tmp, name)
    os.makedirs(os.path.join(base, ".github", "plugin"))
    shutil.copytree(PLUGIN_SRC, os.path.join(base, "plugins", "bc-al-toolkit"))

    with open(os.path.join(PLUGIN_SRC, "plugin.json"), encoding="utf-8") as handle:
        version = json.load(handle)["version"]

    market = {
        "name": "fixture-marketplace",
        "owner": {"name": "Fixture"},
        "metadata": {"description": "Built by tests/run.py.", "version": version},
        "plugins": [
            {
                "name": "bc-al-toolkit",
                "description": "Built by tests/run.py.",
                "version": version,
                "source": "./plugins/bc-al-toolkit",
            }
        ],
    }
    with open(os.path.join(base, MARKET_REL), "w", encoding="utf-8") as handle:
        json.dump(market, handle, indent=2)

    write(base, "README.md", "# Fixture\n")
    write(base, "CHANGELOG.md", f"# Changelog\n\n## [{version}] — 2026-08-15\n\nFixture.\n")
    return base


def verdict(base: str) -> int:
    return subprocess.run(
        [sys.executable, VALIDATOR, base], capture_output=True, text=True
    ).returncode


def main() -> int:
    failures = 0

    with tempfile.TemporaryDirectory() as tmp:
        if verdict(build(tmp, "valid")) == 0:
            print("  ok   valid — the reference package validates")
        else:
            failures += 1
            print("  FAIL valid — the reference package does not validate")

        for defect, description in CASES:
            base = build(tmp, defect.__name__)
            defect(base)
            if verdict(base) == 0:
                failures += 1
                print(f"  FAIL {defect.__name__} — accepted a package where {description}")
            else:
                print(f"  ok   {defect.__name__} — rejected: {description}")

    total = len(CASES) + 1
    print()
    if failures:
        print(f"FAILED — {failures} of {total} case(s) gave the wrong verdict")
        return 1
    print(f"OK — {total} cases, each with the expected verdict")
    return 0


if __name__ == "__main__":
    sys.exit(main())
