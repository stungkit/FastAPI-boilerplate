from abc import ABC, abstractmethod
from typing import Generic, TypeVar, cast
from uuid import uuid4

from pydantic import BaseModel

from ...config import SessionBackend
from ...logging import get_logger

T = TypeVar("T", bound=BaseModel)
logger = get_logger()


class AbstractSessionStorage(Generic[T], ABC):
    """Abstract base class for session storage implementations."""

    def __init__(
        self,
        prefix: str = "session:",
        expiration: int = 1800,
    ):
        """Initialize the session storage.

        Args:
            prefix: Prefix for all session keys
            expiration: Default session expiration in seconds
        """
        self.prefix = prefix
        self.expiration = expiration

    def generate_session_id(self) -> str:
        """Generate a unique session ID.

        Returns:
            A unique session ID string
        """
        return str(uuid4())

    def get_key(self, session_id: str) -> str:
        """Generate the full key for a session ID.

        Args:
            session_id: The session ID

        Returns:
            The full storage key
        """
        return f"{self.prefix}{session_id}"

    @abstractmethod
    async def create(self, data: T, session_id: str | None = None, expiration: int | None = None) -> str:
        """Create a new session.

        Args:
            data: Session data (must be a Pydantic model)
            session_id: Optional session ID. If not provided, one will be generated
            expiration: Optional custom expiration in seconds

        Returns:
            The session ID
        """
        pass

    @abstractmethod
    async def get(self, session_id: str, model_class: type[T]) -> T | None:
        """Get session data.

        Args:
            session_id: The session ID
            model_class: The Pydantic model class to decode the data into

        Returns:
            The session data or None if session doesn't exist
        """
        pass

    @abstractmethod
    async def update(self, session_id: str, data: T, reset_expiration: bool = True, expiration: int | None = None) -> bool:
        """Update session data.

        Args:
            session_id: The session ID
            data: New session data
            reset_expiration: Whether to reset the expiration
            expiration: Optional custom expiration in seconds

        Returns:
            True if the session was updated, False if it didn't exist
        """
        pass

    @abstractmethod
    async def delete(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: The session ID

        Returns:
            True if the session was deleted, False if it didn't exist
        """
        pass

    @abstractmethod
    async def extend(self, session_id: str, expiration: int | None = None) -> bool:
        """Extend the expiration of a session.

        Args:
            session_id: The session ID
            expiration: Optional custom expiration in seconds

        Returns:
            True if the session was extended, False if it didn't exist
        """
        pass

    @abstractmethod
    async def exists(self, session_id: str) -> bool:
        """Check if a session exists.

        Args:
            session_id: The session ID

        Returns:
            True if the session exists, False otherwise
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the storage connection."""
        pass


class SessionStorage(AbstractSessionStorage[T], Generic[T]):
    def __new__(cls, backend: str = "memory", **kwargs) -> "SessionStorage[T]":
        """Factory method to create the appropriate session storage backend.

        Args:
            backend: The backend to use ("redis", "memcached", "memory")
            **kwargs: Additional arguments to pass to the backend

        Returns:
            An initialized storage backend
        """
        storage: AbstractSessionStorage[T] = get_session_storage(backend, cast(type[T], BaseModel), **kwargs)
        return cast("SessionStorage[T]", storage)


def get_session_storage(backend: str, model_type: type[BaseModel], **kwargs) -> AbstractSessionStorage[T]:
    """Get the appropriate session storage backend.

    Args:
        backend: The backend to use ("redis", "memcached", "memory")
        model_type: The pydantic model type for type checking
        **kwargs: Additional arguments to pass to the backend

    Returns:
        An initialized storage backend
    """
    if backend == SessionBackend.REDIS.value:
        from .backends.redis import RedisSessionStorage

        return RedisSessionStorage(**kwargs)
    elif backend == SessionBackend.MEMCACHED.value:
        from .backends.memcached import MemcachedSessionStorage

        return MemcachedSessionStorage(**kwargs)
    elif backend == SessionBackend.MEMORY.value:
        from .backends.memory import MemorySessionStorage

        return MemorySessionStorage(**kwargs)
    else:
        raise ValueError(f"Unknown backend: {backend}")
