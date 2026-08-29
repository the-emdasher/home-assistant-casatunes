# Release notes

## 0.1.1 - 2026-08-29

### Fixed

- Keep Home Assistant's mute indicator synchronized after both mute and unmute
  commands, even when CasaTunes briefly returns its previous zone state.
- Update the Home Assistant playback-position control immediately after seeking
  and prevent a stale CasaTunes snapshot from moving it back to the old position.
- Reconcile optimistic mute and seek state with CasaTunes for up to five seconds,
  then return to the server-reported state if a command is not confirmed.

## 0.1.0 - 2026-08-28

### Added

- Initial CasaTunes custom integration for Home Assistant.
- UI configuration, coordinated zone and source state, media-player entities,
  media browsing, queues, grouping, diagnostics, and advanced zone controls.
