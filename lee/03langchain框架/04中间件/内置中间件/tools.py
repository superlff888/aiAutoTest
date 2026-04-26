# @Author  : 木森
# @weixin: python771
import os
from dataclasses import dataclass
from langchain.tools import tool, ToolRuntime
from my_memory import MemoryManager

memory = MemoryManager()


@tool("记忆读取的工具", description="用户读取用户的记忆中的规则")
def load_memory(runtime: ToolRuntime):
    print("[正在加载记忆].....")
    user_id = runtime.context.user_id
    return memory.get(user_id)


@tool("记忆写入的工具", description="用于保存用户规则到长期记忆中")
def save_memory(content: dict, runtime: ToolRuntime):
    """
    :param content: 保存记忆内容的字典：{"规则":内容,"规则2":"内容2"}
    :return:
    """
    user_id = runtime.context.user_id
    memory.put(user_id, content)
    print("[正在写入记忆].....")


@tool("记忆清除的工具", description="用于清除用户记忆中的指令")
def clear_memory(runtime: ToolRuntime):
    print("[正在清除记忆].....")
    user_id = runtime.context.user_id
    memory.clear(user_id)


@dataclass
class AgentContext:
    user_id: str


# 定义一个文件写入的工具
@tool("文件写入的工具", description="用于写入文件")
def write_file(file_path: str, content: str, runtime: ToolRuntime[AgentContext]):
    """
    :param file_path: 文件路径
    :param content: 文件内容
    :param runtime:
    :return:
    """
    # 先判断文件路径是否存在
    if not os.path.exists(os.path.dirname(file_path)):
        # 如果不存在则创建
        os.makedirs(os.path.dirname(file_path))
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


@tool("文件读取的工具", description="用于读取文件")
def read_file(file_path: str, runtime: ToolRuntime[AgentContext]):
    """
    :param file_path: 文件路径
    :param runtime:
    :return:
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


# 二进制文件读取的工具
@tool("文件读取二进制文件的工具", description="用于读取二进制文件")
def read_binary_file(file_path: str, runtime: ToolRuntime[AgentContext]):
    """
    :param file_path: 文件的路径
    :param runtime:
    :return:
    """
    with open(file_path, "rb") as f:
        return f.read()


# 二进制文件写入的工具
@tool("文件写入二进制文件的工具", description="用于写入二进制文件")
def write_binary_file(file_path: str, content: bytes, runtime: ToolRuntime[AgentContext]):
    """
    :param file_path: 文件路径
    :param content: 文件的二进制内容
    :param runtime:
    :return:
    """
    # 先判断文件路径是否存在
    if not os.path.exists(os.path.dirname(file_path)):
        # 如果不存在则创建
        os.makedirs(os.path.dirname(file_path))
    with open(file_path, "wb") as f:
        f.write(content)


# 文件目录读取的工具
@tool("文件目录读取的工具", description="用于读取文件目录")
def read_directory(file_path: str, runtime: ToolRuntime[AgentContext]):
    """
    :param file_path: 文件目录的路径
    :param runtime:
    :return:
    """
    if not os.path.exists(file_path):
        return []
    return os.listdir(file_path)
