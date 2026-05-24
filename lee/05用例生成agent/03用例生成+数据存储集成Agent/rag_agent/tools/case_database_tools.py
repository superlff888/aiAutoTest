# @Author  : 木森
# @weixin: python771
"""
定义用例存储的工具，用于把AI生成的测试用例保存到数据库。

CREATE TABLE function_test_case (
    id                BIGINT PRIMARY KEY AUTO_INCREMENT,
    -- 用例基本信息
    case_id           VARCHAR(50) NOT NULL COMMENT '用例编号',
    case_name         VARCHAR(255) NOT NULL COMMENT '测试用例名称',
    priority          VARCHAR(10) NOT NULL COMMENT '优先级 P0/P1/P2',
    test_data         JSON COMMENT '测试数据',
    setup             JSON COMMENT '前提条件列表',
    execute_step      JSON NOT NULL COMMENT '测试步骤列表',
    except_result     JSON NOT NULL COMMENT '预期结果',
    result            VARCHAR(255) NOT NULL COMMENT '实际结果',

    requirement_id    VARCHAR(50) NOT NULL COMMENT '关联需求的编号',

    is_active         TINYINT DEFAULT 1,
);



"""
import os
import dotenv
from typing import List
from langchain.tools import tool
from rag_agent.tools.data_model import GenerateCase
import pymysql
import json

dotenv.load_dotenv()


class DataBaseHandel:
    """
    定义数据库操作类
    """

    def __init__(self):
        """
        初始化数据库链接
        """
        self.connect = pymysql.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT")),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_DATABASE"),
            charset="utf8mb4"
        )

        # 创建一个游标对象
        self.cursor = self.connect.cursor(cursor=pymysql.cursors.DictCursor)

    def close(self):
        """
        关闭数据库链接
        """
        self.cursor.close()
        self.connect.close()

    def save_case(self, case: List[GenerateCase], requirement_id: str) -> list:
        """
        :param case: 用例数据
        :return: 存储结果
        """
        # 构建用例存储的sql语句
        sql = """
              INSERT INTO funtion_teest_case(case_id, case_name, priority, test_data, setup, execute_step,
                                             except_result, result, requirement_id VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s); \
              """
        try:
            # 执行用例存储的sql语句
            for case_ in case:
                self.cursor.execute(sql, (
                    case_.case_id,
                    case_.case_name,
                    case_.priority,
                    json.dumps(case_.test_data, ensure_ascii=False),
                    json.dumps(case_.setup, ensure_ascii=False),
                    json.dumps(case_.execute_step, ensure_ascii=False),
                    json.dumps(case_.except_result, ensure_ascii=False),
                    case_.result,
                    requirement_id
                ))
        except Exception as e:
            self.connect.rollback()
            print(f"保存用例到数据库失败：{e}")
            raise e
        else:
            # 提交数据
            self.connect.commit()
        finally:
            self.close()

    def query_case(self, requirement_id: str) -> list:
        """
        :param requirement_id: 功能的需求文档
        :return: 已有的用例
        """
        sql = "SELECT * FROM  funtion_teest_case WHERE requirement_id = %s"
        try:
            self.cursor.execute(sql, requirement_id)
            # 获取查询结果
            result = self.cursor.fetchall()
        except Exception as e:
            print(f"查询已存在的用例失败：{e}")
            raise e
        else:
            return result


@tool("测试用例存储", description="把AI生成的测试用例保存到数据库中")
def save_case_to_database(case: List[GenerateCase]) -> str:
    """
    :param case: 用例数据
    :return: 保存结果
    """
    print(f"========开始保存用例:{case}=========")
    # 获取需求的编号
    requirement_id = "T001"
    try:
        # 保存用例到数据库
        DataBaseHandel().save_case(case, requirement_id)
    except Exception as e:
        print(f"保存用例到数据失败：{e}")
        return f"保存用例到数据失败，错误信息为：{e}"
    print(f"=========={len(case)}条用例已经全部保存到数据库==========")
    return f"=========={len(case)}条用例已经全部保存到数据库=========="


@tool("数据库中查询需求已存在的用例", description="根据需求，从数据库中查询已存在的用例")
def query_exist_case(requirement_id: str = "T001") -> str:
    """
    :param requirements: 功能的需求文档
    :return: 已有的用例
    """
    print(f"========开始从数据库中查询需求:{requirement_id},已存在的用例=========")
    try:
        # 查询已存在的用例
        cases = DataBaseHandel().query_case(requirement_id="T001")
    except Exception as e:
        print(f"查询已存在的用例失败：{e}")
        return f"查询已存在的用例失败，错误信息为：{e}"
    return f"已查询到当前需求已存在的用例：\n {cases}"
