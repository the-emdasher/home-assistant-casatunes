# CasaTunes to Home Assistant capability mapping

## Scope

The captured CasaTunes documentation describes 16 resource families and 344
operations. "Full functionality" therefore has two layers:

1. The client library should model the documented CasaTunes API cleanly.
2. The Home Assistant integration should expose homeowner-facing behavior through
   standard entities and actions, without turning server administration into
   hundreds of noisy or dangerous entities.

## Primary entities

### CasaTunes server device

The config entry represents one CasaTunes server. System information supplies the
stable server identity, host name, CasaTunes version, REST service version, matrix
information, sleep state, and licensing state. Diagnostics must redact the MAC
address, IP address, passwords, account data, and other credentials.

### Media player per zone

Each non-hidden CasaTunes zone becomes a `media_player` entity. The persistent
zone ID is the entity's unique identifier; the numeric zone ID is runtime routing
data and must not be used as identity.

| Home Assistant behavior | CasaTunes data or operation |
| --- | --- |
| State and availability | `GET /zones`, `Power`, and now-playing `Status` |
| Turn on/off | `GET /zones/{id}?Power=on\|off` |
| Volume | `Volume` normalized from 0–100 to 0.0–1.0 |
| Volume step | `AdjustVolume` |
| Mute | `Mute` |
| Source list | `GET /sources`, filtered by the zone's enabled-source data |
| Select source | `SourceID` |
| Play/pause/stop | `/zones/{id}/player/{action}` |
| Previous/next | `/zones/{id}/player/previous\|next` |
| Seek | `/zones/{id}/player/position/{seconds}` |
| Shuffle | `/zones/{id}/player/shuffle/{on\|off}` |
| Repeat | `/zones/{id}/player/repeat/{off\|on\|once}` |
| Metadata | `RESTNowPlayingMediaItem.CurrSong` |
| Artwork | Absolute `ArtworkURI`, or CasaTunes image service for relative IDs |
| Group members | `Shared`, `SharedRoomID`, saved group information, and join/group/ungroup endpoints |
| Browse/search/play media | `/media/zones/{id}`, search, and play endpoints |
| Queue | Zone queue read, play, move, remove, clear, append, and save endpoints |

Supported features must be calculated dynamically from zone capabilities and the
now-playing `Controls` bit field. A radio source, streaming service, and physical
matrix input should not advertise identical controls.

Live transient grouping uses a sequence that is not obvious from the endpoint
names. The leader must be powered before the first member is added. The first
member uses `/zones/{joinId}/join/{toId}`; subsequent members use
`/zones/{id}/group/{zoneId}`. Active members report `Shared: true` and a common
opaque `SharedRoomID`, while `ZoneGroupInfo` remains empty. A member leaves by
calling `/zones/{member}/ungroup/{member}`. Because CasaTunes applies these
changes asynchronously, commands poll the zone list for bounded confirmation
before returning.

## Secondary entities and actions

Capabilities with useful Home Assistant semantics can be exposed selectively:

- Zone `number` entities: balance, bass, treble, maximum volume, power-on
  volume, page volume, fixed volume, and supported low-pass filter values.
- Zone `switch` entities: do-not-disturb, keypad lock, loudness, fixed-volume
  mode, night mode, and supported low-pass filtering.
- Zone `select` entity: equalizer preset where supported.
- Server actions: text-to-speech, paging, doorbell/chime playback, task
  invocation, sleep timers, and safe backup/update status reads.
- Trigger state may become event entities or device triggers after real response
  behavior is captured.

Configuration-oriented entities should be disabled by default to avoid entity
sprawl.

The initial advanced-control implementation follows this rule: balance, bass,
treble, maximum volume, power-on volume, page volume, and fixed volume are
`number` entities; do-not-disturb, keypad lock, loudness, reset-volume-on-power,
and supported low-pass filtering are `switch` entities. Each is created only
when the server and zone capability data support it, and each is disabled by
default.

## Resource disposition

| Resource family | Integration disposition |
| --- | --- |
| `zones`, `sources` | Core state and control |
| `media`, `playlists`, `bookmarks` | Browse, search, favorites, and playback |
| `zonegroups`, `zonegroupitems` | Standard media-player grouping plus optional management actions |
| `equalizers` | Optional zone controls and preset selection |
| `images` | Artwork proxy and caching |
| `tasks`, `triggers` | Optional actions, events, and device automations |
| `system` | Safe information, sleep, TTS, paging, doorbell, and update status only |
| `streamers` | Configuration flow or advanced options where useful |
| `dante`, `diags`, `settings` | Client support and diagnostics; not general-purpose entities |

## Deliberate safety boundaries

The integration will not expose a generic URL or command pass-through action.
In particular, arbitrary command execution, password management, Wi-Fi
credentials, remote-access installation, activation/deactivation, destructive
configuration changes, and backup restoration require dedicated designs and
must never be reachable through user-supplied API paths.

Although CasaTunes documents many mutations as GET requests, the client will
name and separate read and command methods so callers cannot confuse them.

## Initial data update design

The first implementation should use one coordinator update for zone and source
state, with now-playing requests limited to active sources or zones. Command
methods should optimistically refresh only when safe, followed by a coordinator
refresh. Poll frequency will be measured against the real server before choosing
the default.

If the CasaTunes WebSocket service exposes a usable state protocol, it should be
investigated after the polling implementation is correct; the documented REST
surface only shows WebSocket service enable/disable status, not an event schema.
