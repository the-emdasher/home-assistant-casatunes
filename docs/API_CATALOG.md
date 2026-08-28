# CasaTunes REST API catalog

Generated from 16 machine-readable resource documents containing 344 operations. The server address is intentionally omitted.

> Important: CasaTunes supports state-changing operations through GET requests. Treat method names as documentation, not as a safety boundary.

## Resource summary

| Resource | Paths | Operations | Models |
| --- | ---: | ---: | ---: |
| /bookmarks | 5 | 5 | 17 |
| /dante | 8 | 8 | 14 |
| /diags | 6 | 6 | 12 |
| /equalizers | 6 | 6 | 11 |
| /images | 4 | 4 | 7 |
| /media | 27 | 27 | 48 |
| /playlists | 11 | 11 | 13 |
| /settings | 116 | 116 | 251 |
| /sources | 15 | 15 | 28 |
| /streamers | 7 | 7 | 20 |
| /system | 60 | 60 | 96 |
| /tasks | 29 | 29 | 67 |
| /triggers | 3 | 3 | 5 |
| /zonegroupitems | 1 | 1 | 1 |
| /zonegroups | 7 | 7 | 13 |
| /zones | 39 | 39 | 69 |

## `/bookmarks`

| Method | Path | Summary | Parameters | Response |
| --- | --- | --- | --- | --- |
 | GET | `/bookmarks/` | Bookmarks | limit, offset, sortByRecentlyPlayed | `RESTMediaCollectionItem` |
 | GET | `/bookmarks/add/{id}` | Add a bookmark | id | `Result` |
 | GET | `/bookmarks/remove/{id}` | Remove a bookmark | id | `Result` |
 | GET | `/bookmarks/sources/{id}` | Get bookmarks suitable for the specified source. | id | `RESTMediaCollectionItem` |
 | GET | `/bookmarks/zones/{id}` | Get bookmarks suitable for the specified zone. | id | `RESTMediaCollectionItem` |

## `/dante`

| Method | Path | Summary | Parameters | Response |
| --- | --- | --- | --- | --- |
 | GET | `/dante` | Get all the Dante Information |  | `DanteInfoResponse` |
 | POST | `/dante/account` | Set Dante Account |  | `DanteInfoResponse` |
 | POST | `/dante/apikey` | Set Dante ApiKey |  | `DanteInfoResponse` |
 | DELETE | `/dante/devices` | Delete Dante Device |  | `DanteInfoResponse` |
 | POST | `/dante/devices/name` | Set Dante Device name |  | `DanteInfoResponse` |
 | POST | `/dante/devices/visibility` | Set Dante Device visibility |  | `DanteInfoResponse` |
 | POST | `/dante/domain` | Set Dante Domain |  | `DanteInfoResponse` |
 | GET | `/dante/refresh` | Refresh all the Dante Information |  | `DanteInfoResponse` |

## `/diags`

| Method | Path | Summary | Parameters | Response |
| --- | --- | --- | --- | --- |
 | GET | `/diags/keypads` | Get Keypad Diagnostics |  | `List[RESTKeypadDiags]` |
 | GET | `/diags/keypads/reset/{serialPort}` | Reset USB Keypad Hub | serialPort | `RESTResultBoolean` |
 | GET | `/diags/keypads/reset/{serialPort}/{keypadID}` | Reset Keypad in USB Keypad Hub | serialPort, keypadID, removeOnly | `RESTResultBoolean` |
 | GET | `/diags/ping` | Get Internet Monitoring results |  | `InternetMonitorResults` |
 | GET | `/diags/ping/{action}` | Start, Stop or Reset Internet Monitoring | action, ipAddress, interval, timeout | `InternetMonitorResults` |
 | GET | `/diags/ping/notifications/{enable}` | Enable Internet Failure Notifications | enable | `RESTResultBoolean` |

## `/equalizers`

| Method | Path | Summary | Parameters | Response |
| --- | --- | --- | --- | --- |
 | GET | `/equalizers/` | Get List of Equalizers |  | `List[EQSettings]` |
 | POST | `/equalizers/` | Add New Equalizer | name, isPreset, canDelete | `EQSettings` |
 | GET | `/equalizers/{id}` | Get Equalizer | id | `EQSettings` |
 | DELETE | `/equalizers/{id}` | Delete Equalizer | id | `RESTResultBoolean` |
 | PUT | `/equalizers/{id}` | Update Equalizer | id | `RESTResultBoolean` |
 | POST | `/equalizers/type/{eqType}` | Sets the type of EQ to use | eqType | `` |

## `/images`

| Method | Path | Summary | Parameters | Response |
| --- | --- | --- | --- | --- |
 | GET | `/images/{id}` | Get image | id, imageTransform, width, height, minWidthBeforeScaling, minHeightBeforeScaling, reflectionPercent, backgroundColor, useDefaultImage, theme, safeBase64Encoded | `Stream` |
 | GET | `/images/folders/{folder}` | Get all custom images for folder | folder | `List[string]` |
 | GET | `/images/folders/delete/{folder}/{id}` | Delete custom images from folder | folder, id | `RESTResultBoolean` |
 | POST | `/images/folders/upload/{folder}/{imageType}` | Upload a custom image to a folder | folder, imageType | `RESTResultString` |

## `/media`

