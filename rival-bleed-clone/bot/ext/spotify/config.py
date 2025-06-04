import tekore

CLIENT_ID = ""
CLIENT_SECRET = ""
CLIENT_REDIRECT = ""


def get_token():
    return tekore.Credentials(
        CLIENT_ID, CLIENT_SECRET, CLIENT_REDIRECT, asynchronous=True
    )
