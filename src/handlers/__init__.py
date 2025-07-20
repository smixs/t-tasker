"""Bot handlers."""

from .callbacks import callback_router
from .commands import command_router
from .edit_handlers import edit_router
from .errors import error_router
from .messages import message_router

__all__ = ["callback_router", "command_router", "edit_router", "error_router", "message_router"]
