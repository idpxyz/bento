from fastapi import FastAPI
from loms.shared.platform.errors.middleware import install_error_handlers


def install_platform(app: FastAPI, *, error_mapper):
    install_error_handlers(app, error_mapper)
    return app
