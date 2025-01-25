"""
$description Green Channel
$url sp.gch.jp
$type live
$account Required username and password
"""

import logging
import re

from streamlink.plugin import Plugin, PluginError, pluginargument, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.stream.hls import MuxedHLSStream
from streamlink.stream.hls.segment import Media
from streamlink.stream.ffmpegmux import FFMPEGMuxer
from streamlink.stream.hls.m3u8 import parse_m3u8
from streamlink.session import Streamlink

log = logging.getLogger(__name__)

@pluginmatcher(re.compile(r"https?://sp\.gch\.jp/(#ch(?P<channel_code>[0-9]+))?"))
@pluginargument(
    "email",
    sensitive=False,
    requires=["password"],
    metavar="EMAIL",
    help="The email used to register with sp.gch.jp.",
    required=True
)
@pluginargument(
    "password",
    sensitive=True,
    metavar="PASSWORD",
    help="A sp.gch.jp account password to use with --greenchannel-username.",
    required=True
)

class Greenchannel(Plugin):

    _API_URL = "https://sp.gch.jp/api"
    _API_EPG_URL = "https://sp.gch.jp/api_epg"

    _AUTH_SCHEMA = validate.Schema({"at": str, "dt": str})

    def _get_streams(self):

        self.login(self.get_option("email"), self.get_option("password"))
        self.channel_code = 1

        if self.match["channel_code"]:
            self.channel_code = int(self.match["channel_code"])

        self.program_code = self.get_latest_epg()
        self.m3u8_data = self.get_m3u8_data()

        return self.parse_variant_playlist(self.session)
    
    def login(self, email:str, password:str):
        log.info(f"Attempting login as {email}")
        res = self.session.http.post(
            url=self._API_URL+"/at",
            headers={"Content-Type": "application/json"},
            json={"login_id": email, "password": password},
        )
        jsonres = self.session.http.json(res, schema=self._AUTH_SCHEMA)

        if "at" in jsonres and "dt" in jsonres:
            log.info(f"Login successfull as {email}")
            self.at = jsonres["at"]
            self.dt = jsonres["dt"]
        else:
            raise PluginError("Login failed")

    def get_latest_epg(self):
        res = self.session.http.get(
            url=self._API_EPG_URL+"/latest",
            params={"channel_code": f"ch{self.channel_code}"}
        )
        if res.status_code != 200:
            raise PluginError(f"ch{self.channel_code}: latest epg data was not found.")
        jsonres = self.session.http.json(res)
        if len(jsonres) > 0 and  len(jsonres[0]) > 0 and 'program_code' in jsonres[0][0]:
            log.info("program_code: "+jsonres[0][0]['program_code'])
            return jsonres[0][0]['program_code']
        else:
            raise PluginError(f"ch{self.channel_code}: latest epg data response were unexpected format.")

    def get_m3u8_data(self):
        res = self.session.http.post(
            url=self._API_URL+"/vi",
            headers={"Content-Type": "application/json", "Authorization": f"{self.at}"},
            json={"pc": self.program_code, "di": "1", "dgi": "2", "ch": f"ch{self.channel_code}", "lightviewer": False},
        )
        if res.status_code != 200:
            raise PluginError(f"ch{self.channel_code}: get m3u8 process was failed.")
        jsonres = self.session.http.json(res)
        if len(jsonres) > 0 and 'v' in jsonres[0]:
            return jsonres[0]['v']
        else:
            raise PluginError(f"ch{self.channel_code}: get m3u8 response were invalid.")

    def parse_variant_playlist(
        self,
        session: Streamlink,
        name_key: str = "name",
        name_prefix: str = "",
        check_streams: bool = False,
        force_restart: bool = False,
        name_fmt: str | None = None,
        start_offset: float = 0,
        duration: float | None = None,
        **kwargs,
    ) -> dict[str, HLSStream | MuxedHLSStream]:

        locale = session.localization
        audio_select = session.options.get("hls-audio-select")

        request_args = session.http.valid_request_args(**kwargs)

        try:
            multivariant = parse_m3u8(data=self.m3u8_data)
        except ValueError as err:
            raise OSError(f"Failed to parse playlist: {err}") from err

        stream_name: str | None
        stream: HLSStream | MuxedHLSStream
        streams: dict[str, HLSStream | MuxedHLSStream] = {}

        for playlist in multivariant.playlists:
            if playlist.is_iframe:
                continue

            names: dict[str, str | None] = dict(name=None, pixels=None, bitrate=None)
            audio_streams = []
            fallback_audio: list[Media] = []
            default_audio: list[Media] = []
            preferred_audio: list[Media] = []

            for media in playlist.media:
                if media.type == "VIDEO" and media.name:
                    names["name"] = media.name
                elif media.type == "AUDIO":
                    audio_streams.append(media)

            for media in audio_streams:
                # Media without a URI is not relevant as external audio
                if not media.uri:
                    continue

                if not fallback_audio and media.default:
                    fallback_audio = [media]

                # if the media is "autoselect" and it better matches the users preferences, use that
                # instead of default
                if not default_audio and (media.autoselect and locale.equivalent(language=media.language)):
                    default_audio = [media]

                # select the first audio stream that matches the user's explict language selection
                if (
                    (
                        "*" in audio_select
                        or media.language in audio_select
                        or media.name in audio_select
                    )
                    or (
                        (not preferred_audio or media.default)
                        and locale.explicit
                        and locale.equivalent(language=media.language)
                    )
                ):  # fmt: skip
                    preferred_audio.append(media)

            # final fallback on the first audio stream listed
            if not fallback_audio and audio_streams and audio_streams[0].uri:
                fallback_audio = [audio_streams[0]]

            if playlist.stream_info.resolution and playlist.stream_info.resolution.height:
                names["pixels"] = f"{playlist.stream_info.resolution.height}p"

            if playlist.stream_info.bandwidth:
                bw = playlist.stream_info.bandwidth

                if bw >= 1000:
                    names["bitrate"] = f"{int(bw / 1000.0)}k"
                else:
                    names["bitrate"] = f"{bw / 1000.0}k"

            if name_fmt:
                stream_name = name_fmt.format(**names)
            else:
                stream_name = (
                    names.get(name_key)
                    or names.get("name")
                    or names.get("pixels")
                    or names.get("bitrate")
                )  # fmt: skip

            if not stream_name:
                continue
            if name_prefix:
                stream_name = f"{name_prefix}{stream_name}"

            if stream_name in streams:  # rename duplicate streams
                stream_name = f"{stream_name}_alt"
                num_alts = len([k for k in streams.keys() if k.startswith(stream_name)])

                # We shouldn't need more than 2 alt streams
                if num_alts >= 2:
                    continue
                elif num_alts > 0:
                    stream_name = f"{stream_name}{num_alts + 1}"

            if check_streams:
                # noinspection PyBroadException
                try:
                    session.http.get(playlist.uri, **request_args)
                except KeyboardInterrupt:
                    raise
                except Exception:
                    continue

            external_audio = preferred_audio or default_audio or fallback_audio

            if external_audio and FFMPEGMuxer.is_usable(session):
                external_audio_msg = ", ".join([
                    f"(language={x.language}, name={x.name or 'N/A'})"
                    for x in external_audio
                ])  # fmt: skip
                log.debug(f"Using external audio tracks for stream {stream_name} {external_audio_msg}")

                stream = MuxedHLSStream(
                    session,
                    video=playlist.uri,
                    audio=[x.uri for x in external_audio if x.uri],
                    hlsstream=HLSStream(),
                    multivariant=multivariant,
                    force_restart=force_restart,
                    start_offset=start_offset,
                    duration=duration,
                    **kwargs,
                )
            else:
                stream = HLSStream(
                    session,
                    playlist.uri,
                    multivariant=multivariant,
                    force_restart=force_restart,
                    start_offset=start_offset,
                    duration=duration,
                    **kwargs,
                )

            streams[stream_name] = stream

        return streams

__plugin__ = Greenchannel
