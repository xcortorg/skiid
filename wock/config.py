from discord import Intents  # type: ignore

CONFIG_DICT = {
    "prefix": "z!",
    "intents": Intents.all(),
    "token": "MTIwMzQxOTMxNjIzMDQyMjU0OA.GnEsMb.s6NZBn04AI7lta_SswJuFUnpDcgcDp9uoq3asU",
    "owners": {
        1200230992368123965,
        352190010998390796,
        1109861649910874274,
        1252500004782870532,
    },
    "rival_api": "abc2f2fe-a27b-43c0-8b0d-5b4b76752209",
    "domain": "https://wock.bott",
}


CHANCES = {
    "roll": {"percentage": 50.0, "total": 100.0},
    "coinflip": {"percentage": 50.0, "total": 100.0},
    "gamble": {"percentage": 20.0, "total": 100.0},
    "supergamble": {"percentage": 50.0, "total": 1000.0},
}


class Authorization:
    class Instagram:
        session_id = ""
        csrf_token = ""
