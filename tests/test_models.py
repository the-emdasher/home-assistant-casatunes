"""Tests for CasaTunes response models."""

from __future__ import annotations

import unittest

from casatunes_api.enums import (
    ControllerFeature,
    MediaItemFlag,
    PlayerControl,
    SourceControlType,
    SourceKind,
)
from casatunes_api.exceptions import CasaTunesResponseError
from casatunes_api.models import (
    MediaCollection,
    MediaQueue,
    NowPlaying,
    Source,
    SystemInfo,
    Zone,
    ZoneCapabilities,
)

SYSTEM = {
    "AppName": "CasaTunes",
    "HostName": "CASASERVER",
    "MACAddress": "001122334455",
    "CasaTunesVersion": "5.00.260818",
    "RESTServicesVersion": "1.107",
    "IsLicenseValid": True,
    "IsSystemSleepEnabled": False,
    "IsPasswordRequired": False,
    "IsSettingsPasswordRequired": False,
    "VolumeSettings": {"Minimum": 0, "Maximum": 100, "Increment": 1},
    "EQSettings": {"Minimum": -18, "Maximum": 18, "Increment": 2},
    "MatrixInfo": [{"Title": "Test matrix"}],
    "ControllerFeatures": int(
        ControllerFeature.LOUDNESS_COMPENSATION
        | ControllerFeature.HARDWARE_DND
        | ControllerFeature.HARDWARE_KEYPAD_LOCK
        | ControllerFeature.RESET_VOLUME_ON_POWER
    ),
}

ZONE = {
    "ZoneID": 2,
    "PersistentZoneID": "zone-persistent-id",
    "Name": "Patio",
    "Hidden": False,
    "Power": True,
    "Mute": False,
    "Volume": 34,
    "MaxVolume": 80,
    "SourceID": 2,
    "EnabledSources": 15,
    "VolumeControlType": 1,
    "FixedVolumeEnabled": False,
    "FixedVolume": 100,
    "PageVolume": 35,
    "PowerOnVolume": 30,
    "ResetPowerOnVolume": True,
    "ZoneGroupInfo": [],
}

ZONE_CAPABILITIES = {
    "Hide": True,
    "ExcludeFromPowerAllZones": True,
    "Balance": True,
    "EQ": True,
    "EQPresets": False,
    "Loudness": True,
    "StereoOrMono": False,
    "AbsoluteVolume": True,
    "PowerOnVolume": 5,
    "MaxVolume": True,
    "MutePageVolume": 5,
    "FixedVolume": 5,
    "RenameZone": True,
    "AddRemoveZones": False,
    "BalanceSettings": {"Minimum": -18, "Maximum": 18, "Increment": 2},
    "EQSettings": {"Minimum": -18, "Maximum": 18, "Increment": 2},
    "AllowRoomGroupAssignedToKeypad": False,
}

SOURCE = {
    "SourceID": 2,
    "Name": "Player A",
    "Hidden": False,
    "IsShared": True,
    "MediaTypesSupported": 33024,
    "SourceType": 6,
    "Type": 1,
}

NOW_PLAYING = {
    "SourceID": 2,
    "Status": 2,
    "Controls": 511,
    "RepeatMode": 0,
    "ShuffleMode": False,
    "CurrProgress": 42,
    "QueueCount": 3,
    "QueueSongIndex": 1,
    "CurrSong": {
        "ID": "song-1",
        "PersistentID": "persistent-song-1",
        "Title": "Test Song",
        "Album": "Test Album",
        "Artists": "Test Artist",
        "ArtworkURI": "artwork-id",
        "Duration": 180.5,
        "Type": 1,
        "ServiceName": "Test Service",
    },
}

MEDIA_ITEM = {
    "Flags": int(MediaItemFlag.TRACK | MediaItemFlag.ALLOW_ADD_TO_QUEUE),
    "QueueType": "MEDIAPLAYER",
    "ID": "media-item-id",
    "PersistentID": "persistent-media-item-id",
    "GroupName": "Songs",
    "Title": "Browsable Song",
    "Type": 1,
    "ArtworkURI": "browse-artwork-id",
    "ArtworkRatio": 1.0,
    "Duration": 201.5,
    "TotalItems": -1,
    "DisplayInfo": ["Test Artist"],
}

