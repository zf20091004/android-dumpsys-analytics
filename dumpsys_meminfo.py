#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import glob
from datetime import datetime

# ========== 配置区（请根据实际环境修改）==========
SOURCE_DIR = "/storage/emulated/0/文档/日志/状态"
OUTPUT_DIR = "/storage/emulated/0/文档/文档/txt/内容分析"
# ===============================================

# OOM 分类中文注释
OOM_CN_MAP = {
    'Native': '原生进程',
    'System': '系统进程',
    'Persistent': '持久进程',
    'Persistent Service': '持久服务',
    'Foreground': '前台进程',
    'Visible': '可见进程',
    'Perceptible': '可感知进程',
    'Perceptible Low': '低优先级可感知',
    'Heavy Weight': '重量级进程',
    'Home': '主页进程',
    'Previous': '上一个进程',
    'B Services': '后台服务',
    'Cached': '缓存进程',
}

def format_size(size_bytes):
    """智能格式化大小（字节 → KB/MB/GB）"""
    if size_bytes == 0:
        return "0 B"
    kb = size_bytes / 1024
    if kb >= 1024 * 1024:
        return f"{kb / (1024*1024):.2f} GB"
    elif kb >= 1024:
        return f"{kb / 1024:.1f} MB"
    elif kb >= 1:
        return f"{kb:.1f} KB"
    else:
        return f"{size_bytes} B"

def format_size_short(size_bytes):
    """简短格式（用于图表）"""
    if size_bytes == 0:
        return "0"
    kb = size_bytes / 1024
    if kb >= 1024 * 1024:
        return f"{kb / (1024*1024):.1f}G"
    elif kb >= 1024:
        return f"{kb / 1024:.0f}M"
    elif kb >= 1:
        return f"{kb:.0f}K"
    else:
        return f"{size_bytes}B"

