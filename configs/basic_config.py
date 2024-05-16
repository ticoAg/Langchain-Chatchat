import os
import shutil
import sys
import tempfile
from functools import partial
from pathlib import Path

import langchain
from loguru import logger

logger.remove()


# 是否显示详细日志
log_verbose = False
langchain.verbose = False

# 通常情况下不需要更改以下内容
console_level = "TRACE"
file_level = "DEBUG"

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
        LOG_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{file.path}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

        logger.add(
            sink=sys.stderr,
            level=console_level,
            format=LOG_FORMAT,
            backtrace=True,
            diagnose=True,
            filter=partial(filter_function, appid),
        )
        logger.add(
            sink=LOG_PATH / f"{appid}.log",
            level=file_level,
            format=LOG_FORMAT,
            rotation="50 MB",
            colorize=False,
            encoding="utf-8",
            backtrace=True,
            diagnose=True,
        )  # 文件输出，文件大小超过50MB时滚动
        self.logger = logger


logger = Logger("Langchain-ChatChat").logger

# 临时文件目录，主要用于文件对话
BASE_TEMP_DIR = os.path.join(tempfile.gettempdir(), "chatchat")
try:
    shutil.rmtree(BASE_TEMP_DIR)
except Exception:
    pass
os.makedirs(BASE_TEMP_DIR, exist_ok=True)
