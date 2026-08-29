"""Tests for CasaTunes Home Assistant media-player entities."""

from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

from homeassistant.components.media_player import (
    MediaPlayerEnqueue,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
    SearchMediaQuery,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from custom_components.casatunes.casatunes_api.models import (
    CasaTunesSnapshot,
    MediaCollection,
    MediaQueue,
    NowPlaying,
    Source,
    SystemInfo,
    Zone,
)
from custom_components.casatunes.media_player import (
    QUEUE_ITEM_PREFIX,
    QUEUE_MEDIA_CONTENT_ID,
    CasaTunesZoneEntity,
)
from tests.test_models import (
    MEDIA_COLLECTION,
    MEDIA_ITEM,
    NOW_PLAYING,
    SOURCE,
    SYSTEM,
    ZONE,
)


class FakeClient:
    """Record commands issued by an entity."""

    def __init__(self, zones: tuple[Zone, ...] = ()) -> None:
        self.zone_commands: list[tuple[str, dict[str, object]]] = []
        self.player_commands: list[tuple[str, str, str | int | None]] = []
        self.media_commands: list[tuple[str, object]] = []
        self.group_commands: list[tuple[str, str, str]] = []
        self.zones = zones

    async def async_update_zone(self, zone_id: str, **changes: object) -> Zone:
        self.zone_commands.append((zone_id, changes))
        self.zones = tuple(
            replace(zone, power=bool(changes["Power"]))
            if zone.persistent_zone_id == zone_id and "Power" in changes
            else zone
            for zone in self.zones
        )
        return Zone.from_dict(dict(ZONE, **changes))

    async def async_player_action(
        self, zone_id: str, action: str, option: str | int | None = None
    ) -> None:
        self.player_commands.append((zone_id, action, option))

    def artwork_url(self, artwork_uri: str) -> str:
        return f"http://casaserver.local/art/{artwork_uri}"

    async def async_browse_zone(self, zone_id: str) -> MediaCollection:
        self.media_commands.append(("browse_zone", zone_id))
        return MediaCollection.from_dict(MEDIA_COLLECTION)

    async def async_browse_media(self, media_id: str) -> MediaCollection:
        self.media_commands.append(("browse_media", media_id))
        return MediaCollection.from_dict(MEDIA_COLLECTION)

    async def async_search_zone(
        self, zone_id: str, search_text: str
    ) -> MediaCollection:
        self.media_commands.append(("search_zone", (zone_id, search_text)))
        return MediaCollection.from_dict(MEDIA_COLLECTION)

    async def async_search_media(
        self, media_id: str, search_text: str
    ) -> MediaCollection:
        self.media_commands.append(("search_media", (media_id, search_text)))
        return MediaCollection.from_dict(MEDIA_COLLECTION)

    async def async_get_zone_queue(self, zone_id: str) -> MediaQueue:
        self.media_commands.append(("get_queue", zone_id))
        return MediaQueue.from_dict(
            {"StartIndex": 0, "TotalAvailable": 1, "MediaItems": [MEDIA_ITEM]}
        )

    async def async_play_media(
        self,
        zone_id: str,
        media_id: str,
        *,
        add_to_queue: bool,
        auto_start: bool,
    ) -> int:
        self.media_commands.append(
            ("play_media", (zone_id, media_id, add_to_queue, auto_start))
        )
        return 1

    async def async_play_queue_item(self, zone_id: str, index: int) -> None:
        self.media_commands.append(("play_queue", (zone_id, index)))

    async def async_clear_queue(self, zone_id: str) -> None:
        self.media_commands.append(("clear_queue", zone_id))

    async def async_get_zones(self) -> tuple[Zone, ...]:
        return self.zones

    async def async_join_zone(self, join_id: str, to_id: str) -> None:
        self.group_commands.append(("join", join_id, to_id))
        leader = next(zone for zone in self.zones if zone.persistent_zone_id == to_id)
        self.zones = tuple(
            replace(
                zone,
                power=True,
                source_id=leader.source_id,
                shared=True,
                shared_room_id="transient-shared-room-id",
            )
            if zone.persistent_zone_id in {join_id, to_id}
            else zone
            for zone in self.zones
        )

    async def async_group_zone(self, group_id: str, grouped_zone_id: str) -> None:
        self.group_commands.append(("group", group_id, grouped_zone_id))
        leader = next(
            zone for zone in self.zones if zone.persistent_zone_id == group_id
        )
        self.zones = tuple(
            replace(
                zone,
                power=True,
                source_id=leader.source_id,
                shared=True,
                shared_room_id=leader.shared_room_id,
            )
            if zone.persistent_zone_id == grouped_zone_id
            else zone
            for zone in self.zones
        )

    async def async_ungroup_zone(self, group_id: str, grouped_zone_id: str) -> None:
        self.group_commands.append(("ungroup", group_id, grouped_zone_id))


class FakeEntityRegistry:
    def __init__(self) -> None:
        self.entries = {
            "media_player.patio": SimpleNamespace(
                platform="casatunes", unique_id="zone-persistent-id"
            ),
            "media_player.kitchen": SimpleNamespace(
                platform="casatunes", unique_id="member-zone-id"
            ),
            "media_player.den": SimpleNamespace(
                platform="casatunes", unique_id="third-zone-id"
            ),
        }

    def async_get(self, entity_id: str) -> object | None:
        return self.entries.get(entity_id)

    def async_get_entity_id(
        self, domain: str, platform: str, unique_id: str
    ) -> str | None:
        del domain, platform
        return next(
            (
                entity_id
                for entity_id, entry in self.entries.items()
                if entry.unique_id == unique_id
            ),
            None,
        )


class FakeCoordinator:
    """Supply the coordinator surface used by CasaTunesZoneEntity."""

    def __init__(self, data: CasaTunesSnapshot) -> None:
        self.data = data
        self.client = FakeClient(data.zones)
        self.config_entry = SimpleNamespace(unique_id="established-server-id")
        self.last_update_success = True
        self.refresh_count = 0

    async def async_request_refresh(self) -> None:
        self.refresh_count += 1

    def async_set_optimistic_mute(self, zone: Zone, mute: bool) -> None:
        optimistic_zone = replace(zone, mute=mute)
        self.data = replace(
            self.data,
            zones=tuple(
                optimistic_zone
                if item.persistent_zone_id == zone.persistent_zone_id
                else item
                for item in self.data.zones
            ),
        )

    def async_set_optimistic_position(self, source_id: int, position: int) -> None:
        self.data = replace(
            self.data,
            now_playing=tuple(
                replace(item, progress=position)
                if item.source_id == source_id
                else item
                for item in self.data.now_playing
            ),
            captured_at=datetime.now(UTC),
        )


def _snapshot(
    *,
    zone_data: dict[str, Any] | None = None,
    source_data: dict[str, Any] | None = None,
    now_playing_data: dict[str, Any] | None = None,
    zones_data: list[dict[str, Any]] | None = None,
) -> CasaTunesSnapshot:
    return CasaTunesSnapshot(
        system=SystemInfo.from_dict(SYSTEM),
        zones=tuple(
            Zone.from_dict(item) for item in (zones_data or [zone_data or ZONE])
        ),
        sources=(Source.from_dict(source_data or SOURCE),),
        now_playing=(NowPlaying.from_dict(now_playing_data or NOW_PLAYING),),
        captured_at=datetime.now(UTC),
    )


class MediaPlayerEntityTests(unittest.IsolatedAsyncioTestCase):
    def test_entity_maps_state_metadata_volume_and_sources(self) -> None:
        coordinator = FakeCoordinator(_snapshot())
        entity = CasaTunesZoneEntity(  # type: ignore[arg-type]
            coordinator, "zone-persistent-id"
        )

        self.assertEqual(entity.state, MediaPlayerState.PLAYING)
        self.assertEqual(entity.volume_level, 0.34)
        self.assertEqual(entity.volume_step, 0.01)
        self.assertFalse(entity.is_volume_muted)
        self.assertEqual(
            entity.extra_state_attributes,
            {"casatunes_group_volume": True},
        )
        self.assertEqual(entity.source, "Player A")
        self.assertEqual(entity.source_list, ["Player A"])
        self.assertEqual(entity.media_title, "Test Song")
        self.assertEqual(entity.media_artist, "Test Artist")
        self.assertEqual(entity.media_album_name, "Test Album")
        self.assertEqual(entity.media_duration, 180.5)
        self.assertEqual(entity.media_position, 42)
        self.assertEqual(
            entity.media_image_url,
            "http://casaserver.local/art/artwork-id",
        )
        self.assertEqual(
            entity.device_info["via_device"],
            ("casatunes", "established-server-id"),
        )

        features = entity.supported_features
        for expected in (
            MediaPlayerEntityFeature.TURN_ON,
            MediaPlayerEntityFeature.TURN_OFF,
            MediaPlayerEntityFeature.VOLUME_SET,
            MediaPlayerEntityFeature.VOLUME_STEP,
            MediaPlayerEntityFeature.VOLUME_MUTE,
            MediaPlayerEntityFeature.SELECT_SOURCE,
            MediaPlayerEntityFeature.PLAY,
            MediaPlayerEntityFeature.PAUSE,
            MediaPlayerEntityFeature.STOP,
            MediaPlayerEntityFeature.NEXT_TRACK,
            MediaPlayerEntityFeature.PREVIOUS_TRACK,
            MediaPlayerEntityFeature.SEEK,
            MediaPlayerEntityFeature.SHUFFLE_SET,
            MediaPlayerEntityFeature.REPEAT_SET,
            MediaPlayerEntityFeature.BROWSE_MEDIA,
            MediaPlayerEntityFeature.PLAY_MEDIA,
            MediaPlayerEntityFeature.MEDIA_ENQUEUE,
            MediaPlayerEntityFeature.CLEAR_PLAYLIST,
            MediaPlayerEntityFeature.SEARCH_MEDIA,
        ):
            self.assertTrue(features & expected)

    def test_tuner_bits_are_not_mapped_as_player_features(self) -> None:
        tuner_source = dict(SOURCE, SourceType=1, Type=2)
        tuner_now_playing = dict(NOW_PLAYING, Controls=0x07)
        coordinator = FakeCoordinator(
            _snapshot(
                source_data=tuner_source,
                now_playing_data=tuner_now_playing,
            )
        )
        entity = CasaTunesZoneEntity(  # type: ignore[arg-type]
            coordinator, "zone-persistent-id"
        )

        player_features = (
            MediaPlayerEntityFeature.PLAY
            | MediaPlayerEntityFeature.PAUSE
            | MediaPlayerEntityFeature.STOP
        )
        self.assertFalse(entity.supported_features & player_features)

    async def test_entity_commands_translate_to_casatunes(self) -> None:
        coordinator = FakeCoordinator(_snapshot())
        entity = CasaTunesZoneEntity(  # type: ignore[arg-type]
            coordinator, "zone-persistent-id"
        )

        await entity.async_turn_on()
        await entity.async_set_volume_level(0.5)
        await entity.async_volume_up()
        await entity.async_volume_down()
        await entity.async_mute_volume(True)
        await entity.async_select_source("Player A")
        await entity.async_media_play()
        await entity.async_media_seek(12.6)

        self.assertEqual(
            coordinator.client.zone_commands,
            [
                ("zone-persistent-id", {"Power": True}),
                ("zone-persistent-id", {"Volume": 50}),
                ("zone-persistent-id", {"AdjustVolume": 1}),
                ("zone-persistent-id", {"AdjustVolume": -1}),
                ("zone-persistent-id", {"Mute": True}),
                ("zone-persistent-id", {"SourceID": 2}),
            ],
        )
        self.assertEqual(
            coordinator.client.player_commands,
            [
                ("zone-persistent-id", "play", None),
                ("zone-persistent-id", "position", 13),
            ],
        )
        self.assertEqual(coordinator.refresh_count, 8)
        self.assertTrue(entity.is_volume_muted)
        self.assertEqual(entity.media_position, 13)

    async def test_browse_search_play_enqueue_and_queue(self) -> None:
        coordinator = FakeCoordinator(_snapshot())
        entity = CasaTunesZoneEntity(  # type: ignore[arg-type]
            coordinator, "zone-persistent-id"
        )

        root = await entity.async_browse_media()
        queue = await entity.async_browse_media(media_content_id=QUEUE_MEDIA_CONTENT_ID)
        child = await entity.async_browse_media(media_content_id="collection-id")
        search = await entity.async_search_media(SearchMediaQuery(search_query="song"))
        await entity.async_play_media(
            MediaType.MUSIC,
            "media-item-id",
            enqueue=MediaPlayerEnqueue.ADD,
        )
        await entity.async_play_media(
            MediaType.TRACK,
            f"{QUEUE_ITEM_PREFIX}0",
        )
        await entity.async_clear_playlist()

        self.assertEqual(root.title, "Music")
        self.assertEqual(root.children[0].media_content_id, QUEUE_MEDIA_CONTENT_ID)
        self.assertEqual(root.children[1].media_content_id, "media-item-id")
        self.assertEqual(queue.children[0].media_content_id, f"{QUEUE_ITEM_PREFIX}0")
        self.assertEqual(child.children[0].title, "Browsable Song")
        self.assertEqual(search.result[0].media_content_id, "media-item-id")
        self.assertEqual(
            coordinator.client.media_commands,
            [
                ("browse_zone", "zone-persistent-id"),
                ("get_queue", "zone-persistent-id"),
                ("browse_media", "collection-id"),
                ("search_zone", ("zone-persistent-id", "song")),
                (
                    "play_media",
                    ("zone-persistent-id", "media-item-id", True, False),
                ),
                ("play_queue", ("zone-persistent-id", 0)),
                ("clear_queue", "zone-persistent-id"),
            ],
        )
        self.assertEqual(coordinator.refresh_count, 3)

    def test_powered_off_zone_maps_to_off(self) -> None:
        coordinator = FakeCoordinator(_snapshot(zone_data=dict(ZONE, Power=False)))
        entity = CasaTunesZoneEntity(  # type: ignore[arg-type]
            coordinator, "zone-persistent-id"
        )

        self.assertEqual(entity.state, MediaPlayerState.OFF)
        self.assertFalse(
            entity.supported_features & MediaPlayerEntityFeature.MEDIA_ENQUEUE
        )

    async def test_enqueue_requires_zone_to_be_on(self) -> None:
        coordinator = FakeCoordinator(_snapshot(zone_data=dict(ZONE, Power=False)))
        entity = CasaTunesZoneEntity(  # type: ignore[arg-type]
            coordinator, "zone-persistent-id"
        )

        with self.assertRaisesRegex(HomeAssistantError, "Turn.*zone on"):
            await entity.async_play_media(
                MediaType.MUSIC,
                "media-item-id",
                enqueue=MediaPlayerEnqueue.ADD,
            )
        self.assertEqual(coordinator.client.media_commands, [])

    async def test_enqueue_requires_zone_to_be_unmuted(self) -> None:
        coordinator = FakeCoordinator(_snapshot(zone_data=dict(ZONE, Mute=True)))
        entity = CasaTunesZoneEntity(  # type: ignore[arg-type]
            coordinator, "zone-persistent-id"
        )

        self.assertFalse(
            entity.supported_features & MediaPlayerEntityFeature.MEDIA_ENQUEUE
        )
        with self.assertRaisesRegex(HomeAssistantError, "unmute"):
            await entity.async_play_media(
                MediaType.MUSIC,
                "media-item-id",
                enqueue=MediaPlayerEnqueue.ADD,
            )
        self.assertEqual(coordinator.client.media_commands, [])

    async def test_saved_group_members_and_master_unjoin(self) -> None:
        group_info = [
            {"zoneId": 2, "master": True},
            {"zoneId": 3, "master": False},
        ]
        patio = dict(ZONE, ZoneGroupInfo=group_info)
        kitchen = dict(
            ZONE,
            ZoneID=3,
            PersistentZoneID="member-zone-id",
            Name="Kitchen",
            ZoneGroupInfo=group_info,
        )
        coordinator = FakeCoordinator(_snapshot(zones_data=[patio, kitchen]))
        entity = CasaTunesZoneEntity(  # type: ignore[arg-type]
            coordinator, "zone-persistent-id"
        )
        entity.hass = object()  # type: ignore[assignment]
        registry = FakeEntityRegistry()

        with patch.object(er, "async_get", return_value=registry):
            self.assertEqual(
                entity.group_members,
                ["media_player.patio", "media_player.kitchen"],
            )
            self.assertTrue(
                entity.supported_features & MediaPlayerEntityFeature.GROUPING
            )
            await entity.async_unjoin_player()

        self.assertEqual(
            coordinator.client.group_commands,
            [("ungroup", "zone-persistent-id", "member-zone-id")],
        )
        self.assertEqual(coordinator.refresh_count, 1)

    async def test_join_starts_group_then_adds_later_members(self) -> None:
        patio = dict(ZONE, Power=False)
        kitchen = dict(
            ZONE,
            ZoneID=3,
            PersistentZoneID="member-zone-id",
            Name="Kitchen",
            Power=False,
        )
        den = dict(
            ZONE,
            ZoneID=4,
            PersistentZoneID="third-zone-id",
            Name="Den",
            Power=False,
        )
        coordinator = FakeCoordinator(_snapshot(zones_data=[patio, kitchen, den]))
        entity = CasaTunesZoneEntity(  # type: ignore[arg-type]
            coordinator, "zone-persistent-id"
        )
        entity.hass = object()  # type: ignore[assignment]
        registry = FakeEntityRegistry()

        with (
            patch.object(er, "async_get", return_value=registry),
            patch(
                "custom_components.casatunes.media_player.asyncio.sleep",
                new=AsyncMock(),
            ),
        ):
            await entity.async_join_players(
                ["media_player.kitchen", "media_player.den"]
            )

        self.assertEqual(
            coordinator.client.zone_commands,
            [("zone-persistent-id", {"Power": True})],
        )
        self.assertEqual(
            coordinator.client.group_commands,
            [
                ("join", "member-zone-id", "zone-persistent-id"),
                ("group", "zone-persistent-id", "third-zone-id"),
            ],
        )
        self.assertEqual(coordinator.refresh_count, 1)

    async def test_transient_group_members_and_self_unjoin(self) -> None:
        patio = dict(
            ZONE,
            Shared=True,
            SharedRoomID="transient-shared-room-id",
        )
        kitchen = dict(
            ZONE,
            ZoneID=3,
            PersistentZoneID="member-zone-id",
            Name="Kitchen",
            Shared=True,
            SharedRoomID="transient-shared-room-id",
        )
        coordinator = FakeCoordinator(_snapshot(zones_data=[patio, kitchen]))
        entity = CasaTunesZoneEntity(  # type: ignore[arg-type]
            coordinator, "member-zone-id"
        )
        entity.hass = object()  # type: ignore[assignment]
        registry = FakeEntityRegistry()

        with patch.object(er, "async_get", return_value=registry):
            self.assertEqual(
                entity.group_members,
                ["media_player.patio", "media_player.kitchen"],
            )
            await entity.async_unjoin_player()

        self.assertEqual(
            coordinator.client.group_commands,
            [("ungroup", "member-zone-id", "member-zone-id")],
        )
        self.assertEqual(coordinator.refresh_count, 1)

    async def test_slave_unjoins_from_master(self) -> None:
        group_info = [
            {"zoneId": 2, "master": True},
            {"zoneId": 3, "master": False},
        ]
        patio = dict(ZONE, ZoneGroupInfo=group_info)
        kitchen = dict(
            ZONE,
            ZoneID=3,
            PersistentZoneID="member-zone-id",
            Name="Kitchen",
            ZoneGroupInfo=group_info,
        )
        coordinator = FakeCoordinator(_snapshot(zones_data=[patio, kitchen]))
        entity = CasaTunesZoneEntity(  # type: ignore[arg-type]
            coordinator, "member-zone-id"
        )

        await entity.async_unjoin_player()

        self.assertEqual(
            coordinator.client.group_commands,
            [("ungroup", "zone-persistent-id", "member-zone-id")],
        )
