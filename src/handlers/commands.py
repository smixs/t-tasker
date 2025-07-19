"""Command handlers for the bot."""

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

logger = logging.getLogger(__name__)

# Create router for commands
command_router = Router(name="commands")


@command_router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """Handle /start command."""
    user = message.from_user
    logger.info(f"User {user.id} started the bot")
    
    await message.answer(
        f"=K @825B, {user.first_name}!\n\n"
        "/ ?><>3C B515 1KAB@> A>74020BL 7040G8 2 Todoist:\n"
        "" B?@02L B5:AB>2>5 A>>1I5=85\n"
        "" 0?8H8 3>;>A>2>5 A>>1I5=85\n"
        "" B?@02L 2845> A @5GLN\n\n"
        "/ ?@52@0IC 8E 2 7040G8 2A53> 70 =5A:>;L:> A5:C=4! =€\n\n"
        "A?>;L7C9 /help 4;O ?>4@>1=>9 8=D>@<0F88."
    )


@command_router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Handle /help command."""
    await message.answer(
        "=Ö <b>0: ?>;L7>20BLAO 1>B><:</b>\n\n"
        "<b>!>740=85 7040G:</b>\n"
        "" "5:AB: ?@>AB> >B?@02L A>>1I5=85\n"
        "" >;>A: 70?8H8 3>;>A>2>5 A>>1I5=85\n"
        "" 845>: >B?@02L 2845> A @5GLN\n\n"
        "<b>@8<5@K A>>1I5=89:</b>\n"
        "" \"C?8BL <>;>:> 702B@0\"\n"
        "" \"AB@5G0 A :;85=B>< 2 ?OB=8FC 2 15:00\"\n"
        "" \">43>B>28BL >BG5B 4> :>=F0 =545;8 #@01>B0\"\n\n"
        "<b>><0=4K:</b>\n"
        "/start - 0G0BL @01>BC A 1>B><\n"
        "/help - >:070BL MBC A?@02:C\n"
        "/settings - 0AB@>9:8 (2 @07@01>B:5)\n\n"
        "=¡ <i>!>25B: O 02B><0B8G5A:8 @0A?>7=0N 40BK, 2@5<O 8 ?@>5:BK!</i>"
    )


@command_router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    """Handle /settings command."""
    await message.answer(
        "™ 0AB@>9:8 ?>:0 2 @07@01>B:5.\n\n"
        "!:>@> 745AL <>6=> 1C45B:\n"
        "" >4:;NG8BL A2>9 Todoist 0::0C=B\n"
        "" K1@0BL ?@>5:B ?> C<>;G0=8N\n"
        "" 0AB@>8BL O7K: @0A?>7=020=8O\n"
        "" #?@02;OBL C254><;5=8O<8"
    )