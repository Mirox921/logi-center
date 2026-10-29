"""Resolve canonical assets in a checkout, wheel or user-local installation."""
from pathlib import Path


def assets_dir():
    package = Path(__file__).resolve().parent
    bundled = package / 'assets'
    if bundled.is_dir():
        return bundled
    source = package.parents[1] / 'assets'
    if source.is_dir():
        return source
    raise FileNotFoundError('Logi Center assets are missing; reinstall the application.')


def asset_url(relative):
    return (assets_dir() / relative).as_uri()


def configure_engine(engine):
    # Central injection also works in standalone component review tools.
    engine.rootContext().setContextProperty('logiAssetsUrl', assets_dir().as_uri() + '/')
