from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status

from .config import settings
from .env_writer import update_env_values
from .schemas import Chatter


class TwitchClient:
    base_url = 'https://api.twitch.tv/helix'
    auth_base_url = 'https://id.twitch.tv/oauth2'

    def build_auth_url(self) -> str:
        params = {
            'client_id': settings.twitch_client_id or '',
            'redirect_uri': settings.effective_twitch_redirect_uri,
            'response_type': 'code',
            'scope': settings.twitch_scopes,
        }
        return f'{self.auth_base_url}/authorize?{urlencode(params)}'

    def _headers(self, access_token: str | None = None) -> dict:
        return {
            'Client-Id': settings.twitch_client_id,
            'Authorization': 'Bearer ' + (access_token or settings.twitch_access_token),
        }

    async def exchange_code(self, code: str) -> dict:
        payload = {
            'client_id': settings.twitch_client_id,
            'client_secret': settings.twitch_client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': settings.effective_twitch_redirect_uri,
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(f'{self.auth_base_url}/token', data=payload)
            if response.status_code >= 400:
                error_text = response.text
                print(
                    'TWITCH_TOKEN_ERROR',
                    response.status_code,
                    error_text,
                    'redirect_uri=',
                    settings.effective_twitch_redirect_uri,
                    flush=True,
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail={
                        'error': 'twitch_token_exchange_failed',
                        'twitch_status_code': response.status_code,
                        'twitch_response': error_text,
                        'redirect_uri': settings.effective_twitch_redirect_uri,
                    },
                )

            data = response.json()
            access_token = data.get('access_token')
            refresh_token = data.get('refresh_token')
            user = await self._get_current_user_with_token(client, access_token)

        updates = {
            'TWITCH_ACCESS_TOKEN': access_token,
            'TWITCH_REFRESH_TOKEN': refresh_token,
        }

        if user:
            updates['TWITCH_BROADCASTER_ID'] = user.get('id')
            updates['TWITCH_MODERATOR_ID'] = user.get('id')

        update_env_values(updates)

        return {
            'ok': True,
            'scope': data.get('scope', []),
            'expires_in': data.get('expires_in'),
            'user_id': user.get('id') if user else None,
            'user_login': user.get('login') if user else None,
            'user_name': user.get('display_name') if user else None,
        }

    async def refresh_access_token(self) -> dict:
        if not settings.twitch_refresh_token:
            raise HTTPException(status_code=400, detail='missing_twitch_refresh_token')

        payload = {
            'client_id': settings.twitch_client_id,
            'client_secret': settings.twitch_client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': settings.twitch_refresh_token,
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(f'{self.auth_base_url}/token', data=payload)

        if response.status_code >= 400:
            print('TWITCH_REFRESH_ERROR', response.status_code, response.text, flush=True)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    'error': 'twitch_refresh_failed',
                    'twitch_status_code': response.status_code,
                    'twitch_response': response.text,
                },
            )

        data = response.json()
        update_env_values({
            'TWITCH_ACCESS_TOKEN': data.get('access_token'),
            'TWITCH_REFRESH_TOKEN': data.get('refresh_token') or settings.twitch_refresh_token,
        })

        return {
            'ok': True,
            'scope': data.get('scope', []),
            'expires_in': data.get('expires_in'),
        }

    async def _get_current_user_with_token(self, client: httpx.AsyncClient, access_token: str | None) -> dict | None:
        if not settings.twitch_client_id or not access_token:
            return None

        response = await client.get(
            f'{self.base_url}/users',
            headers={
                'Client-Id': settings.twitch_client_id,
                'Authorization': 'Bearer ' + access_token,
            },
        )

        if response.status_code >= 400:
            print('TWITCH_USERS_ERROR', response.status_code, response.text, flush=True)
            return None

        payload = response.json()
        users = payload.get('data') or []
        return users[0] if users else None

    async def get_me(self) -> dict:
        if not settings.twitch_access_token:
            raise HTTPException(status_code=400, detail='missing_twitch_access_token')

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f'{self.base_url}/users', headers=self._headers())

            if response.status_code == 401:
                refreshed = await self.refresh_access_token()
                response = await client.get(
                    f'{self.base_url}/users',
                    headers=self._headers(refreshed.get('access_token')),
                )

            if response.status_code >= 400:
                print('TWITCH_ME_ERROR', response.status_code, response.text, flush=True)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail={
                        'error': 'twitch_me_failed',
                        'twitch_status_code': response.status_code,
                        'twitch_response': response.text,
                    },
                )

            payload = response.json()

        users = payload.get('data') or []
        user = users[0] if users else None

        return {
            'ok': True,
            'user': user,
        }

    async def setup_current_user_ids(self) -> dict:
        result = await self.get_me()
        user = result.get('user')

        if not user or not user.get('id'):
            raise HTTPException(status_code=502, detail='twitch_user_id_not_found')

        twitch_user_id = user['id']

        update_env_values({
            'TWITCH_BROADCASTER_ID': twitch_user_id,
            'TWITCH_MODERATOR_ID': twitch_user_id,
        })

        return {
            'ok': True,
            'broadcaster_id': twitch_user_id,
            'moderator_id': twitch_user_id,
            'login': user.get('login'),
            'display_name': user.get('display_name'),
        }

    async def get_chatters(self) -> list[Chatter]:
        if not all([
            settings.twitch_client_id,
            settings.twitch_access_token,
            settings.twitch_broadcaster_id,
            settings.twitch_moderator_id,
        ]):
            return []

        headers = self._headers()
        params = {
            'broadcaster_id': settings.twitch_broadcaster_id,
            'moderator_id': settings.twitch_moderator_id,
            'first': 1000,
        }

        chatters: list[Chatter] = []

        async with httpx.AsyncClient(timeout=15.0) as client:
            while True:
                response = await client.get(f'{self.base_url}/chat/chatters', headers=headers, params=params)

                if response.status_code == 401:
                    await self.refresh_access_token()
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail='twitch_token_refreshed_restart_streamer_proxy',
                    )

                if response.status_code >= 400:
                    print('TWITCH_CHATTERS_ERROR', response.status_code, response.text, flush=True)
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail={
                            'error': 'twitch_chatters_failed',
                            'twitch_status_code': response.status_code,
                            'twitch_response': response.text,
                        },
                    )

                payload = response.json()
                for item in payload.get('data', []):
                    chatters.append(Chatter(**item))

                cursor = payload.get('pagination', {}).get('cursor')
                if not cursor:
                    break

                params['after'] = cursor

        return chatters
