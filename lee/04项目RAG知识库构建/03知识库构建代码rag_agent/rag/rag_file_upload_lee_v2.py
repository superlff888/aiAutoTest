# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\04项目RAG知识库构建\03知识库构建代码rag_agent\rag\rag_file_upload.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI自动化测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


"""
提供带有图片的PDF或者word文档，将文本与图片描述合并后上传到知识库

1、minerU 解析文档的内容（可先用 Windows 客户端生成）
    得到纯文本的 md 文件，以及包含图片的 images 文件夹

2、通过封装的 vlm_images.py 解析 images 文件夹
    得到 图片内容描述 的 json 文件

3、将图片描述注入到 md 文件的图片引用位置（merge_image_desc_into_md）
    生成 _merged.md 文件，使文本与图片语义绑定在同一文本块中

4、将合并后的 _merged.md 上传到知识库 API
    http://localhost:9621/documents/upload

    图片和文本内容通过知识图谱建立关联关系
    （LightRAG 纯文本检索系统不识别图片语法，需将 VLM 图片描述注入文本）
"""


import json
import os
import re
import subprocess

import dotenv
import requests

dotenv.load_dotenv(dotenv.find_dotenv())  # 从当前文件所在目录逐级向上搜索 .env 文件

from vlm_images import ImageVLMParser


