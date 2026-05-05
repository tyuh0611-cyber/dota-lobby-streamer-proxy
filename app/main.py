from fastapi import Depends, FastAPI, Query
from .dota_adapter import dota_adapter
from .schemas import InviteRequest
from .security import require_proxy_key
from .twitch_client import TwitchClient

app = FastAPI(title='Streamer Proxy', version='0.1.0')
twitch_client = TwitchClient()


@app.get('/health')
async def health() -> dict:
    return {'ok': True}


@app.get('/twitch/auth-url', dependencies=[Depends(require_proxy_key)])
async def twitch_auth_url() -> dict:
    return {'url': twitch_client.build_auth_url()}


@app.get('/twitch/callback')
async def twitch_callback(code: str = Query(...)) -> dict:
    result = await twitch_client.exchange_code(code)
    return {
        'ok': True,
        'message': 'Twitch tokens saved to .env. Restart streamer-proxy now.',
        'result': result,
    }


@app.get('/chatters', dependencies=[Depends(require_proxy_key)])
async def get_chatters() -> dict:
    chatters = await twitch_client.get_chatters()
    return {'data': [c.model_dump() for c in chatters], 'total': len(chatters)}


@app.get('/dota/status', dependencies=[Depends(require_proxy_key)])
async def dota_status() -> dict:
    return await dota_adapter.get_status()


@app.get('/dota/lobby', dependencies=[Depends(require_proxy_key)])
async def dota_lobby() -> dict:
    lobby = await dota_adapter.get_lobby()
    return lobby.model_dump()


@app.post('/dota/invite', dependencies=[Depends(require_proxy_key)])
async def dota_invite(payload: InviteRequest) -> dict:
    result = await dota_adapter.invite_to_lobby(payload.steam_id)
    return result.model_dump()
