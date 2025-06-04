from pydantic import BaseModel


class InstagramCredentials(BaseModel):
    id: str
    password: str
    authenticator: str
    mail: str
    mail_pass: str
    smtp_host: str
    smtp_port: int


class Credentials(BaseModel):
    instagram: InstagramCredentials
