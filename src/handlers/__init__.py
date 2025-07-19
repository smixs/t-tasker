"""Bot handlers."""

from .commands import command_router
from .errors import error_router
from .messages import message_router

__all__ = ["command_router", "error_router", "message_router"]