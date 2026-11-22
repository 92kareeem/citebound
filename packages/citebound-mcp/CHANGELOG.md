# Changelog

All notable changes to `citebound-mcp`. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.0] - 2026-11-22

### Changed

- **Renamed: `sentinel-proof-mcp` is now `citebound-mcp`.** Point MCP clients
  at `uvx citebound-mcp`. The server, its `verify_answer` tool and every
  argument are unchanged. "Sentinel" collides with Microsoft Sentinel, which
  ships its own MCP server, so the collision was direct.
- The registry entry is now `io.github.92kareeem/citebound`. Registry versions
  are immutable, so the old `io.github.92kareeem/sentinel-proof` entry remains
  published and points at this one.
- `sentinel-proof-mcp` 0.1.3 is a final shim release that forwards to this
  package, so an MCP client still configured with the old command keeps
  working. It is deprecated, not yanked, and receives no further releases.
- Requires `citebound>=0.2.0`.

## [0.1.2] - 2026-11-16

Documentation and CI only; the server is unchanged.

### Added

- `compat/`: one script per agent framework (OpenAI Agents SDK, Pydantic AI,
  LangChain/LangGraph) that launches the installed server through that
  framework's MCP client and verifies an answer. A nightly workflow runs them
  against the latest release of each framework and of this package, plus the
  official MCP Inspector as a reference client.

### Changed

- README install section covers every client: one-click links for Cursor and
  VS Code, `claude`/`codex`/`gemini` CLI commands, the standard `mcpServers`
  block with a table of where it goes per client, HTTP for remote clients,
  and the framework snippets above. (Written for 0.1.1 but merged after its
  tag, so it ships here.)

## [0.1.1] - 2026-11-16

Documentation and metadata only; the server is unchanged.

### Changed

- README leads with the problem, adds "use it when", a comparison with other
  ways to check an answer from an MCP agent, and a FAQ.
- PyPI description and keywords name the clients and the problem.
- The README's JSON example is pinned by a test to the tool's real output.

## [0.1.0] - 2026-11-16

First release.

### Added

- `verify_answer` tool: checks a drafted answer against its passages with the
  `citebound` grounding gate and returns the verdict as structured JSON
  with per-claim detail, a one-line `summary` and the `safe_text` to show.
  Passages as strings or objects; numeric or tag citations; question-aware;
  configurable strip limit. Read-only, idempotent, no network.
- `cite_for_verification` prompt: how to draft so every sentence is checkable.
- `citebound://about` resource.
- `citebound-mcp` command: stdio by default, `--transport streamable-http`
  for HTTP.
