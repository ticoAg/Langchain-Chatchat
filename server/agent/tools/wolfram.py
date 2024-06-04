# Langchain 自带的 Wolfram Alpha API 封装
from pydantic import BaseModel, Field
from langchain_community.utilities import WolframAlphaAPIWrapper

wolfram_alpha_appid = "your key"
def wolfram(query: str):
    wolfram = WolframAlphaAPIWrapper(wolfram_alpha_appid=wolfram_alpha_appid)
    ans = wolfram.run(query)
    return ans

class WolframInput(BaseModel):
    location: str = Field(description="需要运算的具体问题")