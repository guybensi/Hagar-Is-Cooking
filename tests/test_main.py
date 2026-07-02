from unittest.mock import MagicMock, patch

from app.__main__ import main


def test_main_builds_application_inits_db_and_runs_polling():
    fake_engine = MagicMock()
    fake_application = MagicMock()
    fake_application.bot_data = {"engine": fake_engine}
    fake_settings = MagicMock(log_level="INFO")

    with (
        patch("app.__main__.get_settings", return_value=fake_settings) as mock_get_settings,
        patch("app.__main__.configure_logging") as mock_configure_logging,
        patch("app.__main__.build_application", return_value=fake_application) as mock_build,
        patch("app.__main__.init_db") as mock_init_db,
        patch("app.__main__.asyncio.run") as mock_asyncio_run,
    ):
        main()

        mock_get_settings.assert_called_once()
        mock_configure_logging.assert_called_once_with("INFO")
        mock_build.assert_called_once_with(fake_settings)
        mock_init_db.assert_called_once_with(fake_engine)
        mock_asyncio_run.assert_called_once()
        fake_application.run_polling.assert_called_once()
