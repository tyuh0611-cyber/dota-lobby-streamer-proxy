import inspect
import pkg_resources
from typing import Any


def _safe_text(value: Any, limit: int = 4000) -> str:
    try:
        text = str(value)
    except Exception as exc:
        text = f'<str_error {type(exc).__name__}: {exc}>'
    return text[:limit]


def _source(obj: Any, limit: int = 8000) -> str:
    try:
        return inspect.getsource(obj)[:limit]
    except Exception as exc:
        return f'{type(exc).__name__}: {exc}'


def collect_dota_probe(real_adapter: Any) -> dict:
    out: dict[str, Any] = {}

    for package in ('steam', 'dota2'):
        try:
            out[f'{package}_version'] = pkg_resources.get_distribution(package).version
        except Exception as exc:
            out[f'{package}_version_error'] = f'{type(exc).__name__}: {exc}'

    try:
        import dota2.client as dota_client
        import dota2.features.lobby as lobby_feature
        import dota2.features.sharedobjects as so_feature
        from dota2.enums import EDOTAGCMsg

        out['dota2_client_file'] = getattr(dota_client, '__file__', None)
        out['lobby_feature_file'] = getattr(lobby_feature, '__file__', None)
        out['sharedobjects_file'] = getattr(so_feature, '__file__', None)
        out['practice_lobby_enum_values'] = {
            name: int(value)
            for name, value in EDOTAGCMsg.__members__.items()
            if 'PracticeLobby' in name or 'Lobby' in name
        }
        out['Dota2Client_launch_source'] = _source(getattr(dota_client.Dota2Client, 'launch', None))
        out['Lobby_create_tournament_lobby_source'] = _source(
            getattr(lobby_feature.Lobby, 'create_tournament_lobby', None)
        )
        out['SharedObjects_source_head'] = _source(so_feature, limit=12000)
    except Exception as exc:
        out['import_error'] = f'{type(exc).__name__}: {exc}'

    dota = getattr(real_adapter, '_dota', None)
    client = getattr(real_adapter, '_client', None)

    out['runtime'] = {
        'connected': getattr(real_adapter, 'connected', None),
        'gc_started': getattr(real_adapter, 'gc_started', None),
        'has_client': client is not None,
        'has_dota': dota is not None,
    }

    if client is not None:
        out['client_runtime'] = {
            'logged_on': _safe_text(getattr(client, 'logged_on', None)),
            'steam_id': _safe_text(getattr(client, 'steam_id', None)),
            'current_games_played': _safe_text(getattr(client, 'current_games_played', None)),
        }

    if dota is not None:
        out['dota_runtime'] = {
            'ready': _safe_text(getattr(dota, 'ready', None)),
            'steam_id': _safe_text(getattr(dota, 'steam_id', None)),
            'account_id': _safe_text(getattr(dota, 'account_id', None)),
            'connection_status': _safe_text(getattr(dota, 'connection_status', None)),
            'lobby': _safe_text(getattr(dota, 'lobby', None), 1000),
            'party': _safe_text(getattr(dota, 'party', None), 1000),
        }

        socache = getattr(dota, 'socache', None)
        out['socache_runtime'] = {
            'type': type(socache).__name__ if socache is not None else None,
            'repr': _safe_text(socache, 1000),
            'dir': [name for name in dir(socache) if not name.startswith('__')][:120] if socache is not None else [],
        }

    return out