| Method | Path | Summary | Parameters | Response |
| --- | --- | --- | --- | --- |
 | GET | `/media/{id}` | Get all media items in a collection | id, limit, offset, userid | `RESTMediaCollectionItem` |
 | GET | `/media/{id}/color` | Gets the color assigned to the music account associated with the id | id | `RESTResultString` |
 | DELETE | `/media/{id}/color` | Remove the color assigned to the music account associated with the id | id | `RESTResultBoolean` |
 | POST | `/media/{id}/color/{color}` | Add a color to the music service account associated with the id | id, color | `RESTResultBoolean` |
 | GET | `/media/artists/{id}/bio` | Get artist bio | id | `ArtistBiography` |
 | GET | `/media/delete/{id}` | Delete media item | id | `` |
 | POST | `/media/form/{id}` | Submit a form | id | `RESTMediaCollectionItem` |
 | POST | `/media/idcache/add` | Add a persistent identifier to the ID cache and return its hashed value. | PersistentId | `IdCacheAddResult` |
 | GET | `/media/refresh/{id}` | Refresh or resync media items | id | `` |
 | GET | `/media/refresh/{id}/status` | Get music service refresh status | id | `` |
 | GET | `/media/rename/{id}/{name}` | Rename media item | id, name | `RenameResult` |
 | GET | `/media/search/{mcId}/{searchText}` | Search for music in this collection | mcId, searchText, limit, offset, userid | `RESTMediaCollectionItem` |
 | GET | `/media/sources/{id}` | Get all music services for a Source | id, includePlaylists, maxPlaylists, includeOtherPlaylists, maxBookmarks, includeSelectionHistory, userid | `RESTMediaCollectionItem` |
 | GET | `/media/sources/{id}/play/{mediaId}` | Play media item on a source | id, addToQueue, mediaId, autoStart | `RESTResultInteger` |
 | GET | `/media/sources/{id}/play/{mediaId}/addtoqueue/{addToQueue}` | Play media item on a source and specify whether to play now or add to queue | addToQueue, id, mediaId, autoStart | `RESTResultInteger` |
 | GET | `/media/sources/{sId}/search/{searchText}` | Search for music on this source | sId, searchText, limit, offset, userid | `RESTMediaCollectionItem` |
 | GET | `/media/stations/` | Get all my custom Internet stations | limit, offset, userid | `RESTMediaCollectionItem` |
 | POST | `/media/stations/` | Add a custom Internet station |  | `RESTMediaItem` |
 | GET | `/media/stations/{id}` | Obtains the fields needed for updating the properties of a user-defined radio station. | id | `StationProperties` |
 | PUT | `/media/stations/{id}` | Update a custom Internet station | id | `RESTMediaItem` |
 | DELETE | `/media/stations/{id}` | Delete a custom Internet station | id | `RESTResultBoolean` |
 | GET | `/media/stations/categories` | Get a list of all category names available for radio stations. |  | `RadioStationsCategoriesResult` |
 | GET | `/media/zones/{id}` | Get all music services for a zone | id, includePlaylists, maxPlaylists, includeOtherPlaylists, maxBookmarks, includeSelectionHistory, userid | `RESTMediaCollectionItem` |
 | POST | `/media/zones/{id}/play` | Play a list of media items in a zone and specify whether to play now or add to queue. | id, addToQueue, mediaIdList, autoStart | `PlayMediaItemListResult` |
 | GET | `/media/zones/{id}/play/{mediaId}` | Play media item in a zone | id, addToQueue, mediaId, autoStart | `RESTResultInteger` |
 | GET | `/media/zones/{id}/play/{mediaId}/addtoqueue/{addToQueue}` | Play media item in a zone and specify whether to play now or add to queue | addToQueue, id, mediaId, autoStart | `RESTResultInteger` |
 | GET | `/media/zones/{zId}/search/{searchText}` | Search for music on this zone | zId, searchText, limit, offset, userid | `RESTMediaCollectionItem` |

## `/playlists`

| Method | Path | Summary | Parameters | Response |
| --- | --- | --- | --- | --- |
 | GET | `/playlists` | Get all playlists | appendableOnly, includeOtherPlaylists, limit, offset | `List[RESTPlaylist]` |
 | GET | `/playlists/{id}/{action}/{mediaId}` | Add or Delete a media item to/from a CasaTunes Playlist | id, action, mediaId | `` |
 | GET | `/playlists/{id}/add` | Add list of media items to a CasaTunes playlist | id, mediaItemIDs | `` |
 | GET | `/playlists/{id}/delete` | Delete a list of media items from a CasaTunes playlist | id, mediaItemIDs | `` |
 | GET | `/playlists/add` | Create a new CasaTunes playlist with a list of media items | name, mediaItemIDs | `` |
 | POST | `/playlists/add/{id}` | Add a list of media items to a playlist | id, mediaItemIDs | `` |
 | POST | `/playlists/create/{name}` | Create a new playlist with a list of media items | name, mediaItemIDs | `` |
 | GET | `/playlists/delete` | Delete a CasaTunes playlist | id | `` |
 | GET | `/playlists/sources/{id}/play/{name}` | Play a playlist on a source by name | id, name, addToQueue, includeOtherPlaylists | `RESTResultInteger` |
 | GET | `/playlists/update` | Rename a CasaTunes playlist | id, name | `` |
 | GET | `/playlists/zones/{id}/play/{name}` | Play a playlist on a zone by name | id, name, addToQueue, includeOtherPlaylists | `RESTResultInteger` |

## `/settings`

