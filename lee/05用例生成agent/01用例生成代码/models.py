# @Author  : 木森
# @weixin: python771
import os
import dotenv
from llama_index.core import Settings
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from langchain_openai.chat_models import ChatOpenAI
dotenv.load_dotenv()

# ============第一步===========全局的配置=========================

# 配置llama-index全局的嵌入模型
Settings.embed_model = OpenAILikeEmbedding(
    model_name=os.getenv("EMBED_MODEL"),
    api_base=os.getenv("BASE_URL"),
    api_key=os.getenv("API_KEY"),
)
# 配置llama-index全局的llm
Settings.llm = OpenAILike(
    model=os.getenv("MODEL1"),
    api_base=os.getenv("BASE_URL"),
    api_key=os.getenv("API_KEY"),
    temperature=0.5,
    context_window=1024 * 100,
    max_tokens=4096,
)


# ===================定义langchian的模型对象===========
# 如果配置的API_KEY 和BASE_URL 使用的使用变量名 OPENAI_API_KEY 和 OPENAI_BASE_URL 在通过ChatOpenAI去初始化模型对象的时候，可以不传参数base_url和api_key
llm_model2 = ChatOpenAI(
    model=os.getenv("MODEL"),
    temperature=0.5,
)

llm_model = ChatOpenAI(
    base_url=os.getenv("MINIMAX_BASE_URL"),
    api_key=os.getenv("MINIMAX_API_KEY"),
    model="MiniMax-M2.7-highspeed",
    temperature=0.5
)