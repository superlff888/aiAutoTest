

import os
import dotenv   
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call




llm = ChatOpenAI(
    model_name=os.getenv("MODEL_NAME"),
    openai_api_key=os.getenv("API_KEY"),
    openai_api_base=os.getenv("BASE_URL")
)


vl_model = ChatOpenAI(
    model_name=os.getenv("MODEL_NAME_QWEN3"),
    openai_api_key=os.getenv("API_KEY"),
    openai_api_base=os.getenv("BASE_URL")   
)


