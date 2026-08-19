#!/usr/bin/env python3
"""Validate the marketplace manifest, the plugin manifest, the MCP server, and the skill.

This repository ships no application code, so this script is what stands in for a
test suite. It is dependency-free on purpose: it parses the small subset of YAML
that a skill's frontmatter actually uses, so it runs on a bare Python 3 with no
pip install, both locally and in CI.

Usage:
    python3 scripts/validate.py

Exits 0 if everything checks out, 1 otherwise. Errors fail the build; warnings do not.
"""

from __future__ import annotations

import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKETPLACE_MANIFEST = os.path.join(".github", "plugin", "marketplace.json")
CHANGELOG = "CHANGELOG.md"

AGENT_PLUGINS_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
MCP_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"

# Agent Plugins 1.0 defines mcp.json as a closed schema. Only these two top-level
# fields are allowed, and both are required.
MCP_TOP_LEVEL_FIELDS = {"$schema", "mcpServers"}

# The transports the specification defines. `http` is not one of them. An unknown
# type value makes the server entry invalid, and a strict client drops the server
# while the skill still loads — the review then runs with no documentation
# grounding and says nothing about it.
MCP_TRANSPORTS = {
    # type: (required fields, optional fields)
    "stdio": ({"command"}, {"args", "env", "cwd"}),
    "streamable-http": ({"url"}, {"headers"}),
    "sse": ({"url"}, {"headers"}),
}

# Client support for `sse` is OPTIONAL in the specification, so a package that
# depends on it is not portable.
MCP_DEPRECATED_TRANSPORTS = {"sse"}

# Fields that mean something in the older Copilot-only plugin format but are not
# portable top-level fields in Agent Plugins 1.0. Declaring them is not a syntax
# error, it is worse: the loader ignores them, so the file reads as if it
# configures something it does not configure.
NON_PORTABLE_PLUGIN_FIELDS = {"agents", "hooks", "mcpServers", "commands", "lsp"}

# Every MCP server this package is allowed to declare, with its endpoint. The
# package's stated boundary is that every server is read-only, so adding one is a
# reviewed decision rather than an edit. A new server fails this check until it is
# added here on purpose. Query strings (for example `?maxTokenBudget=2000`) are
# ignored when comparing.
ALLOWED_MCP_ENDPOINTS = {
    "microsoft-learn": "https://learn.microsoft.com/api/mcp",
}

# Tool names that look plausible but do not exist. Flagged in prose, because a
# skill body that tells the model to use a non-existent tool is just as broken
# as declaring one in frontmatter.
KNOWN_BAD_TOOLS = {"search", "read_file", "write_file", "list_files", "codebase"}

MAX_NAME = 64
MAX_DESCRIPTION = 1024
NAME_PATTERN = re.compile(r"^[a-zA-Z0-9-]+$")
SEMVER_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+([-+][0-9A-Za-z.-]+)?$")

errors: list[str] = []
warnings: list[str] = []


