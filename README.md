# mb-al-ai-toolkit-agent-plugin

An Agent Plugins 1.0 marketplace for Microsoft Dynamics 365 Business Central AL code review.

The repository publishes one plugin, `bc-al-toolkit`. You build it once, and the Copilot clients read the same package.

The scope stays small on purpose: one plugin, one skill, one MCP server. It is a hobby project, and a small scope keeps it one.

## The plugin

| Component | Type | What it does |
|---|---|---|
| `al-code-review` | Skill (`skills/al-code-review/SKILL.md`) | The AL review checklist: data access, object structure, events, permissions, tests, upgrade code. |
| `microsoft-learn` | MCP server (`mcp.json`) | Public Microsoft Learn documentation, read-only and unauthenticated. |

Both are portable Agent Plugins 1.0 components — the only two types the standard defines. Any conformant client loads them the same way, from the file tree, with no per-client setup.

```
mb-al-ai-toolkit-agent-plugin/
├── .github/plugin/marketplace.json
├── plugins/bc-al-toolkit/
│   ├── plugin.json                     Agent Plugins 1.0 $schema
│   ├── mcp.json
│   └── skills/al-code-review/SKILL.md
└── scripts/validate.py
```

The `source` of each marketplace entry is a repository-root path, so the plugin sits in `plugins/<plugin-name>/`.

## Boundaries

- **Read-only.** `microsoft-learn` returns documentation text. Nothing here writes to a repository, triggers a workflow, or changes Business Central data.
- **Suggestion-based.** The skill gives findings. It approves and rejects nothing.
- **Approval-based.** Each finding goes through a pull request, human review, and your AL-Go pipeline.
- **No repository data.** The plugin reads no pull request metadata and no Actions status.
- **No compiler validation.** The plugin gives AL-aware instructions, not build-time checks.

Read-only is not the same as low risk. The skill reads your proprietary AL source, and that source enters the model context. Confirm your own data policy before a team adopts this.

## Installation

The marketplace address is the same in all three clients. Each client keeps its own copy, so each one needs its own install and its own update.

**Copilot app.** **Settings → Plugins → Add marketplace**, enter `mbaic/mb-al-ai-toolkit-agent-plugin`. Then **Install**, enter `bc-al-toolkit@mb-al-ai-toolkit-agent-plugin`. Confirm under **Skills** and **MCP Servers**.

**Copilot CLI.**

```bash
copilot plugin marketplace add mbaic/mb-al-ai-toolkit-agent-plugin
copilot plugin install bc-al-toolkit@mb-al-ai-toolkit-agent-plugin
```

**VS Code Copilot Chat.** Add the marketplace to `settings.json`, then install `bc-al-toolkit` from the Extensions view.

```json
"chat.plugins.marketplaces": ["mbaic/mb-al-ai-toolkit-agent-plugin"]
```

Ask for an AL review in plain words, in any client. The skill loads from your request.

For a team, an administrator sets `managed-settings.json` once for all three clients: `extraKnownMarketplaces` adds this repository, `enabledPlugins` turns on `bc-al-toolkit`, and `strictKnownMarketplaces`, if set, must include this repository.

| Client | Update |
|---|---|
| Copilot app | Reinstall from **Settings → Plugins** |
| Copilot CLI | `copilot plugin update bc-al-toolkit` |
| VS Code | **Extensions: Check for Extension Updates** |

## Validation

The repository ships no application code, so `scripts/validate.py` stands in for a test suite. It checks what fails silently rather than loudly:

```bash
python3 scripts/validate.py
```

- `plugin.json` declares the Agent Plugins 1.0 `$schema` and no field the loader ignores.
- `mcp.json` declares a transport the standard defines. An unknown one such as `http` drops the server in silence while the skill still loads.
- The MCP server is on the reviewed read-only list, so a new one needs a deliberate edit.
- The skill name equals its folder name, because a skill loads by directory.
- All three version fields agree.

`python3 tests/run.py` tests the validator against broken copies of the plugin. Both run in CI.

[`evals/`](evals/) answers a different question: not whether the package loads, but whether the review is any good.

## Releases

Semantic versioning. Record every user-visible change in [CHANGELOG.md](CHANGELOG.md).

Cut a release from **Actions → Release → Run workflow** with the version, no leading `v`. The workflow refuses to tag when the manifests fail validation, the version fields disagree, or the changelog has no section for the version.

A tag is not an installation boundary. Clients install from `main`.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Marketplace not found | Not registered, or the name is wrong | Run `copilot plugin marketplace list` |
| Plugin missing after install | `source` path in `marketplace.json` is wrong | Make it relative to the repository root |
| Skill does not load | `name` in `SKILL.md` differs from the folder name | Make them identical, kebab-case |
| MCP server missing | Not `mcp.json` at the plugin root, or the transport is wrong | Run the validator |
| Changes have no effect | The client cache holds old content | Reinstall, or run the update command |
| Organization blocks the marketplace | `strictKnownMarketplaces` is set | Ask an administrator to add this repository |

To cap lookup cost, add `?maxTokenBudget=2000` to the `microsoft-learn` URL in `mcp.json`.

## Contributing

Run `python3 scripts/validate.py` before you open a pull request. The output must end with `OK — no errors`. Record every user-visible change in `CHANGELOG.md`.

Keep documentation short and use ASD-STE100 Simplified Technical English: short sentences, one instruction per sentence, active voice, plain words.

## License

MIT. See [LICENSE](LICENSE).
