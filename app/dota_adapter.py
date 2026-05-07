from fastapi import HTTPException, status

from .config import settings
from .dota_lobby_diagnostics import patch_real_dota_adapter_create_lobby
from .dota_probe import collect_dota_probe
from .dota_real_adapter import real_dota_adapter
from .schemas import InviteResult, LobbyMember, LobbyState

patch_real_dota_adapter_create_lobby()


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

    async def diagnostics(self) -> dict:
        if not settings.dota_mock_mode:
            return await real_dota_adapter._run_sync(collect_dota_probe, real_dota_adapter)

        return {
            'ok': True,
            'mode': 'mock',
            'message': 'Dota diagnostics are only useful when DOTA_MOCK_MODE=false.',
            'config': real_dota_adapter.config_status(),
        }

    async def connect(self, steam_guard_code: str | None = None) -> dict:
        if not settings.dota_mock_mode:
            return await real_dota_adapter.connect(steam_guard_code)

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                'error': 'dota_mock_mode_enabled',
                'message': 'Dota connect is only available when DOTA_MOCK_MODE=false.',
            },
        )

    async def create_lobby(self) -> dict:
        if not settings.dota_mock_mode:
            return await real_dota_adapter.create_lobby()

        return {
            'ok': True,
            'mode': 'mock',
            'lobby_detected': True,
            'lobby_id': settings.dota_lobby_id or 'mock-lobby-1',
            'message': 'Mock lobby already exists.',
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
