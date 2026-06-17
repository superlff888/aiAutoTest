"""
图片清晰化处理
- Lanczos 上采样 2x（最高质量插值）
- UnsharpMask 锐化（增强边缘文字可读性）
- 保存为高质量 PNG（optimize）
"""
from PIL import Image, ImageFilter, ImageEnhance
import os

SRC = r".claude\picture\image.png"
DST = r".claude\picture\image_2x.png"  # 不覆盖原图，输出到新文件
DST_HD = r".claude\picture\image_2x_sharp.png"  # 放大+锐化版本

def main():
    img = Image.open(SRC).convert("RGB")
    w, h = img.size
    print(f"[原图] {w}x{h}  {os.path.getsize(SRC)/1024:.1f} KB")

    # 1) 2x 超分上采样：Lanczos 是 PIL 内置最高质量的重采样算法
    upscaled = img.resize((w * 2, h * 2), Image.Resampling.LANCZOS)
    print(f"[放大2x] {upscaled.size[0]}x{upscaled.size[1]}")

    # 保存纯放大版本（无锐化，便于对比）
    upscaled.save(DST, "PNG", optimize=True)
    print(f"[保存] {DST}  {os.path.getsize(DST)/1024:.1f} KB")

    # 2) 锐化：UnsharpMask(半径, 百分比, 阈值)
    #    半径 2 / 数量 150 / 阈值 2 —— 适合表格+文字类截图
    sharpened = upscaled.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=2))

    # 3) 适度提对比度，进一步让文字更"硬"
    sharpened = ImageEnhance.Contrast(sharpened).enhance(1.10)

    sharpened.save(DST_HD, "PNG", optimize=True)
    print(f"[保存] {DST_HD}  {os.path.getsize(DST_HD)/1024:.1f} KB")

if __name__ == "__main__":
    main()
