# @Author  : 木森
# @weixin: python771
import os
import dotenv
from llama_index.core import Settings
from llama_index.embeddings import OpenAILikeEmbedding
from llama_index.llms.openai_like import OpenAILike
from llama_index.core import SimpleDirectoryReader  

Settings.embed_model = OpenAILikeEmbedding(
    model_name=os.getenv("EMBED_MODEL"),    
    api_base=os.getenv("BASE_URL"),
    api_key=os.getenv("API_KEY"),
)

Settings.llm = OpenAILike(
    model_name=os.getenv("LLM_MODEL"),    
    api_base=os.getenv("BASE_URL"),
    api_key=os.getenv("API_KEY"),
    temperature=0.1,
    max_tokens=2048,    
)