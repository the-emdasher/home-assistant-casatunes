# CasaTunes enum and image reference

This reference is derived from the CasaTunes server's `Enums.aspx` and
`Images.aspx` pages. The corresponding typed constants live in
`custom_components/casatunes/casatunes_api/enums.py`.

## Playback

### Player status

| Value | Meaning |
| ---: | --- |
| 0 | Stopped |
| 1 | Paused |
| 2 | Playing |
| 3 | Retrying |
| 4 | Buffering |
| 5 | Seeking |

### Repeat mode

| Value | Meaning |
| ---: | --- |
| 0 | Off |
| 1 | On/all |
| 2 | Once/one |

### Media-player control flags

| Flag | Capability |
| ---: | --- |
| `0x01` | Play |
| `0x02` | Stop |
| `0x04` | Pause |
| `0x08` | Shuffle |
| `0x10` | Repeat |
| `0x20` | Next track |
| `0x40` | Previous track |
| `0x80` | Display progress |
| `0x100` | Seek within a track |
| `0x200` | Display favorite state |
| `0x40000` | Display queue |
| `0x80000` | Thumbs up/down |
| `0x100000` | Rate song |
| `0x200000` | Save as playlist |
| `0x1000000` | Next track currently enabled |
| `0x2000000` | Previous track currently enabled |
| `0x4000000` | Queue display currently enabled |
| `0x8000000` | Artist images available |
| `0x10000000` | Artist biography available |

The API distinguishes capability flags such as “can move to next track” from
current-state flags such as “next track enabled.” Home Assistant feature support
uses the capability flag; a later queue implementation may use both.

The `Controls` field is interpreted only after inspecting the active source's
control type. This prevents a tuner's RDS, band, or seek bit from being mistaken
for media-player Play, Stop, or Pause support.

### Tuner control flags

| Flag | Capability |
| ---: | --- |
| `0x01` | RDS |
| `0x02` | Band selection |
| `0x04` | Seek up |
| `0x08` | Seek down |
| `0x10` | Scan |
| `0x20` | Step |
| `0x200` | Direct-tune AM/FM |
| `0x400` | Direct-tune XM/Sirius |
| `0x800` | Direct-tune DAB |

## Media item flags

Media item flags describe both item type and allowed operations. The documented
values cover tracks, streams, stations, collections, grouped collections,
playlists, continuous streams, image-oriented selection, and permissions for
queueing, selecting, refreshing, deleting, sorting, renaming, searching, and
moving items.

These are an `IntFlag`, not mutually exclusive enum choices.

## Zones and scheduling

- Volume control type: absolute `1`, relative `2`.
- Wired/matrix zone IDs: `0..99`.
- AirPlay zone IDs: `100..999`.
- Multi-zone group IDs: `1000+`.
- Schedule days are bit flags from Sunday `0x01` through Saturday `0x40`.
- Tuner bands: current `-1`, AM `1`, FM `2`, XM `8`, Sirius `0x10`, DAB
  `0x20`.

Persistent zone IDs remain the integration identity. Numeric ranges are useful
for classification and routing only.

## Source enum discrepancy

The enum page labels the hardware/player values `0..17` as `SourceInfo.Type`
and the high-level media-player/tuner/external/browser flags as
`SourceInfo.MediaTypesSupported`.

The live JSON shows different practical placement:

- `SourceType` contains the documented hardware/player values; for example,
  Windows Media Player is `6`.
- `Type` contains the high-level control classification; media player is `1`
  and external device is `4`.
- `MediaTypesSupported` contains a separate bit field not fully described by
  this enum page.

The client names these observed semantics `SourceKind` and
`SourceControlType`, while retaining the raw `MediaTypesSupported` integer.

## Image service

Absolute artwork URIs are returned unchanged. Relative artwork IDs are resolved
through:

```text
http://<server>/casatunes/GetImage.ashx
```

The integration sends the documented parameters `ID`, `Transform`, `Width`,
`Height`, `Reflection`, `MinWidth`, `MinHeight`, and `Type`. Default artwork is
requested as a 500×500 aspect-fill JPEG without reflection.

### Transform values

| Value | Transform |
| ---: | --- |
| 0 | Raw/no transform |
| 1 | Aspect fill |
| 2 | Aspect fit |
| 3 | Scale to fit |
| 4–6 | Top left, center, right |
| 7–9 | Center left, center, right |
| 10–12 | Bottom left, center, right |
| 13 | Minimum aspect fit |

Supported output types are `PNG` and `JPG`.
