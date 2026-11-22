# `sentinel-proof-mcp` is now [`citebound-mcp`](https://pypi.org/project/citebound-mcp/)

```jsonc
{
  "mcpServers": {
    "citebound": { "command": "uvx", "args": ["citebound-mcp"] }
  }
}
```

The server, its `verify_answer` tool and every argument are unchanged. Only the
package and command names are different.

## Why the name changed

"Sentinel" is Microsoft's SIEM product — which ships its own MCP server, so the
collision was direct — and HashiCorp's policy-as-code framework. **Citebound**
names what the server actually enforces: every claim is bound to the passage it
cites.

## What this package is

A shim that depends on `citebound-mcp` and forwards to it, so an MCP client
still configured with `uvx sentinel-proof-mcp` keeps working. **This is the
final release under this name**; it is not yanked, but it will not be updated.

The registry entry moved too: the server is now `io.github.92kareeem/citebound`.

- **New package**: https://pypi.org/project/citebound-mcp/
- **Source, install guides for every client**: https://github.com/92kareeem/citebound/tree/main/packages/citebound-mcp
- **Try it in the browser**: https://92kareeem.github.io/citebound/
