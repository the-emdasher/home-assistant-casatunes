"""CasaTunes media-player entities."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from datetime import datetime
from typing import Any

from homeassistant.components.media_player import (
    ATTR_MEDIA_ENQUEUE,
    BrowseMedia,
    MediaClass,
    MediaPlayerDeviceClass,
    MediaPlayerEnqueue,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
    RepeatMode,
    SearchMedia,
    SearchMediaQuery,
)
from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .casatunes_api import (
    CasaTunesError,
    MediaCollection,
    MediaItem,
    MediaItemFlag,
    MediaQueue,
    NowPlaying,
    PlayerControl,
    PlayerStatus,
    Source,
    SourceControlType,
    Zone,
)
from .const import CONF_INCLUDE_HIDDEN, DOMAIN
from .coordinator import CasaTunesCoordinator
from .data import CasaTunesConfigEntry

PARALLEL_UPDATES = 0

ROOT_MEDIA_CONTENT_ID = "casatunes:root"
QUEUE_MEDIA_CONTENT_ID = "casatunes:queue"
QUEUE_ITEM_PREFIX = "casatunes:queue-item:"
GROUP_POLL_INTERVAL = 0.5
GROUP_WAIT_SECONDS = 6.0
POWER_SETTLE_SECONDS = 1.0


def _media_class(item: MediaItem) -> MediaClass:
    if item.flags & MediaItemFlag.PLAYLIST:
        return MediaClass.PLAYLIST
    if item.flags & MediaItemFlag.TRACK:
        return MediaClass.TRACK
    if item.flags & (MediaItemFlag.STATION | MediaItemFlag.STREAM):
        return MediaClass.CHANNEL
    if item.can_expand:
        return MediaClass.DIRECTORY
    return MediaClass.MUSIC


def _media_type(item: MediaItem) -> MediaType:
    media_class = _media_class(item)
    return {
        MediaClass.PLAYLIST: MediaType.PLAYLIST,
        MediaClass.TRACK: MediaType.TRACK,
        MediaClass.CHANNEL: MediaType.CHANNEL,
    }.get(media_class, MediaType.MUSIC)


def _group_members_for_zone(
    zone: Zone,
    zones: tuple[Zone, ...],
) -> tuple[tuple[Zone, bool], ...]:
    """Resolve saved or transient CasaTunes group membership."""
    if zone.shared and zone.shared_room_id:
        return tuple(
            (member, False)
            for member in sorted(zones, key=lambda item: item.zone_id)
            if member.shared and member.shared_room_id == zone.shared_room_id
        )
    if not zone.group_info:
        return ()
    zones_by_id = {item.zone_id: item for item in zones}
    members: list[tuple[Zone, bool]] = []
    for group_item in zone.group_info:
        raw_zone_id = group_item.get("zoneId", group_item.get("ZoneID"))
        if (
            isinstance(raw_zone_id, int)
            and not isinstance(raw_zone_id, bool)
            and (member := zones_by_id.get(raw_zone_id)) is not None
        ):
            members.append((member, bool(group_item.get("master", False))))
    return tuple(sorted(members, key=lambda item: not item[1]))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CasaTunesConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up dynamically discovered CasaTunes zones."""
    coordinator = entry.runtime_data.coordinator
    include_hidden = entry.options.get(
        CONF_INCLUDE_HIDDEN,
        entry.data.get(CONF_INCLUDE_HIDDEN, False),
    )
    known_zone_ids: set[str] = set()

    @callback
    def async_add_new_zones() -> None:
        new_zones = [
            zone
            for zone in coordinator.data.zones
            if zone.persistent_zone_id not in known_zone_ids
            and (include_hidden or not zone.hidden)
        ]
        if not new_zones:
            return
        known_zone_ids.update(zone.persistent_zone_id for zone in new_zones)
        async_add_entities(
            CasaTunesZoneEntity(coordinator, zone.persistent_zone_id)
            for zone in new_zones
        )

    async_add_new_zones()
    entry.async_on_unload(coordinator.async_add_listener(async_add_new_zones))


