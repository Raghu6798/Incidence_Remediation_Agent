from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from pydantic import BaseModel

from tools.github.factory import GitHubToolset
from tools.prometheus.factory import PrometheusToolset

import os
from dotenv import load_dotenv

from llms.factory import LLMFactory, LLMType
from llms.base import ModelConfig

load_dotenv()
gemini_config = ModelConfig(
    model_name="gemini-2.5-flash", api_key=os.getenv("GOOGLE_API_KEY")
)
llm = LLMFactory.create_provider(LLMType.GEMINI, config=gemini_config)
model = llm.get_model()
print(type(model))


print(GitHubToolset.get_tools())
