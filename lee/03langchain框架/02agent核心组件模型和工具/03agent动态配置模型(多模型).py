

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

#  装饰器没带括号（@wrap_model_call 而非 @wrap_model_call()），Python 把被装饰函数 dynamic_model_selection 作为 func 参数直接传入，然后立即调用内层的 decorator(func)
@wrap_model_call  
def dynamic_model_selection(request: ModelRequest, handler) -> ModelResponse:  # 参数参考了装饰器参数func的注解类的回调函数
    """动态模型选择的中间件函数"""
    selected_model = if_message_type_is_image(request.state["messages"])
    # 创建一个新的请求对象，保持原有请求的其他属性不变
    new_request = request.override(model = selected_model)  #  关键字传参 -- > override(self, **overrides: Unpack[_ModelRequestOverrides])
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
path_name = Path(__file__).parent / "picture" / "login.png"

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





response = agent.stream(
    {"messages": [user_prompt]}
    )
for chunk in response:
    for node_name, node_data in chunk.items():
        if "messages" in node_data:
            for message in node_data["messages"]:
                if hasattr(message, "content") and isinstance(message.content, str):
                    print(message.content, end="", flush=True)




"""
看 types.py:828-833：

class _CallableReturningModelResponse(Protocol):  # 继承了Protocol
    def __call__(
        self,
        request: ModelRequest[ContextT],
        handler: Callable[[ModelRequest[ContextT]], ModelResponse[ResponseT]],
    ) -> ModelResponse[ResponseT] | AIMessage:

注意 handler 的类型：

handler: Callable[[ModelRequest[ContextT]], ModelResponse[ResponseT]]
翻译一下：一个函数，接收 1 个 ModelRequest，返回 1 个 ModelResponse。



"""




"""
wrap_model_call装饰器的两种调用方式：


方式一：直接装饰器 @wrap_model_call

@wrap_model_call
def retry_on_error(request, handler):
    return handler(request)
执行顺序：

1.Python 等价执行 wrap_model_call(retry_on_error)，注意：若为三层，最外层不能定义func参数，它只接收装饰器本身定义的参数
2.进入第1层，func = retry_on_error（非 None），**kwargs 为空
3.走到 if func is not None: return decorator(func) ← 立刻调用第2层
4.进入 decorator(retry_on_error)
5.scoroutinefunction(func) 判断是否为 async 函数
6.根据同步/异步，创建 wrapped 或 async_wrapped 函数
7.用 type() 动态创建一个继承 AgentMiddleware 的类
8.实例化并返回这个类的对象

方式二：带参数装饰 @wrap_model_call(name="my_middleware")

@wrap_model_call(name="retry")
def retry_on_error(request, handler):
    return handler(request)
执行顺序：

1.Python 等价执行 wrap_model_call(name="retry")，没有传 func
2.进入第1层，func = None
3.走到 return decorator ← 只返回第2层函数本身，不执行
4.Python 拿到 decorator 后，用它去装饰函数：decorator(retry_on_error)
5.后续流程同上



【注意】
1. 作为外层函数wrap_model_call的函数体，中间层的decorator，定义了func参数，它能获取到被装饰函数
2. 最内层wrapped作为中间层，最内层wrapped可以从中间层decorator捕获func,所以严格意义上讲，如果中间层没有定义func参数，wrapped内部函数体就没办法获取func

"""


"""

def wrapped(
            _self: AgentMiddleware[StateT, ContextT],
            request: ModelRequest[ContextT],
            handler: Callable[[ModelRequest[ContextT]], ModelResponse[ResponseT]],
        ) -> ModelResponse[ResponseT] | AIMessage:
            return func(request, handler)

装饰器最内层返回被装饰函，这块直接影响自定义函数的参数，注解request: ModelRequest[ContextT]直接决定了request可调用哪些方法


"""


"""
【装饰器】
def outer(params:str):  # 可以定义，但这里params不会是原add,它是装饰器外层定义的参数
    def middle(func):     # 真正接收原函数的是这里
        def inner(*args, **kwargs):
            print(f"真正的func是：{func.__name__}")
            return func(*args, **kwargs)
        return inner
    return middle

@outer("装饰器参数")
def add(a,b):
    return a+b


if __name__ == "__main__":  

    add(1,2)



核心规律（永远不变）
最外面 N 层：都是用来传装饰器参数的，碰不到 func
倒数第二层：唯一接收 func 的地方
最内层：通过闭包拿到 func


def layer1(a):          # 第1层：装饰器参数
    def layer2(b):      # 第2层：装饰器参数
        def layer3(func):  # 第3层：【唯一能拿到 func 的层】
            def layer4(*args, **kwargs):  # 第4层：wrapper
                return func(*args, **kwargs) 
            return layer4
        return layer3
    return layer2
"""