def draw_bar(label, value, max_value, width=35):
    """绘制横向条形图"""
    if max_value == 0:
        return f"{label}: (0)"
    ratio = value / max_value
    filled = int(ratio * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"{label}: {bar} {format_size_short(value)}"

def parse_kb_string(s):
    """将 "1,234,567K" 转换为整数（字节）"""
    s = s.replace(',', '').strip()
    if s.endswith('K'):
        return int(s[:-1]) * 1024
    else:
        return int(s) * 1024   # 假设都是K

def find_latest_file(directory, pattern):
    """在目录中查找符合模式的最新文件"""
    files = glob.glob(os.path.join(directory, pattern))
    if not files:
        raise FileNotFoundError(f"在 {directory} 中未找到匹配 {pattern} 的文件")
    latest = max(files, key=os.path.getmtime)
    return latest

def parse_meminfo(filepath):
    """解析 dumpsys meminfo 文件，返回结构化数据"""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    data = {
        'uptime': None,
        'realtime': None,
        'rss_process': [],          # [{'name':, 'pid':, 'rss_bytes':, 'activities':}]
        'rss_oom': {},              # {category: [process_dict, ...]}
        'rss_category': {},         # {category_name: bytes}
        'pss_process': [],
        'pss_oom': {},
        'pss_category': {},
        'summary': {}               # 总内存信息
    }

    # 正则：进程行（有 pid）
    proc_re = re.compile(r'^\s*([\d,]+)K:\s*([^(]+?)\s*\(pid\s*(\d+)(?:\s*/.*)?\)')
    # 正则：类别行（无 pid），用于 category 和 OOM 头
    cat_re = re.compile(r'^\s*([\d,]+)K:\s*(.+)$')

    current_section = None
    current_oom_cat = None
    summary_lines = []

    for line in lines:
        line = line.rstrip()
        if not line:
            continue

        # ---- 识别段落标题 ----
        if line.startswith('Uptime:'):
            parts = line.split()
            if len(parts) >= 2:
                data['uptime'] = parts[1]
            if 'Realtime:' in line:
                rt = line.split('Realtime:')[1].strip()
                data['realtime'] = rt
            continue

        if line.startswith('Total RSS by process:'):
            current_section = 'rss_process'
            continue
        if line.startswith('Total RSS by OOM adjustment:'):
            current_section = 'rss_oom'
            continue
        if line.startswith('Total RSS by category:'):
            current_section = 'rss_category'
            continue
        if line.startswith('Total PSS by process:'):
            current_section = 'pss_process'
            continue
        if line.startswith('Total PSS by OOM adjustment:'):
            current_section = 'pss_oom'
            continue
        if line.startswith('Total PSS by category:'):
            current_section = 'pss_category'
            continue
        if line.startswith('Total RAM:'):
            current_section = 'summary'
            summary_lines.append(line)
            continue

        # ---- 根据当前段落解析 ----
        if current_section == 'summary':
            summary_lines.append(line)
            continue

        # 进程行（包含 pid）
        m = proc_re.match(line)
        if m:
            size_k = m.group(1)
            name = m.group(2).strip()
            pid = int(m.group(3))
            bytes_size = parse_kb_string(size_k)

            if current_section == 'rss_process':
                data['rss_process'].append({'name': name, 'pid': pid, 'rss_bytes': bytes_size})
            elif current_section == 'pss_process':
                data['pss_process'].append({'name': name, 'pid': pid, 'pss_bytes': bytes_size})
            elif current_section == 'rss_oom' and current_oom_cat:
                data['rss_oom'][current_oom_cat].append({'name': name, 'pid': pid, 'rss_bytes': bytes_size})
            elif current_section == 'pss_oom' and current_oom_cat:
                data['pss_oom'][current_oom_cat].append({'name': name, 'pid': pid, 'pss_bytes': bytes_size})
            continue

        # 类别行（无 pid）
        m = cat_re.match(line)
        if m:
            size_k = m.group(1)
            label = m.group(2).strip()
            bytes_size = parse_kb_string(size_k)

            if current_section == 'rss_category':
                data['rss_category'][label] = bytes_size
            elif current_section == 'pss_category':
                data['pss_category'][label] = bytes_size
            elif current_section == 'rss_oom':
                # 这是 OOM 分类的标题行，后续进程归属此类别
                current_oom_cat = label
                data['rss_oom'][label] = []
            elif current_section == 'pss_oom':
                current_oom_cat = label
                data['pss_oom'][label] = []
            continue

        # 其他行忽略

    # ---- 解析 summary ----
    summary_text = '\n'.join(summary_lines)
    summary = {}
    # Total RAM
    m = re.search(r'Total RAM:\s*([\d,]+)K', summary_text)
    if m:
        summary['total_ram_bytes'] = parse_kb_string(m.group(1))
    # Free RAM
    m = re.search(r'Free RAM:\s*([\d,]+)K\s*\(([^)]+)\)', summary_text)
    if m:
        summary['free_ram_bytes'] = parse_kb_string(m.group(1))
        summary['free_ram_detail'] = m.group(2)
    # Used RAM
    m = re.search(r'Used RAM:\s*([\d,]+)K\s*\(([^)]+)\)', summary_text)
    if m:
        summary['used_ram_bytes'] = parse_kb_string(m.group(1))
        summary['used_ram_detail'] = m.group(2)
    # Lost RAM
    m = re.search(r'Lost RAM:\s*([\d,]+)K', summary_text)
    if m:
        summary['lost_ram_bytes'] = parse_kb_string(m.group(1))
    # ZRAM
    m = re.search(r'ZRAM:\s*([\d,]+)K\s+physical used for ([\d,]+)K in swap', summary_text)
    if m:
        summary['zram_physical_bytes'] = parse_kb_string(m.group(1))
        summary['zram_swap_used_bytes'] = parse_kb_string(m.group(2))
    # DMA-BUF
    m = re.search(r'DMA-BUF:\s*([\d,]+)K', summary_text)
    if m:
        summary['dma_buf_bytes'] = parse_kb_string(m.group(1))
    # GPU
    m = re.search(r'GPU:\s*([\d,]+)K', summary_text)
    if m:
        summary['gpu_bytes'] = parse_kb_string(m.group(1))

    data['summary'] = summary
    return data

def generate_report(data, source_file, output_dir):
    """生成分析报告，返回输出文件路径"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_filename = f"dumpsys_meminfo_analysis_{timestamp}.txt"
    out_path = os.path.join(output_dir, out_filename)

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    with open(out_path, 'w', encoding='utf-8') as f:
        # ---- 标题 ----
        f.write("=" * 80 + "\n")
        f.write(f"📊 内存分析报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"📁 数据来源: {os.path.basename(source_file)}\n")
        f.write("=" * 80 + "\n\n")

        # ---- 运行时间 ----
        if data['uptime'] and data['realtime']:
            f.write(f"⏱️  Uptime: {data['uptime']}  |  Realtime: {data['realtime']}\n\n")

        # ---- 总体内存概况 ----
        s = data['summary']
        f.write("-" * 80 + "\n")
        f.write("🖥️  总体内存概况\n")
        f.write("-" * 80 + "\n")
        if 'total_ram_bytes' in s:
            total = s['total_ram_bytes']
            f.write(f"  总 RAM: {format_size(total)}\n")
        if 'free_ram_bytes' in s:
            free = s['free_ram_bytes']
            f.write(f"  空闲 RAM: {format_size(free)}  (包括缓存和可用内存)\n")
        if 'used_ram_bytes' in s:
            used = s['used_ram_bytes']
            f.write(f"  已用 RAM: {format_size(used)}  (PSS + 内核占用)\n")
        if 'lost_ram_bytes' in s:
            lost = s['lost_ram_bytes']
            f.write(f"  丢失 RAM: {format_size(lost)}\n")
        if 'zram_physical_bytes' in s:
            zram = s['zram_physical_bytes']
            f.write(f"  ZRAM 物理占用: {format_size(zram)}\n")
        if 'zram_swap_used_bytes' in s:
            swap = s['zram_swap_used_bytes']
            f.write(f"  ZRAM 交换区使用: {format_size(swap)}\n")
        if 'dma_buf_bytes' in s:
            f.write(f"  DMA-BUF: {format_size(s['dma_buf_bytes'])}\n")
        if 'gpu_bytes' in s:
            f.write(f"  GPU 占用: {format_size(s['gpu_bytes'])}\n")
        # 内存状态评估
        if 'free_ram_bytes' in s and 'total_ram_bytes' in s:
            free_ratio = s['free_ram_bytes'] / s['total_ram_bytes']
            if free_ratio < 0.1:
                status = "🔴 内存严重不足，建议关闭后台应用或重启"
            elif free_ratio < 0.2:
                status = "🟡 内存较为紧张，可清理缓存"
            else:
                status = "🟢 内存状态正常"
            f.write(f"\n  📌 内存状态: {status}\n")
        f.write("\n")

        # ---- 辅助函数：输出进程排行和条形图 ----
        def output_process_rankings(proc_list, title, key_bytes, key_name, top_n=15):
            if not proc_list:
                return
            sorted_proc = sorted(proc_list, key=lambda x: x[key_bytes], reverse=True)
            total = sum(p[key_bytes] for p in proc_list)
            f.write("-" * 80 + "\n")
            f.write(f"🏆 {title} (Top {top_n}，总占用 {format_size(total)})\n")
            f.write("-" * 80 + "\n")
            max_val = sorted_proc[0][key_bytes] if sorted_proc else 1
            f.write(f"{'Rank':4} {'进程名':45} {'占用':>12} {'占比':>8}\n")
            f.write("    " + "-" * 70 + "\n")
            for i, p in enumerate(sorted_proc[:top_n], 1):
                size = p[key_bytes]
                ratio = size / total if total > 0 else 0
                name = p['name'][:45]
                f.write(f"{i:4} {name:45} {format_size(size):>12} {ratio*100:>6.1f}%\n")
            f.write("\n")
            # 条形图（前10）
            f.write("  📊 占用分布（前10）\n")
            for i, p in enumerate(sorted_proc[:10], 1):
                name = p['name'][:30]
                size = p[key_bytes]
                f.write(f"  {draw_bar(f'{i:2}. {name}', size, max_val, 40)}\n")
            f.write("\n")

        def output_category_table(category_dict, title):
            if not category_dict:
                return
            sorted_items = sorted(category_dict.items(), key=lambda x: x[1], reverse=True)
            total = sum(category_dict.values())
            f.write("-" * 80 + "\n")
            f.write(f"📂 {title} (总计 {format_size(total)})\n")
            f.write("-" * 80 + "\n")
            max_val = sorted_items[0][1] if sorted_items else 1
            for name, size in sorted_items:
                ratio = size / total if total > 0 else 0
                f.write(f"  {draw_bar(name, size, max_val, 40)}  {ratio*100:>5.1f}%\n")
            f.write("\n")

        def output_oom_table(oom_dict, title, key_bytes):
            if not oom_dict:
                return
            oom_total = {}
            total_procs = 0
            for cat, procs in oom_dict.items():
                oom_total[cat] = sum(p[key_bytes] for p in procs)
                total_procs += len(procs)
            sorted_cats = sorted(oom_total.items(), key=lambda x: x[1], reverse=True)
            total_all = sum(oom_total.values())
            f.write("-" * 80 + "\n")
            f.write(f"⚖️  {title} (按 OOM 调整分类，总计 {format_size(total_all)}，共 {total_procs} 个进程)\n")
            f.write("-" * 80 + "\n")
            max_val = sorted_cats[0][1] if sorted_cats else 1
            for cat, size in sorted_cats:
                ratio = size / total_all if total_all > 0 else 0
                f.write(f"  {draw_bar(cat, size, max_val, 40)}  {ratio*100:>5.1f}%\n")
            f.write("\n")
            f.write("  类别详情:\n")
            for cat, size in sorted_cats:
                count = len(oom_dict[cat])
                comment = OOM_CN_MAP.get(cat, '')
                if comment:
                    f.write(f"    {cat} ({comment}): {count} 个进程，共 {format_size(size)}\n")
                else:
                    f.write(f"    {cat}: {count} 个进程，共 {format_size(size)}\n")
            f.write("\n")

        # ---- 输出 RSS 分析 ----
        if data['rss_process']:
            output_process_rankings(data['rss_process'], "RSS 进程占用排行", 'rss_bytes', 'RSS')
        if data['rss_category']:
            output_category_table(data['rss_category'], "RSS 按内存类型分类")
        if data['rss_oom']:
            output_oom_table(data['rss_oom'], "RSS 按 OOM 分类", 'rss_bytes')

        # ---- 输出 PSS 分析 ----
        if data['pss_process']:
            output_process_rankings(data['pss_process'], "PSS 进程占用排行", 'pss_bytes', 'PSS')
        if data['pss_category']:
            output_category_table(data['pss_category'], "PSS 按内存类型分类")
        if data['pss_oom']:
            output_oom_table(data['pss_oom'], "PSS 按 OOM 分类", 'pss_bytes')

        # ---- 详细进程列表（RSS + PSS 对比） ----
        f.write("-" * 80 + "\n")
        f.write("📋 所有进程详情 (按 RSS 降序)\n")
        f.write("-" * 80 + "\n")
        if data['rss_process']:
            sorted_rss = sorted(data['rss_process'], key=lambda x: x['rss_bytes'], reverse=True)
            f.write(f"{'进程名':50} {'RSS':>12} {'PSS':>12} {'PID':>8}\n")
            f.write("-" * 90 + "\n")
            pss_map = {p['pid']: p['pss_bytes'] for p in data.get('pss_process', [])}
            for p in sorted_rss:
                name = p['name'][:50]
                rss = p['rss_bytes']
                pss = pss_map.get(p['pid'], 0)
                pid = p['pid']
                f.write(f"{name:50} {format_size(rss):>12} {format_size(pss):>12} {pid:>8}\n")
        f.write("\n")

        # ---- 结束 ----
        f.write("=" * 80 + "\n")
        f.write("✅ 报告生成完成\n")

    return out_path

def main():
    try:
        # 1. 查找最新的 dumpsys_meminfo_*.txt 文件
        pattern = "dumpsys_meminfo_*.txt"
        latest_file = find_latest_file(SOURCE_DIR, pattern)
        print(f"✅ 找到最新文件: {latest_file}")

        # 2. 解析文件
        print("📂 正在解析内存数据...")
        data = parse_meminfo(latest_file)

        # 3. 生成报告
        print("📝 正在生成分析报告...")
        out_path = generate_report(data, latest_file, OUTPUT_DIR)

        print(f"🎉 报告已生成: {out_path}")

    except Exception as e:
        print(f"❌ 发生错误: {e}")

if __name__ == "__main__":
    main()