import os
import re
import json
from datetime import datetime

# ===== 配置区（只改这里就行）=====
SOURCE_DIR = "/sdcard/文档/日志/状态"
OUTPUT_DIR = "/storage/emulated/0/文档/文档/txt/内容分析"
# ==============================

def format_size(size_bytes):
    """智能格式化大小，>1000MB转为GB，否则用MB"""
    if size_bytes == 0:
        return "0 B"
    mb = size_bytes / (1024 * 1024)
    if mb >= 1024:
        return f"{mb/1024:.2f} GB"
    elif mb >= 1:
        return f"{mb:.1f} MB"
    else:
        return f"{size_bytes / 1024:.1f} KB"

def format_size_short(size_bytes):
    """用于图表的简短格式"""
    if size_bytes == 0:
        return "0"
    mb = size_bytes / (1024 * 1024)
    if mb >= 1024:
        return f"{mb/1024:.1f}G"
    elif mb >= 1:
        return f"{mb:.0f}M"
    else:
        return f"{size_bytes / 1024:.0f}K"

def draw_bar(label, value, max_value, width=35):
    """绘制简单的横条图"""
    if max_value == 0:
        return f"{label}: (0)"
    ratio = value / max_value
    filled = int(ratio * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"{label}: {bar} {format_size_short(value)}"

# 1️⃣ 找最新的 app_size_*.txt
txt_files = [
    os.path.join(SOURCE_DIR, f)
    for f in os.listdir(SOURCE_DIR)
    if f.startswith("app_size_") and f.endswith(".txt")
]

if not txt_files:
    raise FileNotFoundError("❌ 没找到 app_size_*.txt 文件")

latest_file = max(txt_files, key=os.path.getmtime)
print(f"✅ 读取文件: {latest_file}")

# 2️⃣ 读取并解析完整内容
with open(latest_file, "r", encoding="utf-8", errors="ignore") as f:
    txt = f.read()

# 解析所有头部信息
header_info = {}

# 延迟 - 更健壮的正则
latency_match = re.search(r"Latency:\s*([\d.]+ms\s*\[[^\]]+\])", txt)
if latency_match:
    header_info['latency'] = latency_match.group(1)

# 各类空间信息 - 增强解析，同时计算已使用量
free_patterns = {
    'Data-Free': {
        'pattern': r"Data-Free:\s*(\d+)K\s*/\s*(\d+)K\s*total\s*=\s*([\d.]+)%\s*free",
        'label': '数据空间'
    },
    'Cache-Free': {
        'pattern': r"Cache-Free:\s*(\d+)K\s*/\s*(\d+)K\s*total\s*=\s*([\d.]+)%\s*free",
        'label': '缓存空间'
    },
    'System-Free': {
        'pattern': r"System-Free:\s*(\d+)K\s*/\s*(\d+)K\s*total\s*=\s*([\d.]+)%\s*free",
        'label': '系统空间'
    },
    'Metadata-Free': {
        'pattern': r"Metadata-Free:\s*(\d+)K\s*/\s*(\d+)K\s*total\s*=\s*([\d.]+)%\s*free",
        'label': '元数据空间'
    },
}

for name, config in free_patterns.items():
    match = re.search(config['pattern'], txt)
    if match:
        free_k = int(match.group(1))
        total_k = int(match.group(2))
        free_percent = float(match.group(3))
        used_k = total_k - free_k
        used_percent = 100 - free_percent
        header_info[name] = {
            'free_kb': free_k,
            'total_kb': total_k,
            'used_kb': used_k,
            'free_mb': free_k / 1024,
            'total_mb': total_k / 1024,
            'used_mb': used_k / 1024,
            'free_percent': free_percent,
            'used_percent': used_percent,
            'label': config['label']
        }

# 加密状态
encrypt_match = re.search(r"File-based Encryption:\s*(true|false)", txt)
if encrypt_match:
    header_info['encryption'] = encrypt_match.group(1)

# 各类大小（这些是字节）
size_keys = [
    'App Size', 'App Data Size', 'App Cache Size',
    'Photos Size', 'Videos Size', 'Audio Size',
    'Downloads Size', 'System Size', 'Other Size'
]

for key in size_keys:
    match = re.search(rf"{re.escape(key)}:\s*(\d+)", txt)
    if match:
        header_info[key] = int(match.group(1))

# 解析应用列表（增强健壮性）
pkgs_match = re.search(r"Package Names:\s*\[(.*?)\]", txt, re.DOTALL)
apps_match = re.search(r"App Sizes:\s*\[(.*?)\]", txt, re.DOTALL)
data_match = re.search(r"App Data Sizes:\s*\[(.*?)\]", txt, re.DOTALL)
caches_match = re.search(r"Cache Sizes:\s*\[(.*?)\]", txt, re.DOTALL)

if not all([pkgs_match, apps_match, data_match, caches_match]):
    raise ValueError("❌ 解析应用数据失败，请检查文件格式")

pkgs = json.loads("[" + pkgs_match.group(1) + "]")
apps = list(map(int, apps_match.group(1).split(",")))
data = list(map(int, data_match.group(1).split(",")))
caches = list(map(int, caches_match.group(1).split(",")))

# 3️⃣ 确保输出目录存在
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 4️⃣ 生成带时间戳的输出文件名
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_FILE = f"storage_dumpsys_diskstats_analysis_{timestamp}.txt"

# 5️⃣ 写入结果
out_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)

