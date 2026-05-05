from .schemas import InviteResult, LobbyMember, LobbyState


class DotaAdapter:
    async def get_status(self) -> dict:
        return {'ok': True, 'mode': 'mock', 'connected': False}

    async def get_lobby(self) -> LobbyState:
        return LobbyState(
            lobby_exists=True,
            lobby_id='mock-lobby-1',
            members=[
                LobbyMember(steam_id='76561198000000001', dota_id='100000001', dota_name='MockPlayerOne'),
                LobbyMember(steam_id='76561198000000002', dota_id='100000002', dota_name='MockPlayerTwo'),
            ],
        )

    async def invite_to_lobby(self, steam_id: str) -> InviteResult:
        return InviteResult(ok=True, message=f'mock_invite_sent_to_{steam_id}')


dota_adapter = DotaAdapter()
