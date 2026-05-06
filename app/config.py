from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_host: str = '0.0.0.0'
    app_port: int = 8081
    public_base_url: str = 'http://localhost:8081'
    twitch_redirect_uri: str = ''
    post_twitch_auth_redirect_url: str = ''

    proxy_api_key: str = 'change_me_long_random_value'
    allowed_client_ip: str = ''

    twitch_client_id: str = ''
    twitch_client_secret: str = ''
    twitch_access_token: str = ''
    twitch_refresh_token: str = ''
    twitch_broadcaster_id: str = ''
    twitch_moderator_id: str = ''
    twitch_scopes: str = 'moderator:read:chatters'

    dota_mock_mode: bool = True
    dota_lobby_id: str = ''
    dota_lobby_name: str = ''
    dota_account_id: str = ''
    steam_username: str = ''
    steam_password: str = ''
    steam_shared_secret: str = ''

    @property
    def effective_twitch_redirect_uri(self) -> str:
        if self.twitch_redirect_uri:
            return self.twitch_redirect_uri
        return f'{self.public_base_url.rstrip("/")}/twitch/callback'


settings = Settings()
