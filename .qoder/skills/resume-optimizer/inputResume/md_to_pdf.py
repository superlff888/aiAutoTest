"""
将 Markdown 简历转为 PDF。

- 使用 markdown 库解析为 HTML
- 使用 html.parser 解析 HTML 元素
- 使用 reportlab.platypus 渲染 PDF（A4，中文微软雅黑）
- 处理范围：标题、段落、表格、列表、引用、加粗、行内代码
"""
import re
import os
from pathlib import Path
from html.parser import HTMLParser

import markdown
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether,
)

SRC = Path(r"e:\AI\pythonProject\aiAutoTest\.claude\skills\resume-optimizer\inputResume\简历-李茂-系统运维工程师-徐州.md")
DST = SRC.with_suffix(".pdf")

# 颜色
HEADING_COLOR = colors.HexColor("#1F4E79")  # 深蓝
H3_COLOR = colors.HexColor("#2E75B6")
TABLE_HEADER_BG = colors.HexColor("#D9E2F3")
TABLE_BORDER = colors.HexColor("#8FAADC")
QUOTE_BG = colors.HexColor("#F2F2F2")

# 注册中文字体（Windows 自带）
def register_cn_font():
    """注册微软雅黑（常规 + 粗体）；若粗体 ttc 不存在则降级到伪粗体"""
    candidates = [
        (r"C:\Windows\Fonts\msyh.ttc", "MicrosoftYaHei", 0),
        (r"C:\Windows\Fonts\msyhbd.ttc", "MicrosoftYaHei-Bold", 0),
        (r"C:\Windows\Fonts\simfang.ttf", "FangSong", 0),
        (r"C:\Windows\Fonts\simsun.ttc", "SimSun", 0),
    ]
    found = {}
    for path, name, subfont in candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path, subfontIndex=subfont))
                found[name] = name  # 关键：value 存字体名而不是路径
            except Exception as e:
                print(f"[warn] 字体注册失败 {name}: {e}")

    # 注册字体家族（让 ps2tt 能找到 bold 变体）
    if "MicrosoftYaHei" in found:
        try:
            from reportlab.pdfbase.pdfmetrics import registerFontFamily
            bold_name = found.get("MicrosoftYaHei-Bold", "MicrosoftYaHei")
            registerFontFamily(
                "MicrosoftYaHei",
                normal="MicrosoftYaHei",
                bold=bold_name,
                italic="MicrosoftYaHei",
                boldItalic=bold_name,
            )
        except Exception as e:
            print(f"[warn] 字体家族注册失败: {e}")

    return found


