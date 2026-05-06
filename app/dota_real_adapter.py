import asyncio
import base64
import hashlib
import hmac
import importlib.util
import time
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
        self.last_login_result: str | None = None
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
            'last_login_result': self.last_login_result,
        }

    def _status_message(self, deps: DotaDependencyStatus, missing_config: list[str]) -> str:
        if not deps.ready:
            return 'Real Dota adapter dependencies are not installed yet.'
        if missing_config:
            return 'Real Dota adapter credentials are incomplete.'
        if self.connected:
            return 'Steam login completed. Dota GC lobby/invite wiring is next.'
        return 'Ready for Steam login attempt.'

    def _two_factor_code(self) -> str:
        secret = settings.steam_shared_secret.strip()
        if not secret:
            return ''

        shared_secret = base64.b64decode(secret)
        timestamp = int(time.time()) // 30
        time_bytes = timestamp.to_bytes(8, byteorder='big')
        digest = hmac.new(shared_secret, time_bytes, hashlib.sha1).digest()
        start = digest[19] & 0x0F
        code_int = int.from_bytes(digest[start:start + 4], byteorder='big') & 0x7FFFFFFF
        chars = '23456789BCDFGHJKMNPQRTVWXY'

        code = ''
        for _ in range(5):
            code += chars[code_int % len(chars)]
            code_int //= len(chars)

        return code

    async def connect(self) -> dict:
        deps = self.dependency_status()
        missing = self.missing_config()

        if not deps.ready:
            self.connected = False
            self.last_error = 'missing_python_dependencies'
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    'error': 'missing_python_dependencies',
                    'dependencies': deps.model_dump(),
                    'message': 'Install streamer proxy requirements first.',
                },
            )

        if missing:
            self.connected = False
            self.last_error = 'missing_config:' + ','.join(missing)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    'error': 'missing_config',
                    'missing_config': missing,
                    'config': self.config_status(),
                },
            )

        try:
            result = await asyncio.to_thread(self._connect_sync)
        except Exception as exc:
            self.connected = False
            self.last_error = f'{type(exc).__name__}: {exc}'
            print('DOTA_CONNECT_ERROR', self.last_error, flush=True)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    'error': 'steam_login_failed',
                    'message': self.last_error,
                    'status': await self.get_status(),
                },
            )

        self.connected = True
        self.last_error = None
        self.last_login_result = str(result)

        return {
            'ok': True,
            'mode': 'real_pending',
            'connected': True,
            'login_result': self.last_login_result,
            'message': 'Steam login completed. Dota GC lobby/invite wiring is next.',
        }

    def _connect_sync(self) -> Any:
        from steam.client import SteamClient
        from dota2.client import Dota2Client

        two_factor_code = self._two_factor_code()

        client = SteamClient()
        login_result = client.login(
            username=settings.steam_username,
            password=settings.steam_password,
            two_factor_code=two_factor_code,
        )

        self._client = client
        self._dota = Dota2Client(client)

        return login_result

    async def get_lobby(self) -> LobbyState:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={
                'error': 'real_dota_lobby_not_implemented',
                'message': 'Steam login boundary exists. Dota GC lobby reading is next.',
                'connected': self.connected,
                'last_login_result': self.last_login_result,
                'last_error': self.last_error,
            },
        )

    async def invite_to_lobby(self, steam_id: str) -> InviteResult:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={
                'error': 'real_dota_invite_not_implemented',
                'message': 'Steam login boundary exists. Dota GC invite wiring is next.',
                'steam_id': steam_id,
                'connected': self.connected,
                'last_login_result': self.last_login_result,
                'last_error': self.last_error,
            },
        )


real_dota_adapter = RealDotaAdapter()
