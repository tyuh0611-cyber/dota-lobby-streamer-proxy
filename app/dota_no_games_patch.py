def patch_disable_games_played_570() -> None:
    from steam.client import SteamClient

    original_games_played = SteamClient.games_played

    def games_played_guard(self, games):
        print(
            'STEAM_GAMES_PLAYED_INTERCEPT', games,
            'logged_on', getattr(self, 'logged_on', None),
            'steam_id', getattr(self, 'steam_id', None),
            'connected', getattr(self, 'connected', None),
            flush=True,
        )
        if list(games or []) == [570]:
            print('STEAM_GAMES_PLAYED_BLOCK_570_TO_AVOID_DISCONNECT', flush=True)
            return None
        return original_games_played(self, games)

    SteamClient.games_played = games_played_guard