class MDToFlowables(HTMLParser):
    """解析 markdown 输出的 HTML，生成 reportlab flowables"""

    def __init__(self, styles):
        super().__init__(convert_charrefs=True)
        self.styles = styles
        self.flowables = []
        # 栈：每个元素是一个 dict {tag, children, text_buffer}
        self.stack = [{"tag": "root", "children": [], "text": ""}]
        # 表格处理：临时状态
        self.in_table = False
        self.table_rows = []      # [[cell, cell, ...], ...]
        self.current_row = []
        self.current_cell = []
        self.in_cell = False
        # 列表
        self.list_stack = []      # [{"type": "ul"|"ol", "index": int, "items": []}]
        self.in_li = False
        self.li_text = []
        self.li_ol_index = 0
        # 块级元素缓冲
        self.paragraph_buf = []

    def get_current(self):
        return self.stack[-1]

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "table":
            self.in_table = True
            self.table_rows = []
        elif tag == "tr":
            self.current_row = []
        elif tag in ("td", "th"):
            self.in_cell = True
            self.current_cell = []
        elif tag in ("ul", "ol"):
            self.list_stack.append({"type": tag, "index": 0})
        elif tag == "li":
            self.in_li = True
            self.li_text = []
            if self.list_stack and self.list_stack[-1]["type"] == "ol":
                self.list_stack[-1]["index"] += 1
        elif tag == "blockquote":
            self.stack.append({"tag": "blockquote", "children": [], "text": ""})
        elif tag in ("p", "h1", "h2", "h3", "h4", "h5", "h6"):
            self.stack.append({"tag": tag, "children": [], "text": ""})
        elif tag == "hr":
            # 插入一条水平分隔
            self.flowables.append(Spacer(1, 0.3 * cm))
        elif tag in ("br",):
            if self.in_cell:
                self.current_cell.append("\n")
        # 行内元素：透传到当前 text buffer
        elif tag in ("strong", "b", "em", "i", "code", "span"):
            self.stack[-1]["text"] += f"<{tag}>"

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "table":
            self.flush_table()
            self.in_table = False
        elif tag == "tr":
            if self.current_row:
                self.table_rows.append(self.current_row)
            self.current_row = []
        elif tag in ("td", "th"):
            is_header = (tag == "th")
            cell_text = self._inline_to_html("".join(self.current_cell).strip())
            self.current_row.append((cell_text, is_header))
            self.current_cell = []
            self.in_cell = False
        elif tag in ("ul", "ol"):
            if self.list_stack:
                self.flush_list()
        elif tag == "li":
            self.flush_li()
            self.in_li = False
        elif tag == "blockquote":
            # 弹出 blockquote 子元素
            children = self.stack[-1]["children"]
            self.stack.pop()
            inner_text = self._inline_to_html(self.stack[-1]["text"] if False else "")
            # blockquote 实际内容从 children 中渲染
            block_text = "\n".join(c.get("text", "") for c in children).strip()
            if not block_text and "text" in self.stack[-1]:
                pass
            # 简化：直接用 children 中的 Paragraph，套上引用样式
            for child in children:
                if "paragraph" in child:
                    child["paragraph"].style = self.styles["quote"]
                    self.flowables.append(child["paragraph"])
        elif tag in ("p", "h1", "h2", "h3", "h4", "h5", "h6"):
            # 弹出当前段落元素
            el = self.stack.pop()
            inline_html = self._inline_to_html(el["text"])
            if not inline_html.strip():
                return
            style_name = {
                "h1": "h1", "h2": "h2", "h3": "h3",
                "h4": "h3", "h5": "h3", "h6": "h3",
                "p": "body",
            }.get(tag, "body")
            try:
                p = Paragraph(inline_html, self.styles[style_name])
            except Exception as e:
                # HTML 解析失败时回退到纯文本
                plain = re.sub(r"<[^>]+>", "", inline_html)
                p = Paragraph(plain, self.styles[style_name])
            if tag in ("h1", "h2", "h3"):
                # 标题和上下文保持在一起
                self.flowables.append(KeepTogether([p, Spacer(1, 0.15 * cm)]))
            else:
                self.flowables.append(p)
                self.flowables.append(Spacer(1, 0.1 * cm))
        elif tag in ("strong", "b", "em", "i", "code", "span"):
            if self.stack:
                self.stack[-1]["text"] += f"</{tag}>"

    def handle_data(self, data):
        # HTML 实体由 convert_charrefs=True 自动转义
        if not data:
            return
        # 跳过纯空白（HTML 中 <li> 之间的换行符会被传到这里）
        if data.strip() == "":
            return
        escaped = data
        if self.in_table and self.in_cell:
            self.current_cell.append(escaped)
        elif self.in_li:
            self.li_text.append(escaped)
        elif self.stack:
            # 如果不在任何块级元素中（直接挂在 root），丢弃
            top_tag = self.stack[-1].get("tag")
            if top_tag == "root":
                return
            self.stack[-1]["text"] += escaped

    def _inline_to_html(self, text: str) -> str:
        """把解析器累积的 <b>/<i>/<code> 标记转成 reportlab 段落支持的标签"""
        # 已经使用了 <b>/<i> 等标签
        return text

    def flush_table(self):
        if not self.table_rows:
            return
        # 规范化：每行等列数
        cols = max(len(r) for r in self.table_rows)
        norm_rows = [r + [("", False)] * (cols - len(r)) for r in self.table_rows]
        data = []
        for r in norm_rows:
            data.append([Paragraph(self._inline_to_html(cell[0]), self.styles["cell"])
                          if not cell[1] else
                          Paragraph(f"<b>{self._inline_to_html(cell[0])}</b>", self.styles["cell"])
                          for cell in r])
        # 列宽：按可用宽度平均分配
        col_widths = [16.0 * cm / cols] * cols
        t = Table(data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), HEADING_COLOR),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, TABLE_BORDER),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        self.flowables.append(t)
        self.flowables.append(Spacer(1, 0.2 * cm))

    def flush_li(self):
        text = "".join(self.li_text).strip()
        if not text:
            return
        inline_html = self._inline_to_html(text)
        prefix = ""
        if self.list_stack:
            top = self.list_stack[-1]
            if top["type"] == "ul":
                prefix = "• "
            else:
                prefix = f"{top['index']}. "
        try:
            p = Paragraph(prefix + inline_html, self.styles["list"])
        except Exception:
            plain = re.sub(r"<[^>]+>", "", prefix + inline_html)
            p = Paragraph(plain, self.styles["list"])
        self.flowables.append(p)

    def flush_list(self):
        # 列表项已经在 flush_li 中添加为独立段落，无需额外 flush
        self.list_stack.pop()
        self.flowables.append(Spacer(1, 0.1 * cm))


