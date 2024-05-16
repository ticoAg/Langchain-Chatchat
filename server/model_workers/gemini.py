import json
import sys
from typing import Dict, List

import httpx
from fastchat import conversation as conv
from fastchat.conversation import Conversation

from configs import log_verbose, logger
from server.model_workers.base import *
from server.utils import get_httpx_client


class GeminiWorker(ApiModelWorker):
    def __init__(
        self,
        *,
        controller_addr: str = None,
        worker_addr: str = None,
        model_names: List[str] = ["gemini-api"],
        **kwargs,
    ):
        kwargs.update(
            model_names=model_names,
            controller_addr=controller_addr,
            worker_addr=worker_addr,
        )
        kwargs.setdefault("context_len", 4096)
        super().__init__(**kwargs)

    def create_gemini_messages(self, messages) -> json:
        has_history = any(msg["role"] == "assistant" for msg in messages)
        gemini_msg = []

        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                continue
            if has_history:
                if role == "assistant":
                    role = "model"
                transformed_msg = {"role": role, "parts": [{"text": content}]}
            else:
                if role == "user":
                    transformed_msg = {"parts": [{"text": content}]}

            gemini_msg.append(transformed_msg)

        msg = dict(contents=gemini_msg)
        return msg

    def do_chat(self, params: ApiChatParams) -> Dict:
        params.load_config(self.model_names[0])
        data = self.create_gemini_messages(messages=params.messages)
        generationConfig = dict(
            temperature=params.temperature,
            topK=1,
            topP=1,
            maxOutputTokens=4096,
            stopSequences=[],
        )

        data["generationConfig"] = generationConfig
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
            + "?key="
            + params.api_key
        )
        headers = {
            "Content-Type": "application/json",
        }
        if log_verbose:
            logger.info(f"{self.__class__.__name__}:url: {url}")
            logger.info(f"{self.__class__.__name__}:headers: {headers}")
            logger.info(f"{self.__class__.__name__}:data: {data}")

        text = ""
        json_string = ""
        timeout = httpx.Timeout(60.0)
        client = get_httpx_client(timeout=timeout)
        with client.stream("POST", url, headers=headers, json=data) as response:
            for line in response.iter_lines():
                line = line.strip()
                if not line or "[DONE]" in line:
                    continue

                json_string += line

            try:
                resp = json.loads(json_string)
                if "candidates" in resp:
                    for candidate in resp["candidates"]:
                        content = candidate.get("content", {})
                        parts = content.get("parts", [])
                        for part in parts:
                            if "text" in part:
                                text += part["text"]
                                yield {"error_code": 0, "text": text}
                        logger.debug(text)
            except json.JSONDecodeError as e:
                logger.debug("Failed to decode JSON:", e)
                logger.debug("Invalid JSON string:", json_string)

    def get_embeddings(self, params):
        logger.debug("embedding")
        logger.debug(params)

    def make_conv_template(
        self, conv_template: str = None, model_path: str = None
    ) -> Conversation:
        return conv.Conversation(
            name=self.model_names[0],
            system_message="You are a helpful, respectful and honest assistant.",
            messages=[],
            roles=["user", "assistant"],
            sep="\n### ",
            stop_str="###",
        )


if __name__ == "__main__":
    import uvicorn
    from fastchat.serve.base_model_worker import app

    from server.utils import MakeFastAPIOffline

    worker = GeminiWorker(
        controller_addr="http://127.0.0.1:20001",
        worker_addr="http://127.0.0.1:21012",
    )
    sys.modules["fastchat.serve.model_worker"].worker = worker
    MakeFastAPIOffline(app)
    uvicorn.run(app, port=21012)
