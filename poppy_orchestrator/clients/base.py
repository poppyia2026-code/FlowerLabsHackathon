"""Abstract SuperNode claim client."""

from __future__ import annotations

from abc import ABC, abstractmethod

from poppy_orchestrator.contracts.claims import ClaimRequest, ClaimResponse


class SuperNodeClaimClient(ABC):
    """Interface every node client must implement.

    Real implementations talk to SuperGrid / SuperNode connectors.
    Stubs read fixtures for local dry-run without credentials.
    """

    node_name: str

    @abstractmethod
    def request_claims(self, request: ClaimRequest) -> ClaimResponse:
        """Request typed claims. Must not return raw credential files."""
        raise NotImplementedError
