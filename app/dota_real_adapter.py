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
from .schemas import InviteResult, LobbyMember, LobbyState


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
        self.gc_started = False
        self.last_error: str | None = None
        self.last_login_result: str | None = None
        self.last_gc_result: str | None = None
        self.last_gc_error: str | None = None
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
        missing = []
        if not settings.steam_username:
            missing.append('STEAM_USERNAME')
        if not settings.steam_password:
            missing.append('STEAM_PASSWORD')
        return missing

    async def get_status(self) -> dict:
        deps = self.dependency_status()
        missing_config = self.missing_config()
        return {
            'ok': True,
            'mode': 'real_pending',
            'connected': self.connected,
            'gc_started': self.gc_started,
            'real_adapter_ready': self.connected and self.gc_started,
            'ready_for_login_attempt': deps.ready and not missing_config,
            'message': self._status_message(deps, missing_config),
            'dependencies': deps.model_dump(),
            'config': self.config_status(),
            'missing_config': missing_config,
            'last_error': self.last_error,
            'last_login_result': self.last_login_result,
            'last_gc_result': self.last_gc_result,
            'last_gc_error': self.last_gc_error,
            'dota_methods': self._public_methods(self._dota),
            'steam_methods': self._public_methods(self._client),
        }

    def _status_message(self, deps: DotaDependencyStatus, missing_config: list[str]) -> str:
        if not deps.ready:
            return 'Real Dota adapter dependencies are not installed yet.'
        if missing_config:
            return 'Steam username/password are incomplete.'
        if self.connected and self.gc_started:
            return 'Steam login and Dota GC launch completed. Lobby/invite wiring is being verified.'
        if self.connected:
            return 'Steam login completed. Dota GC launch is not confirmed yet.'
        return 'Ready for Steam login attempt. Use shared_secret or one-time Steam Guard code.'

    def _two_factor_code(self, steam_guard_code: str | None = None) -> str:
        if steam_guard_code:
            return steam_guard_code.strip().replace(' ', '')

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

    async def connect(self, steam_guard_code: str | None = None) -> dict:
        deps = self.dependency_status()
        missing = self.missing_config()

        if not deps.ready:
            self.connected = False
            self.last_error = 'missing_python_dependencies'
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={'error': 'missing_python_dependencies', 'dependencies': deps.model_dump()},
            )

        if missing:
            self.connected = False
            self.last_error = 'missing_config:' + ','.join(missing)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={'error': 'missing_config', 'missing_config': missing, 'config': self.config_status()},
            )

        try:
            result = await asyncio.to_thread(self._connect_sync, steam_guard_code)
        except Exception as exc:
            self.connected = False
            self.gc_started = False
            self.last_error = f'{type(exc).__name__}: {exc}'
            print('DOTA_CONNECT_ERROR', self.last_error, flush=True)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={'error': 'steam_login_failed', 'message': self.last_error, 'status': await self.get_status()},
            )

        self.connected = True
        self.last_error = None
        self.last_login_result = str(result)

        return {
            'ok': True,
            'mode': 'real_pending',
            'connected': True,
            'gc_started': self.gc_started,
            'login_result': self.last_login_result,
            'gc_result': self.last_gc_result,
            'gc_error': self.last_gc_error,
            'message': 'Steam login completed. Dota GC launch was attempted.',
        }

    def _connect_sync(self, steam_guard_code: str | None = None) -> Any:
        from steam.client import SteamClient
        from dota2.client import Dota2Client

        two_factor_code = self._two_factor_code(steam_guard_code)

        client = SteamClient()
        login_result = client.login(
            username=settings.steam_username,
            password=settings.steam_password,
            two_factor_code=two_factor_code,
        )

        self._client = client
        self._dota = Dota2Client(client)
        self._launch_gc_sync()

        return login_result

    def _launch_gc_sync(self) -> None:
        self.gc_started = False
        self.last_gc_result = None
        self.last_gc_error = None

        if not self._dota:
            self.last_gc_error = 'dota_client_not_initialized'
            return

        for method_name in ('launch', 'start', 'connect'):
            method = getattr(self._dota, method_name, None)
            if not callable(method):
                continue

            try:
                result = method()
                self.gc_started = True
                self.last_gc_result = f'{method_name}: {result}'
                print('DOTA_GC_LAUNCH_OK', self.last_gc_result, flush=True)
                return
            except TypeError:
                continue
            except Exception as exc:
                self.last_gc_error = f'{method_name}: {type(exc).__name__}: {exc}'
                print('DOTA_GC_LAUNCH_ERROR', self.last_gc_error, flush=True)
                return

        self.last_gc_error = 'no_launch_method_found:' + ','.join(self._public_methods(self._dota))
        print('DOTA_GC_LAUNCH_ERROR', self.last_gc_error, flush=True)

    async def get_lobby(self) -> LobbyState:
        if not self.connected:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={'error': 'steam_not_connected', 'message': 'Call /dota/connect first.'},
            )

        lobby_payload = self._read_lobby_payload()

        if lobby_payload is None:
            return LobbyState(
                lobby_exists=False,
                lobby_id=None,
                lobby_name='Real Dota lobby not detected yet',
                mode='real_pending',
                connected=self.connected,
                members=[],
            )

        members = self._extract_lobby_members(lobby_payload)

        return LobbyState(
            lobby_exists=True,
            lobby_id=str(self._read_field(lobby_payload, ('lobby_id', 'id', 'server_id')) or 'real-lobby'),
            lobby_name=str(self._read_field(lobby_payload, ('lobby_name', 'name')) or 'Real Dota Lobby'),
            mode='real_pending',
            connected=self.connected,
            members=members,
        )

    async def invite_to_lobby(self, steam_id: str) -> InviteResult:
        if not self.connected:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={'error': 'steam_not_connected', 'message': 'Call /dota/connect first.', 'steam_id': steam_id},
            )

        if not self._dota:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={'error': 'dota_client_not_initialized'})

        candidate_methods = (
            'invite_to_lobby',
            'invite_to_party',
            'invite_to_game',
            'invite_to_practice_lobby',
            'send_lobby_invite',
        )

        errors = []

        for method_name in candidate_methods:
            method = getattr(self._dota, method_name, None)
            if not callable(method):
                continue

            try:
                result = await asyncio.to_thread(method, int(steam_id))
                return InviteResult(
                    ok=True,
                    message=f'{method_name}:{result}',
                    mode='real_pending',
                    steam_id=steam_id,
                )
            except Exception as exc:
                errors.append(f'{method_name}: {type(exc).__name__}: {exc}')

        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={
                'error': 'real_dota_invite_method_not_found_or_failed',
                'steam_id': steam_id,
                'attempted_methods': list(candidate_methods),
                'method_errors': errors,
                'available_dota_methods': self._public_methods(self._dota),
                'connected': self.connected,
                'gc_started': self.gc_started,
                'last_gc_result': self.last_gc_result,
                'last_gc_error': self.last_gc_error,
            },
        )

    def _read_lobby_payload(self) -> Any | None:
        if not self._dota:
            return None

        for attr in ('lobby', 'party', 'lobby_state', 'party_state', 'practice_lobby'):
            value = getattr(self._dota, attr, None)
            if value:
                return value

        for method_name in ('get_lobby', 'get_party', 'request_lobby', 'request_party'):
            method = getattr(self._dota, method_name, None)
            if not callable(method):
                continue

            try:
                value = method()
                if value:
                    return value
            except Exception as exc:
                self.last_gc_error = f'{method_name}: {type(exc).__name__}: {exc}'

        return None

    def _extract_lobby_members(self, lobby_payload: Any) -> list[LobbyMember]:
        raw_members = self._read_field(lobby_payload, ('members', 'all_members', 'players', 'slots')) or []
        members = []

        for item in raw_members:
            steam_id = self._read_field(item, ('steam_id', 'id', 'account_id'))
            dota_name = self._read_field(item, ('name', 'persona_name', 'player_name'))

            members.append(
                LobbyMember(
                    steam_id=str(steam_id) if steam_id else None,
                    dota_id=None,
                    dota_name=str(dota_name) if dota_name else None,
                )
            )

        return members

    def _read_field(self, obj: Any, names: tuple[str, ...]) -> Any | None:
        for name in names:
            if isinstance(obj, dict) and name in obj:
                return obj[name]
            if hasattr(obj, name):
                return getattr(obj, name)
        return None

    def _public_methods(self, obj: Any | None) -> list[str]:
        if obj is None:
            return []

        names = []
        for name in dir(obj):
            if name.startswith('_'):
                continue
            value = getattr(obj, name, None)
            if callable(value):
                names.append(name)

        return names[:80]


real_dota_adapter = RealDotaAdapter()
