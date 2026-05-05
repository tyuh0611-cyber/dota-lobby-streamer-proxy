from fastapi import Header, HTTPException, Request, status
from .config import settings


async def require_proxy_key(request: Request, x_api_key: str | None = Header(default=None)) -> None:
    if settings.allowed_client_ip:
        client_host = request.client.host if request.client else None
        if client_host != settings.allowed_client_ip:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='client_ip_not_allowed')

    if not x_api_key or x_api_key != settings.proxy_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='invalid_api_key')
