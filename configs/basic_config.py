import logging
import os
import shutil
import sys
import tempfile
from functools import partial
from pathlib import Path
from types import FrameType
from typing import cast

import langchain
from loguru import logger

logger.remove()


# 是否显示详细日志
log_verbose = False
langchain.verbose = False

# 通常情况下不需要更改以下内容
console_log_level = "TRACE"
file_log_level = "DEBUG"

# 日志存储路径
# 日志存储路径
LOG_PATH = Path(__file__).parents[1] / "logs"
if not os.path.exists(LOG_PATH):
    os.mkdir(LOG_PATH)


def filter_function(appid, record):
    record["file"].path = (
        record["file"].path.split(f"{appid}/")[1]
        if f"{appid}/" in record["file"].path
        else record["file"].path
    )
    return True


# 日志格式
class Logger:

    def __init__(self, appid):
        # 日志格式
        CONSOLE_LOG_FORMAT = (
            "<green>{time:YYYYMMDD HH:mm:ss}</green> | "  # 颜色>时间
            "{process.name} | "  # 进程名
            "{thread.name} | "  # 进程名
            "<cyan>{file.path}</cyan>:<cyan>{line}</cyan> | "  # 行号
            "<level>{level}</level>: "  # 等级
            "<level>{message}</level>"  # 日志内容
        )

        logger.add(
            sink=sys.stdout,
            level=console_log_level,
            format=CONSOLE_LOG_FORMAT,
            # backtrace=True,
            # diagnose=True,
            filter=partial(filter_function, appid),
        )
        FILE_LOG_FORMAT = (
            "{time:YYYYMMDD HH:mm:ss} - "  # 时间
            "{process.name} | "  # 进程名
            "{thread.name} | "  # 进程名
            "{module}.{function}:{line} - {level} - {message}"  # 模块名.方法名:行号
        )
        logger.add(
            sink=LOG_PATH / f"{appid}.log",
            level=file_log_level,
            format=FILE_LOG_FORMAT,
            retention="7 days",  # 设置历史保留时长
            backtrace=True,  # 回溯
            diagnose=True,  # 诊断
            # enqueue=True,  # 异步写入
            rotation="10 MB",
            filter=partial(filter_function, appid),
        )  # 文件输出，文件大小超过10 MB时滚动
        self.logger = logger

    def init_config(self):
        LOGGER_NAMES = ("uvicorn.asgi", "uvicorn.access", "uvicorn")

        # change handler for default uvicorn logger
        logging.getLogger().handlers = [InterceptHandler()]
        for logger_name in LOGGER_NAMES:
            logging_logger = logging.getLogger(logger_name)
            logging_logger.handlers = [InterceptHandler()]

    def get_logger(self):
        return self.logger


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:  # noqa: WPS609
            frame = cast(FrameType, frame.f_back)
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level,
            record.getMessage(),
        )


_logger = Logger("langchain-chatchat")
# _logger.init_config()
logger = _logger.get_logger()

# 临时文件目录，主要用于文件对话
BASE_TEMP_DIR = os.path.join(tempfile.gettempdir(), "chatchat")
try:
    shutil.rmtree(BASE_TEMP_DIR)
except Exception:
    pass
os.makedirs(BASE_TEMP_DIR, exist_ok=True)
