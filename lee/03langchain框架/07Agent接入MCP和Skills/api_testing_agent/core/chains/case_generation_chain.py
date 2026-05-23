"""
用例生成链
根据 API 信息生成测试用例
"""

from typing import Dict, Any
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate


def create_case_generation_chain(model: BaseChatModel) -> Any:
    """
    创建用例生成链

    Args:
        model: 聊天模型实例

    Returns:
        Runnable 链对象
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个专业的接口测试工程师，擅长根据 API 文档生成全面的测试用例。

请根据提供的 API 信息，生成测试用例。测试用例应包含：
1. 测试用例名称
2. 请求方法、URL、Headers、Body
3. 断言规则
4. 预期结果

请以 JSON 格式输出测试用例列表。"""),
        ("human", """API 信息：
{message}

请生成测试用例：""")
    ])

    chain = prompt | model.with_structured_output(Dict[str, Any])
    return chain
