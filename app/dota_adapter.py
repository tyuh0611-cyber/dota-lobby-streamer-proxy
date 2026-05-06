from .config import settings
from .dota_real_adapter import real_dota_adapter
from .schemas import InviteResult, LobbyMember, LobbyState


class DotaAdapter:
    async def get_status(self) -> dict:
        if not settings.dota_mock_mode:
            return await real_dota_adapter.get_status()

        return {
            'ok': True,
            'mode': 'mock',
            'connected': False,
            'mock_mode': True,
            'real_adapter_ready': False,
            'message': 'Dota adapter is in mock mode.',
            'config': real_dota_adapter.config_status(),
        }

    async def get_lobby(self) -> LobbyState:
        if not settings.dota_mock_mode:
            return await real_dota_adapter.get_lobby()

        lobby_id = settings.dota_lobby_id or 'mock-lobby-1'
        lobby_name = settings.dota_lobby_name or 'Mock Lobby'

        return LobbyState(
            lobby_exists=True,
            lobby_id=lobby_id,
            lobby_name=lobby_name,
            mode='mock',
            connected=False,
            members=[
                LobbyMember(steam_id='76561198000000001', dota_id='100000001', dota_name='MockPlayerOne'),
                LobbyMember(steam_id='76561198000000002', dota_id='100000002', dota_name='MockPlayerTwo'),
            ],
        )

    async def invite_to_lobby(self, steam_id: str) -> InviteResult:
        if not settings.dota_mock_mode:
            return await real_dota_adapter.invite_to_lobby(steam_id)

        return InviteResult(
            ok=True,
            message=f'mock_invite_sent_to_{steam_id}',
            mode='mock',
            steam_id=steam_id,
        )


dota_adapter = DotaAdapter()
