# @Author  : 木森
# @weixin: python771
"""
提供带有图片的PDF或者word文档

1、解析文档minerU解析文档的内容
    得到纯文本的md文件（含图片路径），同时在相同目录包含图片的image文件夹

2、将带有images的文件夹 通过封装的vlm_images进行解析
    ```
    {
            "image_path": image_path,  # 图片路径
            "image_content": response.content  # 图片内容的文本描述
        }
    ```
3、将纯文本的md 和解析图片得到的json文件通过知识库文件上传的api直接上传到知识库中
    http://localhost:9621
    通过图片路径 关联 图片的文本描述和md文件中的文本内容，使图片和文本内容在知识库中建立关联关系

"""
import os
from pathlib import Path
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
        # 将图片的json文件上传到知识库中
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
    _BASE = Path(__file__).parent.parent / "docs"
    doc = _BASE / "电子商务项目二期需求规格说明书" / "电子商务项目二期需求规格说明书.md"
    out = _BASE / "out"

    kd = AddDocumentToKnowledgeBase(str(doc), str(out))
    kd.main()
