from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_host: str = '0.0.0.0'
    app_port: int = 8081
    public_base_url: str = 'http://localhost:8081'
    proxy_api_key: str
    allowed_client_ip: str | None = None

    twitch_client_id: str | None = None
    twitch_client_secret: str | None = None
    twitch_access_token: str | None = None
    twitch_refresh_token: str | None = None
    twitch_broadcaster_id: str | None = None
    twitch_moderator_id: str | None = None
    twitch_redirect_uri: str = ''
    twitch_scopes: str = 'moderator:read:chatters'

    dota_mock_mode: bool = True
    steam_username: str | None = None
    steam_password: str | None = None
    steam_shared_secret: str | None = None


settings = Settings()
