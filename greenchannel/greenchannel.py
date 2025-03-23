"""
$description Green Channel
$url sp.gch.jp
$type live
$account Required username and password
"""

import logging,os,re
from streamlink.plugin import Plugin, PluginError, pluginargument, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream

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
@pluginargument(
    "low-latency",
    type=bool,
    sensitive=False,
    metavar="LOW_LATENCY",
    help="Request Low latency stream --greenchannel-low-latency.",
    required=False,
    default=False,
)

class Greenchannel(Plugin):

    _API_URL = "https://sp.gch.jp/api"
    _API_EPG_URL = "https://sp.gch.jp/api_epg"

    _AUTH_SCHEMA = validate.Schema({"at": str, "dt": str})

    def _get_streams(self):

        username = self.get_option("email")
        password = self.get_option("password")
        
        # for debug
        if username == "debug" and password == "debug":
            username = os.getenv("GREENCHANNEL_USERNAME")
            password = os.getenv("GREENCHANNEL_PASSWORD")

        self.login(self.get_option("email"), self.get_option("password"))
        self.channel_code = 1
        self.low_latency = self.get_option("low-latency")
        if self.channel_code != 1:
            self.low_latency = False

        if self.match["channel_code"]:
            self.channel_code = int(self.match["channel_code"])

        self.program_code = self.get_latest_epg()

        self.m3u8_url = self.get_m3u8_url()
        streams = HLSStream.parse_variant_playlist(self.session, self.m3u8_url)
        return streams

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

    def get_latest_epg(self) -> str:
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

    def get_m3u8_url(self) -> str:
        res = self.session.http.post(
            url=self._API_URL+"/vi",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"{self.at}"
            },
            json={
                "pc": self.program_code,
                "di": "1",
                "dgi": "2",
                "ch": f"ch{self.channel_code}",
                "lightviewer": False,
                "is_low_latency": self.low_latency
            },
        )
        if res.status_code != 200:
            raise PluginError(f"ch{self.channel_code}: get m3u8 process was failed.")
        jsonres = self.session.http.json(res)

        if (len(jsonres) > 0
            and 'v' in jsonres[0]
            and 'streaks' in jsonres[0]['v']
            and 'sources' in jsonres[0]['v']['streaks']
            and len(jsonres[0]['v']['streaks']['sources']) > 0
            and 'src' in jsonres[0]['v']['streaks']['sources'][0]
        ):
            url = jsonres[0]['v']['streaks']['sources'][0]['src']
            log.info(f"successful to fetch m3u8 url: {url}")
            return url

        raise PluginError(f"ch{self.channel_code}: get m3u8 response were invalid.")

__plugin__ = Greenchannel
