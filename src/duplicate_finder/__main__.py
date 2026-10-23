"""`python -m duplicate_finder` starts the app."""

from duplicate_finder.infrastructure import app_logging


def main() -> None:
    app_logging.start()               # logging to %APPDATA%\BuscadorDuplicados\logs
    app_logging.install_hooks()       # and also log the errors nobody has caught

    from duplicate_finder.presentation.main_window import launch
    launch()


if __name__ == "__main__":
    main()
