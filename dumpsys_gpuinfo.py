#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import glob
import subprocess
from datetime import datetime

# ========== 配置区 ==========
SOURCE_DIR = "/storage/emulated/0/文档/日志/状态"
OUTPUT_DIR = "/storage/emulated/0/文档/文档/txt/内容分析"
# =============================

# GPU 状态中文注释
GPU_STATE_CN = {
    'GLES': 'OpenGL ES图形接口',
    'Vulkan': 'Vulkan图形API',
    'ANGLE': 'ANGLE翻译层(WebGL)',
    'createdGlesContext': '已创建GLES上下文',
    'createdVulkanDevice': '已创建Vulkan设备',
    'createdVulkanSwapchain': '已创建Vulkan交换链',
    'cpuVulkanInUse': 'CPU端Vulkan使用中',
    'falsePrerotation': '预旋转功能禁用',
    'gles1InUse': 'GLES 1.x使用中',
    'angleInUse': 'ANGLE翻译层使用中',
}

def format_size(bytes_val):
    """格式化字节大小"""
    if bytes_val == 0:
        return "0 B"
    if bytes_val < 1024:
        return f"{bytes_val} B"
    kb = bytes_val / 1024
    if kb < 1024:
        return f"{kb:.2f} KB"
    mb = kb / 1024
    if mb < 1024:
        return f"{mb:.2f} MB"
    gb = mb / 1024
    if gb < 1024:
        return f"{gb:.2f} GB"
    tb = gb / 1024
    return f"{tb:.2f} TB"

def format_time_ns(ns):
    """格式化纳秒时间为可读格式"""
    if ns == 0:
        return "0"
    if ns < 1000:
        return f"{ns:.0f} ns"
    us = ns / 1000
    if us < 1000:
        return f"{us:.2f} μs"
    ms = us / 1000
    if ms < 1000:
        return f"{ms:.2f} ms"
    s = ms / 1000
    if s < 60:
        return f"{s:.2f} s"
    m = s / 60
    if m < 60:
        return f"{m:.2f} min"
    h = m / 60
    if h < 24:
        return f"{h:.2f} h"
    d = h / 24
    return f"{d:.2f} d"

def format_time_ns_short(ns):
    """简短格式（用于图表）"""
    if ns == 0:
        return "0"
    if ns < 1000:
        return f"{ns:.0f}ns"
    us = ns / 1000
    if us < 1000:
        return f"{us:.1f}μs"
    ms = us / 1000
    if ms < 1000:
        return f"{ms:.1f}ms"
    s = ms / 1000
    if s < 60:
        return f"{s:.1f}s"
    m = s / 60
    if m < 60:
        return f"{m:.1f}m"
    h = m / 60
    if h < 24:
        return f"{h:.1f}h"
    d = h / 24
    return f"{d:.1f}d"

def format_size_short(bytes_val):
    """简短格式（用于图表）"""
    if bytes_val == 0:
        return "0"
    if bytes_val < 1024:
        return f"{bytes_val}B"
    kb = bytes_val / 1024
    if kb < 1024:
        return f"{kb:.1f}K"
    mb = kb / 1024
    if mb < 1024:
        return f"{mb:.1f}M"
    gb = mb / 1024
    if gb < 1024:
        return f"{gb:.2f}G"
    tb = gb / 1024
    return f"{tb:.2f}T"

def draw_bar(label, value, max_value, width=40, is_time=False):
    """绘制横向条形图"""
    if max_value == 0:
        return f"{label}: (0)"
    ratio = min(value / max_value, 1.0)
    filled = int(ratio * width)
    bar = "█" * filled + "░" * (width - filled)
    if is_time:
        return f"{label}: {bar} {format_time_ns_short(value)}"
    else:
        return f"{label}: {bar} {format_size_short(value)}"

def parse_hex_value(s):
    """解析十六进制值"""
    if not s or s == '0x0':
        return 0
    try:
        return int(s, 16) if s.startswith('0x') else int(s)
    except:
        return 0

def get_package_name(pid):
    """通过PID获取包名"""
    try:
        cmd = f"ps -p {pid} -o NAME="
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=2)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except:
        pass
    return "未知"

def find_latest_file(directory, pattern):
    """在目录中查找符合模式的最新文件"""
    files = glob.glob(os.path.join(directory, pattern))
    if not files:
        raise FileNotFoundError(f"在 {directory} 中未找到匹配 {pattern} 的文件")
    latest = max(files, key=os.path.getmtime)
    return latest