def error(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def parse_frontmatter(path: str) -> tuple[dict, str]:
    """Parse the YAML frontmatter subset a skill file uses.

    Supports `key: value`, block lists (`- item` on following lines), and inline
    JSON-ish lists (`key: [a, b]`). Returns (frontmatter, body).
    """
    with open(path, encoding="utf-8") as handle:
        text = handle.read()

    if not text.startswith("---"):
        return {}, text

    end = text.find("\n---", 3)
    if end == -1:
        return {}, text

    raw = text[3:end].strip("\n")
    body = text[end + 4:]

    data: dict = {}
    current_key: str | None = None

    for line in raw.split("\n"):
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        stripped = line.strip()

        if stripped.startswith("- ") and current_key:
            # `key:` with no inline value parses to None; a following block list
            # must replace that None, not be dropped by setdefault.
            if not isinstance(data.get(current_key), list):
                data[current_key] = []
            data[current_key].append(stripped[2:].strip().strip("\"'"))
            continue

        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", stripped)
        if not match:
            continue

        key, value = match.group(1), match.group(2).strip()
        current_key = key

        if value.startswith("[") and value.endswith("]"):
            items = [v.strip().strip("\"'") for v in value[1:-1].split(",")]
            data[key] = [v for v in items if v]
        elif value:
            data[key] = value.strip("\"'")
        else:
            data[key] = None

    return data, body


def check_name(value: str, label: str) -> None:
    if len(value) > MAX_NAME:
        error(f"{label}: name is {len(value)} chars, limit is {MAX_NAME}")
    if not NAME_PATTERN.match(value):
        error(f"{label}: name {value!r} must contain only letters, numbers, and hyphens")


def check_description(value: str, label: str) -> None:
    if len(value) > MAX_DESCRIPTION:
        error(f"{label}: description is {len(value)} chars, limit is {MAX_DESCRIPTION}")


def check_version(value, label: str) -> None:
    if not isinstance(value, str) or not SEMVER_PATTERN.match(value):
        error(f"{label}: version {value!r} is not a semantic version (expected e.g. 1.0.0)")


def load_json(path: str, label: str):
    if not os.path.isfile(path):
        error(f"{label}: missing file {path}")
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        error(f"{label}: invalid JSON — {exc}")
        return None


def check_body_for_bad_tools(body: str, label: str) -> None:
    """Flag backticked references to non-existent tools in prose."""
    for bad in sorted(KNOWN_BAD_TOOLS):
        if re.search(rf"`{re.escape(bad)}`", body):
            error(
                f"{label}: body references `{bad}`, which is not a Copilot tool name. "
                f"Use a real tool (grep, glob, view, edit, bash) or reword."
            )


def validate_skill(path: str, rel: str) -> str | None:
    front, body = parse_frontmatter(path)
    if not front:
        error(f"{rel}: missing or unparseable YAML frontmatter")
        return None

    name = front.get("name")
    if not name:
        error(f"{rel}: 'name' is required in skill frontmatter")
    else:
        check_name(name, rel)
        folder = os.path.basename(os.path.dirname(path))
        if name != folder:
            # Agent Plugins 1.0 discovers skills by directory. A mismatch means the
            # skill either never loads or loads under a name nothing refers to.
            error(
                f"{rel}: skill name {name!r} does not match its folder {folder!r}. "
                f"They must be identical or the skill will not load."
            )

    description = front.get("description")
    if not description:
        error(f"{rel}: 'description' is required — it is the only signal Copilot uses to select a skill")
    else:
        check_description(description, rel)

    check_body_for_bad_tools(body, rel)
    return name


def validate_mcp(plugin_dir: str, rel_dir: str) -> int:
    """Validate mcp.json, and hold the read-only boundary this package states."""
    path = os.path.join(plugin_dir, "mcp.json")
    rel = f"{rel_dir}/mcp.json"

    if os.path.isfile(os.path.join(plugin_dir, ".mcp.json")):
        error(
            f"{rel_dir}: found '.mcp.json'. Agent Plugins 1.0 reads 'mcp.json', without the leading "
            f"dot. A client reads no MCP server from the dotted name."
        )

    if not os.path.isfile(path):
        warn(f"{rel_dir}: no mcp.json — the plugin declares no MCP server")
        return 0

    config = load_json(path, rel)
    if config is None:
        return 0

    schema = config.get("$schema")
    if schema != MCP_SCHEMA:
        error(
            f"{rel}: '$schema' is required and must be {MCP_SCHEMA!r}. "
            f"Found {schema!r}. Agent Plugins 1.0 defines mcp.json as a closed schema."
        )

    for field in sorted(set(config) - MCP_TOP_LEVEL_FIELDS):
        error(f"{rel}: unknown top-level field {field!r}. Only '$schema' and 'mcpServers' are allowed.")

    servers = config.get("mcpServers")
    if not isinstance(servers, dict) or not servers:
        error(f"{rel}: 'mcpServers' must be a non-empty object")
        return 0

    for name, server in sorted(servers.items()):
        label = f"{rel} → {name}"

        if not isinstance(server, dict):
            error(f"{label}: server entry must be an object")
            continue

        transport = server.get("type")
        if transport not in MCP_TRANSPORTS:
            error(
                f"{label}: type {transport!r} is not a transport that Agent Plugins 1.0 defines. "
                f"Use one of {', '.join(sorted(MCP_TRANSPORTS))}. An unknown type makes the server "
                f"entry invalid, and a strict client drops the server while the skill still loads."
            )
        else:
            if transport in MCP_DEPRECATED_TRANSPORTS:
                warn(f"{label}: client support for {transport!r} is optional, so this server is not portable")

            required, optional = MCP_TRANSPORTS[transport]
            for field in sorted(required - set(server)):
                error(f"{label}: {field!r} is required for transport {transport!r}")
            for field in sorted(set(server) - required - optional - {"type"}):
                error(
                    f"{label}: field {field!r} does not belong to transport {transport!r}. "
                    f"A field of another variant makes the server entry invalid."
                )

        url = server.get("url")

        if name not in ALLOWED_MCP_ENDPOINTS:
            error(
                f"{label}: server is not on the reviewed read-only list. "
                f"This package states that every MCP server is read-only. Review the server, "
                f"then add it to ALLOWED_MCP_ENDPOINTS in scripts/validate.py."
            )
            continue

        expected = ALLOWED_MCP_ENDPOINTS[name]
        if isinstance(url, str) and url.split("?", 1)[0] != expected:
            error(
                f"{label}: url {url!r} does not match the reviewed endpoint {expected!r}. "
                f"A query string such as '?maxTokenBudget=2000' is allowed; a different host or path is not."
            )

    print(f"  mcp.json: {len(servers)} server(s) — {', '.join(sorted(servers))}")
    return len(servers)


def validate_plugin(plugin_dir: str, entry: dict, marketplace_version) -> None:
    rel_dir = os.path.relpath(plugin_dir, REPO_ROOT)
    manifest_path = os.path.join(plugin_dir, "plugin.json")
    label = f"{rel_dir}/plugin.json"
    plugin = load_json(manifest_path, label)
    if plugin is None:
        return

    schema = plugin.get("$schema")
    if not schema:
        error(
            f"{label}: '$schema' is required. Without it the package is read as the older "
            f"Copilot-only format, not as Agent Plugins 1.0. Expected {AGENT_PLUGINS_SCHEMA!r}."
        )
    elif schema != AGENT_PLUGINS_SCHEMA:
        warn(f"{label}: '$schema' is {schema!r}, expected {AGENT_PLUGINS_SCHEMA!r}")

    for field in sorted(NON_PORTABLE_PLUGIN_FIELDS & set(plugin)):
        error(
            f"{label}: {field!r} is not a portable Agent Plugins 1.0 field and is ignored by the loader. "
            f"Skills come from 'skills/' and MCP servers come from 'mcp.json'. Remove the field."
        )

    name = plugin.get("name")
    if not name:
        error(f"{label}: 'name' is required")
    else:
        check_name(name, label)
        if entry.get("name") and entry["name"] != name:
            error(
                f"name drift: marketplace entry says {entry['name']!r}, "
                f"{label} says {name!r}"
            )

    if plugin.get("description"):
        check_description(plugin["description"], label)

    version = plugin.get("version")
    if not version:
        error(f"{label}: 'version' is required")
    else:
        check_version(version, label)

    # The three version fields are what a release is cut against. If they disagree,
    # the release workflow refuses to tag, so catch it here instead of in the release.
    if version and entry.get("version") and entry["version"] != version:
        error(
            f"version drift: marketplace entry says {entry['version']!r}, "
            f"{label} says {version!r}. "
            f"Bump them together, and record it in CHANGELOG.md."
        )
    if version and marketplace_version and marketplace_version != version:
        error(
            f"version drift: marketplace 'metadata.version' says {marketplace_version!r}, "
            f"{label} says {version!r}. Bump them together."
        )

    # Skills — each is a folder containing SKILL.md. This is the one portable
    # component type this package ships; the other, mcp.json, is checked below.
    skills_dir = os.path.join(plugin_dir, "skills")
    skill_names: list[str] = []
    if os.path.isdir(skills_dir):
        for folder in sorted(os.listdir(skills_dir)):
            if not os.path.isdir(os.path.join(skills_dir, folder)):
                continue
            skill_path = os.path.join(skills_dir, folder, "SKILL.md")
            if not os.path.isfile(skill_path):
                error(f"{rel_dir}/skills/{folder}: missing SKILL.md")
                continue
            found = validate_skill(skill_path, os.path.relpath(skill_path, REPO_ROOT))
            if found:
                skill_names.append(found)

    if not skill_names:
        error(f"{rel_dir}: no skill found. A skill is the portable component of this package.")

    duplicates = {n for n in skill_names if skill_names.count(n) > 1}
    for dup in sorted(duplicates):
        error(f"{rel_dir}: duplicate skill name {dup!r} — they dedupe by name, so one shadows the other")

    if not os.path.isfile(os.path.join(plugin_dir, "README.md")):
        warn(f"{rel_dir}: no README.md — the plugin has no install or usage guide of its own")

    print(f"  {name}: {len(skill_names)} skill(s)")
    validate_mcp(plugin_dir, rel_dir)


def check_changelog(version) -> None:
    """Warn when the declared version has no changelog section.

    This is a warning, not an error: the section is often written in the same pull
    request as the bump, and the release workflow fails hard if it is still missing
    at release time.
    """
    if not version or not os.path.isfile(CHANGELOG):
        if not os.path.isfile(CHANGELOG):
            warn(f"{CHANGELOG}: not found — the release workflow reads release notes from it")
        return

    with open(CHANGELOG, encoding="utf-8") as handle:
        text = handle.read()

    if not re.search(rf"^##\s+\[?{re.escape(version)}\]?(?:\s|$)", text, re.M):
        warn(
            f"{CHANGELOG}: no section for version {version}. "
            f"Add '## [{version}] — <date>' before you run the release workflow."
        )


def check_docs_match_artifact() -> None:
    """Fail when the documentation describes an MCP transport the package does not use.

    The package once shipped `"type": "http"` while the READMEs described
    `streamable-http`. Structural validation did not catch it, because each file
    was valid on its own. Only the pair was wrong. This check compares the two
    directly, which is the cheapest form of the test that was missing.
    """
    mcp_path = os.path.join("plugins", "bc-al-toolkit", "mcp.json")
    if not os.path.isfile(mcp_path):
        return

    with open(mcp_path, encoding="utf-8") as handle:
        try:
            servers = json.load(handle).get("mcpServers") or {}
        except json.JSONDecodeError:
            return  # validate_mcp reports the parse error

    transports = {s.get("type") for s in servers.values() if isinstance(s, dict)}

    for doc in ("README.md", os.path.join("plugins", "bc-al-toolkit", "README.md")):
        if not os.path.isfile(doc):
            continue
        with open(doc, encoding="utf-8") as handle:
            text = handle.read()
        for named in MCP_TRANSPORTS:
            quoted = f'"type": "{named}"'
            if quoted in text and named not in transports:
                error(
                    f"{doc}: documents the MCP transport {named!r}, which no server in {mcp_path} "
                    f"declares. The documentation and the package must not disagree."
                )


def main(root: str | None = None) -> int:
    global REPO_ROOT
    if root:
        REPO_ROOT = os.path.abspath(root)
    os.chdir(REPO_ROOT)
    print("Validating marketplace...")

    marketplace = load_json(MARKETPLACE_MANIFEST, MARKETPLACE_MANIFEST)
    if marketplace is None:
        print_report()
        return 1

    market_name = marketplace.get("name")
    if not market_name:
        error(f"{MARKETPLACE_MANIFEST}: 'name' is required")
    else:
        check_name(market_name, MARKETPLACE_MANIFEST)

    if not marketplace.get("owner"):
        error(f"{MARKETPLACE_MANIFEST}: 'owner' is required")

    marketplace_version = (marketplace.get("metadata") or {}).get("version")
    if marketplace_version:
        check_version(marketplace_version, f"{MARKETPLACE_MANIFEST} metadata")

    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        error(f"{MARKETPLACE_MANIFEST}: 'plugins' must be a non-empty array")
        print_report()
        return 1 if errors else 0

    print(f"  marketplace: {market_name} ({len(plugins)} plugin(s))")

    seen: set[str] = set()
    for index, entry in enumerate(plugins):
        label = f"{MARKETPLACE_MANIFEST} plugins[{index}]"

        if not entry.get("name"):
            error(f"{label}: 'name' is required")
        elif entry["name"] in seen:
            error(f"{label}: duplicate plugin name {entry['name']!r}")
        else:
            seen.add(entry["name"])

        if entry.get("description"):
            check_description(entry["description"], label)

        if entry.get("version"):
            check_version(entry["version"], label)

        source = entry.get("source")
        if not source:
            error(f"{label}: 'source' is required")
            continue
        if not isinstance(source, str):
            warn(f"{label}: non-string source not validated by this script")
            continue

        plugin_dir = os.path.normpath(os.path.join(REPO_ROOT, source))
        if not os.path.isdir(plugin_dir):
            error(f"{label}: source {source!r} does not resolve to a directory")
            continue

        validate_plugin(plugin_dir, entry, marketplace_version)

    check_docs_match_artifact()
    check_changelog(marketplace_version)

    print_report()
    return 1 if errors else 0


def print_report() -> None:
    for message in warnings:
        print(f"WARNING: {message}")
    for message in errors:
        print(f"ERROR: {message}")
    print()
    if errors:
        print(f"FAILED — {len(errors)} error(s), {len(warnings)} warning(s)")
    else:
        print(f"OK — no errors, {len(warnings)} warning(s)")


if __name__ == "__main__":
    # An optional path lets the fixture suite in tests/ validate a package other
    # than this repository.
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
