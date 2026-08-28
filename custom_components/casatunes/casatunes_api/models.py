"""Typed models returned by CasaTunes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Self

from .enums import (
    ControllerFeature,
    MediaItemFlag,
    PlayerControl,
    SourceControlType,
    SourceKind,
)
from .exceptions import CasaTunesResponseError


def _required_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise CasaTunesResponseError(f"Response is missing string field {key}")
    return value


def _optional_string(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise CasaTunesResponseError(f"Response field {key} is not a string or null")
    return value


def _integer(data: dict[str, Any], key: str, default: int = 0) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise CasaTunesResponseError(f"Response field {key} is not an integer")
    return value


def _number(data: dict[str, Any], key: str, default: float = 0) -> float:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise CasaTunesResponseError(f"Response field {key} is not a number")
    return float(value)


def _string_tuple(data: dict[str, Any], key: str) -> tuple[str, ...]:
    value = data.get(key) or []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise CasaTunesResponseError(f"Response field {key} is not a string list")
    return tuple(value)


@dataclass(frozen=True, slots=True)
class SettingsRange:
    """A numeric range advertised by CasaTunes."""

    minimum: int
    maximum: int
    increment: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            minimum=_integer(data, "Minimum"),
            maximum=_integer(data, "Maximum"),
            increment=_integer(data, "Increment", 1),
        )


@dataclass(frozen=True, slots=True)
class SystemInfo:
    """CasaTunes server identity and global capabilities."""

    app_name: str
    host_name: str
    mac_address: str
    casatunes_version: str
    rest_services_version: str
    is_license_valid: bool
    is_system_sleep_enabled: bool
    is_password_required: bool
    is_settings_password_required: bool
    volume_settings: SettingsRange
    eq_settings: SettingsRange
    matrix_count: int
    controller_features: ControllerFeature

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            app_name=_required_string(data, "AppName"),
            host_name=_required_string(data, "HostName"),
            mac_address=_required_string(data, "MACAddress"),
            casatunes_version=_required_string(data, "CasaTunesVersion"),
            rest_services_version=_required_string(data, "RESTServicesVersion"),
            is_license_valid=bool(data.get("IsLicenseValid", False)),
            is_system_sleep_enabled=bool(data.get("IsSystemSleepEnabled", False)),
            is_password_required=bool(data.get("IsPasswordRequired", False)),
            is_settings_password_required=bool(
                data.get("IsSettingsPasswordRequired", False)
            ),
            volume_settings=SettingsRange.from_dict(data.get("VolumeSettings", {})),
            eq_settings=SettingsRange.from_dict(data.get("EQSettings", {})),
            matrix_count=len(data.get("MatrixInfo") or []),
            controller_features=ControllerFeature(_integer(data, "ControllerFeatures")),
        )


@dataclass(frozen=True, slots=True)
class ZoneCapabilities:
    """Advanced controls advertised for one CasaTunes zone."""

    can_hide: bool
    exclude_from_power_all_zones: bool
    balance: bool
    eq: bool
    eq_presets: bool
    loudness: bool
    stereo_or_mono: bool
    absolute_volume: bool
    power_on_volume: int
    max_volume: bool
    mute_page_volume: int
    fixed_volume: int
    rename_zone: bool
    add_remove_zones: bool
    balance_settings: SettingsRange
    eq_settings: SettingsRange
    allow_room_group_assigned_to_keypad: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            can_hide=bool(data.get("Hide", False)),
            exclude_from_power_all_zones=bool(
                data.get("ExcludeFromPowerAllZones", False)
            ),
            balance=bool(data.get("Balance", False)),
            eq=bool(data.get("EQ", False)),
            eq_presets=bool(data.get("EQPresets", False)),
            loudness=bool(data.get("Loudness", False)),
            stereo_or_mono=bool(data.get("StereoOrMono", False)),
            absolute_volume=bool(data.get("AbsoluteVolume", False)),
            power_on_volume=_integer(data, "PowerOnVolume"),
            max_volume=bool(data.get("MaxVolume", False)),
            mute_page_volume=_integer(data, "MutePageVolume"),
            fixed_volume=_integer(data, "FixedVolume"),
            rename_zone=bool(data.get("RenameZone", False)),
            add_remove_zones=bool(data.get("AddRemoveZones", False)),
            balance_settings=SettingsRange.from_dict(data.get("BalanceSettings") or {}),
            eq_settings=SettingsRange.from_dict(data.get("EQSettings") or {}),
            allow_room_group_assigned_to_keypad=bool(
                data.get("AllowRoomGroupAssignedToKeypad", False)
            ),
        )


@dataclass(frozen=True, slots=True)
class Zone:
    """A CasaTunes room, speaker, or room group."""

    zone_id: int
    persistent_zone_id: str
    name: str
    hidden: bool
    power: bool
    mute: bool
    volume: int
    max_volume: int
    source_id: int
    enabled_sources: int
    volume_control_type: int
    fixed_volume_enabled: bool
    fixed_volume: int
    page_volume: int
    power_on_volume: int
    reset_power_on_volume: bool
    shared: bool
    shared_room_id: str | None
    group_name: str
    group_info: tuple[dict[str, Any], ...]
    sleep_enabled: bool
    hide_power_control: bool
    hide_source_control: bool
    hide_dnd_control: bool
    dnd: bool
    keypad_lock: bool
    loudness: bool
    balance: int
    bass: int
    treble: int
    eq_id: str
    low_pass_filter_supported: bool
    low_pass_filter_enabled: bool
    low_pass_filter: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        group_info = data.get("ZoneGroupInfo") or []
        if not isinstance(group_info, list) or not all(
            isinstance(item, dict) for item in group_info
        ):
            raise CasaTunesResponseError(
                "Response field ZoneGroupInfo is not a list of objects"
            )
        return cls(
            zone_id=_integer(data, "ZoneID"),
            persistent_zone_id=_required_string(data, "PersistentZoneID"),
            name=_required_string(data, "Name"),
            hidden=bool(data.get("Hidden", False)),
            power=bool(data.get("Power", False)),
            mute=bool(data.get("Mute", False)),
            volume=_integer(data, "Volume"),
            max_volume=_integer(data, "MaxVolume", 100),
            source_id=_integer(data, "SourceID"),
            enabled_sources=_integer(data, "EnabledSources"),
            volume_control_type=_integer(data, "VolumeControlType"),
            fixed_volume_enabled=bool(data.get("FixedVolumeEnabled", False)),
            fixed_volume=_integer(data, "FixedVolume", 100),
            page_volume=_integer(data, "PageVolume"),
            power_on_volume=_integer(data, "PowerOnVolume"),
            reset_power_on_volume=bool(data.get("ResetPowerOnVolume", False)),
            shared=bool(data.get("Shared", False)),
            shared_room_id=_optional_string(data, "SharedRoomID"),
            group_name=str(data.get("GroupName") or data.get("Name") or ""),
            group_info=tuple(group_info),
            sleep_enabled=bool(data.get("SleepEnabled", False)),
            hide_power_control=bool(data.get("HidePowerControl", False)),
            hide_source_control=bool(data.get("HideSourceControl", False)),
            hide_dnd_control=bool(data.get("HideDNDControl", False)),
            dnd=bool(data.get("DND", False)),
            keypad_lock=bool(data.get("KeypadLock", False)),
            loudness=bool(data.get("Loudness", False)),
            balance=_integer(data, "Balance"),
            bass=_integer(data, "Bass"),
            treble=_integer(data, "Treble"),
            eq_id=str(data.get("EqID") or ""),
            low_pass_filter_supported=bool(data.get("LowPassFilterSupported", False)),
            low_pass_filter_enabled=bool(data.get("LowPassFilterEnabled", False)),
            low_pass_filter=_integer(data, "LowPassFilter"),
        )

    def supports_source(self, source_id: int) -> bool:
        """Return whether a source bit is enabled for this zone."""
        return source_id >= 0 and bool(self.enabled_sources & (1 << source_id))


@dataclass(frozen=True, slots=True)
class Source:
    """A CasaTunes physical input or media-player source."""

    source_id: int
    name: str
    hidden: bool
    is_shared: bool
    media_types_supported: int
    source_kind: SourceKind | int
    control_type: SourceControlType

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        raw_source_kind = _integer(data, "SourceType")
        try:
            source_kind: SourceKind | int = SourceKind(raw_source_kind)
        except ValueError:
            source_kind = raw_source_kind
        return cls(
            source_id=_integer(data, "SourceID"),
            name=_required_string(data, "Name"),
            hidden=bool(data.get("Hidden", False)),
            is_shared=bool(data.get("IsShared", False)),
            media_types_supported=_integer(data, "MediaTypesSupported"),
            source_kind=source_kind,
            control_type=SourceControlType(_integer(data, "Type")),
        )


@dataclass(frozen=True, slots=True)
class MediaItem:
    """Current or queued media metadata."""

    id: str
    persistent_id: str
    title: str
    album: str
    artists: str
    artwork_uri: str
    duration: float | None
    media_type: int
    service_name: str
    flags: MediaItemFlag
    queue_type: str
    group_name: str
    details: str
    description: str
    artwork_ratio: float
    total_items: int
    display_info: tuple[str, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        duration = data.get("Duration")
        if isinstance(duration, bool) or not isinstance(duration, int | float):
            duration = None
        return cls(
            id=str(data.get("ID") or ""),
            persistent_id=str(data.get("PersistentID") or ""),
            title=str(data.get("Title") or ""),
            album=str(data.get("Album") or ""),
            artists=str(data.get("Artists") or ""),
            artwork_uri=str(data.get("ArtworkURI") or ""),
            duration=float(duration) if duration is not None else None,
            media_type=_integer(data, "Type"),
            service_name=str(data.get("ServiceName") or ""),
            flags=MediaItemFlag(_integer(data, "Flags")),
            queue_type=str(data.get("QueueType") or ""),
            group_name=str(data.get("GroupName") or ""),
            details=str(data.get("Details") or ""),
            description=str(data.get("Description") or ""),
            artwork_ratio=_number(data, "ArtworkRatio"),
            total_items=_integer(data, "TotalItems", -1),
            display_info=_string_tuple(data, "DisplayInfo"),
        )

    @property
    def can_expand(self) -> bool:
        """Return whether the item represents a browsable collection."""
        return bool(
            self.flags
            & (MediaItemFlag.MEDIA_COLLECTION | MediaItemFlag.GROUPED_COLLECTION)
        )

    @property
    def can_play(self) -> bool:
        """Return whether CasaTunes advertises the item as playable/queueable."""
        return bool(
            self.flags
            & (
                MediaItemFlag.TRACK
                | MediaItemFlag.STREAM
                | MediaItemFlag.STATION
                | MediaItemFlag.PLAYLIST
                | MediaItemFlag.ALLOW_ADD_TO_QUEUE
            )
        )


@dataclass(frozen=True, slots=True)
class MediaCollection:
    """A CasaTunes media collection and one page of its children."""

    id: str
    persistent_id: str
    title: str
    flags: MediaItemFlag
    queue_type: str
    artwork_uri: str
    artwork_ratio: float
    search_placeholder_text: str
    start_index: int
    total_available: int
    media_items: tuple[MediaItem, ...]
    display_info: tuple[str, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        media_items = data.get("MediaItems") or []
        if not isinstance(media_items, list) or not all(
            isinstance(item, dict) for item in media_items
        ):
            raise CasaTunesResponseError("Response field MediaItems is not a list")
        return cls(
            id=str(data.get("ID") or ""),
            persistent_id=str(data.get("PersistentID") or ""),
            title=str(data.get("Title") or ""),
            flags=MediaItemFlag(_integer(data, "Flags")),
            queue_type=str(data.get("QueueType") or ""),
            artwork_uri=str(data.get("ArtworkURI") or ""),
            artwork_ratio=_number(data, "ArtworkRatio"),
            search_placeholder_text=str(data.get("SearchPlaceholderText") or ""),
            start_index=_integer(data, "StartIndex"),
            total_available=_integer(data, "TotalAvailable", -1),
            media_items=tuple(MediaItem.from_dict(item) for item in media_items),
            display_info=_string_tuple(data, "DisplayInfo"),
        )

    @property
    def can_search(self) -> bool:
        """Return whether CasaTunes advertises search within this collection."""
        return bool(self.flags & MediaItemFlag.ALLOW_SEARCH)


@dataclass(frozen=True, slots=True)
class MediaQueue:
    """One page of a CasaTunes zone or source queue."""

    start_index: int
    total_available: int
    media_items: tuple[MediaItem, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        media_items = data.get("MediaItems") or []
        if not isinstance(media_items, list) or not all(
            isinstance(item, dict) for item in media_items
        ):
            raise CasaTunesResponseError("Response field MediaItems is not a list")
        return cls(
            start_index=_integer(data, "StartIndex"),
            total_available=_integer(data, "TotalAvailable"),
            media_items=tuple(MediaItem.from_dict(item) for item in media_items),
        )


@dataclass(frozen=True, slots=True)
class NowPlaying:
    """Source-centric player state returned by CasaTunes."""

    source_id: int
    status: int
    controls: int
    repeat_mode: int
    shuffle_mode: bool
    progress: int
    queue_count: int
    queue_song_index: int
    current_song: MediaItem | None
    next_song: MediaItem | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        current_song = data.get("CurrSong")
        next_song = data.get("NextSong")
        return cls(
            source_id=_integer(data, "SourceID"),
            status=_integer(data, "Status"),
            controls=_integer(data, "Controls"),
            repeat_mode=_integer(data, "RepeatMode"),
            shuffle_mode=bool(data.get("ShuffleMode", False)),
            progress=_integer(data, "CurrProgress"),
            queue_count=_integer(data, "QueueCount"),
            queue_song_index=_integer(data, "QueueSongIndex", -1),
            current_song=(
                MediaItem.from_dict(current_song)
                if isinstance(current_song, dict)
                else None
            ),
            next_song=(
                MediaItem.from_dict(next_song) if isinstance(next_song, dict) else None
            ),
        )

    def supports(self, control_flag: PlayerControl) -> bool:
        """Return whether the now-playing controls bit field contains a flag."""
        return bool(self.controls & control_flag)


@dataclass(frozen=True, slots=True)
class CasaTunesSnapshot:
    """One coherent coordinator snapshot of CasaTunes state."""

    system: SystemInfo
    zones: tuple[Zone, ...]
    sources: tuple[Source, ...]
    now_playing: tuple[NowPlaying, ...]
    captured_at: datetime

    @property
    def zones_by_persistent_id(self) -> dict[str, Zone]:
        return {zone.persistent_zone_id: zone for zone in self.zones}

    @property
    def sources_by_id(self) -> dict[int, Source]:
        return {source.source_id: source for source in self.sources}

    @property
    def now_playing_by_source_id(self) -> dict[int, NowPlaying]:
        return {item.source_id: item for item in self.now_playing}
