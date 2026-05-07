import time
from typing import Any


def _wait_tick(client: Any, seconds: float = 2.0) -> None:
    try:
        client.sleep(seconds)
        return
    except Exception:
        pass
    try:
        import gevent
        gevent.sleep(seconds)
    except Exception:
        time.sleep(seconds)


def run_presence_probe(real_adapter: Any) -> dict:
    client = getattr(real_adapter, '_client', None)
    if client is None:
        return {'ok': False, 'error': 'steam_client_not_initialized'}

    before = {
        'logged_on': str(getattr(client, 'logged_on', None)),
        'steam_id': str(getattr(client, 'steam_id', None)),
        'connected': str(getattr(client, 'connected', None)),
        'games': str(getattr(client, 'current_games_played', None)),
    }

    results = []

    def snapshot(label: str) -> dict:
        return {
            'label': label,
            'logged_on': str(getattr(client, 'logged_on', None)),
            'steam_id': str(getattr(client, 'steam_id', None)),
            'connected': str(getattr(client, 'connected', None)),
            'games': str(getattr(client, 'current_games_played', None)),
        }

    def try_recover() -> dict:
        out = {'attempted': False}
        if bool(getattr(client, 'logged_on', False)):
            return out
        reconnect = getattr(client, 'reconnect', None)
        if callable(reconnect):
            out['attempted'] = True
            try:
                out['reconnect_result'] = str(reconnect())
            except Exception as exc:
                out['reconnect_error'] = f'{type(exc).__name__}: {exc}'
            _wait_tick(client, 3)
        out.update(snapshot('after_recover'))
        return out

    def run_variant(name: str, fn) -> None:
        entry = {'variant': name, 'before': snapshot('before')}
        if not bool(getattr(client, 'logged_on', False)):
            entry['recover_before'] = try_recover()
        try:
            send_result = fn()
            entry['send_result'] = str(send_result)
        except Exception as exc:
            entry['send_error'] = f'{type(exc).__name__}: {exc}'
        _wait_tick(client, 3)
        entry['after'] = snapshot('after')
        results.append(entry)

    from steam.core.msg import MsgProto
    from steam.enums.emsg import EMsg

    def proto_570():
        return client.send(MsgProto(EMsg.ClientGamesPlayed), {
            'games_played': [{'game_id': 570}],
        })

    def proto_gameid_shifted():
        return client.send(MsgProto(EMsg.ClientGamesPlayed), {
            'games_played': [{'game_id': 570 << 24}],
        })

    def proto_with_extra_info():
        return client.send(MsgProto(EMsg.ClientGamesPlayed), {
            'games_played': [{'game_id': 570, 'game_extra_info': 'Dota 2'}],
        })

    def no_data_blob_570():
        return client.send(MsgProto(EMsg.ClientGamesPlayedNoDataBlob), {
            'games_played': [{'game_id': 570}],
        })

    for variant, fn in (
        ('ClientGamesPlayed_570', proto_570),
        ('ClientGamesPlayed_gameid_shifted_570_24', proto_gameid_shifted),
        ('ClientGamesPlayed_570_extra_info', proto_with_extra_info),
        ('ClientGamesPlayedNoDataBlob_570', no_data_blob_570),
    ):
        run_variant(variant, fn)
        if not bool(getattr(client, 'logged_on', False)):
            break

    return {
        'ok': True,
        'before': before,
        'results': results,
        'final': snapshot('final'),
    }
