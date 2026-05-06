from fastapi import HTTPException, status

from .config import settings
from .schemas import InviteResult, LobbyMember, LobbyState


class DotaAdapter:
    def _steam_config_status(self) -> dict:
        return {
            'steam_username_set': bool(settings.steam_username),
            'steam_password_set': bool(settings.steam_password),
            'steam_shared_secret_set': bool(settings.steam_shared_secret),
            'dota_account_id_set': bool(settings.dota_account_id),
            'dota_lobby_id_set': bool(settings.dota_lobby_id),
            'dota_lobby_name_set': bool(settings.dota_lobby_name),
        }

    async def get_status(self) -> dict:
        return {
            'ok': True,
            'mode': 'mock' if settings.dota_mock_mode else 'real_pending',
            'connected': False,
            'mock_mode': settings.dota_mock_mode,
            'real_adapter_ready': False,
            'message': 'Dota adapter is in mock mode.' if settings.dota_mock_mode else 'Real Steam/Dota GC adapter is not implemented yet.',
            'config': self._steam_config_status(),
        }

    async def get_lobby(self) -> LobbyState:
        if not settings.dota_mock_mode:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail={
                    'error': 'real_dota_adapter_not_implemented',
                    'message': 'Real Steam/Dota GC lobby reading is not implemented yet. Enable DOTA_MOCK_MODE=true until real adapter is added.',
                    'config': self._steam_config_status(),
                },
            )

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
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail={
                    'error': 'real_dota_adapter_not_implemented',
                    'message': 'Real Steam/Dota GC invite is not implemented yet. Enable DOTA_MOCK_MODE=true until real adapter is added.',
                    'steam_id': steam_id,
                    'config': self._steam_config_status(),
                },
            )

        return InviteResult(
            ok=True,
            message=f'mock_invite_sent_to_{steam_id}',
            mode='mock',
            steam_id=steam_id,
        )


dota_adapter = DotaAdapter()
