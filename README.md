# CasaTunes for Home Assistant

A clean-room Home Assistant integration for CasaTunes 5 systems, built from
CasaTunes' documented REST API.

The project now contains an initial working integration slice. See:

- [CasaTunes REST API catalog](docs/API_CATALOG.md)
- [Home Assistant capability mapping](docs/HOME_ASSISTANT_MAPPING.md)
- [Initial live response capture](docs/LIVE_CAPTURE.md)
- [Enum and image reference](docs/API_REFERENCE_VALUES.md)
- [Release notes](CHANGELOG.md)

## Design goals

- Use Home Assistant's standard media-player behavior wherever possible.
- Keep all network I/O asynchronous and isolate it in a reusable client library.
- Determine supported features dynamically from CasaTunes source and zone
  capability data.
- Make potentially disruptive or administrative operations explicit and safe.
- Support UI configuration, stable unique IDs, diagnostics, reconfiguration,
  unload/reload, and comprehensive fixture-based tests from the start.

No code from previous CasaTunes Home Assistant integrations is used.

## Installation with HACS

This integration is currently distributed as a custom HACS repository:

1. In HACS, open **Integrations**.
2. Open the three-dot menu and choose **Custom repositories**.
3. Enter `https://github.com/the-emdasher/home-assistant-casatunes` and select
   **Integration** as the category.
4. Add the repository, select **CasaTunes**, and choose **Download**.
5. Restart Home Assistant.
6. Go to **Settings > Devices & services > Add integration**, search for
   **CasaTunes**, and enter the CasaTunes server connection details.

HACS requires access to the public GitHub repository when initially adding or
updating the integration.

## Group-volume Tile feature

CasaTunes includes a custom feature for Home Assistant Tile cards. It adds a
mute button, volume slider, and grouped-speaker button in one row. When the
speaker button is selected, a modal shows a prominent Master section followed
by independent controls for every active joined room. This feature requires
Home Assistant 2026.6 or newer.

After installing or updating CasaTunes and restarting Home Assistant, register
the bundled JavaScript module once:

1. Go to **Settings > Dashboards**.
2. Open the three-dot menu and select **Resources**.
3. Add `/casatunes_frontend/casatunes-group-volume.js` as a **JavaScript
   module**.
4. Refresh the Home Assistant frontend.

Add or edit a Tile card and select the CasaTunes zone that should be treated as
the group Master. Add **CasaTunes group volume** under the card's features and
remove the built-in volume-slider feature to avoid showing two sliders.

The equivalent YAML is:

```yaml
type: tile
entity: media_player.office
features:
  - type: custom:casatunes-group-volume-card-feature
```

The speaker button is disabled when the selected Master has no active group
members. Joined entities are discovered from Home Assistant's standard
`group_members` state attribute; no room names are hard-coded.

## Current implementation

- UI setup using host and REST API port
- Connection validation and duplicate-server detection
- One coordinated snapshot of server, zone, source, and now-playing state
- A media-player entity for each visible zone, with an option to include hidden
  zones
- Power, volume, mute, source, transport, seek, repeat, and shuffle controls
- Native Home Assistant media browsing and search over CasaTunes collections
- Play-media and enqueue routing, queue browsing, queue-item playback, and queue
  clearing
- Standard Home Assistant speaker grouping and ungrouping mappings
- Capability-driven advanced zone numbers and switches, disabled by default
- Host/port reconfiguration, reload-on-change options, and privacy-safe
  diagnostics
- Source-centric metadata and CasaTunes artwork URL handling
- Automatic recovery from temporary connection failures
- Fixture-based client/model tests plus Home Assistant config-flow,
  coordinator, entity-property, feature, and command-mapping tests
- Guarded, state-restoring live control harnesses for deliberately selected
  zones, media queues, and zone pairs

The integration is still pre-release. EQ preset selection, playlist editing,
announcements, tasks, and broader end-to-end Home Assistant coverage remain
before normal installation is recommended.

## Development checks

```shell
python3 -m unittest discover -s tests -t . -v
python3 -m compileall -q custom_components tests tools
ruff check .
ruff format --check .
```

The optional probes perform only read operations and print sanitized summaries.
The first covers the coordinator; the second covers media roots, one nested
collection, search, and the queue:

```shell
python3 tools/probe_readonly.py casaserver.local
python3 tools/probe_media_readonly.py casaserver.local "Test Zone"
python3 tools/probe_capabilities_readonly.py casaserver.local "Test Zone"
```

Live control validation is intentionally separate and requires an explicit
acknowledgement flag. Each harness uses exact visible-zone matches and guarded
preconditions appropriate to the operation:

```shell
python3 tools/live_test_zone.py casaserver.local "Test Zone" --execute
python3 tools/live_test_media.py casaserver.local "Test Zone" --execute
python3 tools/live_test_grouping.py casaserver.local "Leader Zone" \
  "Joining Zone" --execute
```
