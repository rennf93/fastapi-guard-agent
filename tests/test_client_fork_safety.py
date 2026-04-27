import asyncio
import os
import subprocess
import sys
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from guard_agent.client import GuardAgentHandler
from guard_agent.models import AgentConfig


@pytest.fixture(autouse=True)
def reset_singleton() -> Generator[None, None, None]:
    GuardAgentHandler._instance = None
    GuardAgentHandler._fork_hook_registered = False
    yield
    GuardAgentHandler._instance = None
    GuardAgentHandler._fork_hook_registered = False


@pytest.fixture
def agent_config() -> AgentConfig:
    return AgentConfig(
        api_key="test-api-key",
        endpoint="http://localhost:8000",
        project_id="test-project",
        buffer_size=10,
        flush_interval=1,
        timeout=5,
        retry_attempts=1,
    )


_FORK_CHILD_SCRIPT = """\
import os
import sys

sys.path.insert(0, sys.argv[1])

from guard_agent.client import GuardAgentHandler
from guard_agent.models import AgentConfig

config = AgentConfig(
    api_key="test-api-key",
    endpoint="http://localhost:8000",
    project_id="test-project",
    buffer_size=10,
    flush_interval=1,
    timeout=5,
    retry_attempts=1,
)

parent_handler = GuardAgentHandler(config)
parent_handler._initialized = True

pid_file = sys.argv[2]

pid = os.fork()
if pid == 0:
    try:
        child = GuardAgentHandler(config)
        child_initialized = child._initialized
        with open(pid_file, "w") as f:
            f.write(f"{child_initialized}|{os.getpid()}")
    finally:
        os._exit(0)
else:
    os.waitpid(pid, 0)
"""


@pytest.mark.skipif(
    not hasattr(os, "fork"), reason="fork() unavailable on this platform"
)
def test_singleton_re_initializes_in_forked_child(tmp_path: Path) -> None:
    pid_file = tmp_path / "result.txt"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            _FORK_CHILD_SCRIPT,
            str(Path(__file__).parent.parent),
            str(pid_file),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    text = pid_file.read_text()
    child_initialized_str, child_pid_str = text.split("|")
    assert child_initialized_str == "True", (
        "fork-child re-initializes fully; _initialized ends True after __init__"
    )
    assert int(child_pid_str) != os.getpid()


@pytest.mark.skipif(
    not hasattr(os, "fork"), reason="fork() unavailable on this platform"
)
def test_pid_mismatch_resets_and_reinits(agent_config: AgentConfig) -> None:
    handler = GuardAgentHandler(agent_config)
    handler._initialized = True
    handler._owner_pid = os.getpid() + 1

    new_handler = GuardAgentHandler(agent_config)
    assert new_handler._initialized is True


def test_fork_hook_registered_once(agent_config: AgentConfig) -> None:
    registered_before: bool = GuardAgentHandler._fork_hook_registered
    assert not registered_before
    GuardAgentHandler(agent_config)
    registered_after_first: bool = GuardAgentHandler._fork_hook_registered
    assert registered_after_first
    GuardAgentHandler(agent_config)
    registered_after_second: bool = GuardAgentHandler._fork_hook_registered
    assert registered_after_second


def test_reset_after_fork_noop_when_no_instance() -> None:
    GuardAgentHandler._instance = None
    GuardAgentHandler._reset_after_fork()


@pytest.mark.asyncio
async def test_reset_after_fork_clears_task_attrs(agent_config: AgentConfig) -> None:
    handler = GuardAgentHandler(agent_config)
    t1: asyncio.Task[None] = asyncio.create_task(asyncio.sleep(0))
    t2: asyncio.Task[None] = asyncio.create_task(asyncio.sleep(0))
    t3: asyncio.Task[None] = asyncio.create_task(asyncio.sleep(0))
    handler._flush_task = t1
    handler._status_task = t2
    handler._rules_task = t3

    GuardAgentHandler._reset_after_fork()

    flush_task: asyncio.Task[None] | None = handler._flush_task
    status_task: asyncio.Task[None] | None = handler._status_task
    rules_task: asyncio.Task[None] | None = handler._rules_task
    assert flush_task is None
    assert status_task is None
    assert rules_task is None
    assert handler._initialized is False

    for t in (t1, t2, t3):
        t.cancel()
        try:
            await t
        except asyncio.CancelledError:
            pass


def test_owner_pid_set_on_creation(agent_config: AgentConfig) -> None:
    handler = GuardAgentHandler(agent_config)
    assert handler._owner_pid == os.getpid()


def test_pid_mismatch_clears_tasks_in_new_call(agent_config: AgentConfig) -> None:
    handler = GuardAgentHandler(agent_config)
    handler._initialized = True
    handler._owner_pid = os.getpid() + 999
    handler._flush_task = MagicMock(spec=asyncio.Task)
    handler._status_task = MagicMock(spec=asyncio.Task)
    handler._rules_task = MagicMock(spec=asyncio.Task)

    result = GuardAgentHandler(agent_config)

    assert result._flush_task is None
    assert result._status_task is None
    assert result._rules_task is None


def test_register_fork_hook_skips_when_no_register_at_fork(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delattr(os, "register_at_fork", raising=False)
    GuardAgentHandler._register_fork_hook()
    assert GuardAgentHandler._fork_hook_registered
