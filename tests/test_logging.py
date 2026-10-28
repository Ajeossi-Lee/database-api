"""日志按级别写入不同文件。"""

import logging
from datetime import datetime

from app.core.logging import setup_logging


def test_level_logs_go_to_separate_daily_files(tmp_path, monkeypatch):
    import app.core.logging as logging_module

    monkeypatch.setattr(logging_module, "LOG_DIR", tmp_path)
    root = logging.getLogger()
    previous_handlers = list(root.handlers)
    previous_level = root.level
    try:
        setup_logging()
        probe = logging.getLogger("test.logging.levels")
        probe.debug("debug-marker")
        probe.info("info-marker")
        probe.warning("warn-marker")
        probe.error("error-marker")
        for handler in root.handlers:
            handler.flush()

        day = datetime.now().strftime("%Y-%m-%d")
        debug_text = (tmp_path / f"log-debug-{day}.log").read_text(encoding="utf-8")
        info_text = (tmp_path / f"log-info-{day}.log").read_text(encoding="utf-8")
        warn_text = (tmp_path / f"log-warn-{day}.log").read_text(encoding="utf-8")
        error_text = (tmp_path / f"log-error-{day}.log").read_text(encoding="utf-8")

        assert "debug-marker" in debug_text
        assert "info-marker" not in debug_text
        assert "info-marker" in info_text
        assert "warn-marker" not in info_text
        assert "warn-marker" in warn_text
        assert "error-marker" not in warn_text
        assert "error-marker" in error_text
        assert "warn-marker" not in error_text
    finally:
        for handler in list(root.handlers):
            if getattr(handler, "_app_log_handler", False):
                root.removeHandler(handler)
                handler.close()
        root.setLevel(previous_level)
        for handler in previous_handlers:
            if handler not in root.handlers:
                root.addHandler(handler)


def test_sqlalchemy_statements_show_on_console_only(tmp_path, monkeypatch, capsys):
    import app.core.logging as logging_module

    monkeypatch.setattr(logging_module, "LOG_DIR", tmp_path)
    monkeypatch.setattr(logging_module.settings, "LOG_LEVEL", "DEBUG")
    root = logging.getLogger()
    previous_handlers = list(root.handlers)
    previous_level = root.level
    try:
        setup_logging()
        engine_logger = logging.getLogger("sqlalchemy.engine.Engine")
        engine_logger.setLevel(logging.INFO)
        engine_logger.info("select-marker")
        logging.getLogger("app.core.lifespan").info("startup-marker")
        for handler in root.handlers:
            handler.flush()

        day = datetime.now().strftime("%Y-%m-%d")
        info_text = (tmp_path / f"log-info-{day}.log").read_text(encoding="utf-8")
        assert "select-marker" not in info_text
        assert "startup-marker" in info_text
        assert "select-marker" in capsys.readouterr().out
    finally:
        for handler in list(root.handlers):
            if getattr(handler, "_app_log_handler", False):
                root.removeHandler(handler)
                handler.close()
        root.setLevel(previous_level)
        for handler in previous_handlers:
            if handler not in root.handlers:
                root.addHandler(handler)
