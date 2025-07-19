"""Global error handler for the bot."""

import logging

from aiogram import Router
from aiogram.types import ErrorEvent

from src.core.exceptions import (
    TranscriptionError,
    OpenAIError,
    TodoistError,
    RateLimitError,
    AuthenticationError,
    ValidationError
)

logger = logging.getLogger(__name__)

# Create router for errors
error_router = Router(name="errors")


@error_router.error()
async def handle_error(event: ErrorEvent) -> None:
    """Global error handler for all errors."""
    exception = event.exception
    update = event.update
    
    logger.exception(f"Error handling update {update}: {exception}")
    
    # Get message object if available
    message = None
    if update.message:
        message = update.message
    elif update.callback_query and update.callback_query.message:
        message = update.callback_query.message
    
    if not message:
        logger.error("Cannot send error message: no message object available")
        return
    
    # Handle specific error types
    if isinstance(exception, RateLimitError):
        await message.answer(
            "ñ @52KH5= ;8<8B 70?@>A>2. >60;C9AB0, ?>4>648B5 =5<=>3> 8 ?>?@>1C9B5 A=>20."
        )
    elif isinstance(exception, TranscriptionError):
        await message.answer(
            "<¤ 5 C40;>AL @0A?>7=0BL @5GL. >?@>1C9B5 70?8A0BL A>>1I5=85 5I5 @07 "
            "8;8 >B?@02LB5 B5:AB><."
        )
    elif isinstance(exception, OpenAIError):
        await message.answer(
            "> H81:0 ?@8 >1@01>B:5 20H53> 70?@>A0. >?@>1C9B5 AD>@<C;8@>20BL 8=0G5 "
            "8;8 ?>2B>@8B5 ?>765."
        )
    elif isinstance(exception, TodoistError):
        await message.answer(
            "=Ý 5 C40;>AL A>740BL 7040GC 2 Todoist. @>25@LB5 ?>4:;NG5=85 : 0::0C=BC "
            "8;8 ?>?@>1C9B5 ?>765."
        )
    elif isinstance(exception, AuthenticationError):
        await message.answer(
            "= 5>1E>48<> ?>4:;NG8BL 0::0C=B Todoist. A?>;L7C9B5 /settings 4;O =0AB@>9:8."
        )
    elif isinstance(exception, ValidationError):
        await message.answer(
            f"L H81:0 20;840F88: {str(exception)}"
        )
    else:
        # Generic error message
        await message.answer(
            "L @>87>H;0 =5>6840==0O >H81:0. K C65 @01>B05< =04 @5H5=85<.\n"
            ">60;C9AB0, ?>?@>1C9B5 ?>765."
        )
    
    # TODO: Send error to Sentry when configured