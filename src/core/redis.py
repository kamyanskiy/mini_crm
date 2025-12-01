from typing import Annotated

from fastapi import Depends

from core.cache import AbstractCache

cache: AbstractCache | None = None


async def get_cache() -> AbstractCache:
    """Dependency для получения cache клиента."""
    if cache is None:
        raise RuntimeError("Cache not initialized")
    return cache


CacheDep = Annotated[AbstractCache, Depends(get_cache)]
