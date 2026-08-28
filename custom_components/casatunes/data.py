"""Runtime data types for the CasaTunes integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry

from .casatunes_api import CasaTunesClient

if TYPE_CHECKING:
    from .coordinator import CasaTunesCoordinator


@dataclass(slots=True)
class CasaTunesRuntimeData:
    """Data shared by CasaTunes platforms."""

    client: CasaTunesClient
    coordinator: CasaTunesCoordinator


type CasaTunesConfigEntry = ConfigEntry[CasaTunesRuntimeData]
