"""
ritam.runtime.v01.observation_channel
ObservationChannel stub for v0.1.
Buffers signals in-memory; supports drain() for test use.
Full push-subscription implementation deferred to Session 080.
Session 079.
"""
from __future__ import annotations

import uuid
from typing import Callable

from .types import SubstrateSignal, SignalType


SignalHandler = Callable[[SubstrateSignal], None]


class ObservationChannel:
    """
    Signal bus stub. Buffers all emitted signals in a list.
    drain() returns and clears the buffer.

    Invariants upheld even in stub form:
    - I5: all repair/decay events will emit signals (decay not yet wired; stubs emit nothing extra).
    - I8: all quarantine events emit signals (wired in AdmissionGateway).
    - A-list #7: all OBSERVATION_GAP events emit signals (wired in AdmissionGateway).
    - Subscriber errors do NOT suppress emission to other subscribers.
    """

    def __init__(self) -> None:
        self._buffer: list[SubstrateSignal] = []
        self._subscribers: dict[str, SignalHandler] = {}

    # ------------------------------------------------------------------
    # Internal: called by AdmissionGateway and other substrate components
    # ------------------------------------------------------------------

    def emit(self, signal: SubstrateSignal) -> None:
        """Buffer the signal and dispatch to all subscribers."""
        self._buffer.append(signal)
        for sub_id, handler in list(self._subscribers.items()):
            try:
                handler(signal)
            except Exception:
                # Subscriber errors must not suppress emission (Appendix B invariant)
                pass

    # ------------------------------------------------------------------
    # Public API (from API_SPEC.md §3)
    # ------------------------------------------------------------------

    def subscribe(self, handler: SignalHandler) -> str:
        sub_id = str(uuid.uuid4())
        self._subscribers[sub_id] = handler
        return sub_id

    def unsubscribe(self, subscription_id: str) -> None:
        self._subscribers.pop(subscription_id, None)

    def drain(self) -> list[SubstrateSignal]:
        """Return all buffered signals and clear the buffer."""
        signals = list(self._buffer)
        self._buffer.clear()
        return signals
