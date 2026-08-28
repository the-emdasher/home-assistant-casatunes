"""Asynchronous CasaTunes REST client."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import UTC, datetime
from json import JSONDecodeError
from typing import Any
from urllib.parse import quote, urlsplit

import aiohttp
from yarl import URL

from .enums import ImageTransform, ImageType
from .exceptions import CasaTunesConnectionError, CasaTunesResponseError
from .models import (
    CasaTunesSnapshot,
    MediaCollection,
    MediaQueue,
    NowPlaying,
    Source,
    SystemInfo,
    Zone,
    ZoneCapabilities,
)

DEFAULT_PORT = 8735


class CasaTunesClient:
    """Client for a single CasaTunes server."""

    def __init__(
        self,
        host: str,
        session: aiohttp.ClientSession,
        *,
        port: int = DEFAULT_PORT,
        request_timeout: float = 10.0,
    ) -> None:
        scheme, normalized_host, normalized_port = self._normalize_address(host, port)
        self._session = session
        self._request_timeout = request_timeout
        self._web_root = URL.build(scheme=scheme, host=normalized_host)
        self._base_url = URL.build(
            scheme=scheme,
            host=normalized_host,
            port=normalized_port,
            path="/api/v1/",
        )

    @staticmethod
    def _normalize_address(host: str, port: int) -> tuple[str, str, int]:
        candidate = host.strip()
        if not candidate:
            raise ValueError("CasaTunes host must not be empty")

        parsed = urlsplit(candidate if "://" in candidate else f"//{candidate}")
        scheme = parsed.scheme or "http"
        if scheme not in {"http", "https"}:
            raise ValueError("CasaTunes URL must use HTTP or HTTPS")
        if parsed.hostname is None:
            raise ValueError("CasaTunes host is invalid")

        normalized_port = parsed.port or port
        if not 1 <= normalized_port <= 65535:
            raise ValueError("CasaTunes port must be between 1 and 65535")
        return scheme, parsed.hostname, normalized_port

    @property
    def base_url(self) -> str:
        """Return the normalized API root."""
        return str(self._base_url).rstrip("/")

    def artwork_url(
        self,
        artwork_uri: str,
        *,
        transform: ImageTransform = ImageTransform.ASPECT_FILL,
        width: int = 500,
        height: int = 500,
        reflection: int = 0,
        min_width: int = 0,
        min_height: int = 0,
        image_type: ImageType = ImageType.JPEG,
    ) -> str | None:
        """Resolve a CasaTunes artwork ID or absolute URL."""
        if not artwork_uri:
            return None
        parsed = urlsplit(artwork_uri)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return artwork_uri
        return str(
            self._web_root.with_path("/casatunes/GetImage.ashx").with_query(
                {
                    "ID": artwork_uri,
                    "Transform": int(transform),
                    "Width": width,
                    "Height": height,
                    "Reflection": max(0, min(100, reflection)),
                    "MinWidth": min_width,
                    "MinHeight": min_height,
                    "Type": image_type.value,
                }
            )
        )

    async def _get_json(
        self, path: str, params: Mapping[str, str | int | float | bool] | None = None
    ) -> Any:
        url = self._base_url.join(URL(path.lstrip("/")))
        try:
            async with asyncio.timeout(self._request_timeout):
                response = await self._session.get(
                    url,
                    params=params,
                    headers={"Accept": "application/json"},
                )
                async with response:
                    if response.status >= 400:
                        body = (await response.text())[:500]
                        raise CasaTunesResponseError(
                            f"CasaTunes returned HTTP {response.status}: {body}",
                            status=response.status,
                        )
                    try:
                        return await response.json(content_type=None)
                    except (
                        aiohttp.ContentTypeError,
                        JSONDecodeError,
                        ValueError,
                    ) as err:
                        raise CasaTunesResponseError(
                            "CasaTunes returned a non-JSON response",
                            status=response.status,
                        ) from err
        except CasaTunesResponseError:
            raise
        except (TimeoutError, aiohttp.ClientError) as err:
            raise CasaTunesConnectionError(
                f"Unable to communicate with CasaTunes at {self._base_url.host}"
            ) from err

    async def _get_command(
        self, path: str, params: Mapping[str, str | int | float | bool] | None = None
    ) -> None:
        """Invoke a GET-based command whose response body is undocumented."""
        url = self._base_url.join(URL(path.lstrip("/")))
        try:
            async with asyncio.timeout(self._request_timeout):
                response = await self._session.get(
                    url,
                    params=params,
                    headers={"Accept": "application/json"},
                )
                async with response:
                    if response.status >= 400:
                        body = (await response.text())[:500]
                        raise CasaTunesResponseError(
                            f"CasaTunes returned HTTP {response.status}: {body}",
                            status=response.status,
                        )
                    await response.read()
        except CasaTunesResponseError:
            raise
        except (TimeoutError, aiohttp.ClientError) as err:
            raise CasaTunesConnectionError(
                f"Unable to communicate with CasaTunes at {self._base_url.host}"
            ) from err

    @staticmethod
    def _path_segment(value: str | int) -> str:
        """Encode an opaque CasaTunes identifier as one URL path segment."""
        return quote(str(value), safe="")

    @staticmethod
    def _require_object(payload: Any, endpoint: str) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise CasaTunesResponseError(f"{endpoint} did not return an object")
        return payload

    @staticmethod
    def _require_object_list(payload: Any, endpoint: str) -> list[dict[str, Any]]:
        if not isinstance(payload, list) or not all(
            isinstance(item, dict) for item in payload
        ):
            raise CasaTunesResponseError(f"{endpoint} did not return a list of objects")
        return payload

    async def async_get_system_info(self) -> SystemInfo:
        payload = self._require_object(
            await self._get_json("system/info"), "/system/info"
        )
        return SystemInfo.from_dict(payload)

    async def async_get_zones(self) -> tuple[Zone, ...]:
        payload = self._require_object_list(await self._get_json("zones"), "/zones")
        return tuple(Zone.from_dict(item) for item in payload)

    async def async_get_zone(self, zone_id: str) -> Zone:
        """Return one physical or virtual CasaTunes zone."""
        payload = self._require_object(
            await self._get_json(f"zones/{self._path_segment(zone_id)}"),
            f"/zones/{zone_id}",
        )
        return Zone.from_dict(payload)

    async def async_get_sources(self) -> tuple[Source, ...]:
        payload = self._require_object_list(await self._get_json("sources"), "/sources")
        return tuple(Source.from_dict(item) for item in payload)

    async def async_get_now_playing(self) -> tuple[NowPlaying, ...]:
        payload = self._require_object_list(
            await self._get_json("sources/nowplaying"), "/sources/nowplaying"
        )
        return tuple(NowPlaying.from_dict(item) for item in payload)

    async def async_browse_zone(self, zone_id: str) -> MediaCollection:
        """Return the media roots suitable for a zone."""
        payload = self._require_object(
            await self._get_json(
                f"media/zones/{self._path_segment(zone_id)}",
                {
                    "includePlaylists": "true",
                    "maxPlaylists": 50,
                    "includeOtherPlaylists": "true",
                    "maxBookmarks": 50,
                    "includeSelectionHistory": "true",
                },
            ),
            f"/media/zones/{zone_id}",
        )
        return MediaCollection.from_dict(payload)

    async def async_browse_media(
        self,
        media_id: str,
        *,
        limit: int = 200,
        offset: int = 0,
    ) -> MediaCollection:
        """Return one page of a CasaTunes media collection."""
        payload = self._require_object(
            await self._get_json(
                f"media/{self._path_segment(media_id)}",
                {"limit": limit, "offset": offset},
            ),
            f"/media/{media_id}",
        )
        return MediaCollection.from_dict(payload)

    async def async_search_zone(
        self,
        zone_id: str,
        search_text: str,
        *,
        limit: int = 200,
        offset: int = 0,
    ) -> MediaCollection:
        """Search all media services available to a zone."""
        payload = self._require_object(
            await self._get_json(
                "media/zones/"
                f"{self._path_segment(zone_id)}/search/"
                f"{self._path_segment(search_text)}",
                {"limit": limit, "offset": offset},
            ),
            f"/media/zones/{zone_id}/search",
        )
        return MediaCollection.from_dict(payload)

    async def async_search_media(
        self,
        media_id: str,
        search_text: str,
        *,
        limit: int = 200,
        offset: int = 0,
    ) -> MediaCollection:
        """Search within one CasaTunes media collection."""
        payload = self._require_object(
            await self._get_json(
                "media/search/"
                f"{self._path_segment(media_id)}/"
                f"{self._path_segment(search_text)}",
                {"limit": limit, "offset": offset},
            ),
            f"/media/search/{media_id}",
        )
        return MediaCollection.from_dict(payload)

    async def async_get_zone_queue(
        self,
        zone_id: str,
        *,
        limit: int = 200,
        offset: int = 0,
    ) -> MediaQueue:
        """Return one page of a zone's playback queue."""
        payload = self._require_object(
            await self._get_json(
                f"zones/{self._path_segment(zone_id)}/queue",
                {"limit": limit, "offset": offset},
            ),
            f"/zones/{zone_id}/queue",
        )
        return MediaQueue.from_dict(payload)

    async def async_get_groupable_zones(self, zone_id: str) -> tuple[Zone, ...]:
        """Return zones that CasaTunes says can be grouped with a zone."""
        payload = self._require_object_list(
            await self._get_json(f"zones/{self._path_segment(zone_id)}/group"),
            f"/zones/{zone_id}/group",
        )
        return tuple(Zone.from_dict(item) for item in payload)

    async def async_get_zone_capabilities(self, zone_id: str) -> ZoneCapabilities:
        """Return advanced-control capabilities for one zone."""
        payload = self._require_object(
            await self._get_json(f"zones/{self._path_segment(zone_id)}/capabilities"),
            f"/zones/{zone_id}/capabilities",
        )
        return ZoneCapabilities.from_dict(payload)

    async def async_join_zone(self, join_id: str, to_id: str) -> None:
        """Invoke CasaTunes' distinct zone join operation."""
        payload = self._require_object(
            await self._get_json(
                f"zones/{self._path_segment(join_id)}/join/{self._path_segment(to_id)}"
            ),
            f"/zones/{join_id}/join/{to_id}",
        )
        if payload.get("Result") is not True:
            raise CasaTunesResponseError("CasaTunes rejected the zone join")

    async def async_group_zone(self, group_id: str, grouped_zone_id: str) -> None:
        """Add one zone to the synchronized group that another zone belongs to."""
        payload = self._require_object(
            await self._get_json(
                "zones/"
                f"{self._path_segment(group_id)}/group/"
                f"{self._path_segment(grouped_zone_id)}"
            ),
            f"/zones/{group_id}/group/{grouped_zone_id}",
        )
        if payload.get("Result") is not True:
            raise CasaTunesResponseError("CasaTunes rejected the zone group command")

    async def async_ungroup_zone(self, group_id: str, grouped_zone_id: str) -> None:
        """Remove one zone from a synchronized playback group."""
        payload = self._require_object(
            await self._get_json(
                "zones/"
                f"{self._path_segment(group_id)}/ungroup/"
                f"{self._path_segment(grouped_zone_id)}"
            ),
            f"/zones/{group_id}/ungroup/{grouped_zone_id}",
        )
        if payload.get("Result") is not True:
            raise CasaTunesResponseError("CasaTunes rejected the zone ungroup")

    async def async_play_media(
        self,
        zone_id: str,
        media_id: str,
        *,
        add_to_queue: bool = False,
        auto_start: bool = True,
    ) -> int:
        """Play or enqueue a CasaTunes media item in a zone."""
        payload = self._require_object(
            await self._get_json(
                "media/zones/"
                f"{self._path_segment(zone_id)}/play/"
                f"{self._path_segment(media_id)}",
                {
                    "addToQueue": "true" if add_to_queue else "false",
                    "autoStart": "true" if auto_start else "false",
                },
            ),
            f"/media/zones/{zone_id}/play/{media_id}",
        )
        result = payload.get("Result")
        if isinstance(result, bool) or not isinstance(result, int):
            raise CasaTunesResponseError("Play media response has no integer Result")
        return result

    async def async_play_queue_item(self, zone_id: str, index: int) -> None:
        """Start playback at a queue index."""
        if index < 0:
            raise ValueError("Queue index must not be negative")
        await self._get_command(
            f"zones/{self._path_segment(zone_id)}/queue/play/{index}"
        )

    async def async_clear_queue(self, zone_id: str) -> None:
        """Remove every item from a zone queue."""
        await self._get_command(f"zones/{self._path_segment(zone_id)}/queue/delete")

    async def async_remove_queue_item(self, zone_id: str, index: int) -> None:
        """Remove one item from a zone queue."""
        if index < 0:
            raise ValueError("Queue index must not be negative")
        await self._get_command(
            f"zones/{self._path_segment(zone_id)}/queue/delete/{index}"
        )

    async def async_move_queue_item(
        self, zone_id: str, from_index: int, to_index: int
    ) -> None:
        """Move one item within a zone queue."""
        if from_index < 0 or to_index < 0:
            raise ValueError("Queue indexes must not be negative")
        await self._get_command(
            f"zones/{self._path_segment(zone_id)}/queue/move/{from_index}/to/{to_index}"
        )

    async def async_get_snapshot(self) -> CasaTunesSnapshot:
        system, zones, sources, now_playing = await asyncio.gather(
            self.async_get_system_info(),
            self.async_get_zones(),
            self.async_get_sources(),
            self.async_get_now_playing(),
        )
        return CasaTunesSnapshot(
            system=system,
            zones=zones,
            sources=sources,
            now_playing=now_playing,
            captured_at=datetime.now(UTC),
        )

    async def async_update_zone(self, zone_id: str, **changes: object) -> Zone:
        """Update one or more documented zone properties."""
        if not changes:
            raise ValueError("At least one zone property must be supplied")
        params: dict[str, str | int | float] = {}
        for key, value in changes.items():
            if isinstance(value, bool):
                params[key] = "true" if value else "false"
            elif isinstance(value, str | int | float):
                params[key] = value
            else:
                raise TypeError(f"Unsupported value for zone property {key}")
        payload = self._require_object(
            await self._get_json(f"zones/{self._path_segment(zone_id)}", params),
            f"/zones/{zone_id}",
        )
        return Zone.from_dict(payload)

    async def async_player_action(
        self, zone_id: str, action: str, option: str | int | None = None
    ) -> None:
        """Invoke a documented player action for a zone."""
        allowed_actions = {
            "play",
            "pause",
            "stop",
            "toggle",
            "next",
            "previous",
            "thumbsUp",
            "thumbsDown",
            "favorite",
            "repeat",
            "shuffle",
            "position",
            "jump",
        }
        if action not in allowed_actions:
            raise ValueError(f"Unsupported player action: {action}")
        path = f"zones/{self._path_segment(zone_id)}/player/{action}"
        if option is not None:
            path = f"{path}/{option}"
        await self._get_json(path)
