from app.bot.application import build_application


def test_build_application_succeeds_with_dummy_settings(test_settings):
    application = build_application(test_settings)

    assert application is not None
    assert len(application.handlers[0]) >= 3  # /start, /help, /cancel
    assert application.error_handlers
