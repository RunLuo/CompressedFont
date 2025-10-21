# fonttools 字体压缩工具

# 中文汉字数量很多，以思源宋体为例，思源宋体遵循 GB 18030 和通用规范汉字表，包含 8105 个规范字（来源：少数派），
# 可能还有其他语言的字符，实际字符数量肯定是远超这个数字的。

# 实际上，常用汉字数量也就 3500 个左右，如果你的文本相对固定，可以考虑删减掉其他不常用的汉字。

# 极端做法是只保留文本中出现的字符，其他的全部删掉，但是我个人更倾向于折中保留 3500 汉字，
# 在未来如果修改了文本，也不至于每次都要重新压缩一遍字体。

# 这种删减字符的做法叫"取子集"。取子集我们需要定义一个纯文本文件

import subprocess
import os
import glob
import time
from pathlib import Path

def get_font_files(source_dir):
    """获取源字体目录中的所有字体文件"""
    font_extensions = ['*.ttf', '*.otf', '*.woff', '*.woff2', '*.ttc']
    font_files = []
    
    for ext in font_extensions:
        font_files.extend(glob.glob(os.path.join(source_dir, ext)))
        # 也搜索大写扩展名
        font_files.extend(glob.glob(os.path.join(source_dir, ext.upper())))
    
    return font_files

def get_font_count_in_collection(font_file):
    """
    获取字体集合文件中的字体数量
    
    Args:
        font_file: 字体文件路径
    
    Returns:
        int: 字体数量，如果不是集合文件则返回1，出错返回0
    """
    try:
        from fontTools import ttLib
        font = ttLib.TTFont(font_file)
        font.close()
        return 1  # 单个字体文件
    except ttLib.TTLibFileIsCollectionError as e:
        # 从错误信息中提取字体数量
        error_msg = str(e)
        import re
        match = re.search(r'between 0 and (\d+)', error_msg)
        if match:
            return int(match.group(1)) + 1  # 因为是 0 到 N，所以总数是 N+1
        return 0
    except Exception:
        return 0

def compress_single_font(font_file, text_file, output_dir, font_index=None):
    """
    压缩单个字体文件
    
    Args:
        font_file: 源字体文件路径
        text_file: 包含字符集的文本文件
        output_dir: 输出目录
        font_index: 字体索引（用于TTC文件）
    
    Returns:
        bool: 是否成功
    """
    if not os.path.exists(font_file):
        print(f"❌ 字体文件不存在：{font_file}")
        return False
        
    if not os.path.exists(text_file):
        print(f"❌ 文本文件不存在：{text_file}")
        return False
    
    # 生成输出文件名
    font_name = Path(font_file).stem
    font_ext = Path(font_file).suffix.lower()
    
    # 对于TTC文件，添加字体索引到文件名
    if font_index is not None:
        output_file = os.path.join(output_dir, f"{font_name}-{font_index}-subset.ttf")
    else:
        # 对于TTC文件，转换为TTF格式
        if font_ext == '.ttc':
            output_file = os.path.join(output_dir, f"{font_name}-subset.ttf")
        else:
            output_file = os.path.join(output_dir, f"{font_name}-subset{font_ext}")
    
    try:
        # 构建 fonttools subset 命令
        cmd = [
            "fonttools", "subset", 
            font_file,
            f"--text-file={text_file}",
            f"--output-file={output_file}"
        ]
        
        # 如果是TTC文件，添加字体索引参数
        if font_index is not None:
            cmd.extend([f"--font-number={font_index}"])
        
        font_display_name = os.path.basename(font_file)
        if font_index is not None:
            font_display_name += f" (字体 {font_index})"
            
        print(f"正在压缩字体文件：{font_display_name}")
        print(f"命令：{' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ 字体压缩成功！生成文件：{os.path.basename(output_file)}")
            
            # 显示文件大小对比
            original_size = os.path.getsize(font_file) / 1024 / 1024  # MB
            compressed_size = os.path.getsize(output_file) / 1024 / 1024  # MB
            compression_ratio = (1 - compressed_size / original_size) * 100
            
            print(f"原始文件大小：{original_size:.2f} MB")
            print(f"压缩后大小：{compressed_size:.2f} MB")
            print(f"压缩率：{compression_ratio:.1f}%")
            print("-" * 50)
            
            return True
        else:
            print(f"❌ 字体压缩失败：{result.stderr}")
            return False
            
    except FileNotFoundError:
        print("❌ 错误：未找到 fonttools 工具，请先安装：pip install fonttools")
        return False
    except Exception as e:
        print(f"❌ 压缩过程中出现错误：{str(e)}")
        return False

def batch_compress_fonts():
    """
    批量压缩字体文件
    从 sourceFont 目录读取所有字体文件，根据 txt.txt 中的字符集进行压缩，
    输出到 targetFont 目录
    """
    # 定义目录和文件路径
    source_dir = "sourceFont"
    output_dir = "targetFont"
    text_file = "txt.txt"
    
    # 检查必要的目录和文件
    if not os.path.exists(source_dir):
        print(f"❌ 源字体目录不存在：{source_dir}")
        return False
    
    if not os.path.exists(text_file):
        print(f"❌ 字符集文件不存在：{text_file}")
        return False
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取所有字体文件
    font_files = get_font_files(source_dir)
    
    if not font_files:
        print(f"❌ 在 {source_dir} 目录中未找到任何字体文件")
        print("支持的字体格式：.ttf, .otf, .woff, .woff2, .ttc")
        return False
    
    print(f"🔍 找到 {len(font_files)} 个字体文件：")
    for font in font_files:
        print(f"  - {os.path.basename(font)}")
    print("-" * 50)
    
    # 开始批量压缩
    successful_count = 0
    failed_count = 0
    start_time = time.time()
    total_fonts_processed = 0
    
    for i, font_file in enumerate(font_files, 1):
        print(f"📝 处理第 {i}/{len(font_files)} 个字体文件")
        
        # 检查是否是TTC文件
        font_ext = Path(font_file).suffix.lower()
        if font_ext == '.ttc':
            # 获取TTC文件中的字体数量
            font_count = get_font_count_in_collection(font_file)
            if font_count > 1:
                print(f"🔍 检测到TTC字体集合文件，包含 {font_count} 个字体")
                # 分别处理每个字体
                for font_index in range(font_count):
                    print(f"  📝 处理字体 {font_index + 1}/{font_count}")
                    if compress_single_font(font_file, text_file, output_dir, font_index):
                        successful_count += 1
                    else:
                        failed_count += 1
                    total_fonts_processed += 1
            else:
                # 作为单个字体处理
                if compress_single_font(font_file, text_file, output_dir):
                    successful_count += 1
                else:
                    failed_count += 1
                total_fonts_processed += 1
        else:
            # 单个字体文件
            if compress_single_font(font_file, text_file, output_dir):
                successful_count += 1
            else:
                failed_count += 1
            total_fonts_processed += 1
    
    # 显示总结
    end_time = time.time()
    total_time = end_time - start_time
    
    print("=" * 50)
    print("📊 批量压缩完成！")
    print(f"📁 处理了 {len(font_files)} 个字体文件")
    print(f"🎯 总共生成了 {total_fonts_processed} 个字体")
    print(f"✅ 成功：{successful_count} 个字体")
    print(f"❌ 失败：{failed_count} 个字体")
    print(f"⏱️ 总耗时：{total_time:.2f} 秒")
    print(f"📁 输出目录：{output_dir}")
    
    return successful_count > 0

if __name__ == "__main__":
    batch_compress_fonts()