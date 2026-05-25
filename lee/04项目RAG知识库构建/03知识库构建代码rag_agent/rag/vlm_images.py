# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\04项目RAG知识库构建\03知识库构建代码rag_agent\rag\vlm_images.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


import json
import os
import dotenv
from langchain.chat_models import init_chat_model
from base64 import b64encode
from concurrent.futures.thread import ThreadPoolExecutor

dotenv.load_dotenv()

# 初始模型配置
vl_model = init_chat_model(
    model_provider="openai",
    model=os.getenv("MODEL2"),
    api_key=os.getenv("API_KEY"),
    base_url=os.getenv("BASE_URL"),
    temperature=0.5,
)


class ImageVLMParser:
    """图片多模态内容解析器"""

    def images_vlm_content(self, image_path):
        """通过视觉模型识别和理解图片内容"""
        system_prompt = """
        你是一个【多模态软件测试分析智能体】，
    具备测试工程背景，专门用于分析文本与图片等多模态输入。
    你不是通用聊天助手。
    
    你的唯一职责是：
    - 基于输入中“明确可见、可验证”的信息进行分析与整理
    - 辅助测试工程师理解界面、文案和结构性信息
    --------------------------------
    【最高优先级行为约束（必须遵守）】
    --------------------------------
    在任何情况下：
    - 你只能陈述“输入中明确存在”的内容
    - 你不得推测、补全、假设或虚构任何未明确呈现的信息
    - 如果某个结论无法在输入中找到直接证据，你必须明确说明“无法确认”或“不确定”
    - 禁止基于经验或常识对图片或文本进行合理化补全
    
    --------------------------------
    【多模态输入理解原则】
    --------------------------------
    你可能会接收到文本、图片、页面截图或扫描文档。
    
    对于图片输入：
    - 图片仅作为“证据来源”，而不是“推理素材”
    - 你只能基于图片中清晰可辨的内容进行描述
    - 不得对模糊、遮挡、被裁剪或不可读区域作任何判断
    - 不得假设图片中元素的行为、状态变化或业务含义
    
    --------------------------------
    【图片分析行为规范（强制流程）】
    --------------------------------
    当任务涉及图片时，你必须严格按以下顺序执行：
    
    1. 明确图片的类型和语义角色  
       （例如：页面截图、配置页面、错误提示截图、业务流程图等）
    
    2. 客观列出你在图片中“清晰可见”的内容  
       - 可读文字（原样引用）
       - 可识别的控件或区域（仅限外观层面）
       - 明确可见的布局或分区结构
    
    3. 明确标注“不确定或无法识别”的内容  
       - 模糊区域
       - 被遮挡的元素
       - 无法确认用途或含义的控件
    
    4. 在完成以上三步之前，不得进行任何分析、归纳或建议输出
    
    --------------------------------
    【测试分析输出约束】
    --------------------------------
    当输出测试点或测试建议时：
    - 每一条测试点必须明确指出其依据来源
    - 不得针对图片中未明确展示的功能提出测试点
    - 不得假设页面存在提交结果、跳转逻辑或异常流程
    
    --------------------------------
    【能力边界（禁止事项）】
    --------------------------------
    你严禁：
    - 推断页面元素的业务逻辑
    - 假设系统行为或后端处理流程
    - 补全未展示的字段校验、状态变化或交互结果
    - 使用“通常、一般、可能、大概率”等推测性语言
    
    --------------------------------
    【异常与不确定性处理】
    --------------------------------
    当出现以下情况：
    - 输入信息不足
    - 图片内容不清晰或存在歧义
    - 无法从输入中得到可靠结论
    
    你必须：
    - 明确说明无法确认的原因
    - 停止进一步推理
    - 等待补充输入     
        """
        print("开始识别图片:", image_path)
        # 读取图片内容，转换为base64
        with open(image_path, "rb") as f:
            b64_image_content = b64encode(f.read()).decode("utf-8")
        response = vl_model.invoke([
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "请理解下面图片中的内容"},
                    {
                        "type": "image",
                        "base64": b64_image_content,
                        "mime_type": "image/jpeg",
                    },
                ]
            }
        ])
        print("图片识别完成:", image_path)
        return {
            "image_path": image_path,
            "image_content": response.content
        }

    def patch_image_directory(self, image_directory):
        """批量处理图片目录"""
        result = []
        # 判断一下该路径是否存在
        if os.path.isdir(image_directory):
            # 获取配置文件中设定的最大线程数
            max_workers = int(os.getenv("MAX_CONCURRENT_EMBEDDING_THREADS"))

            # 保存线程池执行结果的对象列表
            futures_list = []
            # 创建线程池
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 获取该目录下的所有文件
                for file in os.listdir(image_directory):
                    # 拼接完整的文件路径
                    file_path = os.path.join(image_directory, file)
                    # 往线程池中提交处理的任务：submit 是非阻塞的。也就是说，派完活就立刻返回，不等工人干完，继续派下一个任务；把活交给线程池，拿回一个 Future()对象
                    future = executor.submit(self.images_vlm_content, file_path)

                    futures_list.append(future)
            # 获取线程池执行的结果
            for future in futures_list:
                # 获取线程池中任务的结果
                image_vlm_res = future.result()  # result()阻塞等待，直到跑完 --> 等任务完成，拿回真正的返回值
                result.append(image_vlm_res)
            # 保存图片内容
            json_file_path = os.path.join(image_directory, "image_vlm_content.json")
            self.save_image_vlm_content(result, json_file_path)
            return json_file_path

    # 讲图片内容保存到json文件中
    def save_image_vlm_content(self, image_vlm_content, json_file):
        """保存图片内容到json文件中"""
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(image_vlm_content, f, ensure_ascii=False, indent=4)
            print("图片内容保存成功:", json_file)


if __name__ == '__main__':
    parser = ImageVLMParser()
    res = parser.patch_image_directory(r"G:\AI\上课代码\AI2604\Code_RAG\docs2\images")
    print(res)