| Method | Path | Summary | Parameters | Response |
| --- | --- | --- | --- | --- |
 | GET | `/settings/airplay` | Get current AirPlay settings. |  | `AirPlaySettingsResponse` |
 | POST | `/settings/airplay` | Update current AirPlay settings. |  | `AirPlaySettingsResponse` |
 | GET | `/settings/app/{key}` | Get AppSetting | key | `RESTResultString` |
 | POST | `/settings/app/{key}/{value}` | Set AppSetting | key, value | `RESTResultBoolean` |
 | POST | `/settings/application/activate/{serialNumber}` | Activate application. | serialNumber | `ActivationResponse` |
 | POST | `/settings/application/deactivate/{serialNumber}` | Deactivate application. | serialNumber | `ActivationResponse` |
 | GET | `/settings/bitwise/enable` | Returns whether BitWise controls are enabled. |  | `BitWiseEnableResponse` |
 | POST | `/settings/bitwise/enable/{IsEnabled}` | Enable or disable BitWise controls. | IsEnabled | `BitWiseEnableResponse` |
 | GET | `/settings/caseta` | Get all the Caseta Settings |  | `CasetaSettingsResponse` |
 | PUT | `/settings/caseta` | Update the Lutron Caseta Settings |  | `CasetaSettingsResponse` |
 | GET | `/settings/caseta/autoprogram/{deviceId}/{persistentZoneId}` | Auto program a Caseta device (PICO only) | deviceId, persistentZoneId | `CasetaDeviceResponse` |
 | PUT | `/settings/caseta/button` | Update the Action for a button |  | `CasetaResponse` |
 | GET | `/settings/caseta/devices` | Get the available or configured Caseta devices | configuredOnly | `CasetaDevicesResponse` |
 | GET | `/settings/caseta/refresh` | Refresh Lutron configuration (RadioRA2/HomeWorks QS only) |  | `CasetaStatusResponse` |
 | GET | `/settings/caseta/status` | Gets the Caseta Status |  | `CasetaStatusResponse` |
 | GET | `/settings/caseta/timeclockevents` | Get the available or configured Time Clock Events | configuredOnly | `CasetaTimeClockEventsResponse` |
 | PUT | `/settings/caseta/timeclockevents` | Update the Action for a time clock event |  | `CasetaResponse` |
 | POST | `/settings/caseta/upload` | Upload the Lutron Integration Report |  | `CasetaStatusResponse` |
 | PUT | `/settings/caseta/verify` | Verify your Caseta credentials |  | `CasetaStatusResponse` |
 | GET | `/settings/caseta/verifystatus` | Get verify Caseta credential status |  | `CasetaStatusResponse` |
 | POST | `/settings/controlmodules` | Update control modules settings. |  | `Result` |
 | POST | `/settings/controlmodules/reload` | Reload control modules from disk. |  | `Result` |
 | GET | `/settings/countries` | Get All Countries |  | `AvailableCountries` |
 | POST | `/settings/countries/{countryId}` | Set the current Country | countryId | `Result` |
 | GET | `/settings/countries/current` | Get the current Country |  | `CountryInfo` |
 | GET | `/settings/hdl/chimes` | Get the persistent index for each Chime | wait | `List[HDLItem]` |
 | GET | `/settings/hdl/panels` | Get the type of panels (DLP, Enviro or Mixed) in use |  | `RESTResultString` |
 | GET | `/settings/hdl/panels/{type}` | Sets the type of panels (DLP, Enviro or Mixed) to use | type | `RESTResultBoolean` |
 | GET | `/settings/hdl/playlists` | Get the persistent index for each Playlist | wait | `List[HDLItem]` |
 | GET | `/settings/hdl/status` | Get status of whether the HDL Service is enabled or disabled |  | `RESTResultBoolean` |
 | GET | `/settings/hdl/status/{enable}` | Enable/Disable HDL Service | enable, resetZones, resetChimes | `RESTResultBoolean` |
 | GET | `/settings/hdl/zones` | Get the list of HDL subnet and device IDs assigned to each CasaTunes zone | wait | `List[HDLZone]` |
 | POST | `/settings/keypads/{serialPort}/{keypadID}/Zone/{id}` | Assign Keypad Room | serialPort, keypadID, id | `RESTResultBoolean` |
 | GET | `/settings/knx/status` | Get status of whether the KNX Driver for CasaTunes is enabled or disabled |  | `RESTResultBoolean` |
 | GET | `/settings/knx/status/{enable}` | Enable/Disable KNX Driver for CasaTunes | enable | `RESTResultBoolean` |
 | GET | `/settings/languages` | Get all CasaTunes languages |  | `AvailableLanguages` |
 | POST | `/settings/languages/{languageCode}` | Set the current CasaTunes Language | languageCode | `Result` |
 | GET | `/settings/languages/current` | Get the current CasaTunes Language |  | `LanguageInfo` |
 | POST | `/settings/license` | Update license settings. |  | `Result` |
 | GET | `/settings/lutron` | Get the Lutron Settings |  | `RESTLutronSettings` |
 | POST | `/settings/lutron` | Update Lutron settings |  | `RESTLutronSettings` |
 | GET | `/settings/lutron/containers` | Get the root container of Lutron items | limit, offset | `RESTLutronContainer` |
 | GET | `/settings/lutron/containers/{id}` | Get the container of Lutron items by specified id | id, limit, offset | `RESTLutronContainer` |
 | GET | `/settings/lutron/triggers` | Get the list of Lutron triggers |  | `RESTLutronTriggers` |
 | POST | `/settings/lutron/triggers` | Update Lutron triggers |  | `RESTLutronTriggers` |
 | DELETE | `/settings/lutron/triggers/{triggerId}` | Delete a Lutron trigger | triggerId | `RESTLutronTriggers` |
 | POST | `/settings/matrix` | Update settings for the active matrix. |  | `Result` |
 | GET | `/settings/matrix/default/{MatrixType}` | Get default settings for a given matrix type. | MatrixType | `MatrixSettingsResponse` |
 | PUT | `/settings/matrix/zone` | Create a new software matrix zone. |  | `Result` |
 | DELETE | `/settings/matrix/zone/{id}` | Delete a software matrix zone. | id | `Result` |
 | DELETE | `/settings/matrix/zones` | Delete all software matrix zones. |  | `Result` |
 | PUT | `/settings/musicservices/accounts/{AccountId}` | Update music service account. | AccountId | `MusicServiceAccount` |
 | DELETE | `/settings/musicservices/accounts/{AccountId}` | Deletes a music service account. | AccountId | `Result` |
 | POST | `/settings/musicservices/accounts/{ServiceId}` | Create a new account for the given music service. | ServiceId | `MusicServiceAccount` |
 | PUT | `/settings/musicservices/accounts/config/button/{AccountId}/{ButtonId}` |  | AccountId, ButtonId | `Result` |
 | GET | `/settings/musicservices/accounts/configured` | Get all the configured music service accounts |  | `ConfiguredMusicServiceAccounts` |
 | PUT | `/settings/musicservices/authenticate/{Id}` | Authenticate credentials | Id | `Result` |
 | GET | `/settings/musicservices/available` | Get a list of music services (and optionally exclude uPnP devices. | ExcludeUPNP | `AvailableMusicServices` |
 | GET | `/settings/musicservices/exclusivesource/{ServiceID}` | Get exclusive source ID for the given music service, or -1 if not set. | ServiceID | `MusicServiceExclusiveSourceResponse` |
 | POST | `/settings/musicservices/items` | Update settings for multiple music services. |  | `Result` |
 | GET | `/settings/musicservices/items/{ServiceID}` | Get settings for music service as a list of generic items. | ServiceID | `SettingsListResponse` |
 | POST | `/settings/musicservices/items/{ServiceID}` | Update settings for music service using a list of generic items. | ServiceID | `Result` |
 | GET | `/settings/musicservices/languages` | Get All Languages |  | `AvailableLanguages` |
 | POST | `/settings/musicservices/languages/{languageCode}` | Set the current language to use with Music Services | languageCode | `Result` |
 | GET | `/settings/musicservices/languages/current` | Get the current Language used for Music Services |  | `LanguageInfo` |
 | GET | `/settings/musicservices/oauth/{id}/status` | Get the OAuth Authentication Status | id | `OAuthStatusResult` |
 | GET | `/settings/musicservices/oauth/{id}/uri` | Get the OAuth Authentication Uri | id | `OAuthUriResult` |
 | POST | `/settings/musicservices/save` | Save music services settings. |  | `Result` |
 | POST | `/settings/musicservices/search/save` | Save music services search settings. |  | `Result` |
 | GET | `/settings/nightmode` | Get default Night Mode settings. |  | `NightModeSettingsResponse` |
 | POST | `/settings/nightmode` | Set default Night Mode settings. |  | `NightModeSettingsResponse` |
 | GET | `/settings/prayers` | Get the Prayer settings |  | `RESTPrayerSettings` |
 | POST | `/settings/prayers` | Set the Prayer settings |  | `RESTPrayerSettings` |
 | GET | `/settings/prayers/test/{prayer}` | Test Prayer | prayer | `RESTResultBoolean` |
 | GET | `/settings/prayers/times/{date}` | Get Prayer Times | date | `RESTPrayerTimes` |
 | GET | `/settings/project` | Get project info. |  | `ProjectInfoResponse` |
 | POST | `/settings/project` | Set project info. |  | `ProjectInfoResponse` |
 | GET | `/settings/remoteaccess` | Get remote access settings. |  | `RemoteAccessSettingsResponse` |
 | POST | `/settings/remoteaccess` | Set remote access settings. |  | `RemoteAccessSettingsResponse` |
 | POST | `/settings/serialapi` | Set serial API settings. |  | `SerialApiSettingsResponse` |
 | GET | `/settings/serialapi` | Get serial API settings. |  | `SerialApiSettingsResponse` |
 | GET | `/settings/sounddevices` | Returns a list of sound devices available on this CasaTunes server. |  | `EnumerateSoundDevicesResponse` |
 | POST | `/settings/source` | Set the settings for a source. |  | `Result` |
 | GET | `/settings/source/default/{SourceType}` | Get default source settings for a given source type. | SourceType | `SourceSettingsResponse` |
 | POST | `/settings/source/list` | Set a batch of source settings. |  | `Result` |
 | GET | `/settings/source/list/{SourceConfigType}` | Get a source settings list for a given source config type. | SourceConfigType | `SourceSettingsListResponse` |
 | GET | `/settings/source/types/{SourceConfigType}` | Get source types for particular configuration type(s) and source ID | SourceConfigType | `SourceTypesResponse` |
 | GET | `/settings/splashtop/install` | Install Splashtop |  | `RemoteAccessInstallationResults` |
 | GET | `/settings/splashtop/uninstall` | Uninstall Splashtop |  | `RemoteAccessInstallationResults` |
 | GET | `/settings/summary` | Returns a collection of setup information. |  | `SettingsSummaryResponse` |
 | GET | `/settings/teamviewer/install` | Install Teamviewer |  | `TeamviewerInstallationResults` |
 | GET | `/settings/teamviewer/uninstall` | Uninstall Teamviewer |  | `TeamviewerInstallationResults` |
 | GET | `/settings/timezone` | Get configured time zone. |  | `TimeZoneSettingsResponse` |
 | POST | `/settings/timezone` | Set configured time zone. |  | `TimeZoneSettingsResponse` |
 | GET | `/settings/timezones` | Get All TimeZones |  | `AvailableTimeZones` |
 | POST | `/settings/timezones/{timezoneId}` | Set the current TimeZone | timezoneId | `Result` |
 | GET | `/settings/timezones/current` | Get the current TimeZone |  | `TimeZone` |
 | GET | `/settings/update` | Get Update settings |  | `UpdateSettingsResponse` |
 | POST | `/settings/update` | Save Update settings |  | `Result` |
 | GET | `/settings/userprofiles` | Get User Profiles |  | `GetUserProfilesRsp` |
 | POST | `/settings/userprofiles` | Create New User Profile |  | `GetUserProfilesRsp` |
 | PUT | `/settings/userprofiles/{id}` | Update User Profile | id | `GetUserProfilesRsp` |
 | DELETE | `/settings/userprofiles/{id}` | Delete User Profile | id | `GetUserProfilesRsp` |
 | GET | `/settings/userprofiles/{id}/reset` | Reset user profile settings | id | `GetUserProfilesRsp` |
 | POST | `/settings/userprofiles/custom` | Create New Custom Profile |  | `GetUserProfilesRsp` |
 | GET | `/settings/userprofiles/default/{id}` | Set the default Profile Mode | id | `GetUserProfilesRsp` |
 | GET | `/settings/userprofiles/settings` | Get available User Profile settings |  | `GetUserProfileSettingsRsp` |
 | GET | `/settings/wss/status` | Get status of whether the CasaTunes WebSocket Service is enabled or disabled |  | `RESTResultBoolean` |
 | GET | `/settings/wss/status/{enable}` | Enable/Disable CasaTunes WebSocket Service | enable | `RESTResultBoolean` |
 | POST | `/settings/zoneexpansionmodule/activate/{serialNumber}` | Activate zone expansion module. | serialNumber | `ActivationResponse` |
 | POST | `/settings/zoneexpansionmodule/deactivate/{serialNumber}` | Deactivate zone expansion module. | serialNumber | `ActivationResponse` |
 | POST | `/settings/zonegroups` | Update zone groups settings. |  | `Result` |
 | GET | `/settings/zonegroupsforzone/{PersistentZoneID}` | Get a list of multizone group persistent IDs that a zone belongs to. | PersistentZoneID | `MultiZoneGroupsForZoneResponse` |
 | POST | `/settings/zones` | Update settings for a zone. |  | `Result` |
 | GET | `/settings/zones/{zoneType}` | Get zones settings by zone type. | zoneType | `GetZoneSettingsByZoneTypeResponse` |
 | POST | `/settings/zones/list` | Update settings for one or more zones. |  | `Result` |

## `/sources`

| Method | Path | Summary | Parameters | Response |
| --- | --- | --- | --- | --- |
 | GET | `/sources` | Get All Sources |  | `List[SourceInfo]` |
 | GET | `/sources/{id}` | Get information for the specified source, and update source properties | id, Name, Hidden, SourceImageID, PreferredRadioService, PreferredMusicService | `SourceInfo` |
 | GET | `/sources/{id}/nowplaying` | Get the NowPlaying Information for the source | id, userid | `RESTNowPlayingMediaItem` |
 | GET | `/sources/{id}/player/{action}` | Invoke source player action | id, action | `PlayerActionResult` |
 | GET | `/sources/{id}/player/{action}/{option}` | Invoke source player action with option | id, action, option | `PlayerActionResult` |
 | GET | `/sources/{id}/queue` | Get the queue for Source | id, limit, offset | `RESTNowPlayingQueue` |
 | GET | `/sources/{id}/queue/{index}` | Get media item in sources queue | id, index | `RESTMediaItem` |
 | GET | `/sources/{id}/queue/delete` | Clear all media items in the sources queue | id | `` |
 | GET | `/sources/{id}/queue/delete/{index}` | Remove a media item from the sources queue | id, index | `` |
 | GET | `/sources/{id}/queue/play/{index}` | Play a media item in the sources queue | id, index | `` |
 | GET | `/sources/{id}/queue/save/{name}` | Save queue as a CasaTunes playlist | id, name, replace | `` |
 | GET | `/sources/dynamic` | Get all dynamic sources available |  | `List[DynamicSource]` |
 | POST | `/sources/dynamic` | Add a dynamic source |  | `SourceInfo` |
 | DELETE | `/sources/dynamic` | Delete dynamic Source |  | `RESTResultBoolean` |
 | GET | `/sources/nowplaying` | Get the NowPlaying information for all sources | userid | `List[RESTNowPlayingMediaItem]` |

## `/streamers`

| Method | Path | Summary | Parameters | Response |
| --- | --- | --- | --- | --- |
 | GET | `/streamers/settings` | Get the settings for the configured streamers |  | `StreamerSettingsListResponse` |
 | PUT | `/streamers/settings` | Set the specified streamer settings |  | `StreamerSettingsResponse` |
 | PUT | `/streamers/settings/authenticate` | Authenticate username/password for the specified streamer type |  | `StreamerAuthStatusResponse` |
 | GET | `/streamers/settings/available` | Get the list of available streamer types |  | `StreamerDefinitionsListResponse` |
 | GET | `/streamers/settings/oauth/{id}/status` | Get the OAuth Authentication Status | id | `StreamerAuthStatusResponse` |
 | GET | `/streamers/settings/oauth/{id}/url` | Get oAuth Url for the specified streamer type | id | `StreamerOAuthURLResponse` |
 | GET | `/streamers/sites/{id}` | Get a list of sites for the given streamer type, each containing lists of groups and players. | id | `StreamerSitesListResponse` |

## `/system`

| Method | Path | Summary | Parameters | Response |
| --- | --- | --- | --- | --- |
 | GET | `/system/alexa` | Is Alexa enabled |  | `RESTResultBoolean` |
 | GET | `/system/alexa/{enable}` | Enable or disable Alexa | enable | `RESTResultBoolean` |
 | GET | `/system/alexa/registration` | Get Alexa registration code |  | `AlexaRegistrationCode` |
 | GET | `/system/alexa/status` | Check to see whether the system is ready to attempt Alexa registration. |  | `AlexaRegistryReadyResponse` |
 | DELETE | `/system/backup/{backupId}` | Delete Backup | backupId, mac | `RESTResultBoolean` |
 | GET | `/system/backup/{title}` | Backup the CasaTunes Configuration to the Cloud | title | `RESTResultBoolean` |
 | GET | `/system/backup/available` | Get Backups Available | mac | `List[BackupInfo]` |
 | POST | `/system/backup/named/{name}` | Create a Named Backup | name | `RESTResultBoolean` |
 | GET | `/system/backup/restore/{id}` | Restore Backup | id, mac | `RESTResultBoolean` |
 | GET | `/system/backups` | Get Available Backups | mac | `List[BackupInfo2]` |
 | GET | `/system/bonjour/restart` | Restart Bonjour Service | restartZeroConfig | `RESTResultBoolean` |
 | GET | `/system/cd/eject` | Eject the CD from the CasaTunes CD-ROM drive |  | `RESTResultBoolean` |
 | GET | `/system/doorbell` | Play doorbell chime | preWait, postWait, volume | `Object` |
 | GET | `/system/doorbell/chimes` | List doorbell chimes |  | `List[string]` |
 | GET | `/system/doorbell/chimes/{chime}` | Play the specified doorbell chime | chime, preWait, postWait, volume | `Object` |
 | GET | `/system/doorbell/zones/{id}` | Play doorbell chime in the specified room or room group | id, preWait, postWait, volume | `Object` |
 | GET | `/system/doorbell/zones/{id}/chimes/{chime}` | Play the specified doorbell chime in the specified room or room group | id, chime, preWait, postWait, volume | `Object` |
 | GET | `/system/exec` | Execute command | cmd, args, workingDirectory, domain, username, password | `RESTResultString` |
 | GET | `/system/firmware/start` | Update the matrix firmware | matrixId | `FirmwareUpgradeStatus` |
 | GET | `/system/firmware/status` | Get the status of the firmware upgrade for the specified matrix | matrixId | `FirmwareUpgradeStatus` |
 | DELETE | `/system/home/image` | Delete image for home |  | `RESTResultBoolean` |
 | GET | `/system/home/image/{imageId}` | Set Home Image ID | imageId | `RESTSystemInfo` |
 | GET | `/system/home/name/{name}` | Set Home Name | name | `RESTSystemInfo` |
 | GET | `/system/info` | System Information |  | `RESTSystemInfo` |
 | GET | `/system/internet` | Returns whether internet access is enabled, and whether service restart is needed to complete changes. |  | `InternetEnabledStatus` |
 | GET | `/system/internet/{enable}` | Enable or disable Internet access. Changing this setting requires restarting the music service. | enable | `InternetEnabledStatus` |
 | GET | `/system/license/refresh` | Refresh License Information |  | `RESTSystemInfo` |
 | GET | `/system/matrix/reboot` | Reboot matrix amplifier | matrixId | `RESTResultBoolean` |
 | GET | `/system/message` | Get Message |  | `RESTMessage` |
 | GET | `/system/message/{id}/{buttonSelected}` | Message Response | id, buttonSelected | `RESTMessage` |
 | GET | `/system/message/show` | Show Message | title, body, buttons, duration | `RESTMessage` |
 | GET | `/system/monitor` | Gets Monitoring Info | refresh | `MonitorInfo` |
 | GET | `/system/news` | Gets the latest News Items |  | `List[NewsItem]` |
 | POST | `/system/news/allread` | Set all news items as read |  | `List[NewsItem]` |
 | POST | `/system/news/read/{id}` | Set this news item as having been read | id | `List[NewsItem]` |
 | GET | `/system/page/{action}` | Start or Stop a Page, Mute or Chime | action | `PageStatusResponse` |
 | PUT | `/system/password/{passwordKey}/{passwordValue}` | Create or Update password | passwordKey, passwordValue, currentPassword, lostPasswordEmail, param | `RESTResultPassword` |
 | DELETE | `/system/password/{passwordKey}/{passwordValue}` | Delete password | passwordKey, passwordValue | `RESTResultPassword` |
 | GET | `/system/password/available/{passwordKey}` | Is password set? | passwordKey | `RESTResultBoolean` |
 | GET | `/system/password/recover/{passwordKey}` | Recover password by email | passwordKey | `RESTResultPassword` |
 | GET | `/system/password/verify/{passwordKey}/{passwordValue}` | Verify password | passwordKey, passwordValue | `RESTResultPassword` |
 | GET | `/system/power/{state}` | Change System Power State | state | `RESTResultBoolean` |
 | GET | `/system/power/{state}/{password}` | Change System Power State (with Authentication) | password, state | `RESTResultBoolean` |
 | POST | `/system/restore/{backupId}` | Restore Backup | backupId, mac | `RESTResultBoolean` |
 | GET | `/system/sleep` | Get System Sleep Mode |  | `SleepMode` |
 | GET | `/system/sleep/{enabled}` | Set System Sleep Mode | enabled | `SleepMode` |
 | GET | `/system/sleep/{enabled}/delay/{delay}` | Set System Sleep Mode and Delay | delay, enabled | `SleepMode` |
 | POST | `/system/tts` | Play the specified Text or SSML |  | `RESTResultBoolean` |
 | GET | `/system/tts/input/{input}` | Play the specified Text or SSML | input, ssml, languageCode, gender, voice, preWait, postWait, volume | `RESTResultBoolean` |
 | GET | `/system/tts/input/{input}/zones/{id}` | Play the specified Text or SSML in the specified room or room group | id, input, ssml, languageCode, gender, voice, preWait, postWait, volume | `RESTResultBoolean` |
 | GET | `/system/tts/voices` | List the Text-To-Speech voices available | languageCode | `TTSVoices` |
 | GET | `/system/update` | Perform a CasaTunes update | forceUpdate | `RESTResultInteger` |
 | GET | `/system/update/info` | Get information on the latest release |  | `RESTUpdateInfo` |
 | GET | `/system/updateservice/status` | Get the current status of any Upgrade Service updates |  | `UpdateServiceStatusResponse` |
 | GET | `/system/updateservice/update` | Update the Upgrade Service |  | `UpdateServiceStatusResponse` |
 | GET | `/system/wifi` | Get a list of Access Points |  | `List[WiFiAccessPoint]` |
 | GET | `/system/wifi/{name}` | Get Access Point information | name | `WiFiAccessPoint` |
 | GET | `/system/wifi/{name}/forget` | Forget the information for this Access Point | name | `RESTResultBoolean` |
 | GET | `/system/wifi/connect/{name}` | Connect to an Access Point | name, domainName, userName, password, overwrite | `RESTResultBoolean` |
 | GET | `/system/wifi/disconnect` | Disconnect from WiFi |  | `RESTResultBoolean` |

## `/tasks`

| Method | Path | Summary | Parameters | Response |
| --- | --- | --- | --- | --- |
 | GET | `/tasks` | Get all tasks |  | `AllTasksResponse` |
 | POST | `/tasks` | create a task |  | `CreateTaskResponse` |
 | PUT | `/tasks/{id}` | Update a Task | id | `TaskResponse` |
 | DELETE | `/tasks/{id}` | Deletes a Task User | id | `AllTasksResponse` |
 | PUT | `/tasks/{taskId}/actions` | Replace action in Task Actions list | taskId | `TaskResponse` |
 | DELETE | `/tasks/{taskId}/actions/{actionId}` | Deletes a Task Action | taskId, actionId | `TaskResponse` |
 | PUT | `/tasks/{taskId}/actions/{actionId}/move/{index}` | Move Action to index in Task Actions list | taskId, actionId, index | `TaskResponse` |
 | POST | `/tasks/{taskId}/actions/{type}` | Create an Action for a Task | taskId, type | `CreateTaskActionResponse` |
 | PUT | `/tasks/{taskId}/categories` | Replace the categories for a Task | taskId | `TaskResponse` |
 | PUT | `/tasks/{taskId}/users` | Replace the users for a Task | taskId | `TaskResponse` |
 | POST | `/tasks/addmedia` | Add a media item to tasks |  | `Result` |
 | GET | `/tasks/categories` | Get All Task Categories |  | `TaskCategoriesResponse` |
 | POST | `/tasks/categories` | Create a new Task Category |  | `NewTaskCategoryResponse` |
 | PUT | `/tasks/categories/{catId}/move/{index}` | Move the category to the index position in category list | catId, index | `TaskCategoriesResponse` |
 | PUT | `/tasks/categories/{id}` | Updates a Task Category | id | `TaskCategoryResponse` |
 | DELETE | `/tasks/categories/{id}` | Deletes a Task Category | id | `TaskCategoriesResponse` |
 | POST | `/tasks/copy/{id}` | create a copy of a task | id | `CreateTaskResponse` |
 | POST | `/tasks/invoke/{id}` | Invoke the task. Optionally pass in updated Task with options set | id | `TaskStatusResponse` |
 | GET | `/tasks/invoke/name/{id}` | Invoke the task by name or id (must be an unattended task) | id | `TaskStatusResponse` |
 | GET | `/tasks/name` | Get all unattended tasks by Name and ID |  | `AllTasksByNameResponse` |
 | GET | `/tasks/refresh` | Validate and Get all Tasks |  | `AllTasksResponse` |
 | GET | `/tasks/settings` | Get Task Settings |  | `TaskSettingsResponse` |
 | PUT | `/tasks/settings` | Update Task Settings |  | `TaskSettingsResponse` |
 | GET | `/tasks/stop/{id}` | Stop the active task | id | `TaskStatusResponse` |
 | GET | `/tasks/tts/voices` | Get all TTS voices available |  | `AllTaskTTSVoicesResponse` |
 | GET | `/tasks/users` | Get All Task Users |  | `TaskUsersResponse` |
 | POST | `/tasks/users` | Create a new Task User |  | `NewTaskUsersResponse` |
 | PUT | `/tasks/users/{id}` | Updates a Task User | id | `TaskUserResponse` |
 | DELETE | `/tasks/users/{id}` | Deletes a Task User | id | `TaskUsersResponse` |

## `/triggers`

| Method | Path | Summary | Parameters | Response |
| --- | --- | --- | --- | --- |
 | GET | `/triggers` | Get the list and state of all triggers |  | `List[TriggerInfo]` |
 | GET | `/triggers/{deviceId}/{triggerId}/{triggerType}` | Get the state of the specified trigger | deviceId, triggerId, triggerType | `RESTTriggerState` |
 | GET | `/triggers/{deviceId}/{triggerId}/1/{triggerState}` | Set the state of the specified trigger | deviceId, triggerId, triggerState | `RESTTriggerState` |

## `/zonegroupitems`

| Method | Path | Summary | Parameters | Response |
| --- | --- | --- | --- | --- |
 | GET | `/zonegroupitems/{id}/{action}/{zoneId}` | Modify Zones in Zone Group | action, id, zoneId, volumeAdjustment, master, keypadlock | `` |

## `/zonegroups`

| Method | Path | Summary | Parameters | Response |
| --- | --- | --- | --- | --- |
 | GET | `/zonegroups/{id}/available` | Get IDs of zones that could be added to the given Zone Group. | id | `ZoneGroupGetAvailableZonesReply` |
 | GET | `/zonegroups/{id}/delete` | Delete Zone Group | id | `RESTResultBoolean` |
 | PUT | `/zonegroups/{id}/update` | Update an existing Zone Group | id | `RESTZone` |
 | POST | `/zonegroups/{id}/update` | Update an existing Zone Group | id | `RESTZone` |
 | POST | `/zonegroups/{id}/update/{name}` | Update an existing Zone Group and name | name, id | `RESTZone` |
 | GET | `/zonegroups/{idlist}/test` | Test creation of a Zone Group from the given list of zone IDs. | idlist | `ZoneGroupGetAvailableZonesReply` |
 | GET | `/zonegroups/create/{name}/{record}` | New Zone Group | name, record | `RESTZone` |

## `/zones`

| Method | Path | Summary | Parameters | Response |
| --- | --- | --- | --- | --- |
 | GET | `/zones` | All Zones Properties | Power, Mute, SleepDelay, limit, offset | `List[RESTZone]` |
 | GET | `/zones/{fromId}/move/{toId}` | Move music from one zone to another zone | fromId, toId | `RESTResultBoolean` |
 | GET | `/zones/{fromId}/share/{withId}` | Share music with another zone | fromId, withId | `RESTResultBoolean` |
 | GET | `/zones/{id}` | Zone Properties | id, Balance, Bass, DND, FixedVolume, Hidden, KeypadLock, Loudness, MasterMode, MaxVolume, Mute, Name, PageVolume, PartyMode, Power, ResetPowerOnVolume, PowerOnVolume, ResetMaxPowerOnVolume, MaxPowerOnVolume, LowPassFilterValue, LowPassFilterEnabled, SleepDelay, SourceID, AdjustVolume, Volume, Treble, ZoneImageID, Path, EqID, EqPresetID | `RESTZone` |
 | GET | `/zones/{id}/capabilities` | Zone Capabilities | id | `ZoneCapabilities` |
 | GET | `/zones/{id}/eq/preset/{eqId}` | Set the multi-band equalizer settings for the Zone to the EQ Settings specified by eqId | id, eqId | `EQSettings` |
 | POST | `/zones/{id}/eq/save` | Save the multi-band equalizer settings for Zone | id | `EQSettings` |
 | GET | `/zones/{id}/eqpresets` | Get the list of available EQ Presets for this matrix | id | `List[MatrixEQPreset]` |
 | DELETE | `/zones/{id}/eqpresets/{eqpresetid}` | Delete the multi-band equalizer settings for this Zone speicified by EQ Preset ID | id, eqpresetid | `RESTResultBoolean` |
 | POST | `/zones/{id}/eqpresets/{name}` | Save the current multi-band equalizer settings for this Zone with name | id, name | `MatrixEQPreset` |
 | GET | `/zones/{id}/group` | Get the list of Zones that can be shared with this zone | id | `List[RESTZone]` |
 | GET | `/zones/{id}/group/{zoneId}` | Add zone {zoneId} to the current group zone {id} belongs to | id, zoneId | `RESTResultBoolean` |
 | GET | `/zones/{id}/nightmode/{enable}` | Enable or disable Night Mode for a zone | id, enable | `RESTResultBoolean` |
 | GET | `/zones/{id}/nowplaying` | Get Now Playing Information for Zone | id, userid | `RESTNowPlayingMediaItem` |
 | GET | `/zones/{id}/player/{action}` | Player Action | id, action | `PlayerActionResult` |
 | GET | `/zones/{id}/player/{action}/{option}` | Player Action with parameter | option, id, action | `PlayerActionResult` |
 | GET | `/zones/{id}/preferred/{type}` | Get the preferred radio or music service | id, type, filter | `PreferredServiceResult` |
 | DELETE | `/zones/{id}/property/{name}` | Delete Zone Property | id, name | `RESTResultBoolean` |
 | GET | `/zones/{id}/property/{name}` | Get Zone Property | id, name | `RESTResultString` |
 | GET | `/zones/{id}/property/{name}/{value}` | Set Zone Property | value, id, name | `RESTResultString` |
 | GET | `/zones/{id}/queue` | Queue for Zone | id, limit, offset | `RESTNowPlayingQueue` |
 | GET | `/zones/{id}/queue/{index}` | Queue Media Item | id, index | `RESTMediaItem` |
 | GET | `/zones/{id}/queue/append/{playlistID}` | Append Queue to CasaTunes Playlist | id, playlistID | `` |
 | GET | `/zones/{id}/queue/delete` | Clear all media items in the zones queue | id | `` |
 | GET | `/zones/{id}/queue/delete/{index}` | Remove a media item from the zones queue | id, index | `` |
 | GET | `/zones/{id}/queue/move/{fromIndex}/to/{toIndex}` | Move a Media Item in the Queue for a Zone | id, fromIndex, toIndex | `` |
 | GET | `/zones/{id}/queue/play/{index}` | Play Queue Media Item | id, index | `` |
 | GET | `/zones/{id}/queue/replace/{playlistID}` | Replace CasaTunes Playlist with Queue contents | id, playlistID | `RESTResultString` |
 | GET | `/zones/{id}/queue/save/{name}` | Save Queue as CasaTunes Playlist | id, name, replace | `` |
 | GET | `/zones/{id}/schedule` | Zone Schedule | id | `List[RESTScheduleItem]` |
 | GET | `/zones/{id}/schedule/{action}` | Add a Schedule Item to Zone | id, action, DaysOfTheWeek, Enabled, StartTimeHour, StartTimeMinute, EndTimeEnabled, EndTimeHour, EndTimeMinute, RampVolume, Volume, SourceID, PlaylistID, OneShot, AutoRemove, RepeatMode, ShuffleMode | `` |
 | GET | `/zones/{id}/schedule/{index}/{action}` | Update or Delete a Scheduled Item for a Zone | index, id, action, DaysOfTheWeek, Enabled, StartTimeHour, StartTimeMinute, EndTimeEnabled, EndTimeHour, EndTimeMinute, RampVolume, Volume, SourceID, PlaylistID, OneShot, AutoRemove, RepeatMode, ShuffleMode | `` |
 | GET | `/zones/{id}/status` | Zone Status | id | `RESTStatus` |
 | GET | `/zones/{id}/tuner/band/{bandId}` | Change Tuner Band | id, bandId | `Object` |
 | GET | `/zones/{id}/tuner/band/{bandId}/{action}/{option}` | Control Tuner | action, option, id, bandId | `Object` |
 | GET | `/zones/{id}/ungroup/{groupedZoneId}` | Remove grouped zone {groupZoneId} from current group zone {id} belongs to | id, groupedZoneId | `RESTResultBoolean` |
 | GET | `/zones/{id}/wakeupitems` | Get list of wakeup media item collections suitable for the specified zone. | id | `List[RESTMediaItem]` |
 | GET | `/zones/{id}/wakeupitems/{srcId}` | Get list of wakeup media item collections suitable for the specified zone and source. | id, srcId | `List[RESTMediaItem]` |
 | GET | `/zones/{joinId}/join/{toId}` | Join a zone with another zone | joinId, toId | `RESTResultBoolean` |
