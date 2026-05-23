# @Author  : 木森
# @weixin: python771
from deepagents.backends import LocalShellBackend
from deepagents.middleware import SkillsMiddleware
from langchain.agents import create_agent

agent = create_agent(

    # 通过skills中间件实现支持skills
    middleware=[SkillsMiddleware(backend=LocalShellBackend(root_dir=".", virtual_mode=True),
                                 sources=['skills'])]
)
