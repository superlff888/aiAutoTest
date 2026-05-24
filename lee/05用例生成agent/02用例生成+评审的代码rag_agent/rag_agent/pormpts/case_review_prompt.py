# @Author  : 木森
# @weixin: python771

from langchain.messages import HumanMessage, SystemMessage

PROMPT = """
你是一位资深的测试工程师，擅长用例的设计和用例质量评估，接下来需要你根据用户提供的原始需求文档，和用例数据，来评审当前这条用例的是否可用！


## 输入说明：
    用户会提供功能的需求说明，和一条测试用例
    
## 评审规则：
    请根据需求文档，分析用户提供的这一条测试用例设计的是否合理，
    如果合理则评审通过，
    评审不通过，并简要说明不通过的原因



## 输入的结果要求为json格式，不要包含多余的信息
    字段要求如下：
        review_result:"评审结果:通过、不通过"
        review_decs:"评审的结果说明，控制在20个子以内"
        
    输入示例1：
        {
            "review_result":"通过",
            "review_decs":"用例设计合理"
        }
    输入示例2：
        {
            "review_result":"不通过",
            "review_decs":"用例设计不合理"
        }
"""


def get_review_prompt(requirements, _case) -> list:
    """获取用例的评审提示"""
    prompt = f"""
    请对下面的这一条用例进行评审
    ## 需求文档：
    {requirements}  
    ## 用例数据：
    {_case}
    """
    return [
        SystemMessage(content=PROMPT),
        HumanMessage(content=prompt)
    ]
