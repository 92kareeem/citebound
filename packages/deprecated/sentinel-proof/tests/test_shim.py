"""The shim must forward, not reimplement, and must say it is deprecated."""

import warnings

import citebound
import pytest
import sentinel_proof
from sentinel_proof import cli


def test_importing_the_old_name_warns_and_points_at_the_new_one():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        import importlib

        importlib.reload(sentinel_proof)
    messages = [str(w.message) for w in caught if w.category is DeprecationWarning]
    assert messages, "importing the renamed package must warn"
    assert "citebound" in messages[0]


def test_every_public_name_is_the_citebound_object_itself():
    """Not a copy, not a wrapper: the same object, so behaviour cannot drift."""
    forwarded = [n for n in sentinel_proof.__all__ if n not in {"__version__", "CITEBOUND_VERSION"}]
    assert len(forwarded) > 15, "the shim should cover the whole public surface"
    for name in forwarded:
        assert getattr(sentinel_proof, name) is getattr(citebound, name), name


def test_the_shim_reports_both_its_own_version_and_the_real_one():
    assert sentinel_proof.__version__ == "0.1.3"
    installed = citebound.__version__
    assert installed == sentinel_proof.CITEBOUND_VERSION


def test_verification_still_works_through_the_old_import_path():
    passages = sentinel_proof.passages_from_texts(["Refunds are available within 30 days."])
    good = sentinel_proof.verify("Refunds take 30 days [1].", passages, citation_style="numeric")
    bad = sentinel_proof.verify("Refunds take 90 days [1].", passages, citation_style="numeric")
    assert good.ok
    assert not bad.ok


def test_the_old_command_still_runs(capsys):
    with pytest.raises(SystemExit):
        cli.main(["--help"])
    assert "citebound" in capsys.readouterr().err
