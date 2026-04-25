# @Author  : 木森
# @weixin: python771
"""自定义实现的长期记忆管理器"""
import json
import os


class MemoryManager:
    memory_file = "memory.json"

    def __init__(self):
        # 判断当前是否存在记忆文件
        if os.path.isfile(self.memory_file):
            # 如果存在则创建，并加载记忆文件中的内容
            with open(self.memory_file, "r", encoding="utf-8") as f:
                self.memory = json.load(f)
        else:
            self.memory = {}


    def put(self, user_id: str, memory: dict):
        """保存用户的记忆"""
        user_memory = self.memory.get(user_id, [])
        user_memory.append(memory)
        self.memory[user_id] = user_memory
        # 保存到文件中
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(self.memory, f, ensure_ascii=False, indent=4)

    def get(self, user_id: str) -> dict:
        """加载用户的记忆"""
        return self.memory.get(user_id, {})

    def clear(self, user_id: str):
        """清除用户的记忆"""
        if user_id in self.memory:
            del self.memory[user_id]
            # 保存到文件中
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self.memory, f, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    memory_manager = MemoryManager()
    memory_manager.put("musen001", {"name": "张三", "age": 18})
    memory_manager.put("musen002", {"name": "李四", "age": 19})
    print(memory_manager.get("musen001"))
    memory_manager.clear("musen001")
