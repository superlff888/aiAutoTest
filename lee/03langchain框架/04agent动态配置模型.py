

import base64
import os
from pathlib import Path
import dotenv   
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, ModelResponse, wrap_model_call


dotenv.load_dotenv()  # 加载.env文件中的环境变量

model = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL"),
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
)


vl_model = ChatOpenAI(
    model_name=os.getenv("MODEL_NAME_QWEN3"),
    api_key=os.getenv("API_KEY"),
    base_url=os.getenv("BASE_URL"),
    max_tokens=20480
)



def if_message_type_is_image(messages):
    """判断消息中是否包含图片，如果包含图片则使用视觉模型，不包含图片则使用文本模型"""
    for message in messages:  # 通过断点，找到request模型请求对象的字典属性state,遍历字典属性state的key键"messages"，即request.state["messages"]；通过断点和快捷键Alt+F8对表达式request.state["messages"]求值
        print(type(message),"===============================================\n")
        if message.type == "human" and isinstance(message.content, list):
            for content in message.content:
                if content["type"] == "image":
                    return vl_model
    return model

# func: _CallableReturningModelResponse 
@wrap_model_call  # 装饰器没带括号（@wrap_model_call 而非 @wrap_model_call()），Python 把你的函数 dynamic_model_selection 作为 func 参数直接传入，然后立即调用内层的 decorator(func)
def dynamic_model_selection(request: ModelRequest, handler) -> ModelResponse:
    """动态模型选择的中间件函数"""
    selected_model = if_message_type_is_image(request.state["messages"])
    new_request = request.override(model = selected_model)  # 创建一个新的请求对象，保持原有请求的其他属性不变})  
    return handler(new_request)  # 将选定的模型传递给处理函数；
    # 装饰器函数的内嵌函数中handler: Callable[[ModelRequest[ContextT]], ModelResponse[ResponseT]]决定了handler的类型，handler是一个回调函数，接收一个ModelRequest对象，返回一个ModelResponse对象；在dynamic_model_selection函数中调用handler(new_request)，将新的请求对象传递给处理函数，最终返回处理函数的结果。


system_prompt = """
你是一位资深的软件测试工程师，接下来需要你根据用户提交的需求或者页面截图去分析测试点，生成测试用例
    输出：
       	json格式的用例必须包含如下字段：
       	id,case_name,test_data,test_step
    约束规范：
        1、生成的测试点，不要有重复的内容
"""
path_name = Path(__file__).parent / "msg" / "login.png"

# 2、将图片内容转换为base64编码,然后传递给大模型
with open(path_name, "rb") as f:
    image_data = f.read()
    image_base64 = base64.b64encode(image_data).decode("utf-8")

# print("图片的base64内容：", image_base64)
user_prompt = HumanMessage(content=[
    {"type": "text", "text": "请根据图片中的内容，分析测试点"},
    {
        "type": "image",
        "mime_type": "image/png",
        "base64": image_base64
    }
])


agent = create_agent(
    model=model,
    system_prompt=system_prompt,        
    middleware=[dynamic_model_selection]
)





response = agent.stream({"messages": [user_prompt]})
for item in response:
    print(item.content, end="", flush=True)




"""
看 types.py:828-833：

class _CallableReturningModelResponse(Protocol):
    def __call__(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[[ModelRequest[ContextT]], ModelResponse[ResponseT]],
    ) -> ModelResponse[ResponseT] | AIMessage:

注意 handler 的类型：

handler: Callable[[ModelRequest[ContextT]], ModelResponse[ResponseT]]
翻译一下：一个函数，接收 1 个 ModelRequest，返回 1 个 ModelResponse。



"""