# Release notes

## 0.2.1 - 2026-08-29

### Fixed

- Allow an existing CasaTunes config entry to be reconfigured to a new IP
  address when the server reports a different network-interface MAC address.
- Preserve the Home Assistant server and zone device relationships across an IP
  or network-interface change.
- Continue to reject reconfiguration when the target CasaTunes server is already
  configured as a separate entry.

## 0.2.0 - 2026-08-29

### Added

- Bundle a CasaTunes group-volume card feature for Home Assistant Tile cards.
- Require Home Assistant 2026.6 or newer for custom Tile card feature support.
- Place mute, volume, and grouped-speaker controls in one compact feature row.
- Open a responsive group-volume modal from the grouped-speaker button.
- Present the configured Tile entity as a visually prominent Master, followed by
  separate rows for every active joined room.
- Provide independent volume down, slider, volume up, percentage, and mute
  controls for the Master and each joined room.

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
