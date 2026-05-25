# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\04项目RAG知识库构建\03知识库构建代码rag_agent\rag\rag_file_upload.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


"""
提供带有图片的PDF或者word文档

1、minerU解析文档的内容
    得到纯文本的md文件，包含图片的image文件夹

2、将带有images的文件夹 通过封装的vlm_images进行解析

3、将纯文本的md 和解析图片得到的json文件通过知识库文件上传的api直接上传到知识库中
    http://localhost:9621/documents/upload

    图片和文本内容通过指示图谱建立关联关系


"""
import os
import dotenv

dotenv.load_dotenv()
from vlm_images import ImageVLMParser
import requests
import subprocess


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
        subprocess.run(cmd, shell=True)

    def parse_images(self, images_path):
        """
        解析图片文件夹中图片的内容，并上传到知识库中
        :return:
        """
        parser = ImageVLMParser()
        image_content_json_file_path = parser.patch_image_directory(images_path)
        self.upload_to_knowledge_base(image_content_json_file_path)

    def upload_to_knowledge_base(self, file_path):
        """
        上传文件到知识库中
        :return:
        """
        url = os.getenv('RAG_KNOWLEDGE_BASE_URL') + '/documents/upload'
        # 调用知识库文件上传的api，将图片的json文件上传到知识库中
        response = requests.post(
            url=url,
            files={
                'file': open(file_path, 'rb')
            }
        )
        # 判断文件上传成功还是失败
        if response.status_code == 200 and response.json()['status'] == "success":
            print('文件上传成功')
        else:
            print('文件上传失败')

    def main(self):
        """主方法"""
        # 解析文档
        self.minerU_parse_document()
        # 把解析的文本文档上传到知识库中
        # 获取输出的md文件名称
        md_file_name = os.path.basename(self.document_path).split('.')[0] + '.md'
        print("解析之后的md文件名称为:", md_file_name)
        md_file_path = os.path.join(self.output_path, md_file_name)
        self.upload_to_knowledge_base(md_file_path)
        print("文档中的文本内容已经上传到知识库")
        # 获取图片文件夹
        images_path = os.path.join(self.output_path, 'images')
        # 解析图片文件夹，上传到知识库中
        self.parse_images(images_path)
        print("文档中的图片内容已经上传到知识库")


if __name__ == '__main__':
    kd = AddDocumentToKnowledgeBase(
        r'G:\AI\上课代码\AI2604\Code_RAG\docs2\01测试平台功能说明文档.md',
        r"G:\AI\上课代码\AI2604\Code_RAG\docs2"
    )
    kd.main()



"""
纯文本的需求文档，直接通过web客户端上传即可，如果带有图片，则需要使用我们自己封装的图片解析工具vlm_images进行解析，得到图片的内容之后，再通过知识库文件上传的api上传到知识库中

"""