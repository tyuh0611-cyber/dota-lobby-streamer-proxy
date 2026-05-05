import os


def get_public_base_url() -> str:
    return os.getenv('PUBLIC_BASE_URL', 'http://localhost:8081').rstrip('/')


def get_twitch_redirect_uri() -> str:
    return f'{get_public_base_url()}/twitch/callback'