def parse_gpuinfo(filepath):
    """解析 dumpsys gpuinfo 文件"""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        lines = content.split('\n')

    data = {
        'driver_info': {},
        'gpu_memory': [],
        'app_info': [],
        'gpu_work': [],
        'global_total': 0,
        'app_count': 0,
        'error_count': 0,
        'parse_errors': [],
    }

    # 正则表达式
    proc_mem_re = re.compile(r'^Proc\s+(\d+)\s+total:\s+(\d+)$')
    global_total_re = re.compile(r'^Global total:\s+(\d+)$')
    app_section_re = re.compile(r'^appPackageName\s*=\s*(.+)$')
    
    current_app = None
    in_app_section = False
    in_gpu_work = False
    error_count = 0

    for line in lines:
        line = line.rstrip()
        if not line:
            # 空行可能表示应用段结束
            if in_app_section and current_app:
                if current_app.get('package'):
                    data['app_info'].append(current_app)
                current_app = None
                in_app_section = False
            continue

        # ---- 驱动信息 ----
        if line.startswith('Stable Game Driver:'):
            data['driver_info']['stable_driver'] = line.split(':', 1)[1].strip()
        elif line.startswith('Pre-release Game Driver:'):
            data['driver_info']['pre_release_driver'] = line.split(':', 1)[1].strip()
        elif line.startswith('driverPackageName'):
            data['driver_info']['driver_package'] = line.split('=', 1)[1].strip() if '=' in line else ''
        elif line.startswith('driverVersionName'):
            data['driver_info']['driver_version_name'] = line.split('=', 1)[1].strip() if '=' in line else ''
        elif line.startswith('driverVersionCode'):
            data['driver_info']['driver_version_code'] = line.split('=', 1)[1].strip() if '=' in line else ''
        elif line.startswith('driverBuildTime'):
            data['driver_info']['driver_build_time'] = line.split('=', 1)[1].strip() if '=' in line else ''
        elif line.startswith('glLoadingCount'):
            try:
                data['driver_info']['gl_loading_count'] = int(line.split('=', 1)[1].strip())
            except:
                data['driver_info']['gl_loading_count'] = 0
        elif line.startswith('glLoadingFailureCount'):
            try:
                data['driver_info']['gl_loading_failure'] = int(line.split('=', 1)[1].strip())
            except:
                data['driver_info']['gl_loading_failure'] = 0
        elif line.startswith('angleLoadingCount'):
            try:
                data['driver_info']['angle_loading_count'] = int(line.split('=', 1)[1].strip())
            except:
                data['driver_info']['angle_loading_count'] = 0
        elif line.startswith('angleLoadingFailureCount'):
            try:
                data['driver_info']['angle_loading_failure'] = int(line.split('=', 1)[1].strip())
            except:
                data['driver_info']['angle_loading_failure'] = 0
        elif line.startswith('vkLoadingCount'):
            try:
                data['driver_info']['vk_loading_count'] = int(line.split('=', 1)[1].strip())
            except:
                data['driver_info']['vk_loading_count'] = 0
        elif line.startswith('vkLoadingFailureCount'):
            try:
                data['driver_info']['vk_loading_failure'] = int(line.split('=', 1)[1].strip())
            except:
                data['driver_info']['vk_loading_failure'] = 0
        elif line.startswith('vulkanVersion'):
            try:
                data['driver_info']['vulkan_version'] = int(line.split('=', 1)[1].strip())
            except:
                data['driver_info']['vulkan_version'] = 0
        elif line.startswith('cpuVulkanVersion'):
            try:
                data['driver_info']['cpu_vulkan_version'] = int(line.split('=', 1)[1].strip())
            except:
                data['driver_info']['cpu_vulkan_version'] = 0
        elif line.startswith('glesVersion'):
            try:
                data['driver_info']['gles_version'] = int(line.split('=', 1)[1].strip())
            except:
                data['driver_info']['gles_version'] = 0
        elif line.startswith('glDriverLoadingTime:'):
            val = line.split(':', 1)[1].strip()
            if val:
                data['driver_info']['gl_loading_time'] = val
        elif line.startswith('vkDriverLoadingTime:'):
            val = line.split(':', 1)[1].strip()
            if val:
                data['driver_info']['vk_loading_time'] = val

        # ---- GPU内存快照 ----
        m = global_total_re.match(line)
        if m:
            data['global_total'] = int(m.group(1))
            continue
            
        m = proc_mem_re.match(line)
        if m:
            pid = int(m.group(1))
            mem = int(m.group(2))
            data['gpu_memory'].append({'pid': pid, 'memory_bytes': mem})
            continue

        # ---- 应用信息 ----
        m = app_section_re.match(line)
        if m:
            # 保存之前的应用
            if in_app_section and current_app and current_app.get('package'):
                data['app_info'].append(current_app)
            
            current_app = {'package': m.group(1).strip()}
            in_app_section = True
            continue

        # 解析应用详细信息
        if in_app_section and current_app is not None:
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                if key == 'driverVersionCode':
                    current_app['driver_version_code'] = value
                elif key == 'cpuVulkanInUse':
                    current_app['cpu_vulkan_in_use'] = int(value) if value and value.isdigit() else 0
                elif key == 'falsePrerotation':
                    current_app['false_prerotation'] = int(value) if value and value.isdigit() else 0
                elif key == 'gles1InUse':
                    current_app['gles1_in_use'] = int(value) if value and value.isdigit() else 0
                elif key == 'angleInUse':
                    current_app['angle_in_use'] = int(value) if value and value.isdigit() else 0
                elif key == 'createdGlesContext':
                    current_app['created_gles_context'] = int(value) if value and value.isdigit() else 0
                elif key == 'createdVulkanDevice':
                    current_app['created_vulkan_device'] = int(value) if value and value.isdigit() else 0
                elif key == 'createdVulkanSwapchain':
                    current_app['created_vulkan_swapchain'] = int(value) if value and value.isdigit() else 0
                elif key == 'vulkanApiVersion':
                    current_app['vulkan_api_version'] = value
                elif key == 'vulkanDeviceFeaturesEnabled':
                    current_app['vulkan_features'] = value
                elif key == 'vulkanInstanceExtensions':
                    current_app['vk_instance_ext'] = value if value else ''
                elif key == 'vulkanDeviceExtensions':
                    current_app['vk_device_ext'] = value if value else ''
                elif key == 'vulkanEngineNames':
                    current_app['vk_engine_names'] = value if value else ''

        # ---- GPU工作信息 ----
        if line.startswith('GPU work information.'):
            in_gpu_work = True
            continue
            
        if in_gpu_work and line and not line.startswith('gpu_id'):
            # 解析 GPU 工作数据
            parts = line.split()
            if len(parts) >= 4:
                try:
                    # 检查是否有错误标记
                    error_marker = ''
                    if '[errors:' in line:
                        m = re.search(r'\[errors:(\d+)\]', line)
                        if m:
                            error_count += int(m.group(1))
                            data['error_count'] += int(m.group(1))
                            error_marker = f" [errors:{m.group(1)}]"
                            # 去除错误标记后重新解析
                            clean_line = re.sub(r'\[errors:\d+\]\s*', '', line)
                            parts = clean_line.split()
                            if len(parts) < 4:
                                continue
                    
                    gpu_id = int(parts[0])
                    uid = int(parts[1])
                    active = int(parts[2])
                    inactive = int(parts[3])
                    data['gpu_work'].append({
                        'gpu_id': gpu_id,
                        'uid': uid,
                        'active_ns': active,
                        'inactive_ns': inactive,
                        'total_ns': active + inactive,
                        'error_marker': error_marker
                    })
                except Exception as e:
                    data['parse_errors'].append(str(e))

    # 保存最后一个应用
    if in_app_section and current_app and current_app.get('package'):
        data['app_info'].append(current_app)

    data['app_count'] = len(data['app_info'])
    return data

