#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import glob
from datetime import datetime

# ========== 配置区 ==========
SOURCE_DIR = "/storage/emulated/0/文档/日志/状态"
OUTPUT_DIR = "/storage/emulated/0/文档/文档/txt/内容分析"
# =============================

# CPU 状态中文注释
CPU_STATE_CN = {
    'user': '用户态',
    'kernel': '内核态',
    'iowait': 'IO等待',
    'irq': '硬件中断',
    'softirq': '软中断',
}

# 列宽常量
COL_PROCESS = 45
COL_PID = 8
COL_CPU = 10
COL_FAULT = 12
COL_THREAD = 35
COL_TID = 8

def format_percent(value):
    """格式化百分比"""
    return f"{value:.1f}%"

def draw_bar(label, value, max_value, width=40):
    """绘制横向条形图"""
    if max_value == 0:
        return f"{label}: (0)"
    ratio = min(value / max_value, 1.0)
    filled = int(ratio * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"{label}: {bar} {value:.1f}%"

def find_latest_file(directory, pattern):
    """在目录中查找符合模式的最新文件"""
    files = glob.glob(os.path.join(directory, pattern))
    if not files:
        raise FileNotFoundError(f"在 {directory} 中未找到匹配 {pattern} 的文件")
    latest = max(files, key=os.path.getmtime)
    return latest

def parse_cpuinfo(filepath):
    """解析 dumpsys cpuinfo 文件"""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    data = {
        'load_avg': None,
        'sample_time': None,
        'total_cpu': {},
        'processes': [],
        'thread_count': 0,
        'process_count': 0,
    }

    # 正则：主进程行
    main_re = re.compile(
        r'^\s*([\d.]+)%\s+(\d+)/([^:]+):\s*([\d.]+)%\s+user\s*\+\s*([\d.]+)%\s+kernel'
        r'(?:\s*/\s*faults:\s*(\d+)\s+minor(?:\s+(\d+)\s+major)?)?'
    )
    
    # 正则：子线程行
    thread_re = re.compile(
        r'^\s{2,}([\d.]+)%\s+(\d+)/([^:]+):\s*([\d.]+)%\s+user\s*\+\s*([\d.]+)%\s+kernel'
    )
    
    # 正则：TOTAL 行
    total_re = re.compile(
        r'^([\d.]+)%\s*TOTAL:\s*([\d.]+)%\s+user\s*\+\s*([\d.]+)%\s+kernel'
        r'(?:\s*\+\s*([\d.]+)%\s+iowait)?'
        r'(?:\s*\+\s*([\d.]+)%\s+irq)?'
        r'(?:\s*\+\s*([\d.]+)%\s+softirq)?'
    )
    
    # 负载行
    load_re = re.compile(r'^Load:\s*([\d.]+)\s*/\s*([\d.]+)\s*/\s*([\d.]+)')

    current_process = None
    process_threads = []

    for line in lines:
        line = line.rstrip()
        if not line:
            continue

        # ---- 解析负载 ----
        m = load_re.match(line)
        if m:
            data['load_avg'] = {
                '1min': float(m.group(1)),
                '5min': float(m.group(2)),
                '15min': float(m.group(3))
            }
            continue

        # ---- 解析采样时间 ----
        if 'CPU usage from' in line and 'to' in line:
            time_match = re.search(r'from\s+(.+?)\s+to\s+(.+?)(?:\s|$)', line)
            if time_match:
                data['sample_time'] = {
                    'from': time_match.group(1),
                    'to': time_match.group(2)
                }
            continue

        # ---- 解析 TOTAL ----
        m = total_re.match(line)
        if m:
            data['total_cpu'] = {
                'total': float(m.group(1)),
                'user': float(m.group(2)),
                'kernel': float(m.group(3)),
                'iowait': float(m.group(4)) if m.group(4) else 0,
                'irq': float(m.group(5)) if m.group(5) else 0,
                'softirq': float(m.group(6)) if m.group(6) else 0,
            }
            continue

        # ---- 解析主进程 ----
        if not line.startswith('  +') and not line.startswith(' +'):
            m = main_re.match(line)
            if m:
                # 保存之前的进程
                if current_process:
                    if process_threads:
                        current_process['threads'] = process_threads
                        data['thread_count'] += len(process_threads)
                    else:
                        current_process['threads'] = []
                    data['processes'].append(current_process)

                total = float(m.group(1))
                pid = int(m.group(2))
                name = m.group(3).strip()
                user = float(m.group(4))
                kernel = float(m.group(5))
                minor_faults = int(m.group(6)) if m.group(6) else 0
                major_faults = int(m.group(7)) if m.group(7) else 0

                current_process = {
                    'name': name,
                    'pid': pid,
                    'total': total,
                    'user': user,
                    'kernel': kernel,
                    'minor_faults': minor_faults,
                    'major_faults': major_faults,
                    'threads': []
                }
                process_threads = []
                continue

        # ---- 解析子线程 ----
        if line.startswith('  +') or line.startswith(' +'):
            clean_line = line.replace('+', '', 1)
            m = thread_re.match(clean_line)
            if m and current_process:
                total = float(m.group(1))
                tid = int(m.group(2))
                tname = m.group(3).strip()
                user = float(m.group(4))
                kernel = float(m.group(5))
                process_threads.append({
                    'tid': tid,
                    'name': tname,
                    'total': total,
                    'user': user,
                    'kernel': kernel
                })
                continue

        if line.startswith('    ') or line.startswith('   ') or line.startswith('  '):
            if not main_re.match(line):
                m = thread_re.match(line)
                if m and current_process:
                    total = float(m.group(1))
                    tid = int(m.group(2))
                    tname = m.group(3).strip()
                    user = float(m.group(4))
                    kernel = float(m.group(5))
                    process_threads.append({
                        'tid': tid,
                        'name': tname,
                        'total': total,
                        'user': user,
                        'kernel': kernel
                    })
                    continue

    # 保存最后一个进程
    if current_process:
        if process_threads:
            current_process['threads'] = process_threads
            data['thread_count'] += len(process_threads)
        else:
            current_process['threads'] = []
        data['processes'].append(current_process)

    data['process_count'] = len(data['processes'])
    return data

def write_section_header(f, title, char='-', width=80):
    """写入章节标题"""
    f.write(char * width + "\n")
    f.write(f"{title}\n")
    f.write(char * width + "\n")

def generate_report(data, source_file, output_dir):
    """生成 CPU 分析报告"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_filename = f"dumpsys_cpuinfo_analysis_{timestamp}.txt"
    out_path = os.path.join(output_dir, out_filename)

    os.makedirs(output_dir, exist_ok=True)

    with open(out_path, 'w', encoding='utf-8') as f:
        # ============================================================
        # 1. 报告标题
        # ============================================================
        f.write("=" * 80 + "\n")
        f.write(f"📊 CPU 分析报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"📁 数据来源: {os.path.basename(source_file)}\n")
        f.write("=" * 80 + "\n\n")

        # ============================================================
        # 2. 系统负载
        # ============================================================
        if data['load_avg']:
            la = data['load_avg']
            write_section_header(f, "📈 系统负载 (Load Average)")
            f.write(f"  1分钟   : {la['1min']:>8.2f}\n")
            f.write(f"  5分钟   : {la['5min']:>8.2f}\n")
            f.write(f"  15分钟  : {la['15min']:>8.2f}\n")
            
            # 负载状态评估
            if la['1min'] > la['5min'] * 1.2:
                status = "🔴 负载快速上升，系统可能过载"
            elif la['1min'] < la['5min'] * 0.8:
                status = "🟢 负载下降，系统趋于稳定"
            elif la['1min'] > la['15min'] * 1.1:
                status = "🟡 负载趋势上升，需关注"
            else:
                status = "🟢 负载平稳"
            f.write(f"\n  📌 状态: {status}\n\n")

        # ============================================================
        # 3. 采样时间
        # ============================================================
        if data['sample_time']:
            f.write(f"⏱️  采样时段: {data['sample_time']['from']} → {data['sample_time']['to']}\n\n")

        # ============================================================
        # 4. 总体 CPU 占用
        # ============================================================
        if data['total_cpu']:
            tc = data['total_cpu']
            write_section_header(f, "🖥️  总体 CPU 占用")
            f.write(f"  总占用   : {tc['total']:>8.1f}%\n")
            f.write(f"  用户态   : {tc['user']:>8.1f}%  ({CPU_STATE_CN['user']})\n")
            f.write(f"  内核态   : {tc['kernel']:>8.1f}%  ({CPU_STATE_CN['kernel']})\n")
            if tc.get('iowait', 0) > 0:
                f.write(f"  IO等待   : {tc['iowait']:>8.1f}%  ({CPU_STATE_CN['iowait']})\n")
            if tc.get('irq', 0) > 0:
                f.write(f"  硬中断   : {tc['irq']:>8.1f}%  ({CPU_STATE_CN['irq']})\n")
            if tc.get('softirq', 0) > 0:
                f.write(f"  软中断   : {tc['softirq']:>8.1f}%  ({CPU_STATE_CN['softirq']})\n")
            
            # CPU 使用率状态
            cpu_total = tc['total']
            if cpu_total > 80:
                cpu_status = "🔴 CPU 占用过高，系统繁忙"
            elif cpu_total > 60:
                cpu_status = "🟡 CPU 占用偏高，注意观察"
            else:
                cpu_status = "🟢 CPU 占用正常"
            f.write(f"\n  📌 状态: {cpu_status}\n\n")

        # ============================================================
        # 5. 进程/线程统计
        # ============================================================
        write_section_header(f, "📊 进程/线程统计")
        f.write(f"  📱 进程总数            : {data['process_count']:>8}\n")
        f.write(f"  🧵 线程总数            : {data['thread_count']:>8}\n")
        if data['process_count'] > 0:
            avg_threads = data['thread_count'] / data['process_count']
            f.write(f"  📊 平均每进程线程数    : {avg_threads:>8.1f}\n")
        f.write("\n")

        # ============================================================
        # 6. Top 20 CPU 占用进程
        # ============================================================
        if data['processes']:
            sorted_procs = sorted(data['processes'], key=lambda x: x['total'], reverse=True)
            max_cpu = sorted_procs[0]['total'] if sorted_procs else 1

            write_section_header(f, "🏆 Top 20 CPU 占用进程")
            # 表头
            f.write(f"  {'排名':<6} {'进程名':<40} {'总CPU':>10} {'用户':>10} {'内核':>10} {'线程数':>8}\n")
            f.write(f"  {'-' * 88}\n")
            
            for i, p in enumerate(sorted_procs[:20], 1):
                name = p['name'][:40]
                total = p['total']
                user = p['user']
                kernel = p['kernel']
                thread_count = len(p['threads'])
                f.write(f"  {i:<4} {name:<40} {total:>9.1f}% {user:>9.1f}% {kernel:>9.1f}% {thread_count:>8}\n")
            
            # 条形图
            f.write("\n  📊 CPU 占用分布（前15）\n")
            for i, p in enumerate(sorted_procs[:15], 1):
                name = p['name'][:30]
                total = p['total']
                f.write(f"  {draw_bar(f'{i:2}. {name}', total, max_cpu, 38)}\n")
            f.write("\n")

        # ============================================================
        # 7. 所有进程完整列表
        # ============================================================
        if data['processes']:
            sorted_procs = sorted(data['processes'], key=lambda x: x['total'], reverse=True)
            
            write_section_header(f, "📋 所有进程完整列表（按 CPU 降序）", '=')
            f.write(f"\n  {'进程名':<45} {'PID':>8} {'总CPU':>10} {'用户':>10} {'内核':>10} {'缺页次数':>14}\n")
            f.write(f"  {'-' * 101}\n")
            
            for p in sorted_procs:
                name = p['name'][:45]
                pid = p['pid']
                total = p['total']
                user = p['user']
                kernel = p['kernel']
                
                # 格式化缺页信息
                if p['minor_faults'] > 0 or p['major_faults'] > 0:
                    fault_str = f"minor:{p['minor_faults']} major:{p['major_faults']}"
                else:
                    fault_str = "-"
                
                f.write(f"  {name:<45} {pid:>8} {total:>9.1f}% {user:>9.1f}% {kernel:>9.1f}% {fault_str:>14}\n")
            
            f.write(f"\n  📊 共计 {len(sorted_procs)} 个进程\n\n")

        # ============================================================
        # 8. 进程线程详情（Top 15）
        # ============================================================
        if data['processes']:
            sorted_procs = sorted(data['processes'], key=lambda x: x['total'], reverse=True)
            
            write_section_header(f, "📋 进程线程详情（Top 15 CPU 占用进程）", '=')
            
            shown = 0
            for p in sorted_procs:
                if shown >= 15:
                    break
                if p['total'] == 0 and shown > 5:
                    continue
                
                f.write(f"\n  📦 {p['name']} (PID: {p['pid']})\n")
                f.write(f"     总 CPU: {p['total']:>6.1f}%  |  用户: {p['user']:>6.1f}%  |  内核: {p['kernel']:>6.1f}%\n")
                
                if p['minor_faults'] > 0 or p['major_faults'] > 0:
                    f.write(f"     缺页: minor:{p['minor_faults']} 次, major:{p['major_faults']} 次\n")

                if p['threads']:
                    sorted_threads = sorted(p['threads'], key=lambda x: x['total'], reverse=True)
                    active_threads = [t for t in sorted_threads if t['total'] > 0]
                    display_threads = active_threads if len(active_threads) > 0 else sorted_threads[:10]
                    
                    if display_threads:
                        f.write(f"     线程数: {len(p['threads'])} (显示 {len(display_threads)} 个)\n")
                        f.write(f"     {'线程名':<35} {'TID':>8} {'总CPU':>10} {'用户':>10} {'内核':>10}\n")
                        f.write(f"     {'-' * 75}\n")
                        for t in display_threads[:10]:
                            tname = t['name'][:35]
                            f.write(f"     {tname:<35} {t['tid']:>8} {t['total']:>9.1f}% {t['user']:>9.1f}% {t['kernel']:>9.1f}%\n")
                    else:
                        f.write(f"     线程数: {len(p['threads'])} (无活跃线程)\n")
                else:
                    f.write(f"     无子线程信息\n")
                shown += 1

            f.write("\n")

        # ============================================================
        # 9. 分析建议
        # ============================================================
        write_section_header(f, "💡 分析建议")
        
        suggestions = []
        
        # 检查负载
        if data['load_avg']:
            la = data['load_avg']
            if la['1min'] > 10:
                suggestions.append(f"🔴 系统负载较高 (1分钟 {la['1min']:.2f})，可能存在性能瓶颈")
        
        # 检查 CPU 总占用
        if data['total_cpu'].get('total', 0) > 80:
            suggestions.append(f"🔴 CPU 总占用超过 80% ({data['total_cpu']['total']:.1f}%)，系统繁忙")
        
        # 检查高 CPU 进程
        if data['processes']:
            sorted_procs = sorted(data['processes'], key=lambda x: x['total'], reverse=True)
            high_cpu_procs = [p for p in sorted_procs if p['total'] > 20]
            for p in high_cpu_procs[:3]:
                suggestions.append(f"⚠️  进程 {p['name']} 占用 {p['total']:.1f}% CPU，建议关注")

            # 检查进程数量
            if len(data['processes']) > 100:
                suggestions.append(f"⚠️  进程数量较多 ({len(data['processes'])} 个)，可能影响系统性能")
        
        # 检查 IO 等待
        if data['total_cpu'].get('iowait', 0) > 10:
            suggestions.append(f"⚠️  IO 等待较高 ({data['total_cpu']['iowait']:.1f}%)，可能存在磁盘 I/O 瓶颈")
        
        # 检查中断
        irq_total = data['total_cpu'].get('irq', 0) + data['total_cpu'].get('softirq', 0)
        if irq_total > 10:
            suggestions.append(f"⚠️  中断占用较高 ({irq_total:.1f}%)，可能存在硬件中断频繁")
        
        if suggestions:
            for s in suggestions:
                f.write(f"  {s}\n")
        else:
            f.write("  🟢 系统运行状态良好，未发现明显性能问题\n")
        
        f.write("\n")

        # ============================================================
        # 10. 报告结束
        # ============================================================
        f.write("=" * 80 + "\n")
        f.write("✅ 报告生成完成\n")

    return out_path

def main():
    try:
        pattern = "dumpsys_cpuinfo_*.txt"
        latest_file = find_latest_file(SOURCE_DIR, pattern)
        print(f"✅ 找到最新文件: {latest_file}")

        print("📂 正在解析 CPU 数据...")
        data = parse_cpuinfo(latest_file)

        print("📝 正在生成分析报告...")
        out_path = generate_report(data, latest_file, OUTPUT_DIR)

        print(f"🎉 报告已生成: {out_path}")
        print(f"📊 解析到 {data['process_count']} 个进程，{data['thread_count']} 个线程")

    except Exception as e:
        print(f"❌ 发生错误: {e}")

if __name__ == "__main__":
    main()