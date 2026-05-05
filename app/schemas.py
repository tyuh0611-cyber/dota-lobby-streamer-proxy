from pydantic import BaseModel


class Chatter(BaseModel):
    user_id: str
    user_login: str
    user_name: str


class LobbyMember(BaseModel):
    steam_id: str | None = None
    dota_id: str | None = None
    dota_name: str | None = None


class LobbyState(BaseModel):
    lobby_exists: bool
    lobby_id: str | None = None
    members: list[LobbyMember] = []


class InviteRequest(BaseModel):
    steam_id: str


class InviteResult(BaseModel):
    ok: bool
    message: str
