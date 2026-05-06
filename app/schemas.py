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
    lobby_name: str | None = None
    mode: str = 'mock'
    connected: bool = False
    members: list[LobbyMember] = []


class DotaConnectRequest(BaseModel):
    steam_guard_code: str | None = None


class InviteRequest(BaseModel):
    steam_id: str


class InviteResult(BaseModel):
    ok: bool
    message: str
    mode: str = 'mock'
    steam_id: str | None = None