with open(out_path, "w", encoding="utf-8") as f:
    # ===== 写入头部信息 =====
    f.write("=" * 80 + "\n")
    f.write(f"📊 存储分析报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"📁 数据来源: {os.path.basename(latest_file)}\n")
    f.write("=" * 80 + "\n\n")
    
    # 延迟
    if 'latency' in header_info:
        f.write(f"⏱️  延迟: {header_info['latency']}\n")
    
    # 加密状态
    if 'encryption' in header_info:
        f.write(f"🔐 文件加密: {header_info['encryption']}\n")
    f.write("\n")
    
    # 空间使用概况 - 明确标注"已使用"和"可用"
    f.write("-" * 80 + "\n")
    f.write("📈 空间使用概况\n")
    f.write("-" * 80 + "\n")
    f.write("  💡 说明：显示各分区总容量、已使用量及可用量\n\n")
    
    space_categories = ['Data-Free', 'Cache-Free', 'System-Free', 'Metadata-Free']
    
    for key in space_categories:
        if key in header_info:
            info = header_info[key]
            # 根据使用率给不同的提示
            if info['used_percent'] > 80:
                status = "⚠️  紧张"
            elif info['used_percent'] > 60:
                status = "⚡ 正常"
            else:
                status = "✅ 充裕"
            
            f.write(f"  📂 {info['label']}:\n")
            f.write(f"      总容量: {format_size(info['total_kb'] * 1024)}\n")
            f.write(f"      已使用: {format_size(info['used_kb'] * 1024)} ({info['used_percent']:.1f}%)\n")
            f.write(f"      可  用: {format_size(info['free_kb'] * 1024)} ({info['free_percent']:.1f}%)\n")
            f.write(f"      状  态: {status}\n\n")
    
    # 各类存储大小详情
    f.write("-" * 80 + "\n")
    f.write("📦 存储分类详情（按占用空间排序）\n")
    f.write("-" * 80 + "\n")
    
    size_labels = {
        'App Size': '📱 应用大小',
        'App Data Size': '📊 应用数据',
        'App Cache Size': '🗑️  应用缓存',
        'Photos Size': '🖼️  照片',
        'Videos Size': '🎬 视频',
        'Audio Size': '🎵 音频',
        'Downloads Size': '⬇️  下载',
        'System Size': '⚙️  磁盘大小',
        'Other Size': '📁 其他'
    }
    
    # 收集有数据的项用于图表，按大小排序
    chart_data = []
    for key, label in size_labels.items():
        if key in header_info and header_info[key] > 0:
            size_bytes = header_info[key]
            chart_data.append((label, size_bytes))
    
    # 按大小降序排列
    chart_data.sort(key=lambda x: x[1], reverse=True)
    
    for label, size_bytes in chart_data:
        f.write(f"  {label:20}: {format_size(size_bytes)}\n")
    
    f.write("\n")
    
    # 绘制图表
    if chart_data:
        f.write("-" * 80 + "\n")
        f.write("📊 存储分布可视化图表\n")
        f.write("-" * 80 + "\n")
        max_val = max([item[1] for item in chart_data])
        for label, value in chart_data:
            f.write(f"  {draw_bar(label, value, max_val, 35)}\n")
        f.write("\n")
    
    # 统计汇总
    f.write("-" * 80 + "\n")
    f.write("📊 应用统计汇总\n")
    f.write("-" * 80 + "\n")
    
    total_apps = len(pkgs)
    total_app_size = sum(apps)
    total_data_size = sum(data)
    total_cache_size = sum(caches)
    total_size = total_app_size + total_data_size + total_cache_size
    
    # 计算有数据的应用数量（用于更准确的统计）
    apps_with_data = sum(1 for d in data if d > 0)
    apps_with_cache = sum(1 for c in caches if c > 0)
    
    f.write(f"  📱 应用总数: {total_apps}\n")
    f.write(f"  📊 有数据存储的应用: {apps_with_data} 个\n")
    f.write(f"  🗑️  有缓存的应用: {apps_with_cache} 个\n\n")
    f.write(f"  📦 应用大小总计: {format_size(total_app_size)}\n")
    f.write(f"  📊 数据大小总计: {format_size(total_data_size)}\n")
    f.write(f"  🗑️  缓存大小总计: {format_size(total_cache_size)}\n")
    f.write(f"  ─────────────────────\n")
    f.write(f"  📊 应用占用总计: {format_size(total_size)}\n")
    f.write("\n")
    
    # 按数据大小排序的Top 10
    f.write("-" * 80 + "\n")
    f.write("🏆 Top 10 数据占用最多的应用\n")
    f.write("-" * 80 + "\n")
    
    sorted_apps = sorted(zip(pkgs, apps, data, caches), key=lambda x: x[2], reverse=True)
    for i, (p, a, d, c) in enumerate(sorted_apps[:10], 1):
        if d > 0:
            f.write(f"  {i:2}. {p[:40]:40} 数据: {format_size(d)}  (应用: {format_size(a)}, 缓存: {format_size(c)})\n")
    f.write("\n")
    
    # 按缓存大小排序的Top 10
    f.write("-" * 80 + "\n")
    f.write("🗑️  Top 10 缓存占用最多的应用\n")
    f.write("-" * 80 + "\n")
    
    sorted_cache = sorted(zip(pkgs, apps, data, caches), key=lambda x: x[3], reverse=True)
    top_cache_count = 0
    for i, (p, a, d, c) in enumerate(sorted_cache, 1):
        if c > 0 and top_cache_count < 10:
            f.write(f"  {i:2}. {p[:40]:40} 缓存: {format_size(c)}  (应用: {format_size(a)}, 数据: {format_size(d)})\n")
            top_cache_count += 1
    if top_cache_count == 0:
        f.write("  （无应用缓存数据）\n")
    f.write("\n")
    
    # ===== 原有详细列表 =====
    f.write("=" * 80 + "\n")
    f.write("📋 所有应用详细信息（按数据大小降序排列）\n")
    f.write("=" * 80 + "\n")
    
    # 表头 - 使用更智能的列宽
    f.write(f"{'Package':50} {'Code':>12} {'Data':>12} {'Cache':>12}\n")
    f.write("-" * 90 + "\n")
    
    for p, a, d, c in sorted(zip(pkgs, apps, data, caches),
                              key=lambda x: x[2], reverse=True):
        # 智能格式化每个字段
        a_str = format_size(a)
        d_str = format_size(d)
        c_str = format_size(c)
        f.write(f"{p:50} {a_str:>12} {d_str:>12} {c_str:>12}\n")
    
    # 底部统计
    f.write("-" * 90 + "\n")
    f.write(f"{'合计':50} {format_size(total_app_size):>12} {format_size(total_data_size):>12} {format_size(total_cache_size):>12}\n")
    f.write(f"{'平均':50} {format_size(total_app_size/total_apps if total_apps else 0):>12} {format_size(total_data_size/total_apps if total_apps else 0):>12} {format_size(total_cache_size/total_apps if total_apps else 0):>12}\n")
    
    f.write("\n" + "=" * 80 + "\n")
    f.write("✅ 报告生成完成\n")

print(f"✅ 结果已写入: {out_path}")
print(f"📊 共分析了 {len(pkgs)} 个应用")