MEDIA_COLLECTION = {
    "Flags": int(MediaItemFlag.MEDIA_COLLECTION | MediaItemFlag.ALLOW_SEARCH),
    "QueueType": "NONE",
    "ID": "collection-id",
    "PersistentID": "persistent-collection-id",
    "Title": "Music",
    "ArtworkURI": "collection-artwork-id",
    "ArtworkRatio": 1.0,
    "SearchPlaceholderText": "Search music",
    "StartIndex": 0,
    "TotalAvailable": 1,
    "MediaItems": [MEDIA_ITEM],
    "DisplayInfo": [],
}


class ModelTests(unittest.TestCase):
    def test_system_info(self) -> None:
        system = SystemInfo.from_dict(SYSTEM)
        self.assertEqual(system.casatunes_version, "5.00.260818")
        self.assertEqual(system.volume_settings.maximum, 100)
        self.assertEqual(system.matrix_count, 1)

    def test_zone_source_bit_field(self) -> None:
        zone = Zone.from_dict(ZONE)
        self.assertTrue(zone.supports_source(0))
        self.assertTrue(zone.supports_source(3))
        self.assertFalse(zone.supports_source(4))
        self.assertEqual(zone.power_on_volume, 30)
        self.assertEqual(zone.page_volume, 35)

    def test_zone_transient_shared_room(self) -> None:
        zone = Zone.from_dict(
            dict(
                ZONE,
                Shared=True,
                SharedRoomID="transient-shared-room-id",
            )
        )

        self.assertTrue(zone.shared)
        self.assertEqual(zone.shared_room_id, "transient-shared-room-id")

        with self.assertRaises(CasaTunesResponseError):
            Zone.from_dict(dict(ZONE, SharedRoomID=123))

    def test_zone_capabilities(self) -> None:
        capabilities = ZoneCapabilities.from_dict(ZONE_CAPABILITIES)

        self.assertTrue(capabilities.balance)
        self.assertTrue(capabilities.eq)
        self.assertFalse(capabilities.eq_presets)
        self.assertEqual(capabilities.balance_settings.minimum, -18)
        self.assertEqual(capabilities.eq_settings.increment, 2)

    def test_source(self) -> None:
        source = Source.from_dict(SOURCE)
        self.assertTrue(source.is_shared)
        self.assertEqual(source.source_id, 2)
        self.assertEqual(source.source_kind, SourceKind.WINDOWS_MEDIA_PLAYER)
        self.assertEqual(source.control_type, SourceControlType.MEDIA_PLAYER)

    def test_now_playing_with_optional_song(self) -> None:
        now_playing = NowPlaying.from_dict(NOW_PLAYING)
        self.assertEqual(now_playing.current_song.title, "Test Song")
        self.assertTrue(now_playing.supports(PlayerControl.SEEK))

        without_song = NowPlaying.from_dict(
            {key: value for key, value in NOW_PLAYING.items() if key != "CurrSong"}
        )
        self.assertIsNone(without_song.current_song)

    def test_required_identity_is_validated(self) -> None:
        invalid_zone = dict(ZONE)
        invalid_zone.pop("PersistentZoneID")
        with self.assertRaises(CasaTunesResponseError):
            Zone.from_dict(invalid_zone)

    def test_media_collection_and_queue_are_tolerant_of_sparse_items(self) -> None:
        collection = MediaCollection.from_dict(MEDIA_COLLECTION)

        self.assertTrue(collection.can_search)
        self.assertEqual(collection.total_available, 1)
        self.assertEqual(collection.media_items[0].title, "Browsable Song")
        self.assertTrue(collection.media_items[0].can_play)
        self.assertFalse(collection.media_items[0].can_expand)

        queue = MediaQueue.from_dict(
            {"StartIndex": 2, "TotalAvailable": 1, "MediaItems": [MEDIA_ITEM]}
        )
        self.assertEqual(queue.start_index, 2)
        self.assertEqual(queue.media_items[0].display_info, ("Test Artist",))
