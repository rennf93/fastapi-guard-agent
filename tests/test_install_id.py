from __future__ import annotations

from pathlib import Path

from guard_agent.install_id import resolve_install_id


def test_first_call_creates_file(tmp_path: Path) -> None:
    iid = resolve_install_id(state_path=tmp_path / "install-id")
    assert iid is not None
    assert (tmp_path / "install-id").exists()


def test_second_call_returns_same_id(tmp_path: Path) -> None:
    a = resolve_install_id(state_path=tmp_path / "install-id")
    b = resolve_install_id(state_path=tmp_path / "install-id")
    assert a == b


def test_explicit_override_takes_precedence(tmp_path: Path) -> None:
    iid = resolve_install_id(
        state_path=tmp_path / "install-id",
        override="custom-installation-id",
    )
    assert iid == "custom-installation-id"


def test_id_is_uuid4_format(tmp_path: Path) -> None:
    iid = resolve_install_id(state_path=tmp_path / "install-id")
    parts = iid.split("-")
    assert len(parts) == 5
    assert len(iid) == 36
