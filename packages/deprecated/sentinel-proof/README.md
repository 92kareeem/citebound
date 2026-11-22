# `sentinel-proof` is now [`citebound`](https://pypi.org/project/citebound/)

```bash
pip uninstall sentinel-proof
pip install citebound
```

```diff
- from sentinel_proof import verify, from_langchain
+ from citebound import verify, from_langchain
```

Nothing else changes. Same API, same author, same Apache-2.0 licence, same
zero dependencies. Only the import path and the command name are different.

## Why the name changed

"Sentinel" is Microsoft's SIEM product and HashiCorp's policy-as-code
framework. Both are established names in security and developer tooling, and
the second one is close enough in purpose to be genuinely confusing. A library
nobody can find is a library nobody can use.

**Citebound** names what the library actually enforces: every claim is bound to
the passage it cites. Nothing more is promised, which is the point.

## What this package is

A shim. It depends on `citebound` and re-exports every public name from it, so
code pinned to `sentinel-proof` keeps working and keeps getting the real
implementation. It adds no behaviour of its own and emits a `DeprecationWarning`
on import. `sentinel_proof.CITEBOUND_VERSION` tells you which `citebound`
version is actually answering.

**This is the final release under this name.** Fixes, new guards and new
releases all happen in `citebound`. This package is not yanked, because pinning
to a yanked release breaks installs for people who did nothing wrong — but it
will not be updated again.

- **New package**: https://pypi.org/project/citebound/
- **Source and docs**: https://github.com/92kareeem/citebound
- **MCP server**: `citebound-mcp` (was `sentinel-proof-mcp`)
- **Try it in the browser**: https://92kareeem.github.io/citebound/
