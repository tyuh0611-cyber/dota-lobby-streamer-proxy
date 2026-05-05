from urllib.parse import urlencode
import httpx
from .config import settings
from .env_writer import update_env_values
from .schemas import Chatter
from .public_url import get_twitch_redirect_uri


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
            response.raise_for_status()
            data = response.json()
        update_env_values({
            'TWITCH_ACCESS_TOKEN': data.get('access_token'),
            'TWITCH_REFRESH_TOKEN': data.get('refresh_token'),
        })
        return {'ok': True, 'scope': data.get('scope', []), 'expires_in': data.get('expires_in')}

    async def get_chatters(self) -> list[Chatter]:
        if not all([settings.twitch_client_id, settings.twitch_access_token, settings.twitch_broadcaster_id, settings.twitch_moderator_id]):
            return []

        headers = {
            'Client-Id': settings.twitch_client_id,
            'Authorization': 'Bearer ' + settings.twitch_access_token,
        }
        params = {
            'broadcaster_id': settings.twitch_broadcaster_id,
            'moderator_id': settings.twitch_moderator_id,
            'first': 1000,
        }
        chatters: list[Chatter] = []
        async with httpx.AsyncClient(timeout=15.0) as client:
            while True:
                response = await client.get(f'{self.base_url}/chat/chatters', headers=headers, params=params)
                response.raise_for_status()
                payload = response.json()
                for item in payload.get('data', []):
                    chatters.append(Chatter(**item))
                cursor = payload.get('pagination', {}).get('cursor')
                if not cursor:
                    break
                params['after'] = cursor
        return chatters