def build_styles(fonts):
    """构建 reportlab 段落样式"""
    cn = fonts.get("MicrosoftYaHei", "Helvetica")
    cn_bold = fonts.get("MicrosoftYaHei-Bold", cn)
    base = ParagraphStyle(
        "base", fontName=cn, fontSize=10.5, leading=15,
        textColor=colors.black, alignment=TA_LEFT,
    )
    styles = {
        "base": base,
        "h1": ParagraphStyle("h1", parent=base, fontName=cn_bold, fontSize=22, leading=28,
                             textColor=HEADING_COLOR, alignment=TA_CENTER,
                             spaceBefore=10, spaceAfter=8),
        "h2": ParagraphStyle("h2", parent=base, fontName=cn_bold, fontSize=15, leading=20,
                             textColor=HEADING_COLOR,
                             spaceBefore=10, spaceAfter=4),
        "h3": ParagraphStyle("h3", parent=base, fontName=cn_bold, fontSize=12, leading=17,
                             textColor=H3_COLOR,
                             spaceBefore=6, spaceAfter=3),
        "body": ParagraphStyle("body", parent=base, fontSize=10.5, leading=15,
                               spaceBefore=2, spaceAfter=2),
        "list": ParagraphStyle("list", parent=base, fontSize=10.5, leading=15,
                               leftIndent=14, firstLineIndent=-14,
                               spaceBefore=0, spaceAfter=0),
        "quote": ParagraphStyle("quote", parent=base, fontSize=10.5, leading=15,
                                leftIndent=12, textColor=colors.HexColor("#555555"),
                                backColor=QUOTE_BG, borderColor=TABLE_BORDER,
                                borderWidth=0, borderPadding=6,
                                spaceBefore=4, spaceAfter=4),
        "cell": ParagraphStyle("cell", parent=base, fontSize=10, leading=13),
    }
    return styles


# 简历中常见 emoji → 中文符号/文字（微软雅黑不含 emoji 字形，需替换）
EMOJI_REPLACE = {
    "📌": "【",   # 📌 基本信息 → 【 基本信息
    "🎯": "▍",   # 🎯 求职意向
    "💪": "■",   # 💪 核心优势
    "🛠": "◆",   # 🛠 核心技能
    "💼": "▍",   # 💼 工作经历
    "🏆": "★",   # 🏆 项目经验
    "🎓": "▍",   # 🎓 教育背景
    "🏅": "▍",   # 🏅 证书
    "📞": "▍",   # 📞 联系方式
    "⭐": "★",   # ⭐ 项目一
    "🔧": "▸",   # 🔧 系统运维
    "💾": "▸",   # 💾 数据库
    "🤖": "▸",   # 🤖 AI 工具
    "📋": "▸",   # 📋 业务系统
    "🧪": "▸",   # 🧪 测试工程栈
    "⓫": "▸",
    "①②③④⑤⑥⑦⑧⑨": "①②③④⑤⑥⑦⑧⑨",  # 圈数字保持
}


def replace_emoji(text: str) -> str:
    """把源 Markdown 中的 emoji 替换为中文字符（保证 PDF 渲染）"""
    for k, v in EMOJI_REPLACE.items():
        text = text.replace(k, v)
    # 通用兜底：剩余 BMP 外（>U+FFFF）的 emoji 直接删掉
    text = re.sub(r"[\U00010000-\U0010FFFF]", "", text)
    return text


def main():
    fonts = register_cn_font()
    if "MicrosoftYaHei" not in fonts:
        print("[warn] 未找到微软雅黑，可能中文显示异常")
    print(f"[info] 已注册字体：{list(fonts.keys())}")

    styles = build_styles(fonts)
    src_text = SRC.read_text(encoding="utf-8")
    # 把 emoji 替换为符号（PDF 中字体不支持时不会显示）
    src_text = replace_emoji(src_text)
    # markdown → HTML（启用表格、fenced_code 等扩展）
    html = markdown.markdown(
        src_text,
        extensions=["tables", "fenced_code", "sane_lists"],
    )

    parser = MDToFlowables(styles)
    parser.feed(html)
    flowables = parser.flowables

    doc = SimpleDocTemplate(
        str(DST),
        pagesize=A4,
        leftMargin=2.0 * cm,
        rightMargin=2.0 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title="简历 - 李茂 - 系统运维工程师 - 徐州",
        author="李茂",
    )
    doc.build(flowables)
    size_kb = DST.stat().st_size / 1024
    print(f"已生成：{DST}  ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
