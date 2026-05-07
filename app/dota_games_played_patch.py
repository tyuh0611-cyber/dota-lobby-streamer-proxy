def patch_skip_prelaunch_games_played() -> None:
    from steam.client import SteamClient

    from .dota_real_adapter import RealDotaAdapter

    original_connect_sync = RealDotaAdapter._connect_sync
    original_games_played = SteamClient.games_played

    def _connect_sync(self, *args, **kwargs):
        skipped_first_570 = {'done': False}

        def games_played_guard(steam_client, games):
            logged_on = getattr(steam_client, 'logged_on', None)
            steam_id = getattr(steam_client, 'steam_id', None)
            print('STEAM_GAMES_PLAYED_CALL', games, 'logged_on', logged_on, 'steam_id', steam_id, flush=True)
            if not skipped_first_570['done'] and list(games or []) == [570]:
                skipped_first_570['done'] = True
                print('STEAM_GAMES_PLAYED_SKIP_PRELAUNCH_570', flush=True)
                return None
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
                'dota_ready', getattr(dota, 'ready', None),
                'dota_status', getattr(dota, 'connection_status', None),
                flush=True,
            )
            return result
        finally:
            SteamClient.games_played = original_games_played

    RealDotaAdapter._connect_sync = _connect_sync
