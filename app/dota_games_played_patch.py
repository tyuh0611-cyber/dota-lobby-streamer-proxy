def patch_skip_prelaunch_games_played() -> None:
    from steam.client import SteamClient

    from .dota_real_adapter import RealDotaAdapter

    original_connect_sync = RealDotaAdapter._connect_sync
    original_games_played = SteamClient.games_played

    def _connect_sync(self, *args, **kwargs):
        skipped_first_570 = {'done': False}

        def games_played_guard(steam_client, games):
            if not skipped_first_570['done'] and list(games or []) == [570]:
                skipped_first_570['done'] = True
                print('STEAM_GAMES_PLAYED_SKIP_PRELAUNCH_570', flush=True)
                return None
            return original_games_played(steam_client, games)

        SteamClient.games_played = games_played_guard
        try:
            return original_connect_sync(self, *args, **kwargs)
        finally:
            SteamClient.games_played = original_games_played

    RealDotaAdapter._connect_sync = _connect_sync
