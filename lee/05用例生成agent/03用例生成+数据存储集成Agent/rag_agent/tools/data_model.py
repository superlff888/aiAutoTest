# @Author  : 木森
# @weixin: python771
# 对用例进行结构化提取的pydantic的模型
from pydantic import BaseModel, Field


class GenerateCase(BaseModel):
    case_id: str = Field(..., description="用例编号")
    case_name: str = Field(..., description="用例名称")
    priority: str = Field(..., description="优先级")
    test_data: dict = Field(..., description="测试数据")
    setup: list = Field(..., description="前置条件")
    execute_step: list = Field(..., description="用例执行的步骤")
    except_result: list = Field(..., description="预期结果")
    result: str = Field(None, description="实际结果")

    # 用例管理的需求编号
    requirement_id: str = Field(None, description="需求编号")

