"""
调用示例: python llm_api_stale.py --model-path-address THUDM/chatglm2-6b@localhost@7650 THUDM/chatglm2-6b-32k@localhost@7651
其他fastchat.server.controller/worker/openai_api_server参数可按照fastchat文档调用
但少数非关键参数如--worker-address,--allowed-origins,--allowed-methods,--allowed-headers不支持

"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import argparse
import logging
import re
import subprocess

LOG_PATH = "./logs/"
LOG_FORMAT = "%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s"
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logging.basicConfig(format=LOG_FORMAT)

parser = argparse.ArgumentParser()
# ------multi worker-----------------
parser.add_argument(
    "--model-path-address",
    default="THUDM/chatglm2-6b@localhost@20002",
    nargs="+",
    type=str,
    help="model path, host, and port, formatted as model-path@host@port",
)
# ---------------controller-------------------------

parser.add_argument("--controller-host", type=str, default="localhost")
parser.add_argument("--controller-port", type=int, default=21001)
parser.add_argument(
    "--dispatch-method",
    type=str,
    choices=["lottery", "shortest_queue"],
    default="shortest_queue",
)
controller_args = ["controller-host", "controller-port", "dispatch-method"]

# ----------------------worker------------------------------------------

parser.add_argument("--worker-host", type=str, default="localhost")
parser.add_argument("--worker-port", type=int, default=21002)
# parser.add_argument("--worker-address", type=str, default="http://localhost:21002")
# parser.add_argument(
#     "--controller-address", type=str, default="http://localhost:21001"
# )
parser.add_argument(
    "--model-path",
    type=str,
    default="lmsys/vicuna-7b-v1.3",
    help="The path to the weights. This can be a local folder or a Hugging Face repo ID.",
)
parser.add_argument(
    "--revision",
    type=str,
    default="main",
    help="Hugging Face Hub model revision identifier",
)
parser.add_argument(
    "--device",
    type=str,
    choices=["cpu", "cuda", "mps", "xpu"],
    default="cuda",
    help="The device type",
)
parser.add_argument(
    "--gpus",
    type=str,
    default="0",
    help="A single GPU like 1 or multiple GPUs like 0,2",
)
parser.add_argument("--num-gpus", type=int, default=1)
parser.add_argument(
    "--max-gpu-memory",
    type=str,
    default="20GiB",
    help="The maximum memory per gpu. Use a string like '13Gib'",
)
parser.add_argument("--load-8bit", action="store_true", help="Use 8-bit quantization")
parser.add_argument(
    "--cpu-offloading",
    action="store_true",
    help="Only when using 8-bit quantization: Offload excess weights to the CPU that don't fit on the GPU",
)
parser.add_argument(
    "--gptq-ckpt",
    type=str,
    default=None,
    help="Load quantized model. The path to the local GPTQ checkpoint.",
)
parser.add_argument(
    "--gptq-wbits",
    type=int,
    default=16,
    choices=[2, 3, 4, 8, 16],
    help="#bits to use for quantization",
)
parser.add_argument(
    "--gptq-groupsize",
    type=int,
    default=-1,
    help="Groupsize to use for quantization; default uses full row.",
)
parser.add_argument(
    "--gptq-act-order",
    action="store_true",
    help="Whether to apply the activation order GPTQ heuristic",
)
parser.add_argument(
    "--model-names",
    type=lambda s: s.split(","),
    help="Optional display comma separated names",
)
parser.add_argument(
    "--limit-worker-concurrency",
    type=int,
    default=5,
    help="Limit the model concurrency to prevent OOM.",
)
parser.add_argument("--stream-interval", type=int, default=2)
parser.add_argument("--no-register", action="store_true")

worker_args = [
    "worker-host",
    "worker-port",
    "model-path",
    "revision",
    "device",
    "gpus",
    "num-gpus",
    "max-gpu-memory",
    "load-8bit",
    "cpu-offloading",
    "gptq-ckpt",
    "gptq-wbits",
    "gptq-groupsize",
    "gptq-act-order",
    "model-names",
    "limit-worker-concurrency",
    "stream-interval",
    "no-register",
    "controller-address",
    "worker-address",
]
# -----------------openai server---------------------------

parser.add_argument("--server-host", type=str, default="localhost", help="host name")
parser.add_argument("--server-port", type=int, default=8888, help="port number")
parser.add_argument(
    "--allow-credentials", action="store_true", help="allow credentials"
)
# parser.add_argument(
#     "--allowed-origins", type=json.loads, default=["*"], help="allowed origins"
# )
# parser.add_argument(
#     "--allowed-methods", type=json.loads, default=["*"], help="allowed methods"
# )
# parser.add_argument(
#     "--allowed-headers", type=json.loads, default=["*"], help="allowed headers"
# )
parser.add_argument(
    "--api-keys",
    type=lambda s: s.split(","),
    help="Optional list of comma separated API keys",
)
server_args = [
    "server-host",
    "server-port",
    "allow-credentials",
    "api-keys",
    "controller-address",
]

# 0,controller, model_worker, openai_api_server
# 1, 命令行选项
# 2,LOG_PATH
# 3, log的文件名
base_launch_sh = "nohup python3 -m fastchat.serve.{0} {1} >{2}/{3}.log 2>&1 &"

# 0 log_path
# ! 1 log的文件名，必须与bash_launch_sh一致
# 2 controller, worker, openai_api_server
base_check_sh = """while [ `grep -c "Uvicorn running on" {0}/{1}.log` -eq '0' ];do
                        sleep 5s;
                        echo "wait {2} running"
                done
                echo '{2} running' """


def string_args(args, args_list):
    """将args中的key转化为字符串"""
    args_str = ""
    for key, value in args._get_kwargs():
        # args._get_kwargs中的key以_为分隔符,先转换，再判断是否在指定的args列表中
        key = key.replace("_", "-")
        if key not in args_list:
            continue
        # fastchat中port,host没有前缀，去除前缀
        key = key.split("-")[-1] if re.search("port|host", key) else key
        if not value:
            pass
        # 1==True ->  True
        elif isinstance(value, bool) and value == True:
            args_str += f" --{key} "
        elif (
            isinstance(value, list)
            or isinstance(value, tuple)
            or isinstance(value, set)
        ):
            value = " ".join(value)
            args_str += f" --{key} {value} "
        else:
            args_str += f" --{key} {value} "

    return args_str


def launch_worker(item, args, worker_args=worker_args):
    log_name = (
        item.split("/")[-1]
        .split("\\")[-1]
        .replace("-", "_")
        .replace("@", "_")
        .replace(".", "_")
    )
    # 先分割model-path-address,在传到string_args中分析参数
    args.model_path, args.worker_host, args.worker_port = item.split("@")
    args.worker_address = f"http://{args.worker_host}:{args.worker_port}"
    logger.debug("*" * 80)
    logger.debug(f"如长时间未启动，请到{LOG_PATH}{log_name}.log下查看日志")
    worker_str_args = string_args(args, worker_args)
    logger.debug(worker_str_args)
    worker_sh = base_launch_sh.format(
        "model_worker", worker_str_args, LOG_PATH, f"worker_{log_name}"
    )
    worker_check_sh = base_check_sh.format(
        LOG_PATH, f"worker_{log_name}", "model_worker"
    )
    subprocess.run(worker_sh, shell=True, check=True)
    subprocess.run(worker_check_sh, shell=True, check=True)


def launch_all(
    args,
    controller_args=controller_args,
    worker_args=worker_args,
    server_args=server_args,
):
    logger.debug(f"Launching llm service,logs are located in {LOG_PATH}...")
    logger.debug(f"开始启动LLM服务,请到{LOG_PATH}下监控各模块日志...")
    controller_str_args = string_args(args, controller_args)
    controller_sh = base_launch_sh.format(
        "controller", controller_str_args, LOG_PATH, "controller"
    )
    controller_check_sh = base_check_sh.format(LOG_PATH, "controller", "controller")
    subprocess.run(controller_sh, shell=True, check=True)
    subprocess.run(controller_check_sh, shell=True, check=True)
    logger.debug(f"worker启动时间视设备不同而不同，约需3-10分钟，请耐心等待...")
    if isinstance(args.model_path_address, str):
        launch_worker(args.model_path_address, args=args, worker_args=worker_args)
    else:
        for idx, item in enumerate(args.model_path_address):
            logger.debug(f"开始加载第{idx}个模型:{item}")
            launch_worker(item, args=args, worker_args=worker_args)

    server_str_args = string_args(args, server_args)
    server_sh = base_launch_sh.format(
        "openai_api_server", server_str_args, LOG_PATH, "openai_api_server"
    )
    server_check_sh = base_check_sh.format(
        LOG_PATH, "openai_api_server", "openai_api_server"
    )
    subprocess.run(server_sh, shell=True, check=True)
    subprocess.run(server_check_sh, shell=True, check=True)
    logger.debug("Launching LLM service done!")
    logger.debug("LLM服务启动完毕。")


if __name__ == "__main__":
    args = parser.parse_args()
    # 必须要加http//:，否则InvalidSchema: No connection adapters were found
    args = argparse.Namespace(
        **vars(args),
        **{
            "controller-address": f"http://{args.controller_host}:{str(args.controller_port)}"
        },
    )

    if args.gpus:
        if len(args.gpus.split(",")) < args.num_gpus:
            raise ValueError(
                f"Larger --num-gpus ({args.num_gpus}) than --gpus {args.gpus}!"
            )
        os.environ["CUDA_VISIBLE_DEVICES"] = args.gpus
    launch_all(args=args)
