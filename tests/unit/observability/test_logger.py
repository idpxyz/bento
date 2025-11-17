from __future__ import annotations

import logging

from bento.observability import logger


def test_logger_exports_and_usable(caplog):
    caplog.set_level(logging.DEBUG)
    logger.debug("hello")
    assert any("hello" in rec.message for rec in caplog.records)
