"""The MCP shim must forward to the renamed server, and must not break stdio."""

import io
import warnings
from contextlib import redirect_stdout

import citebound_mcp
import pytest
import sentinel_proof_mcp
from sentinel_proof_mcp import __main__ as entry


def test_importing_the_old_name_warns_and_points_at_the_new_one():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        import importlib

        importlib.reload(sentinel_proof_mcp)
    messages = [str(w.message) for w in caught if w.category is DeprecationWarning]
    assert messages, "importing the renamed package must warn"
    assert "citebound-mcp" in messages[0]


def test_the_server_builder_is_the_renamed_one_itself():
    assert sentinel_proof_mcp.build_server is citebound_mcp.server.build_server


def test_the_shim_reports_both_its_own_version_and_the_real_one():
    assert sentinel_proof_mcp.__version__ == "0.1.3"
    installed = citebound_mcp.__version__
    assert installed == sentinel_proof_mcp.CITEBOUND_MCP_VERSION


def test_the_rename_notice_never_touches_stdout(capsys):
    """stdout is the MCP transport. A stray line there corrupts the session."""
    captured = io.StringIO()
    with redirect_stdout(captured), pytest.raises(SystemExit):
        entry.main(["--version"])
    err = capsys.readouterr().err
    assert "citebound-mcp" in err
    # argparse prints --version to stdout; the notice must not be there with it.
    assert "note:" not in captured.getvalue()
