"""Every Grid wait in a run draws from one allowance."""

from __future__ import annotations

import json
from typing import Any

import pytest

from poppy_orchestrator.clients import grid_clients
from poppy_orchestrator.clients.grid_clients import GridHospitalCredClient, PullBudget
from poppy_orchestrator.contracts.claims import ClaimRequest, ProviderRef
from poppy_orchestrator.grid.fake_grid import FakeAgentGrid


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock(monkeypatch) -> Clock:
    fake = Clock()
    monkeypatch.setattr(grid_clients.time, "monotonic", fake)
    return fake


def test_a_wait_is_capped_by_the_per_message_limit(clock: Clock) -> None:
    budget = PullBudget(per_message=120, total=240)

    assert budget() == 120


def test_later_waits_only_get_what_is_left(clock: Clock) -> None:
    budget = PullBudget(per_message=120, total=240)

    clock.now += 200

    assert budget() == 40


def test_a_spent_budget_checks_once_and_does_not_wait(clock: Clock) -> None:
    budget = PullBudget(per_message=120, total=240)

    clock.now += 500

    assert budget() == 0


def test_three_full_waits_stay_under_the_task_limit(clock: Clock) -> None:
    budget = PullBudget(per_message=120, total=240)
    waited = 0.0

    for _ in range(3):
        wait = budget()
        waited += wait
        clock.now += wait

    assert waited == 240
    assert waited < 300


class RecordingGrid(FakeAgentGrid):
    def __init__(self) -> None:
        super().__init__()
        self.timeouts: list[float] = []

    def _pull_messages(self, message_ids: list[str], timeout: float = 0.0) -> dict[str, Any]:
        self.timeouts.append(timeout)
        return super()._pull_messages(message_ids, timeout)


def test_client_asks_the_budget_at_the_moment_it_waits(clock: Clock) -> None:
    grid = RecordingGrid()
    client = GridHospitalCredClient(grid, pull_timeout=PullBudget(per_message=120, total=240))
    request = ClaimRequest(
        request_id="hosp-1",
        provider=ProviderRef("SYNTH-NPI-1999999999", "SYNTH-NETWORK-X"),
        claim_types=("work_history_complete",),
        source_node="HospitalCred",
    )

    client.request_claims(request)
    clock.now += 230
    client.request_claims(request)

    assert grid.timeouts == [120, 10]
    assert json.dumps(grid.timeouts)
