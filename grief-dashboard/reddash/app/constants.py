import threading

import websocket


class Lock:
    def __init__(self):
        self.lock = threading.Lock()

    def __enter__(self):
        self.lock.acquire()

    def __exit__(self, *args):
        self.lock.release()


DEFAULTS = {
    "botname": "grief",
    "botavatar": "https://media.discordapp.net/attachments/1122755023533768784/1152690416517386282/grief.png?width=204&height=204",
    "botinfo": "grief is one of the most advanced bots on Discord. with over 500 commands and over 20 message-based events, grief is a bot that enhances the Discord experience like no other. whether it's integration with other services and platforms or its advanced moderation commands, servers that use grief are the best servers on Discord.",
    "owner": "",
    "color": "purple",
}

WS_URL = "ws://localhost:"
WS_EXCEPTIONS = (
    ConnectionRefusedError,
    websocket._exceptions.WebSocketConnectionClosedException,
    ConnectionResetError,
    ConnectionAbortedError,
)

ALLOWED_LOCALES = [
    "en",
    "af_ZA",
    "ar_SA",
    "bg_BG",
    "ca_ES",
    "cs_CZ",
    "da_DK",
    "de_DE",
    "el_GR",
    "es_ES",
    "fi_FI",
    "fr_FR",
    "he_IL",
    "hu_HU",
    "id_ID",
    "it_IT",
    "ja_JP",
    "ko_KR",
    "nl_NL",
    "pl_PL",
    "pt_BR",
    "pt_PT",
    "ro_RO",
    "ru_RU",
    "sk_SK",
    "sv_SE",
    "tr_TR",
    "uk_UA",
    "vi_VN",
    "zh_CN",
    "zh_HK",
    "zh_TW",
]
