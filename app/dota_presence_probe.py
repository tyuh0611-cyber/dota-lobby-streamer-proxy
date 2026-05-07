import os
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


def run_presence_probe(real_adapter: Any, selected_variant: str | None = None) -> dict:
    if not selected_variant:
        selected_variant = os.getenv('DOTA_PRESENCE_VARIANT') or None

    client = getattr(real_adapter, '_client', None)
    if client is None:
        return {'ok': False, 'error': 'steam_client_not_initialized', 'selected_variant': selected_variant}

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

    def run_variant(name: str, fn) -> None:
        entry = {'variant': name, 'before': snapshot('before')}
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

    def with_data_blob_empty():
        return client.send(MsgProto(EMsg.ClientGamesPlayedWithDataBlob), {
            'games_played': [{'game_id': 570}],
        })

    variants = {
        'standard': proto_570,
        'shifted': proto_gameid_shifted,
        'extra_info': proto_with_extra_info,
        'no_data_blob': no_data_blob_570,
        'with_data_blob_empty': with_data_blob_empty,
    }

    if selected_variant:
        fn = variants.get(selected_variant)
        if not fn:
            return {
                'ok': False,
                'error': 'unknown_variant',
                'selected_variant': selected_variant,
                'available_variants': list(variants.keys()),
                'before': before,
            }
        run_variant(selected_variant, fn)
    else:
        for variant, fn in variants.items():
            run_variant(variant, fn)
            if not bool(getattr(client, 'logged_on', False)):
                break

    return {
        'ok': True,
        'selected_variant': selected_variant,
        'available_variants': list(variants.keys()),
        'before': before,
        'results': results,
        'final': snapshot('final'),
    }
