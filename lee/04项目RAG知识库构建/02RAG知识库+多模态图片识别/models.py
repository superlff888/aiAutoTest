
import os
import dotenv
from llama_index.core import Settings
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.openai_like import OpenAILikeEmbedding

dotenv.load_dotenv()

# ============第一步===========全局的配置=========================

# 配置llama-index全局的嵌入模型：OpenAILikeEmbedding 表示用的是兼容 OpenAI 接口格式的嵌入模型
Settings.embed_model = OpenAILikeEmbedding(
    model_name=os.getenv("EMBED_MODEL"),
    api_base=os.getenv("BASE_URL"),
    api_key=os.getenv("API_KEY"),
)
# 配置llama-index全局的llm：负责"思考和回答"的那个模型
Settings.llm = OpenAILike(
    model=os.getenv("MODEL1"),
    api_base=os.getenv("BASE_URL"),
    api_key=os.getenv("API_KEY"),
    temperature=0.5,
    context_window=1024 * 100,
    max_tokens=4096,
)


"""
两段配置都通过 Settings 设成全局的,后面任何地方都能直接用，不用重复传参
"""