class AddDocumentToKnowledgeBase:
    """将带有图片的PDF或者word文档添加到知识库中"""

    def __init__(self, document_path, output_path):
        """
        初始化方法
        :param document_path: 文档的路径
        """
        self.document_path = document_path
        self.output_path = output_path

    def minerU_parse_document(self):
        """
        使用minerU解析文档
        
        需要安装
        curl -fsSL https://cdn-mineru.openxlab.org.cn/open-api-cli/install.sh | sh
        在知识库部署的服务器上进行解析(对服务器的配置要求高)
        :return:
        """
        cmd = f"mineru-open-api extract {self.document_path} -o {self.output_path}"
        result = subprocess.run(cmd, shell=True)
        if result.returncode != 0:
            raise RuntimeError(f"minerU 解析失败，返回码: {result.returncode}")

    def parse_images(self, images_path):
        """
        解析图片文件夹中图片的内容
        :param images_path: 图片文件夹路径
        :return: VLM 解析结果 JSON 文件路径，目录不存在时抛出 FileNotFoundError
        """
        parser = ImageVLMParser()
        vlm_json_file_path = parser.patch_image_directory(images_path)
        if vlm_json_file_path is None:
            raise FileNotFoundError(f"图片目录不存在或无可处理图片: {images_path}")
        return vlm_json_file_path

    def upload_to_knowledge_base(self, file_path):
        """
        上传文件到知识库中
        :return:
        """
        base_url = os.getenv('RAG_KNOWLEDGE_BASE_URL')
        if not base_url:
            raise RuntimeError("环境变量 RAG_KNOWLEDGE_BASE_URL 未配置，请在 .env 文件中设置，如: RAG_KNOWLEDGE_BASE_URL=http://localhost:9621")
        url = base_url + '/documents/upload'
        with open(file_path, 'rb') as f:
            response = requests.post(
                url=url,
                files={'file': f}  # 根据接口要求，文件字段名可能需要调整，比如 'file' 或 'document'，具体看服务器端接口定义
            )
        # 判断文件上传成功还是失败
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('status') == "success":
                    print('文件上传成功')
                    return
            except ValueError:
                pass
        print(f'文件上传失败: status={response.status_code}, body={response.text[:200]}')

    @staticmethod
    def merge_image_desc_into_md(md_file_path, vlm_json_file_path):
        """
        方案A：将VLM图片描述注入到MD文本中图片引用的位置
        这样检索时，图片语义信息就跟原文本绑定在同一个文本块里
        """
        # 幂等性保护：如果输入已经是合并后的文件，直接返回
        base, ext = os.path.splitext(md_file_path)
        merged_file_path = base + "_merged" + ext
        if md_file_path == merged_file_path:
            print(f"输入已是合并文件，跳过: {md_file_path}")
            return merged_file_path

        # 若输出已存在且内容未变化，跳过重写
        if os.path.exists(merged_file_path):
            with open(merged_file_path, "r", encoding="utf-8") as f:
                existing_content = f.read()
            with open(md_file_path, "r", encoding="utf-8") as f:
                md_content = f.read()
            with open(vlm_json_file_path, "r", encoding="utf-8") as f:
                vlm_results = json.load(f)
            # 快速判断：检查已合并文件是否包含所有图片描述标记
            image_desc_map = {}
            for item in vlm_results:
                img_path = item.get("image_path", "").replace("\\", "/")
                img_content = item.get("image_content")
                if not img_path or img_content is None:
                    continue
                image_desc_map[img_path] = "".join(img_content) if isinstance(img_content, list) else img_content
            if all(f"[图片描述]: {desc}" in existing_content for desc in image_desc_map.values()):
                print(f"合并文件已是最新，跳过: {merged_file_path}")
                return merged_file_path

        # 读取VLM解析结果
        with open(vlm_json_file_path, "r", encoding="utf-8") as f:
            vlm_results = json.load(f)

        # 构建 image_path -> description 的映射，跳过无效条目
        image_desc_map = {}
        for item in vlm_results:
            img_path = item.get("image_path", "").replace("\\", "/")
            img_content = item.get("image_content")
            if not img_path or img_content is None:
                continue
            image_desc_map[img_path] = img_content

        # 读取原始MD文件
        with open(md_file_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        # 匹配 ![alt](path) 语法，[^\]]* 防止 alt 中包含 ] 导致提前截断
        pattern = r"(!\[[^\]]*\]\((.*?)\))"

        def replacer(match):
            full_ref = match.group(1)
            img_path = match.group(2).replace("\\", "/")

            if img_path in image_desc_map:
                desc = image_desc_map[img_path]
                if isinstance(desc, list):
                    desc = "".join(desc)
                return f"{full_ref}\n\n[图片描述]: {desc}"
            return full_ref

        merged_content = re.sub(pattern, replacer, md_content)

        # 写回合并文件
        with open(merged_file_path, "w", encoding="utf-8") as f:
            f.write(merged_content)

        print(f"图片描述已注入到: {merged_file_path}")
        return merged_file_path

    def _get_parsed_file_paths(self):
        """获取解析后的 MD 文件路径和图片目录路径"""
        # document_path 已经是解析好的 MD 文件，images 与其同级
        md_file_path = self.document_path
        images_path = os.path.join(os.path.dirname(self.document_path), 'images')
        return md_file_path, images_path

    def main(self):
        """主方法"""

        # 若已经通过minerU客户端解析好文档并得到md文件和图片文件夹，可以跳过这一步，直接使用解析后的文件路径进行后续处理
        # 解析文档：得到纯文本的md文件，包含图片的image文件夹（可以通过minerU客户端解析，获取纯文本的md文件和对应图片的image文件夹）
        # self.minerU_parse_document()  

        # 获取解析后的 MD 文件和图片目录路径
        md_file_path, images_path = self._get_parsed_file_paths()
        print("解析之后的md文件名称为:", os.path.basename(md_file_path))

        # 先用VLM解析图片，得到JSON文件
        vlm_json_file_path = self.parse_images(images_path)

        # 方案A：将VLM图片描述合并到MD文本中
        merged_md_path = self.merge_image_desc_into_md(md_file_path, vlm_json_file_path)

        # 上传合并后的MD文件（文本+图片描述在一起）
        self.upload_to_knowledge_base(merged_md_path)
        print("文档（含图片描述）已上传到知识库")


if __name__ == '__main__':
    kd = AddDocumentToKnowledgeBase(
    r'E:\AI\pythonProject\aiAutoTest\lee\04项目RAG知识库构建\03知识库构建代码rag_agent\docs\电子商务项目二期需求规格说明书\电子商务项目二期需求规格说明书.md',
    r"E:\AI\pythonProject\aiAutoTest\lee\04项目RAG知识库构建\03知识库构建代码rag_agent\docs\out"
    )

    kd.main()



# ==========================================================================================================

"""
【LightRAG的接口自动构建知识图谱】

通过LightRAG的接口/documents/upload上传文本后，自动构建知识图谱
POST /documents/upload (文件)
  → LightRAG 服务器端自动执行：
    1. 分块(chunking)
    2. LLM 提取实体(节点)和关系(边)
    3. 构建/更新知识图谱
    4. 建立向量索引
  → 返回成功

"""

# ==========================================================================================================

"""
纯文本的需求文档，直接通过web客户端上传即可，如果带有图片，则需要使用我们自己封装的图片解析工具vlm_images进行解析，得到图片的内容之后，再通过知识库文件上传的api上传到知识库中

"""


# ==========================================================================================================

"""
【构建功能需求文本和该功能对应图片的知识图谱索引】

LightRAG 本身是纯文本 RAG 系统， LightRAG 的文本索引把 ![login_page](images/0.png) 当成一串普通文本字符串，它不会特殊处理图片语法。

LightRAG 如何处理这段文本

```
用户输入账号和密码，点击登录。
![login_page](images/0.png)
如果密码错误，会弹出提示。
```

LightRAG 内部做的是：
文本 → 分块(chunk) → 命名实体提取 → 构建图谱节点和关系
在这个过程中，LightRAG 不会把 ![login_page](images/0.png) 这个“图片文件的相对路径引用”识别为图片引用，它只是当成一串普通文本字符串来处理。实体提取模型可能会识别出 "登录页面" 这个词，但它不会知道这是图片引用。
在图谱中，images/0.png 不会变成图节点，它只是文本块里的一串字符。实体提取模型可能会认出 login_page 这个词，但它不知道这是图片引用。


【正确思路是】

• 新增 merge_image_desc_into_md() 方法：用正则匹配 ![alt](path) 语法，将 VLM 描述插入到对应位置
• 重写了 main()：先 VLM 解析 → 再合并到 MD → 最后只上传一个合并后的文件（不再分别上传两个独立文件）

实现在知识库中构建文本和对应图片的知识图谱索引


"""
