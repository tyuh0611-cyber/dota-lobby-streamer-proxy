import importlib.util
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status

from .config import settings
from .schemas import InviteResult, LobbyState


@dataclass
class DotaDependencyStatus:
    steam_package_available: bool
    dota2_package_available: bool

    @property
    def ready(self) -> bool:
        return self.steam_package_available and self.dota2_package_available

    def model_dump(self) -> dict[str, bool]:
        return {
            'steam_package_available': self.steam_package_available,
            'dota2_package_available': self.dota2_package_available,
            'ready': self.ready,
        }


class RealDotaAdapter:
    def __init__(self) -> None:
        self.connected = False
        self.last_error: str | None = None
        self._client: Any | None = None
        self._dota: Any | None = None

    def dependency_status(self) -> DotaDependencyStatus:
        return DotaDependencyStatus(
            steam_package_available=importlib.util.find_spec('steam') is not None,
            dota2_package_available=importlib.util.find_spec('dota2') is not None,
        )

    def config_status(self) -> dict:
        return {
            'steam_username_set': bool(settings.steam_username),
            'steam_password_set': bool(settings.steam_password),
            'steam_shared_secret_set': bool(settings.steam_shared_secret),
            'dota_account_id_set': bool(settings.dota_account_id),
            'dota_lobby_id_set': bool(settings.dota_lobby_id),
            'dota_lobby_name_set': bool(settings.dota_lobby_name),
        }

    def missing_config(self) -> list[str]:
        missing: list[str] = []
        if not settings.steam_username:
            missing.append('STEAM_USERNAME')
        if not settings.steam_password:
            missing.append('STEAM_PASSWORD')
        if not settings.steam_shared_secret:
            missing.append('STEAM_SHARED_SECRET')
        return missing

    async def get_status(self) -> dict:
        deps = self.dependency_status()
        missing_config = self.missing_config()
        ready_for_login = deps.ready and not missing_config
        return {
            'ok': True,
            'mode': 'real_pending',
            'connected': self.connected,
            'real_adapter_ready': False,
            'ready_for_login_attempt': ready_for_login,
            'message': self._status_message(deps, missing_config),
            'dependencies': deps.model_dump(),
            'config': self.config_status(),
            'missing_config': missing_config,
            'last_error': self.last_error,
        }

    def _status_message(self, deps: DotaDependencyStatus, missing_config: list[str]) -> str:
        if not deps.ready:
            return 'Real Dota adapter dependencies are not installed yet.'
        if missing_config:
            return 'Real Dota adapter credentials are incomplete.'
        return 'Real Dota adapter boundary is ready for Steam/Dota GC implementation.'

    def _not_implemented(self, operation: str, extra: dict | None = None) -> HTTPException:
        payload = {
            'error': 'real_dota_adapter_not_implemented',
            'operation': operation,
            'message': 'Real Steam/Dota Game Coordinator implementation is not wired yet. Keep DOTA_MOCK_MODE=true until the GC client is implemented.',
            'status': {
                'dependencies': self.dependency_status().model_dump(),
                'config': self.config_status(),
                'missing_config': self.missing_config(),
                'connected': self.connected,
                'last_error': self.last_error,
            },
        }
        if extra:
            payload.update(extra)
        return HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=payload)

    async def connect(self) -> dict:
        raise self._not_implemented('connect')

    async def get_lobby(self) -> LobbyState:
        raise self._not_implemented('get_lobby')

    async def invite_to_lobby(self, steam_id: str) -> InviteResult:
        raise self._not_implemented('invite_to_lobby', {'steam_id': steam_id})


real_dota_adapter = RealDotaAdapter()
