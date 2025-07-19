"""FSM states for bot handlers."""

from aiogram.fsm.state import State, StatesGroup


class SetupStates(StatesGroup):
    """States for Todoist setup flow."""
    
    waiting_for_token = State()