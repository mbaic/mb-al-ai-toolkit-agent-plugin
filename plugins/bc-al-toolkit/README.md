# bc-al-toolkit

An Agent Plugins 1.0 package for Business Central AL code review. One skill, one read-only MCP server. You build it once and install it in each client you use.

Source marketplace: `mbaic/mb-al-ai-toolkit-agent-plugin`

## What is inside

| Component | Type | What it does |
|---|---|---|
| `al-code-review` | Skill (`skills/al-code-review/SKILL.md`) | The AL review checklist. |
| `microsoft-learn` | MCP server (`mcp.json`) | Microsoft Learn documentation search, read-only. |

The skill reports findings by severity, each with a location, the problem, why it matters, a recommendation, a confidence level, and the evidence.

Both components are portable Agent Plugins 1.0 types, so any conformant client loads them the same way.

## Boundaries

- **Read-only.** `microsoft-learn` returns published documentation text. It changes nothing.
- **Suggestion-based.** The skill gives findings. It approves and rejects nothing.
- **Approval-based.** Each finding goes through a pull request, human review, and AL-Go.
- **No repository data.** The plugin reads no pull request metadata and no Actions status.
- **No compiler validation.** The plugin gives AL-aware instructions, not build-time checks.

Read-only is not the same as low risk. A review reads your proprietary AL source into the model context.

## Installation

Each client keeps its own copy. An install in one client does not install it in another.

**Copilot app.** **Settings → Plugins → Add marketplace**, enter `mbaic/mb-al-ai-toolkit-agent-plugin`. Then **Install**, enter `bc-al-toolkit@mb-al-ai-toolkit-agent-plugin`. Confirm under **Skills** and **MCP Servers**.

**Copilot CLI.**

```bash
copilot plugin marketplace add mbaic/mb-al-ai-toolkit-agent-plugin
copilot plugin install bc-al-toolkit@mb-al-ai-toolkit-agent-plugin
```

**VS Code.** Register the marketplace in `settings.json`, then install `bc-al-toolkit` from the Extensions view.

```json
"chat.plugins.marketplaces": ["mbaic/mb-al-ai-toolkit-agent-plugin"]
```

## Use it

Ask for an AL review in plain words, for example:

```
Review the AL changes in this branch against main.
```

The skill loads from your request. No slash command or agent name is needed.

## Known limitations

- **`microsoft-learn` is external.** Confirm outbound access to `learn.microsoft.com` from a restricted network.
- **Every client caches the plugin at install time.** No client polls the repository.
- **No AL compiler validation.** Every output still needs the AL-Go pipeline and human review.
- **Organization policy.** If `strictKnownMarketplaces` is set, this repository must be on the allowed list.

## License

MIT.
