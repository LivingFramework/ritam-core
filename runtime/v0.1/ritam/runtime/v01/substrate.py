"""
ritam.runtime.v01.substrate
Substrate factory — single entry point for callers.
Session 079.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from .types import SubstrateConfig
from .observation_channel import ObservationChannel
from .admission_gateway import AdmissionGateway
from .contradiction_store import ContradictionStore


class Substrate:
    """
    Construct once; share the three interface instances throughout the application.

    Usage:
        substrate = Substrate(SubstrateConfig(
            storage_path="./data",
            known_categories=["claim", "evidence", "question"]
        ))
        gw = substrate.admission_gateway()
        cs = substrate.contradiction_store()
        oc = substrate.observation_channel()
    """

    def __init__(self, config: SubstrateConfig) -> None:
        storage = Path(config.storage_path)
        storage.mkdir(parents=True, exist_ok=True)
        db_path = storage / "substrate.db"
        self._db = sqlite3.connect(str(db_path), check_same_thread=False)
        self._channel = ObservationChannel()
        self._gateway = AdmissionGateway(config, self._channel, self._db)
        self._store = ContradictionStore(self._db)

    def admission_gateway(self) -> AdmissionGateway:
        return self._gateway

    def contradiction_store(self) -> ContradictionStore:
        return self._store

    def observation_channel(self) -> ObservationChannel:
        return self._channel
