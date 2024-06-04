# Langchain 自带的 YouTube 搜索工具封装
from pydantic import BaseModel, Field
from langchain_community.tools import YouTubeSearchTool

def search_youtube(query: str):
    tool = YouTubeSearchTool()
    return tool.run(tool_input=query)

class YoutubeInput(BaseModel):
    location: str = Field(description="Query for Videos search")