# T-Tasker Bot Debugging Report

## Executive Summary
Systematically debugged the t-tasker Telegram bot codebase and identified 3 critical bugs in the edit handlers that would cause runtime errors. All bugs have been fixed.

## Bugs Found and Fixed

### 1. Missing Middleware Parameters in Voice Handler (CRITICAL)
**File**: `/root/projects/t-tasker/src/handlers/edit_handlers.py`
**Line**: 115
**Issue**: The voice message handler was missing `user` and `todoist_token` parameters that are injected by AuthMiddleware
**Fix**: Added missing parameters to match the expected signature
```python
# Before:
async def handle_voice_in_edit_mode(message: Message, state: FSMContext, bot: Bot) -> None:

# After:
async def handle_voice_in_edit_mode(message: Message, state: FSMContext, bot: Bot, user: "User", todoist_token: str) -> None:
```

### 2. Incorrect Method Name (CRITICAL)
**File**: `/root/projects/t-tasker/src/handlers/edit_handlers.py`
**Line**: 149
**Issue**: Called `transcribe_audio()` but the actual method is `transcribe()`
**Fix**: Updated to use correct method name with correct parameters
```python
# Before:
transcript = await deepgram_service.transcribe_audio(
    audio_data=voice_buffer.getvalue(),
    mime_type=mime_type,
    filename="voice.ogg"
)

# After:
transcript = await deepgram_service.transcribe(
    audio_bytes=voice_buffer.getvalue(),
    mime_type=mime_type
)
```

### 3. Incorrect Chat Action Method (MINOR)
**File**: `/root/projects/t-tasker/src/handlers/edit_handlers.py`
**Line**: 146
**Issue**: Used non-existent `message.chat.do()` method
**Fix**: Changed to correct `bot.send_chat_action()` method
```python
# Before:
await message.chat.do("typing")

# After:
await bot.send_chat_action(message.chat.id, "typing")
```

## Other Findings

### 1. Hardcoded Timezone (MINOR)
**File**: `/root/projects/t-tasker/src/services/command_executor.py`
**Line**: 162
**Issue**: Hardcoded Tashkent timezone (+5 hours) for all users
**Impact**: Users in other timezones will see incorrect times
**Recommendation**: Add timezone preference to User model

### 2. Duplicate User Models (CONFUSING)
**Files**: 
- `/root/projects/t-tasker/src/models/user.py` (unused)
- `/root/projects/t-tasker/src/models/db.py` (actual model)
**Issue**: Two different User model definitions could cause confusion
**Recommendation**: Remove the unused model file

### 3. DSPy Parser Integration
**Status**: Properly integrated but disabled by default
**Configuration**: `use_dspy_parser = False` in settings
**Model**: Exists at `models/todoist_parser_v1.json`

## Test Results
All critical bugs have been fixed and verified:
- ✅ Edit handler voice signature correct
- ✅ Message handler voice signature correct  
- ✅ DeepgramService has correct transcribe method
- ✅ Callback handlers have correct signatures

## Recommendations
1. Add user timezone preference to handle international users
2. Remove duplicate User model to avoid confusion
3. Add integration tests for voice message handling
4. Consider enabling DSPy parser for better task parsing
5. Add proper error tracking (Sentry is configured but not used)

## Files Modified
1. `/root/projects/t-tasker/src/handlers/edit_handlers.py` - Fixed 3 bugs

## Conclusion
The bot had critical bugs that would cause voice message handling in edit mode to fail with "missing 2 required positional arguments" error. All critical bugs have been fixed. The bot should now handle voice messages correctly in both normal and edit modes.