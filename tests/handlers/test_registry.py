from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler

from app.handlers.registry import register_handlers


def test_register_handlers_wires_expected_handler_types():
    application = Application.builder().token("test-token").build()

    register_handlers(application)

    handlers = application.handlers[0]
    command_handlers = [h for h in handlers if isinstance(h, CommandHandler)]
    callback_handlers = [h for h in handlers if isinstance(h, CallbackQueryHandler)]
    message_handlers = [h for h in handlers if isinstance(h, MessageHandler)]

    assert len(command_handlers) == 3
    assert len(callback_handlers) == 8
    assert len(message_handlers) == 1
    assert len(handlers) == len(command_handlers) + len(callback_handlers) + len(message_handlers)


def test_register_handlers_command_names_cover_start_help_cancel():
    application = Application.builder().token("test-token").build()

    register_handlers(application)

    command_names = {
        command
        for handler in application.handlers[0]
        if isinstance(handler, CommandHandler)
        for command in handler.commands
    }

    assert command_names == {"start", "help", "cancel"}
