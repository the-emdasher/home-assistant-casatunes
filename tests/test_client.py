"""Tests for the asynchronous CasaTunes client."""

from __future__ import annotations

import unittest
from typing import Any

from casatunes_api.client import CasaTunesClient
from casatunes_api.enums import ImageTransform, ImageType
from casatunes_api.exceptions import CasaTunesResponseError

from tests.test_models import (
    MEDIA_COLLECTION,
    MEDIA_ITEM,
    NOW_PLAYING,
    SOURCE,
    SYSTEM,
    ZONE,
    ZONE_CAPABILITIES,
)


class FakeResponse:
    def __init__(self, payload: Any, status: int = 200) -> None:
        self.payload = payload
        self.status = status

    async def __aenter__(self) -> FakeResponse:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def json(self, *, content_type: None = None) -> Any:
        return self.payload

    async def text(self) -> str:
        return str(self.payload)

    async def read(self) -> bytes:
        return b""


class FakeSession:
    def __init__(self, responses: dict[str, Any]) -> None:
        self.responses = responses
        self.requests: list[str] = []
        self.request_kwargs: list[dict[str, Any]] = []

    async def get(self, url: Any, **kwargs: Any) -> FakeResponse:
        path = url.path.removeprefix("/api/v1/")
        self.requests.append(path)
        self.request_kwargs.append(kwargs)
        payload = self.responses[path]
        if isinstance(payload, FakeResponse):
            return payload
        return FakeResponse(payload)


class ClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_snapshot_joins_four_documented_reads(self) -> None:
        session = FakeSession(
            {
                "system/info": SYSTEM,
                "zones": [ZONE],
                "sources": [SOURCE],
                "sources/nowplaying": [NOW_PLAYING],
            }
        )
        client = CasaTunesClient("casaserver.local", session)  # type: ignore[arg-type]

        snapshot = await client.async_get_snapshot()

        self.assertEqual(client.base_url, "http://casaserver.local:8735/api/v1")
        self.assertEqual(snapshot.system.host_name, "CASASERVER")
        self.assertEqual(
            snapshot.zones_by_persistent_id["zone-persistent-id"].name, "Patio"
        )
        self.assertEqual(snapshot.sources_by_id[2].name, "Player A")
        self.assertEqual(
            snapshot.now_playing_by_source_id[2].current_song.title, "Test Song"
        )
        self.assertCountEqual(
            session.requests,
            ["system/info", "zones", "sources", "sources/nowplaying"],
        )

    async def test_get_one_zone(self) -> None:
        session = FakeSession({"zones/zone-persistent-id": ZONE})
        client = CasaTunesClient("casaserver.local", session)  # type: ignore[arg-type]

        zone = await client.async_get_zone("zone-persistent-id")

        self.assertEqual(zone.persistent_zone_id, "zone-persistent-id")
        self.assertEqual(session.requests, ["zones/zone-persistent-id"])

    async def test_invalid_collection_response(self) -> None:
        session = FakeSession({"zones": {"not": "a list"}})
        client = CasaTunesClient("http://casaserver.local:8735/casadev", session)  # type: ignore[arg-type]
        with self.assertRaises(CasaTunesResponseError):
            await client.async_get_zones()

    async def test_zone_command_serializes_boolean(self) -> None:
        updated_zone = dict(ZONE, Power=False, Mute=True)
        session = FakeSession({"zones/zone-persistent-id": updated_zone})
        client = CasaTunesClient("casaserver.local", session)  # type: ignore[arg-type]

        result = await client.async_update_zone(
            "zone-persistent-id", Power=False, Mute=True, Volume=25
        )

        self.assertFalse(result.power)
        self.assertEqual(
            session.request_kwargs[0]["params"],
            {"Power": "false", "Mute": "true", "Volume": 25},
        )

    async def test_player_action_is_allowlisted(self) -> None:
        session = FakeSession(
            {"zones/zone-persistent-id/player/play": {"Result": True}}
        )
        client = CasaTunesClient("casaserver.local", session)  # type: ignore[arg-type]
        await client.async_player_action("zone-persistent-id", "play")
        with self.assertRaises(ValueError):
            await client.async_player_action("zone-persistent-id", "not-an-action")

    async def test_media_browse_play_and_queue_routes(self) -> None:
        session = FakeSession(
            {
                "media/zones/zone-persistent-id": MEDIA_COLLECTION,
                "media/collection-id": MEDIA_COLLECTION,
                "media/zones/zone-persistent-id/search/no match": MEDIA_COLLECTION,
                "media/search/collection-id/song": MEDIA_COLLECTION,
                "zones/zone-persistent-id/queue": {
                    "StartIndex": 0,
                    "TotalAvailable": 1,
                    "MediaItems": [MEDIA_ITEM],
                },
                "media/zones/zone-persistent-id/play/media-item-id": {"Result": 1},
                "zones/zone-persistent-id/queue/play/0": FakeResponse(None),
                "zones/zone-persistent-id/queue/delete": FakeResponse(None),
                "zones/zone-persistent-id/queue/delete/0": FakeResponse(None),
                "zones/zone-persistent-id/queue/move/0/to/1": FakeResponse(None),
            }
        )
        client = CasaTunesClient("casaserver.local", session)  # type: ignore[arg-type]

        root = await client.async_browse_zone("zone-persistent-id")
        child = await client.async_browse_media("collection-id")
        zone_search = await client.async_search_zone("zone-persistent-id", "no match")
        media_search = await client.async_search_media("collection-id", "song")
        queue = await client.async_get_zone_queue("zone-persistent-id")
        result = await client.async_play_media(
            "zone-persistent-id",
            "media-item-id",
            add_to_queue=True,
            auto_start=False,
        )
        await client.async_play_queue_item("zone-persistent-id", 0)
        await client.async_clear_queue("zone-persistent-id")
        await client.async_remove_queue_item("zone-persistent-id", 0)
        await client.async_move_queue_item("zone-persistent-id", 0, 1)

        self.assertEqual(root.title, "Music")
        self.assertEqual(child.media_items[0].id, "media-item-id")
        self.assertEqual(zone_search.title, "Music")
        self.assertEqual(media_search.title, "Music")
        self.assertEqual(queue.total_available, 1)
        self.assertEqual(result, 1)
        self.assertEqual(
            session.request_kwargs[5]["params"],
            {"addToQueue": "true", "autoStart": "false"},
        )
        self.assertEqual(
            session.requests,
            [
                "media/zones/zone-persistent-id",
                "media/collection-id",
                "media/zones/zone-persistent-id/search/no match",
                "media/search/collection-id/song",
                "zones/zone-persistent-id/queue",
                "media/zones/zone-persistent-id/play/media-item-id",
                "zones/zone-persistent-id/queue/play/0",
                "zones/zone-persistent-id/queue/delete",
                "zones/zone-persistent-id/queue/delete/0",
                "zones/zone-persistent-id/queue/move/0/to/1",
            ],
        )

    async def test_queue_indexes_must_not_be_negative(self) -> None:
        client = CasaTunesClient("casaserver.local", FakeSession({}))  # type: ignore[arg-type]

        with self.assertRaises(ValueError):
            await client.async_play_queue_item("zone-persistent-id", -1)
        with self.assertRaises(ValueError):
            await client.async_remove_queue_item("zone-persistent-id", -1)
        with self.assertRaises(ValueError):
            await client.async_move_queue_item("zone-persistent-id", 0, -1)

    async def test_group_routes(self) -> None:
        session = FakeSession(
            {
                "zones/zone-persistent-id/group": [ZONE],
                "zones/zone-persistent-id/group/member-zone-id": {"Result": True},
                "zones/zone-persistent-id/capabilities": ZONE_CAPABILITIES,
                "zones/member-zone-id/join/zone-persistent-id": {"Result": True},
                "zones/zone-persistent-id/ungroup/member-zone-id": {"Result": True},
            }
        )
        client = CasaTunesClient("casaserver.local", session)  # type: ignore[arg-type]

        groupable = await client.async_get_groupable_zones("zone-persistent-id")
        capabilities = await client.async_get_zone_capabilities("zone-persistent-id")
        await client.async_group_zone("zone-persistent-id", "member-zone-id")
        await client.async_join_zone("member-zone-id", "zone-persistent-id")
        await client.async_ungroup_zone("zone-persistent-id", "member-zone-id")

        self.assertEqual(groupable[0].persistent_zone_id, "zone-persistent-id")
        self.assertEqual(capabilities.eq_settings.maximum, 18)
        self.assertEqual(
            session.requests,
            [
                "zones/zone-persistent-id/group",
                "zones/zone-persistent-id/capabilities",
                "zones/zone-persistent-id/group/member-zone-id",
                "zones/member-zone-id/join/zone-persistent-id",
                "zones/zone-persistent-id/ungroup/member-zone-id",
            ],
        )

    async def test_rejected_group_command_raises(self) -> None:
        session = FakeSession(
            {
                "zones/zone-persistent-id/group/member-zone-id": {"Result": False},
                "zones/member-zone-id/join/zone-persistent-id": {"Result": False},
            }
        )
        client = CasaTunesClient("casaserver.local", session)  # type: ignore[arg-type]

        with self.assertRaisesRegex(CasaTunesResponseError, "rejected"):
            await client.async_group_zone("zone-persistent-id", "member-zone-id")
        with self.assertRaisesRegex(CasaTunesResponseError, "rejected"):
            await client.async_join_zone("member-zone-id", "zone-persistent-id")

    def test_artwork_url(self) -> None:
        client = CasaTunesClient("casaserver.local", FakeSession({}))  # type: ignore[arg-type]
        self.assertEqual(
            client.artwork_url("https://example.com/cover.jpg"),
            "https://example.com/cover.jpg",
        )
        resolved = client.artwork_url("relative artwork/id")
        self.assertIn("http://casaserver.local/casatunes/GetImage.ashx?", resolved)
        self.assertIn("ID=relative+artwork/id", resolved)
        self.assertIn("Transform=1", resolved)
        self.assertIn("Reflection=0", resolved)
        self.assertIn("MinWidth=0", resolved)
        self.assertIn("MinHeight=0", resolved)
        self.assertIn("Type=JPG", resolved)

        png = client.artwork_url(
            "image-id",
            transform=ImageTransform.CENTER,
            width=200,
            height=100,
            reflection=25,
            image_type=ImageType.PNG,
        )
        self.assertIn("Transform=8", png)
        self.assertIn("Width=200", png)
        self.assertIn("Height=100", png)
        self.assertIn("Reflection=25", png)
        self.assertIn("Type=PNG", png)

    def test_address_validation(self) -> None:
        session = FakeSession({})
        with self.assertRaises(ValueError):
            CasaTunesClient("ftp://casaserver.local", session)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            CasaTunesClient("", session)  # type: ignore[arg-type]
