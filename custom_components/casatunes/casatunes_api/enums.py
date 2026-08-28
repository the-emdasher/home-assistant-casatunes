"""Documented CasaTunes REST API enumeration values."""

from __future__ import annotations

from enum import IntEnum, IntFlag, StrEnum


class MediaItemFlag(IntFlag):
    """RESTMediaItem.Flags and RESTMediaCollectionItem.Flags."""

    TRACK = 0x01
    STREAM = 0x02
    STATION = 0x04
    MEDIA_COLLECTION = 0x08
    GROUPED_COLLECTION = 0x10
    PLAYLIST = 0x20
    CONTINUOUS_STREAM = 0x40
    SELECT_ITEMS_BY_IMAGE_RECOMMENDED = 0x100
    ALLOW_ADD_TO_QUEUE = 0x1000
    ALLOW_SELECT = 0x2000
    ALLOW_REFRESH = 0x4000
    ALLOW_DELETE = 0x8000
    ALLOW_SORT_AND_INDEX = 0x20000
    ALLOW_RENAME = 0x100000
    ALLOW_SEARCH = 0x200000
    ALLOW_MOVE = 0x400000


class PlayerControl(IntFlag):
    """RESTNowPlayingMediaItem.Controls for media-player sources."""

    PLAY = 0x01
    STOP = 0x02
    PAUSE = 0x04
    SHUFFLE = 0x08
    REPEAT = 0x10
    NEXT_TRACK = 0x20
    PREVIOUS_TRACK = 0x40
    DISPLAY_PROGRESS = 0x80
    SEEK = 0x100
    DISPLAY_FAVORITE = 0x200
    DISPLAY_QUEUE = 0x40000
    THUMBS_UP_DOWN = 0x80000
    RATE_SONG = 0x100000
    SAVE_AS_PLAYLIST = 0x200000
    NEXT_TRACK_ENABLED = 0x1000000
    PREVIOUS_TRACK_ENABLED = 0x2000000
    DISPLAY_QUEUE_ENABLED = 0x4000000
    ARTIST_IMAGES_AVAILABLE = 0x8000000
    ARTIST_BIO_AVAILABLE = 0x10000000


class TunerControl(IntFlag):
    """RESTNowPlayingMediaItem.Controls for tuner sources."""

    RDS = 0x01
    BANDS = 0x02
    SEEK_UP = 0x04
    SEEK_DOWN = 0x08
    SCAN = 0x10
    STEP = 0x20
    DIRECT_TUNE_AM_FM = 0x200
    DIRECT_TUNE_XM_SIRIUS = 0x400
    DIRECT_TUNE_DAB = 0x800


class PlayerStatus(IntEnum):
    """RESTNowPlayingMediaItem.Status."""

    STOPPED = 0
    PAUSED = 1
    PLAYING = 2
    RETRYING = 3
    BUFFERING = 4
    SEEKING = 5


class PlayerRepeatMode(IntEnum):
    """RESTNowPlayingMediaItem.RepeatMode."""

    OFF = 0
    ON = 1
    ONCE = 2


class VolumeControlType(IntEnum):
    """RESTZone.VolumeControlType."""

    ABSOLUTE = 1
    RELATIVE = 2


class DayOfWeek(IntFlag):
    """RESTScheduleItem.DaysOfTheWeek."""

    SUNDAY = 0x01
    MONDAY = 0x02
    TUESDAY = 0x04
    WEDNESDAY = 0x08
    THURSDAY = 0x10
    FRIDAY = 0x20
    SATURDAY = 0x40


class TunerBand(IntEnum):
    """Tuner bandId."""

    CURRENT = -1
    AM = 0x01
    FM = 0x02
    XM = 0x08
    SIRIUS = 0x10
    DAB = 0x20


class SourceKind(IntEnum):
    """Documented source hardware/player type.

    Live responses place these values in ``SourceType``, despite the enum page
    labeling them as ``SourceInfo.Type``.
    """

    NONE = 0
    RUSSOUND_AM_FM_TUNER = 1
    RUSSOUND_XM_TUNER = 2
    NUVO_AM_FM_TUNER = 3
    NUVO_XM_TUNER = 4
    XANTECH_AM_FM_TUNER = 5
    WINDOWS_MEDIA_PLAYER = 6
    BARIX_ESTREAMER_PLAYER = 7
    CATALOGED_SOURCE = 8
    OTHER = 9
    RUSSOUND_SIRIUS_TUNER = 10
    NUVO_AM_FM_T2SR = 11
    NUVO_SIRIUS_T2SR = 12
    ONKYO_TUNER_OR_RECEIVER = 13
    NUVO_T2_DAB = 14
    ARCAM_T32 = 15
    CAMBRIDGE_650T = 16
    BROWSER_SOURCE = 17


class SourceControlType(IntFlag):
    """High-level source control classification.

    Live responses place these values in ``Type``, despite the enum page
    labeling them as ``SourceInfo.MediaTypesSupported``.
    """

    MEDIA_PLAYER = 0x01
    TUNER = 0x02
    EXTERNAL_DEVICE = 0x04
    BROWSER_CONTROLLED_DEVICE = 0x08


class ControllerFeature(IntFlag):
    """RESTSystemInfo.ControllerFeatures."""

    LOUDNESS_COMPENSATION = 0x01
    HARDWARE_MASTER_MODE = 0x02
    HARDWARE_PARTY_MODE = 0x04
    HARDWARE_DND = 0x08
    HARDWARE_KEYPAD_LOCK = 0x10
    POWER_ON_VOLUME = 0x20
    MAXIMUM_VOLUME = 0x40
    RESET_VOLUME_ON_POWER = 0x80
    PAGE_VOLUME = 0x100
    MUTE_PAGING = 0x200
    RELATIVE_VOLUME_ONLY = 0x2000
    EQ_SETTINGS = 0x4000
    BALANCE_SETTING = 0x8000
    ADD_REMOVE_ZONES = 0x40000000


class MessageButton(IntFlag):
    """RESTMessage.Buttons."""

    NONE = 0
    OK = 0x01
    CANCEL = 0x02
    YES = 0x04
    NO = 0x08


class ImageTransform(IntEnum):
    """CasaTunes image service transform modes."""

    RAW = 0
    ASPECT_FILL = 1
    ASPECT_FIT = 2
    SCALE_TO_FIT = 3
    TOP_LEFT = 4
    TOP_CENTER = 5
    TOP_RIGHT = 6
    CENTER_LEFT = 7
    CENTER = 8
    CENTER_RIGHT = 9
    BOTTOM_LEFT = 10
    BOTTOM_CENTER = 11
    BOTTOM_RIGHT = 12
    MIN_ASPECT_FIT = 13


class ImageType(StrEnum):
    """CasaTunes image service output types."""

    PNG = "PNG"
    JPEG = "JPG"