def write_section_header(f, title, char='-', width=80):
    """写入章节标题"""
    f.write(char * width + "\n")
    f.write(f"{title}\n")
    f.write(char * width + "\n")

def generate_report(data, source_file, output_dir):
    """生成 GPU 分析报告"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_filename = f"dumpsys_gpuinfo_analysis_{timestamp}.txt"
    out_path = os.path.join(output_dir, out_filename)

    os.makedirs(output_dir, exist_ok=True)

    with open(out_path, 'w', encoding='utf-8') as f:
        # ============================================================
        # 1. 报告标题
        # ============================================================
        f.write("=" * 80 + "\n")
        f.write(f"🎮 GPU 分析报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"📁 数据来源: {os.path.basename(source_file)}\n")
        f.write("=" * 80 + "\n\n")

        # ============================================================
        # 2. 驱动信息
        # ============================================================
        di = data['driver_info']
        write_section_header(f, "📦 驱动信息 (Driver Information)")
        
        f.write(f"  稳定驱动      : {di.get('stable_driver', 'N/A (不支持)' if 'unsupported' not in str(di) else '不支持')}\n")
        f.write(f"  预发布驱动    : {di.get('pre_release_driver', 'N/A (不支持)' if 'unsupported' not in str(di) else '不支持')}\n")
        f.write(f"  驱动包名      : {di.get('driver_package', 'N/A')}\n")
        f.write(f"  驱动版本      : {di.get('driver_version_name', 'N/A')}\n")
        f.write(f"  驱动版本码    : {di.get('driver_version_code', 'N/A')}\n")
        if di.get('driver_build_time'):
            f.write(f"  驱动构建时间  : {di.get('driver_build_time')}\n")
        
        # 加载统计
        f.write(f"\n  📊 加载统计 (Loading Statistics):\n")
        f.write(f"    GLES加载     : {di.get('gl_loading_count', 0):>8} 次  (失败: {di.get('gl_loading_failure', 0)})  [{GPU_STATE_CN['GLES']}]\n")
        f.write(f"    ANGLE加载    : {di.get('angle_loading_count', 0):>8} 次  (失败: {di.get('angle_loading_failure', 0)})  [{GPU_STATE_CN['ANGLE']}]\n")
        f.write(f"    Vulkan加载   : {di.get('vk_loading_count', 0):>8} 次  (失败: {di.get('vk_loading_failure', 0)})  [{GPU_STATE_CN['Vulkan']}]\n")
        
        # 加载时间
        if di.get('gl_loading_time'):
            f.write(f"\n  ⏱️  GLES加载时间: {di.get('gl_loading_time')}\n")
        if di.get('vk_loading_time'):
            f.write(f"  ⏱️  Vulkan加载时间: {di.get('vk_loading_time')}\n")
        
        # API版本
        f.write(f"\n  📌 API版本 (API Versions):\n")
        vulkan_ver = di.get('vulkan_version', 0)
        cpu_vulkan_ver = di.get('cpu_vulkan_version', 0)
        gles_ver = di.get('gles_version', 0)
        
        if vulkan_ver > 0:
            major = (vulkan_ver >> 22) & 0x3FF
            minor = (vulkan_ver >> 12) & 0x3FF
            patch = vulkan_ver & 0xFFF
            f.write(f"    Vulkan版本   : {major}.{minor}.{patch} (0x{vulkan_ver:08x})\n")
        else:
            f.write(f"    Vulkan版本   : 不支持\n")
        
        if cpu_vulkan_ver > 0:
            f.write(f"    CPU Vulkan   : 0x{cpu_vulkan_ver:08x}\n")
        else:
            f.write(f"    CPU Vulkan   : 不支持\n")
            
        if gles_ver > 0:
            f.write(f"    GLES版本     : 0x{gles_ver:08x}\n")
        else:
            f.write(f"    GLES版本     : 不支持\n")
        f.write("\n")

        # ============================================================
        # 3. GPU内存使用
        # ============================================================
        if data['gpu_memory']:
            sorted_mem = sorted(data['gpu_memory'], key=lambda x: x['memory_bytes'], reverse=True)
            total_mem = sum(p['memory_bytes'] for p in sorted_mem)
            
            write_section_header(f, "🖥️  GPU内存使用 (GPU Memory Usage)")
            f.write(f"  💾 全局总内存  : {format_size(data['global_total'])}\n")
            f.write(f"  📊 进程总占用  : {format_size(total_mem)}\n")
            
            # 计算使用率
            if data['global_total'] > 0:
                usage_ratio = (total_mem / data['global_total']) * 100
                f.write(f"  📈 内存使用率  : {usage_ratio:.1f}%\n")
                if usage_ratio > 100:
                    f.write(f"  ⚠️  内存使用超限: 超出 {usage_ratio - 100:.1f}% (可能存在内存泄漏或统计误差)\n")
            
            f.write(f"  📱 进程数量    : {len(sorted_mem)}\n\n")
            
            # 内存排行
            f.write("  📈 Top 15 GPU内存占用进程 (Top 15 GPU Memory Usage by Process):\n")
            f.write(f"  {'排名':<6} {'进程PID':>8} {'包名/进程名':<30} {'内存占用':>14} {'占比':>10}\n")
            f.write(f"  {'-' * 74}\n")
            
            max_mem = sorted_mem[0]['memory_bytes'] if sorted_mem else 1
            for i, p in enumerate(sorted_mem[:15], 1):
                mem = p['memory_bytes']
                ratio = (mem / total_mem * 100) if total_mem > 0 else 0
                # 尝试获取包名
                pkg_name = get_package_name(p['pid'])
                f.write(f"  {i:<4} {p['pid']:>8} {pkg_name:<30} {format_size(mem):>14} {ratio:>9.1f}%\n")
            
            # 条形图
            if len(sorted_mem) > 1:
                f.write("\n  📊 内存占用分布 (Memory Distribution):\n")
                for i, p in enumerate(sorted_mem[:10], 1):
                    label = f"PID {p['pid']}"
                    f.write(f"  {draw_bar(f'{i:2}. {label}', p['memory_bytes'], max_mem, 38, False)}\n")
            
            # 内存统计
            if len(sorted_mem) > 1:
                avg_mem = total_mem / len(sorted_mem)
                median_mem = sorted_mem[len(sorted_mem)//2]['memory_bytes'] if sorted_mem else 0
                f.write(f"\n  📊 统计 (Statistics):\n")
                f.write(f"    平均占用  : {format_size(avg_mem)}\n")
                f.write(f"    中位占用  : {format_size(median_mem)}\n")
                f.write(f"    最大占用  : {format_size(max_mem)}\n")
                f.write(f"    最小占用  : {format_size(sorted_mem[-1]['memory_bytes'])}\n")
            f.write("\n")

        # ============================================================
        # 4. GPU应用信息
        # ============================================================
        if data['app_info']:
            write_section_header(f, "📱 GPU应用信息 (GPU Application Information)", '=')
            f.write(f"  应用总数 (Total Apps): {len(data['app_info'])}\n\n")
            
            # 统计分类
            gles_apps = [a for a in data['app_info'] if a.get('created_gles_context', 0) > 0]
            vk_apps = [a for a in data['app_info'] if a.get('created_vulkan_device', 0) > 0]
            vk_swapchain = [a for a in data['app_info'] if a.get('created_vulkan_swapchain', 0) > 0]
            angle_apps = [a for a in data['app_info'] if a.get('angle_in_use', 0) > 0]
            gles1_apps = [a for a in data['app_info'] if a.get('gles1_in_use', 0) > 0]
            
            f.write(f"  📊 使用统计 (Usage Statistics):\n")
            f.write(f"    使用 GLES   : {len(gles_apps):>4} 个  [{GPU_STATE_CN['GLES']}]\n")
            f.write(f"    使用 GLES 1 : {len(gles1_apps):>4} 个  [{GPU_STATE_CN['gles1InUse']}]\n")
            f.write(f"    使用 Vulkan : {len(vk_apps):>4} 个  [{GPU_STATE_CN['Vulkan']}]\n")
            f.write(f"    使用交换链  : {len(vk_swapchain):>4} 个  [{GPU_STATE_CN['createdVulkanSwapchain']}]\n")
            f.write(f"    使用 ANGLE  : {len(angle_apps):>4} 个  [{GPU_STATE_CN['ANGLE']}]\n")
            f.write("\n")
            
            # 详细列表 - 显示所有应用
            f.write("  📋 完整应用列表 (All Applications):\n")
            f.write(f"  {'包名':<45} {'GLES':>6} {'GLES1':>8} {'Vulkan':>8} {'交换链':>8} {'引擎':>20}\n")
            f.write(f"  {'-' * 97}\n")
            
            for app in sorted(data['app_info'], key=lambda x: x.get('package', '')):
                pkg = app.get('package', '')[:45]
                gles = '✓' if app.get('created_gles_context', 0) > 0 else '✗'
                gles1 = '✓' if app.get('gles1_in_use', 0) > 0 else '✗'
                vk = '✓' if app.get('created_vulkan_device', 0) > 0 else '✗'
                swap = '✓' if app.get('created_vulkan_swapchain', 0) > 0 else '✗'
                engine = app.get('vk_engine_names', '').strip(' ,')[:20]
                f.write(f"  {pkg:<45} {gles:>6} {gles1:>8} {vk:>8} {swap:>8} {engine:>20}\n")
            f.write("\n")

        # ============================================================
        # 5. GPU工作信息
        # ============================================================
        if data['gpu_work']:
            sorted_work = sorted(data['gpu_work'], key=lambda x: x['active_ns'], reverse=True)
            total_active = sum(w['active_ns'] for w in sorted_work)
            total_inactive = sum(w['inactive_ns'] for w in sorted_work)
            total_time = total_active + total_inactive
            
            write_section_header(f, "⚡ GPU工作信息 (GPU Work Information)", '=')
            f.write(f"  错误数量 (Errors)      : {data['error_count']}\n")
            f.write(f"  工作条目数 (Entries)   : {len(sorted_work)}\n")
            f.write(f"  总活跃时间 (Active)    : {format_time_ns(total_active)}\n")
            f.write(f"  总空闲时间 (Inactive)  : {format_time_ns(total_inactive)}\n")
            f.write(f"  总时间 (Total)         : {format_time_ns(total_time)}\n")
            
            if total_time > 0:
                utilization = (total_active / total_time) * 100
                f.write(f"  GPU利用率 (Utilization): {utilization:.1f}%\n")
                
                # 利用率评级
                if utilization > 80:
                    util_status = "🔴 高负载"
                elif utilization > 50:
                    util_status = "🟡 中等负载"
                elif utilization > 20:
                    util_status = "🟢 低负载"
                else:
                    util_status = "⚪ 空闲"
                f.write(f"  负载状态 (Status)      : {util_status}\n")
            
            f.write("\n")
            
            # Top 10 活跃应用
            f.write("  📈 Top 10 GPU活跃应用 (Top 10 GPU Active Applications by Time):\n")
            f.write(f"  {'排名':<6} {'UID':>8} {'活跃时间':>18} {'空闲时间':>18} {'利用率':>10}\n")
            f.write(f"  {'-' * 64}\n")
            
            max_active = sorted_work[0]['active_ns'] if sorted_work else 1
            for i, w in enumerate(sorted_work[:10], 1):
                active = w['active_ns']
                inactive = w['inactive_ns']
                total = active + inactive
                utilization = (active / total * 100) if total > 0 else 0
                error_mark = w.get('error_marker', '')
                f.write(f"  {i:<4} {w['uid']:>8} {format_time_ns(active):>18} {format_time_ns(inactive):>18} {utilization:>9.1f}%{error_mark}\n")
            
            # 条形图
            f.write("\n  📊 GPU活跃时间分布 (GPU Active Time Distribution):\n")
            for i, w in enumerate(sorted_work[:10], 1):
                label = f"UID {w['uid']}"
                f.write(f"  {draw_bar(f'{i:2}. {label}', w['active_ns'], max_active, 35, True)}\n")
            
            # 按UID统计汇总
            uid_summary = {}
            for w in data['gpu_work']:
                uid = w['uid']
                if uid not in uid_summary:
                    uid_summary[uid] = {'active': 0, 'inactive': 0}
                uid_summary[uid]['active'] += w['active_ns']
                uid_summary[uid]['inactive'] += w['inactive_ns']
            
            if len(uid_summary) > 10:
                f.write(f"\n  📊 UID汇总 (Top 10 UID Summary):\n")
                sorted_uids = sorted(uid_summary.items(), key=lambda x: x[1]['active'], reverse=True)
                f.write(f"  {'UID':>8} {'活跃时间':>18} {'空闲时间':>18} {'利用率':>10}\n")
                f.write(f"  {'-' * 56}\n")
                for uid, vals in sorted_uids[:10]:
                    total = vals['active'] + vals['inactive']
                    utilization = (vals['active'] / total * 100) if total > 0 else 0
                    f.write(f"  {uid:>8} {format_time_ns(vals['active']):>18} {format_time_ns(vals['inactive']):>18} {utilization:>9.1f}%\n")
            
            f.write("\n")

        # ============================================================
        # 6. 分析建议
        # ============================================================
        write_section_header(f, "💡 分析建议 (Analysis Suggestions)")
        
        suggestions = []
        warnings = []
        infos = []
        
        # 检查驱动状态
        stable_driver = data['driver_info'].get('stable_driver', '')
        if 'unsupported' in stable_driver.lower():
            infos.append("ℹ️  稳定游戏驱动不支持 (Stable Game Driver unsupported)")
        
        # 检查内存使用
        if data['gpu_memory'] and data['global_total'] > 0:
            total_mem = sum(p['memory_bytes'] for p in data['gpu_memory'])
            usage_ratio = (total_mem / data['global_total']) * 100
            if usage_ratio > 100:
                warnings.append(f"⚠️  GPU内存使用超限 ({usage_ratio:.1f}%)，可能存在内存泄漏或统计误差")
            elif usage_ratio > 80:
                suggestions.append(f"🔴 GPU内存使用率较高 ({usage_ratio:.1f}%)，建议检查高内存进程")
            elif usage_ratio > 60:
                infos.append(f"🟡 GPU内存使用率偏高 ({usage_ratio:.1f}%)")
            else:
                infos.append(f"🟢 GPU内存使用正常 ({usage_ratio:.1f}%)")
        
        # 检查应用数量
        if data['app_count'] > 50:
            suggestions.append(f"⚠️  活跃GPU应用较多 ({data['app_count']} 个)，可能消耗较多资源")
        
        # 检查GLES/Vulkan使用情况
        gles_count = sum(1 for a in data['app_info'] if a.get('created_gles_context', 0) > 0)
        vk_count = sum(1 for a in data['app_info'] if a.get('created_vulkan_device', 0) > 0)
        swap_count = sum(1 for a in data['app_info'] if a.get('created_vulkan_swapchain', 0) > 0)
        
        infos.append(f"ℹ️  {vk_count} 个应用使用Vulkan，{gles_count} 个使用GLES")
        if swap_count > 0:
            infos.append(f"ℹ️  {swap_count} 个应用使用Vulkan交换链")
        
        # 检查错误
        if data['error_count'] > 0:
            warnings.append(f"⚠️  检测到 {data['error_count']} 个GPU工作错误，建议检查GPU稳定性")
        
        # 检查GPU利用率
        if data['gpu_work']:
            total_active = sum(w['active_ns'] for w in data['gpu_work'])
            total_inactive = sum(w['inactive_ns'] for w in data['gpu_work'])
            if total_active + total_inactive > 0:
                utilization = (total_active / (total_active + total_inactive)) * 100
                if utilization > 80:
                    warnings.append(f"🔴 GPU利用率较高 ({utilization:.1f}%)，可能存在性能瓶颈")
                elif utilization > 50:
                    infos.append(f"🟡 GPU利用率中等 ({utilization:.1f}%)")
                elif utilization > 20:
                    infos.append(f"🟢 GPU利用率较低 ({utilization:.1f}%)")
                else:
                    infos.append(f"⚪ GPU利用率极低 ({utilization:.1f}%)，系统可能空闲")
        
        # 检查解析错误
        if data.get('parse_errors'):
            warnings.append(f"⚠️  解析时遇到 {len(data['parse_errors'])} 个错误，部分数据可能不完整")
        
        # 输出建议
        if infos:
            f.write("  📌 信息 (Info):\n")
            for s in infos:
                f.write(f"    {s}\n")
            f.write("\n")
        
        if warnings:
            f.write("  ⚠️  警告 (Warnings):\n")
            for s in warnings:
                f.write(f"    {s}\n")
            f.write("\n")
        
        if suggestions:
            f.write("  🔧 建议 (Suggestions):\n")
            for s in suggestions:
                f.write(f"    {s}\n")
            f.write("\n")
        
        if not infos and not warnings and not suggestions:
            f.write("  🟢 GPU运行状态良好，未发现明显问题\n")
            f.write("  🟢 GPU is running normally, no issues detected\n")
        
        f.write("\n")

        # ============================================================
        # 7. 报告结束
        # ============================================================
        f.write("=" * 80 + "\n")
        f.write("✅ 报告生成完成 (Report Generation Complete)\n")

    return out_path

def main():
    try:
        pattern = "dumpsys_gpuinfo_*.txt"
        latest_file = find_latest_file(SOURCE_DIR, pattern)
        print(f"✅ 找到最新文件: {latest_file}")

        print("📂 正在解析 GPU 数据...")
        data = parse_gpuinfo(latest_file)

        print("📝 正在生成分析报告...")
        out_path = generate_report(data, latest_file, OUTPUT_DIR)

        print(f"🎉 报告已生成: {out_path}")
        print(f"📊 解析到 {data['app_count']} 个应用，{len(data['gpu_memory'])} 个GPU内存条目")

    except Exception as e:
        print(f"❌ 发生错误: {e}")

if __name__ == "__main__":
    main()