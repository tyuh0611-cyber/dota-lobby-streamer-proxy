def patch_skip_prelaunch_games_played() -> None:
    import os

    from steam.client import SteamClient
    from steam.core.msg import MsgProto
    from steam.enums.emsg import EMsg

    from .dota_real_adapter import RealDotaAdapter

    original_connect_sync = RealDotaAdapter._connect_sync
    original_games_played = SteamClient.games_played

    def _connect_sync(self, *args, **kwargs):
        call_count = {'count': 0}
        license_requested = {'done': False}
        listeners_attached = {'done': False}

        def attach_steam_debug_listeners(steam_client):
            if listeners_attached['done']:
                return
            listeners_attached['done'] = True

            def log_event(name):
                def handler(*event_args, **event_kwargs):
                    print(
                        'STEAM_EVENT', name,
                        'args', event_args,
                        'kwargs', event_kwargs,
                        'logged_on', getattr(steam_client, 'logged_on', None),
                        'steam_id', getattr(steam_client, 'steam_id', None),
                        'connected', getattr(steam_client, 'connected', None),
                        flush=True,
                    )
                return handler

            for event_name in (
                'connected',
                'disconnected',
                'reconnect',
                'error',
                'logged_on',
                'logged_off',
                'channel_secured',
                'new_login_key',
            ):
                try:
                    steam_client.on(event_name, log_event(event_name))
                except Exception as exc:
                    print('STEAM_EVENT_ATTACH_ERROR', event_name, type(exc).__name__, exc, flush=True)

        def steam_is_logged_on(steam_client):
            return bool(getattr(steam_client, 'logged_on', False)) and bool(getattr(steam_client, 'steam_id', 0))

        def ensure_dota_free_license(steam_client):
            if license_requested['done']:
                return
            license_requested['done'] = True

            if not steam_is_logged_on(steam_client):
                print(
                    'STEAM_DOTA_LICENSE_SKIP_NOT_LOGGED_ON',
                    'logged_on', getattr(steam_client, 'logged_on', None),
                    'steam_id', getattr(steam_client, 'steam_id', None),
                    'connected', getattr(steam_client, 'connected', None),
                    flush=True,
                )
                return

            method = getattr(steam_client, 'request_free_license', None)
            if not callable(method):
                print('STEAM_DOTA_LICENSE_SKIP no_request_free_license_method', flush=True)
                return

            try:
                result = method([570])
                print('STEAM_DOTA_LICENSE_REQUEST', result, flush=True)
            except TypeError:
                try:
                    result = method(570)
                    print('STEAM_DOTA_LICENSE_REQUEST', result, flush=True)
                except Exception as exc:
                    print('STEAM_DOTA_LICENSE_ERROR', type(exc).__name__, exc, flush=True)
            except Exception as exc:
                print('STEAM_DOTA_LICENSE_ERROR', type(exc).__name__, exc, flush=True)

            try:
                steam_client.sleep(1.0)
            except Exception:
                try:
                    import gevent
                    gevent.sleep(1.0)
                except Exception:
                    pass

        def selected_game_id() -> tuple[str, int]:
            variant = os.getenv('DOTA_PRESENCE_VARIANT', 'type1_or_app').strip() or 'type1_or_app'
            if variant == 'shifted':
                return variant, 570 << 24
            if variant == 'type2_or_app':
                return variant, (2 << 24) | 570
            if variant == 'standard':
                return variant, 570
            return 'type1_or_app', (1 << 24) | 570

        def send_dota_presence(steam_client):
            if not steam_is_logged_on(steam_client):
                print(
                    'STEAM_GAMES_PLAYED_SKIP_NOT_LOGGED_ON',
                    'logged_on', getattr(steam_client, 'logged_on', None),
                    'steam_id', getattr(steam_client, 'steam_id', None),
                    'connected', getattr(steam_client, 'connected', None),
                    flush=True,
                )
                return None

            variant, game_id = selected_game_id()
            steam_client.current_games_played = [570]
            result = steam_client.send(MsgProto(EMsg.ClientGamesPlayed), {
                'games_played': [{'game_id': game_id}],
            })
            print('STEAM_GAMES_PLAYED_CUSTOM_570_SENT', variant, game_id, result, flush=True)
            return result

        def games_played_guard(steam_client, games):
            attach_steam_debug_listeners(steam_client)
            call_count['count'] += 1
            logged_on = getattr(steam_client, 'logged_on', None)
            steam_id = getattr(steam_client, 'steam_id', None)
            print(
                'STEAM_GAMES_PLAYED_CALL', games,
                'count', call_count['count'],
                'logged_on', logged_on,
                'steam_id', steam_id,
                'connected', getattr(steam_client, 'connected', None),
                flush=True,
            )
            if list(games or []) == [570]:
                ensure_dota_free_license(steam_client)
                return send_dota_presence(steam_client)
            return original_games_played(steam_client, games)

        SteamClient.games_played = games_played_guard
        try:
            result = original_connect_sync(self, *args, **kwargs)
            client = getattr(self, '_client', None)
            dota = getattr(self, '_dota', None)
            print(
                'STEAM_AFTER_CONNECT_SYNC',
                'result', result,
                'logged_on', getattr(client, 'logged_on', None),
                'steam_id', getattr(client, 'steam_id', None),
                'games', getattr(client, 'current_games_played', None),
                'connected', getattr(client, 'connected', None),
                'dota_ready', getattr(dota, 'ready', None),
                'dota_status', getattr(dota, 'connection_status', None),
                flush=True,
            )
            return result
        finally:
            SteamClient.games_played = original_games_played

    RealDotaAdapter._connect_sync = _connect_sync
