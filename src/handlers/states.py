"""FSM states for bot handlers."""

from aiogram.fsm.state import State, StatesGroup


class SetupStates(StatesGroup):
    """States for Todoist setup flow."""

    waiting_for_token = State()


class EditTaskStates(StatesGroup):
    """States for task editing flow."""

    choosing_field = State()
    editing_content = State()
    editing_due_date = State()
    editing_priority = State()
