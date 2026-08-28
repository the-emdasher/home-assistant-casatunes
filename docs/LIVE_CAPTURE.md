# Initial live response capture

The first read-only capture was taken on 2026-08-28. No commands or
state-changing query parameters were sent.

## Server profile

| Property | Observed value |
| --- | --- |
| CasaTunes version | `5.00.260818` |
| REST services version | `1.107` |
| Matrices | 1 |
| Zones returned | 22 |
| Visible zones | 9 |
| Sources returned | 6 |
| Visible sources | 4 |
| Now-playing records | 2 |

Private host, network, hardware-address, persistent-ID, room-name, source-name,
and media metadata values are intentionally not stored in the repository.

## Confirmed response behavior

- `/system/info` returns a JSON object matching `RESTSystemInfo`.
- `/zones` returns a JSON array using the documented PascalCase field names.
- `/sources` returns a JSON array using the documented `SourceInfo` fields.
- `/sources/nowplaying` is source-centric and does not return one item per zone
  or even one item per configured source. On this system it returns records only
  for the two media-player sources.
- All currently visible matrix zones provide non-empty persistent zone IDs.
- The server advertises a global volume range of 0–100 with increments of 1.
- Source availability for a zone is represented by the `EnabledSources` bit
  field; the current configuration confirms source ID maps to bit position.
- Live source values reveal that the enum page's `Type` and
  `MediaTypesSupported` labels do not match the practical JSON field placement;
  the discrepancy and resulting client names are recorded in the enum reference.

## Implementation consequences

- Zone identity uses `PersistentZoneID`, never `ZoneID` or room name.
- The coordinator fetches now-playing state once and joins it to zones using
  `SourceID`, preventing redundant requests when rooms share a source.
- Physical inputs without now-playing records remain powered `on`; they do not
  incorrectly claim playback features or fabricated metadata.
- Hidden zones are excluded by default but can be included during setup.

## Guarded control validation

A later guarded test used one designated visible wired zone while every other
zone was powered off. The test selected the zone by exact display name and then
required exactly one non-hidden match, so a second hidden endpoint with the same
name was not controlled.

Confirmed behavior:

- Power on/off, absolute volume, relative volume up/down, mute, and source
  selection are accepted through `GET /zones/{id}` query parameters.
- At a known-valid starting volume, `AdjustVolume=1` raised the reported value
  by one and `AdjustVolume=-1` returned it to the starting value.
- A muted matrix zone reports `Volume: 0`. Unmuting restores its prior volume;
  this is device behavior rather than a lost Home Assistant value.
- Absolute volume changes made while a wired zone is powered off can be ignored
  or overwritten by its power-on transition. Tests and restoration logic must
  set volume while the zone is powered on and wait for state to settle.
- The tested hardware did not preserve low requested volume values used during
  the first safety pass. Live tests therefore use the captured valid volume and
  a single increment instead of assuming every advertised 0–100 value maps to a
  useful hardware level.
- Switching to an enabled, visible, unshared source and back succeeded.
- Player play/stop requests were accepted. The designated source had an empty
  queue and correctly remained stopped, so this validates command routing but
  not audible playback.

The harness restores source, volume, mute, power, and transport state in a
`finally` block, waits for the matrix transition, and compares a new read with
the original capture. An independent read confirmed restoration and that the
same-named hidden endpoint was unchanged.

## Media browsing and queue validation

Read-only media browsing returned a sparse `RESTMediaCollectionItem` matching
the documented model: collection metadata at the root and `MediaItems` children.
The designated zone exposed multiple expandable roots, a searchable collection,
and an initially empty `RESTNowPlayingQueue`. Empty documented properties are
omitted from live JSON, so media models treat them as optional.

A guarded queue test selected one item advertised with
`ALLOW_ADD_TO_QUEUE`, requested `addToQueue=true` and `autoStart=false`, verified
the queue, and then cleared it. The request returned `3` and added three tracks;
transport remained stopped. Queue clearing returned a successful response with
no model body and restored the empty queue.

The same test revealed two important side effects:

- Enqueueing powers on an off zone even with `autoStart=false`.
- Enqueueing can clear the zone's mute state.

For safety, Home Assistant advertises and accepts enqueue only while the target
zone is already powered on and unmuted. Normal play-media requests may still
power a zone as users would expect. The browse response also includes selection
history; playing or enqueueing an item can therefore add a history entry even
after the queue is cleared.

The live media harness clears the queue and restores transport, source, volume,
mute, and power through nested `finally` blocks. A separate delayed read
confirmed the visible zone's original state, the hidden same-named endpoint's
state, and an empty queue.

## Zone capabilities

`GET /zones/{id}/capabilities` returned the documented `ZoneCapabilities`
object. On the designated wired zone it advertises balance, EQ, loudness,
absolute volume, maximum volume, power-on volume, page volume, and fixed-volume
configuration. EQ presets and low-pass filtering are not supported there.

The live capability ranges are more precise than the general API parameter
descriptions: balance and EQ both report −18 through 18 in increments of 2.
Advanced Home Assistant entities therefore use each zone's capability response
instead of hard-coded prose ranges. These configuration entities are disabled
by default to avoid entity sprawl and accidental changes.

## Zone grouping validation

A guarded two-room test was later run with an explicitly selected second wired
zone. Both source players were required to be stopped, all zones were initially
off, no group could already exist, and both queues were captured for exact
comparison after cleanup.

The live behavior differs in several important ways from the static model:

- Calling `join` while the intended leader is off can return success without
  creating a group. It can also power the joining room and resume that room's
  queued network-player session after a delay.
- Powering the leader first, waiting for the matrix transition, and then calling
  `/zones/{joinId}/join/{toId}` created the initial two-room group in about one
  second.
- Both physical zones then reported `Shared: true`, the leader's `SourceID`, and
  the same opaque `SharedRoomID`. `ZoneGroupInfo` remained empty on both zones.
- The shared-room token is a correlation value, not a retrievable virtual zone;
  requesting `/zones/{SharedRoomID}` returned HTTP 400.
- `/zones/{id}/group/{zoneId}` adds later rooms to an existing group; it does not
  create the initial group when the leader is not already grouped.
- A member successfully removed itself with
  `/zones/{member}/ungroup/{member}`.

The integration therefore correlates transient group members by
`SharedRoomID`, powers and settles an off leader before the first join, uses
`join` for the first member and `group` for later members, and polls for bounded
confirmation. The live harness also stops originally stopped sources during
cleanup because selecting a queued network source can resume playback after a
delay. Final independent reads confirmed that both rooms, both transport
states, and both queues matched their original state, with no active group or
powered zone remaining.