class CasaTunesZoneEntity(CoordinatorEntity[CasaTunesCoordinator], MediaPlayerEntity):
    """A CasaTunes zone represented as a Home Assistant media player."""

    _attr_device_class = MediaPlayerDeviceClass.SPEAKER
    _attr_has_entity_name = True
    _attr_media_content_type = MediaType.MUSIC
    _attr_media_image_remotely_accessible = False
    _attr_name = None

    def __init__(self, coordinator: CasaTunesCoordinator, zone_id: str) -> None:
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._attr_unique_id = zone_id

    @property
    def zone(self) -> Zone | None:
        return self.coordinator.data.zones_by_persistent_id.get(self._zone_id)

    @property
    def now_playing(self) -> NowPlaying | None:
        zone = self.zone
        if zone is None:
            return None
        return self.coordinator.data.now_playing_by_source_id.get(zone.source_id)

    @property
    def current_source(self) -> Source | None:
        zone = self.zone
        if zone is None:
            return None
        return self.coordinator.data.sources_by_id.get(zone.source_id)

    def _group_zone_members(self) -> tuple[tuple[Zone, bool], ...]:
        zone = self.zone
        if zone is None:
            return ()
        return _group_members_for_zone(zone, self.coordinator.data.zones)

    async def _async_wait_for_group_members(self, expected_zone_ids: set[str]) -> None:
        """Wait for CasaTunes' asynchronous sharing state to become visible."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + GROUP_WAIT_SECONDS
        while True:
            zones = await self.coordinator.client.async_get_zones()
            current = next(
                (zone for zone in zones if zone.persistent_zone_id == self._zone_id),
                None,
            )
            if current is not None:
                member_ids = {
                    member.persistent_zone_id
                    for member, _is_master in _group_members_for_zone(current, zones)
                }
                if expected_zone_ids <= member_ids:
                    return
            if loop.time() >= deadline:
                raise HomeAssistantError(
                    "CasaTunes accepted the command but did not expose the "
                    "expected group"
                )
            await asyncio.sleep(GROUP_POLL_INTERVAL)

    @property
    def available(self) -> bool:
        return super().available and self.zone is not None

    @property
    def group_members(self) -> list[str] | None:
        members = self._group_zone_members()
        if len(members) < 2:
            return None
        registry = er.async_get(self.hass)
        entity_ids = [
            entity_id
            for member, _is_master in members
            if (
                entity_id := registry.async_get_entity_id(
                    MEDIA_PLAYER_DOMAIN,
                    DOMAIN,
                    member.persistent_zone_id,
                )
            )
        ]
        return entity_ids or None

    @property
    def extra_state_attributes(self) -> dict[str, bool]:
        """Mark CasaTunes players supported by the bundled group-volume feature."""
        return {"casatunes_group_volume": True}

    @property
    def device_info(self) -> DeviceInfo:
        zone = self.zone
        assert zone is not None
        system = self.coordinator.data.system
        return DeviceInfo(
            identifiers={(DOMAIN, zone.persistent_zone_id)},
            manufacturer="CasaTunes",
            model="Audio zone",
            name=zone.name,
            via_device=(DOMAIN, system.mac_address.lower()),
        )

    @property
    def state(self) -> MediaPlayerState | None:
        zone = self.zone
        if zone is None:
            return None
        if not zone.power:
            return MediaPlayerState.OFF
        now_playing = self.now_playing
        if now_playing is None:
            return MediaPlayerState.ON
        return {
            PlayerStatus.STOPPED: MediaPlayerState.IDLE,
            PlayerStatus.PAUSED: MediaPlayerState.PAUSED,
            PlayerStatus.PLAYING: MediaPlayerState.PLAYING,
            PlayerStatus.RETRYING: MediaPlayerState.BUFFERING,
            PlayerStatus.BUFFERING: MediaPlayerState.BUFFERING,
            PlayerStatus.SEEKING: MediaPlayerState.BUFFERING,
        }.get(now_playing.status, MediaPlayerState.ON)

    @property
    def volume_level(self) -> float | None:
        zone = self.zone
        if zone is None:
            return None
        volume_range = self.coordinator.data.system.volume_settings
        span = volume_range.maximum - volume_range.minimum
        if span <= 0:
            return None
        return max(0.0, min(1.0, (zone.volume - volume_range.minimum) / span))

    @property
    def volume_step(self) -> float:
        settings = self.coordinator.data.system.volume_settings
        span = settings.maximum - settings.minimum
        return settings.increment / span if span > 0 else 0.01

    @property
    def is_volume_muted(self) -> bool | None:
        return self.zone.mute if self.zone is not None else None

    @property
    def _available_sources(self) -> tuple[Source, ...]:
        zone = self.zone
        if zone is None:
            return ()
        return tuple(
            source
            for source in self.coordinator.data.sources
            if not source.hidden and zone.supports_source(source.source_id)
        )

    @property
    def source(self) -> str | None:
        source = self.current_source
        return source.name if source is not None else None

    @property
    def source_list(self) -> list[str]:
        return [source.name for source in self._available_sources]

    @property
    def media_title(self) -> str | None:
        song = self.now_playing.current_song if self.now_playing else None
        return song.title or None if song else None

    @property
    def media_artist(self) -> str | None:
        song = self.now_playing.current_song if self.now_playing else None
        return song.artists or None if song else None

    @property
    def media_album_name(self) -> str | None:
        song = self.now_playing.current_song if self.now_playing else None
        return song.album or None if song else None

    @property
    def media_duration(self) -> float | None:
        song = self.now_playing.current_song if self.now_playing else None
        return song.duration if song else None

    @property
    def media_position(self) -> int | None:
        return self.now_playing.progress if self.now_playing else None

    @property
    def media_position_updated_at(self) -> datetime | None:
        if self.state == MediaPlayerState.PLAYING:
            return self.coordinator.data.captured_at
        return None

    @property
    def media_image_url(self) -> str | None:
        song = self.now_playing.current_song if self.now_playing else None
        return self.coordinator.client.artwork_url(song.artwork_uri) if song else None

    def _browse_item(self, item: MediaItem) -> BrowseMedia:
        return BrowseMedia(
            media_class=_media_class(item),
            media_content_id=item.id,
            media_content_type=_media_type(item),
            title=item.title or item.details or "Untitled",
            can_play=item.can_play,
            can_expand=item.can_expand,
            thumbnail=self.coordinator.client.artwork_url(item.artwork_uri),
        )

    def _browse_collection(
        self,
        collection: MediaCollection,
        *,
        content_id: str,
        include_queue: bool = False,
    ) -> BrowseMedia:
        children = [self._browse_item(item) for item in collection.media_items]
        if include_queue:
            children.insert(
                0,
                BrowseMedia(
                    media_class=MediaClass.PLAYLIST,
                    media_content_id=QUEUE_MEDIA_CONTENT_ID,
                    media_content_type=MediaType.PLAYLIST,
                    title="Queue",
                    can_play=False,
                    can_expand=True,
                ),
            )
        not_shown = (
            max(0, collection.total_available - len(collection.media_items))
            if collection.total_available >= 0
            else 0
        )
        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=content_id,
            media_content_type=MediaType.MUSIC,
            title=collection.title or (self.zone.name if self.zone else "CasaTunes"),
            can_play=False,
            can_expand=True,
            children=children,
            thumbnail=self.coordinator.client.artwork_url(collection.artwork_uri),
            not_shown=not_shown,
            can_search=collection.can_search,
            search_media_classes=[
                MediaClass.ALBUM,
                MediaClass.ARTIST,
                MediaClass.CHANNEL,
                MediaClass.PLAYLIST,
                MediaClass.TRACK,
            ],
        )

    def _browse_queue(self, queue: MediaQueue) -> BrowseMedia:
        children = [
            BrowseMedia(
                media_class=_media_class(item),
                media_content_id=f"{QUEUE_ITEM_PREFIX}{queue.start_index + index}",
                media_content_type=_media_type(item),
                title=item.title or item.details or f"Queue item {index + 1}",
                can_play=True,
                can_expand=False,
                thumbnail=self.coordinator.client.artwork_url(item.artwork_uri),
            )
            for index, item in enumerate(queue.media_items)
        ]
        return BrowseMedia(
            media_class=MediaClass.PLAYLIST,
            media_content_id=QUEUE_MEDIA_CONTENT_ID,
            media_content_type=MediaType.PLAYLIST,
            title="Queue",
            can_play=False,
            can_expand=True,
            children=children,
            not_shown=max(0, queue.total_available - len(queue.media_items)),
        )

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        zone = self.zone
        if zone is None:
            return MediaPlayerEntityFeature(0)
        features = MediaPlayerEntityFeature(0)
        if not zone.hide_power_control:
            features |= (
                MediaPlayerEntityFeature.TURN_ON | MediaPlayerEntityFeature.TURN_OFF
            )
        if not zone.fixed_volume_enabled:
            features |= (
                MediaPlayerEntityFeature.VOLUME_SET
                | MediaPlayerEntityFeature.VOLUME_STEP
                | MediaPlayerEntityFeature.VOLUME_MUTE
            )
        if not zone.hide_source_control and self._available_sources:
            features |= MediaPlayerEntityFeature.SELECT_SOURCE
        if sum(not item.hidden for item in self.coordinator.data.zones) > 1:
            features |= MediaPlayerEntityFeature.GROUPING

        controls = PlayerControl(0)
        if (
            self.now_playing is not None
            and self.current_source is not None
            and self.current_source.control_type & SourceControlType.MEDIA_PLAYER
        ):
            controls = PlayerControl(self.now_playing.controls)
            features |= (
                MediaPlayerEntityFeature.BROWSE_MEDIA
                | MediaPlayerEntityFeature.PLAY_MEDIA
                | MediaPlayerEntityFeature.CLEAR_PLAYLIST
                | MediaPlayerEntityFeature.SEARCH_MEDIA
            )
            if zone.power and not zone.mute:
                features |= MediaPlayerEntityFeature.MEDIA_ENQUEUE
        for flag, feature in (
            (PlayerControl.PLAY, MediaPlayerEntityFeature.PLAY),
            (PlayerControl.STOP, MediaPlayerEntityFeature.STOP),
            (PlayerControl.PAUSE, MediaPlayerEntityFeature.PAUSE),
            (PlayerControl.SHUFFLE, MediaPlayerEntityFeature.SHUFFLE_SET),
            (PlayerControl.REPEAT, MediaPlayerEntityFeature.REPEAT_SET),
            (PlayerControl.NEXT_TRACK, MediaPlayerEntityFeature.NEXT_TRACK),
            (PlayerControl.PREVIOUS_TRACK, MediaPlayerEntityFeature.PREVIOUS_TRACK),
            (PlayerControl.SEEK, MediaPlayerEntityFeature.SEEK),
        ):
            if controls & flag:
                features |= feature
        return features

    async def _async_command(self, command: Awaitable[Any]) -> None:
        try:
            await command
        except CasaTunesError as err:
            raise HomeAssistantError(f"CasaTunes command failed: {err}") from err
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        await self._async_command(
            self.coordinator.client.async_update_zone(self._zone_id, Power=True)
        )

    async def async_turn_off(self) -> None:
        await self._async_command(
            self.coordinator.client.async_update_zone(self._zone_id, Power=False)
        )

    async def async_set_volume_level(self, volume: float) -> None:
        settings = self.coordinator.data.system.volume_settings
        casatunes_volume = round(
            settings.minimum
            + max(0.0, min(1.0, volume)) * (settings.maximum - settings.minimum)
        )
        await self._async_command(
            self.coordinator.client.async_update_zone(
                self._zone_id, Volume=casatunes_volume
            )
        )

    async def async_volume_up(self) -> None:
        await self._async_command(
            self.coordinator.client.async_update_zone(
                self._zone_id,
                AdjustVolume=self.coordinator.data.system.volume_settings.increment,
            )
        )

    async def async_volume_down(self) -> None:
        await self._async_command(
            self.coordinator.client.async_update_zone(
                self._zone_id,
                AdjustVolume=-self.coordinator.data.system.volume_settings.increment,
            )
        )

    async def async_mute_volume(self, mute: bool) -> None:
        try:
            zone = await self.coordinator.client.async_update_zone(
                self._zone_id, Mute=mute
            )
        except CasaTunesError as err:
            raise HomeAssistantError(f"CasaTunes command failed: {err}") from err
        self.coordinator.async_set_optimistic_mute(zone, mute)
        await self.coordinator.async_request_refresh()

    async def async_select_source(self, source: str) -> None:
        match = next(
            (item for item in self._available_sources if item.name == source), None
        )
        if match is None:
            raise HomeAssistantError(f"Unknown CasaTunes source: {source}")
        await self._async_command(
            self.coordinator.client.async_update_zone(
                self._zone_id, SourceID=match.source_id
            )
        )

    async def async_browse_media(
        self,
        media_content_type: MediaType | str | None = None,
        media_content_id: str | None = None,
    ) -> BrowseMedia:
        del media_content_type
        try:
            if media_content_id == QUEUE_MEDIA_CONTENT_ID:
                return self._browse_queue(
                    await self.coordinator.client.async_get_zone_queue(self._zone_id)
                )
            if media_content_id in (None, ROOT_MEDIA_CONTENT_ID):
                collection = await self.coordinator.client.async_browse_zone(
                    self._zone_id
                )
                return self._browse_collection(
                    collection,
                    content_id=ROOT_MEDIA_CONTENT_ID,
                    include_queue=True,
                )
            if media_content_id.startswith(QUEUE_ITEM_PREFIX):
                raise HomeAssistantError("Queue items cannot be expanded")
            collection = await self.coordinator.client.async_browse_media(
                media_content_id
            )
            return self._browse_collection(
                collection,
                content_id=media_content_id,
            )
        except CasaTunesError as err:
            raise HomeAssistantError(
                f"Unable to browse CasaTunes media: {err}"
            ) from err

    async def async_search_media(self, query: SearchMediaQuery) -> SearchMedia:
        try:
            if query.media_content_id in (None, ROOT_MEDIA_CONTENT_ID):
                collection = await self.coordinator.client.async_search_zone(
                    self._zone_id,
                    query.search_query,
                )
            else:
                collection = await self.coordinator.client.async_search_media(
                    query.media_content_id,
                    query.search_query,
                )
        except CasaTunesError as err:
            raise HomeAssistantError(
                f"Unable to search CasaTunes media: {err}"
            ) from err

        results = [self._browse_item(item) for item in collection.media_items]
        if query.media_filter_classes:
            allowed = set(query.media_filter_classes)
            results = [item for item in results if item.media_class in allowed]
        return SearchMedia(result=results)

    async def async_play_media(
        self, media_type: MediaType | str, media_id: str, **kwargs: Any
    ) -> None:
        del media_type
        if media_id.startswith(QUEUE_ITEM_PREFIX):
            try:
                index = int(media_id.removeprefix(QUEUE_ITEM_PREFIX))
            except ValueError as err:
                raise HomeAssistantError("Invalid CasaTunes queue item") from err
            await self._async_command(
                self.coordinator.client.async_play_queue_item(self._zone_id, index)
            )
            return

        enqueue = kwargs.get(ATTR_MEDIA_ENQUEUE, MediaPlayerEnqueue.PLAY)
        add_to_queue = enqueue in (MediaPlayerEnqueue.ADD, MediaPlayerEnqueue.NEXT)
        zone = self.zone
        if zone is None:
            raise HomeAssistantError("CasaTunes zone is unavailable")
        if add_to_queue and (not zone.power or zone.mute):
            raise HomeAssistantError(
                "Turn the CasaTunes zone on and unmute it before adding media "
                "to its queue"
            )
        await self._async_command(
            self.coordinator.client.async_play_media(
                self._zone_id,
                media_id,
                add_to_queue=add_to_queue,
                auto_start=not add_to_queue,
            )
        )

    async def async_clear_playlist(self) -> None:
        await self._async_command(
            self.coordinator.client.async_clear_queue(self._zone_id)
        )

    async def async_join_players(self, group_members: list[str]) -> None:
        zone = self.zone
        if zone is None:
            raise HomeAssistantError("CasaTunes zone is unavailable")
        registry = er.async_get(self.hass)
        target_zone_ids: list[str] = []
        for entity_id in group_members:
            entry = registry.async_get(entity_id)
            if entry is None or entry.platform != DOMAIN:
                raise HomeAssistantError(
                    f"Entity {entity_id} is not a CasaTunes media player"
                )
            target = self.coordinator.data.zones_by_persistent_id.get(entry.unique_id)
            if target is None:
                raise HomeAssistantError(
                    f"CasaTunes zone for entity {entity_id} is unavailable"
                )
            if target.persistent_zone_id == self._zone_id:
                raise HomeAssistantError("A CasaTunes zone cannot join itself")
            if target.persistent_zone_id not in target_zone_ids:
                target_zone_ids.append(target.persistent_zone_id)

        current_members = {
            member.persistent_zone_id
            for member, _is_master in self._group_zone_members()
        }
        target_zone_ids = [
            zone_id for zone_id in target_zone_ids if zone_id not in current_members
        ]
        if not target_zone_ids:
            return

        try:
            if not zone.power:
                await self.coordinator.client.async_update_zone(
                    self._zone_id, Power=True
                )
                await asyncio.sleep(POWER_SETTLE_SECONDS)

            expected_zone_ids = current_members | {self._zone_id}
            if len(current_members) < 2:
                first_zone_id = target_zone_ids.pop(0)
                await self.coordinator.client.async_join_zone(
                    first_zone_id,
                    self._zone_id,
                )
                expected_zone_ids.add(first_zone_id)
                await self._async_wait_for_group_members(expected_zone_ids)

            for target_zone_id in target_zone_ids:
                await self.coordinator.client.async_group_zone(
                    self._zone_id,
                    target_zone_id,
                )
                expected_zone_ids.add(target_zone_id)
                await self._async_wait_for_group_members(expected_zone_ids)
        except CasaTunesError as err:
            raise HomeAssistantError(f"Unable to group CasaTunes zones: {err}") from err
        finally:
            await self.coordinator.async_request_refresh()

    async def async_unjoin_player(self) -> None:
        zone = self.zone
        if zone is None:
            raise HomeAssistantError("CasaTunes zone is unavailable")
        if zone.shared:
            try:
                await self.coordinator.client.async_ungroup_zone(
                    self._zone_id,
                    self._zone_id,
                )
            except CasaTunesError as err:
                raise HomeAssistantError(
                    f"Unable to ungroup CasaTunes zone: {err}"
                ) from err
            await self.coordinator.async_request_refresh()
            return

        members = self._group_zone_members()
        if len(members) < 2:
            return
        current = next(
            (
                (member, is_master)
                for member, is_master in members
                if member.persistent_zone_id == self._zone_id
            ),
            None,
        )
        if current is None:
            raise HomeAssistantError("CasaTunes group does not contain this zone")

        if current[1]:
            removals = [
                (self._zone_id, member.persistent_zone_id)
                for member, _is_master in members
                if member.persistent_zone_id != self._zone_id
            ]
        else:
            master = next((member for member, is_master in members if is_master), None)
            if master is None:
                raise HomeAssistantError("CasaTunes group has no master zone")
            removals = [(master.persistent_zone_id, self._zone_id)]

        try:
            for group_id, grouped_zone_id in removals:
                await self.coordinator.client.async_ungroup_zone(
                    group_id,
                    grouped_zone_id,
                )
        except CasaTunesError as err:
            raise HomeAssistantError(
                f"Unable to ungroup CasaTunes zone: {err}"
            ) from err
        await self.coordinator.async_request_refresh()

    async def _async_player_action(
        self, action: str, option: str | int | None = None
    ) -> None:
        await self._async_command(
            self.coordinator.client.async_player_action(self._zone_id, action, option)
        )

    async def async_media_play(self) -> None:
        await self._async_player_action("play")

    async def async_media_pause(self) -> None:
        await self._async_player_action("pause")

    async def async_media_stop(self) -> None:
        await self._async_player_action("stop")

    async def async_media_next_track(self) -> None:
        await self._async_player_action("next")

    async def async_media_previous_track(self) -> None:
        await self._async_player_action("previous")

    async def async_media_seek(self, position: float) -> None:
        seek_position = max(0, round(position))
        now_playing = self.now_playing
        try:
            await self.coordinator.client.async_player_action(
                self._zone_id, "position", seek_position
            )
        except CasaTunesError as err:
            raise HomeAssistantError(f"CasaTunes command failed: {err}") from err
        if now_playing is not None:
            self.coordinator.async_set_optimistic_position(
                now_playing.source_id, seek_position
            )
        await self.coordinator.async_request_refresh()

    async def async_set_shuffle(self, shuffle: bool) -> None:
        await self._async_player_action("shuffle", "on" if shuffle else "off")

    async def async_set_repeat(self, repeat: RepeatMode) -> None:
        option = {
            RepeatMode.OFF: "off",
            RepeatMode.ALL: "on",
            RepeatMode.ONE: "once",
        }[repeat]
        await self._async_player_action("repeat", option)
