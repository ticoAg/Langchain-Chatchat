"""Usage
加载本地模型：
python webui_allinone.py

调用远程api服务：
python webui_allinone.py --use-remote-api

后台运行webui服务：
python webui_allinone.py --nohup

加载多个非默认模型：
python webui_allinone.py --model-path-address model1@host1@port1 model2@host2@port2 

多卡启动：
python webui_alline.py --model-path-address model@host@port --num-gpus 2 --gpus 0,1 --max-gpu-memory 10GiB

"""

import os
import subprocess

import streamlit as st
from streamlit_option_menu import option_menu

from server.api_allinone_stale import api_args, parser
from server.llm_api_stale import (
    LOG_PATH,
    controller_args,
    launch_all,
    server_args,
    string_args,
    worker_args,
)
from webui_pages import *
from webui_pages.utils import *

parser.add_argument("--use-remote-api", action="store_true")
parser.add_argument("--nohup", action="store_true")
parser.add_argument("--server.port", type=int, default=8501)
parser.add_argument("--theme.base", type=str, default='"light"')
parser.add_argument("--theme.primaryColor", type=str, default='"#165dff"')
parser.add_argument("--theme.secondaryBackgroundColor", type=str, default='"#f5f5f5"')
parser.add_argument("--theme.textColor", type=str, default='"#000000"')
web_args = [
    "server.port",
    "theme.base",
    "theme.primaryColor",
    "theme.secondaryBackgroundColor",
    "theme.textColor",
]


def launch_api(args, args_list=api_args, log_name=None):
    logger.debug("Launching api ...")
    logger.debug("启动API服务...")
    if not log_name:
        log_name = f"{LOG_PATH}api_{args.api_host}_{args.api_port}"
    logger.debug(f"logs on api are written in {log_name}")
    logger.debug(f"API日志位于{log_name}下，如启动异常请查看日志")
    args_str = string_args(args, args_list)
    api_sh = "python  server/{script} {args_str} >{log_name}.log 2>&1 &".format(
        script="api.py", args_str=args_str, log_name=log_name
    )
    subprocess.run(api_sh, shell=True, check=True)
    logger.debug("launch api done!")
    logger.debug("启动API服务完毕.")


def launch_webui(args, args_list=web_args, log_name=None):
    logger.debug("Launching webui...")
    logger.debug("启动webui服务...")
    if not log_name:
        log_name = f"{LOG_PATH}webui"

    args_str = string_args(args, args_list)
    if args.nohup:
        logger.debug(f"logs on api are written in {log_name}")
        logger.debug(f"webui服务日志位于{log_name}下，如启动异常请查看日志")
        webui_sh = "streamlit run webui.py {args_str} >{log_name}.log 2>&1 &".format(
            args_str=args_str, log_name=log_name
        )
    else:
        webui_sh = "streamlit run webui.py {args_str}".format(args_str=args_str)
    subprocess.run(webui_sh, shell=True, check=True)
    logger.debug("launch webui done!")
    logger.debug("启动webui服务完毕.")


if __name__ == "__main__":
    logger.debug(
        "Starting webui_allineone.py, it would take a while, please be patient...."
    )
    logger.debug(
        f"开始启动webui_allinone,启动LLM服务需要约3-10分钟，请耐心等待，如长时间未启动，请到{LOG_PATH}下查看日志..."
    )
    args = parser.parse_args()

    logger.debug("*" * 80)
    if not args.use_remote_api:
        launch_all(
            args=args,
            controller_args=controller_args,
            worker_args=worker_args,
            server_args=server_args,
        )
    launch_api(args=args, args_list=api_args)
    launch_webui(args=args, args_list=web_args)
    logger.debug("Start webui_allinone.py done!")
    logger.debug("感谢耐心等待，启动webui_allinone完毕。")
