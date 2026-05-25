# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\03langchain框架\05人工审核机制\tools.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


import os
import subprocess
import platform
import re
import shutil
from langchain.tools import tool
from typing import Optional
from pydantic import BaseModel, Field


class CommandInput(BaseModel):
    """命令输入参数"""
    command: str = Field(description="要执行的系统命令，如 'ls -la'")
    timeout: int = Field(default=30, description="超时时间（秒）", ge=1, le=300)

# 使用 Pydantic 数据模型来定义工具参数
class DataBaseConfig(BaseModel):
    host: str = Field(..., description="数据库的 host 地址")
    port: int = Field(..., description="数据库端口")
    user: str = Field(..., description="数据库连接的用户名")
    password: str = Field(..., description="数据库连接的用户密码")
    database: str = Field(..., description="操作的库")

class CommandExecutor:
    """安全的跨平台命令执行器"""

    # 危险命令模式
    DANGEROUS_PATTERNS = [
        r"rm\s+-rf\s+/",  # rm -rf /
        r"rm\s+-rf",  # 递归强制删除
        r"format\s+",  # 格式化
        r"del\s+/[fqs]",  # Windows 强制删除
        r">\s*/dev/",  # 写入设备
        r"dd\s+if=",  # dd 复制
        r"mkfs",  # 格式化文件系统
        r"shutdown",  # 关机
        r"reboot",  # 重启
        r"chmod\s+777",  # 过度权限
        r"wget.*\|",  # 管道下载执行
        r"curl.*\|",  # 管道下载执行
    ]

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.platform = platform.system()

    def _is_safe_command(self, command: str) -> tuple[bool, str]:
        """安全检查"""
        cmd_lower = command.lower()
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, cmd_lower):
                return False, f"安全拦截: 匹配危险模式 '{pattern}'"

        return True, ""

    def _resolve_command(self, command: str) -> tuple[bool, str]:
        """检查命令是否存在（避免'系统找不到文件'错误）"""
        cmd_parts = command.strip().split()
        if not cmd_parts:
            return False, "命令为空"
        cmd_name = cmd_parts[0]
        # Windows Store 占位程序特殊处理（python3 是空壳）
        if cmd_name.lower() in ('python3', 'python3.exe') and self.platform == "Windows":
            python_path = shutil.which('python')
            if python_path:
                return False, f"命令不存在: {cmd_name}（Windows 占位程序），建议改为: python {' '.join(cmd_parts[1:])}"
            return False, "命令不存在: python3（系统未安装 Python）"
        # 使用 shutil.which 查找
        if not shutil.which(cmd_name):
            return False, f"命令不存在: {cmd_name}"
        return True, ""

    def run(self, command: str, timeout: Optional[int] = None) -> str:
        """执行命令"""
        timeout = timeout or self.timeout

        # 安全检查
        is_safe, error_msg = self._is_safe_command(command)
        if not is_safe:
            return f"错误信息: {error_msg}"

        # 检查命令是否存在
        cmd_exists, cmd_msg = self._resolve_command(command)
        if not cmd_exists:
            return f"错误信息: {cmd_msg}"
        try:
            if self.platform == "Windows":
                # Windows: 使用 shell
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
            else:
                # Linux/Mac: 使用 sh -c
                result = subprocess.run(
                    ["/bin/sh", "-c", command],
                    shell=False,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )

            # 处理输出
            output = result.stdout.strip() if result.stdout else result.stderr.strip()

            if result.returncode != 0:
                return f"执行失败 (返回码: {result.returncode})\n{output or '无错误信息'}"

            return output or "执行成功，无输出"

        except subprocess.TimeoutExpired:
            return f"执行超时 ({timeout}秒)"
        except FileNotFoundError:
            return "命令未找到"
        except PermissionError:
            return "权限不足"
        except Exception:
            return "执行出错"


@tool("终端命令执行工具", description="用于执行系统终端的操作命令", args_schema=CommandInput)
def execute_command(command: str, timeout: int = 30) -> str:
    """
    执行系统命令（Windows/Linux）。
    Args:
        command: 要执行的命令，如 "ls -la"、"python --version"
        timeout: 超时时间（秒），默认30，最长300
    Returns:
        命令执行结果
    Examples:
        execute_command("ls -la")
        execute_command("python --version")
        execute_command("echo hello")
    """
    # ============手动在命令执行的工具中添加人工确认(简单实现)=============
    # print("【开始执行系统终端命令】:", command)
    # while True:
    #     res = input("请输入是否同意执行(yes/no)：")
    #     if res == "yes":
    #         break
    #     elif res == "no":
    #         return "用户拒绝执行"
    #     else:
    #         print("输入有误，请重新输入！")
    _executor = CommandExecutor()
    return _executor.run(command, timeout)

@tool("获取数据库连接配置", description="获取数据库的连接参数")
def get_database_connect_config() -> DataBaseConfig:
    """获取数据库的连接配置"""
    return DataBaseConfig(
        host=os.getenv("db_host"),
        port=int(os.getenv("db_port")),
        user=os.getenv("db_user"),
        password=os.getenv("db_password"),
        database=os.getenv("database"),
    )

if __name__ == "__main__":
    # 方式1: 直接调用
    print("=== 直接调用 ===")
    result = execute_command.invoke({"command": "echo hello world", "timeout": 10})
    print(result)

    print("=== 测试危险命令拦截 ===")
    result = execute_command.invoke({"command": "rm -rf /", "timeout": 10})
    print(result)

    print("=== 测试超时 ===")
    result = execute_command.invoke({"command": "sleep 5", "timeout": 2})
    print(result)


