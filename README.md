Android 系统 Dumpsys 分析工具

一组 Python 脚本，用于分析 Android 系统 dumpsys 命令输出的日志（内存、GPU、CPU、存储）。自动查找最新日志文件，解析并生成详细的可读分析报告。

脚本概览

脚本输入文件模式输出内容dumpsys_meminfo.pydumpsys_meminfo_*.txt内存使用报告（RSS/PSS 进程排行、OOM 分类、柱状图）dumpsys_gpuinfo.pydumpsys_gpuinfo_*.txtGPU 驱动信息、每 PID 内存占用、应用详情、工作统计dumpsys_cpuinfo.pydumpsys_cpuinfo_*.txtCPU 负载均值、进程/线程 CPU 占用、缺页信息、柱状图disk.pyapp_size_*.txt存储分区使用情况、应用大小/数据/缓存细分、Top 消费者 

使用方法

1. 准备日志文件

将对应的 dumpsys_*.txt 或 app_size_*.txt 文件放入 SOURCE_DIR 指定的目录。

在 Android 设备上获取这些日志的典型命令：

adb shell dumpsys meminfo > dumpsys_meminfo_YYYYMMDD_HHMMSS.txt adb shell dumpsys gpuinfo > dumpsys_gpuinfo_YYYYMMDD_HHMMSS.txt adb shell dumpsys cpuinfo > dumpsys_cpuinfo_YYYYMMDD_HHMMSS.txt adb shell dumpsys diskstats > app_size_YYYYMMDD_HHMMSS.txt 

2. 配置路径

编辑每个脚本顶部的配置区域：

SOURCE_DIR = "/storage/emulated/0/文档/日志/状态" # 日志文件存放目录 OUTPUT_DIR = "/storage/emulated/0/文档/文档/txt/内容分析" # 报告输出目录 

根据你的实际环境调整路径。

3. 运行脚本

无需额外依赖——仅使用 Python 标准库（os, re, glob, json, datetime, subprocess）。

python3 dumpsys_meminfo.py python3 dumpsys_gpuinfo.py python3 dumpsys_cpuinfo.py python3 disk.py 

每个脚本会打印进度信息和最终输出文件路径。

4. 查看报告

生成的报告为纯文本文件（.txt），命名如：

dumpsys_meminfo_analysis_20261011_143022.txt dumpsys_gpuinfo_analysis_20261011_143030.txt dumpsys_cpuinfo_analysis_20261011_143035.txt storage_dumpsys_diskstats_analysis_20261011_143040.txt 

包含格式化的表格、柱状图和分析建议。

输出示例（摘录）

内存报告（dumpsys_meminfo.py）：

📊 内存分析报告 - 2026-10-11 14:30:00 -------------------------------------------------- 🖥️ 总体内存概况 总 RAM: 5.69 GB 空闲 RAM: 892.1 MB 已用 RAM: 4.81 GB 📌 内存状态: 🟡 内存较为紧张，可清理缓存 🏆 RSS 进程占用排行 (Top 15，总占用 4.32 GB) 1 com.android.systemui 287.4 MB 6.5% 2 com.google.android.gms 245.1 MB 5.5% ... 

GPU 报告（dumpsys_gpuinfo.py）：

🎮 GPU 分析报告 - 2026-10-11 14:30:05 -------------------------------------------------- 📦 驱动信息 稳定驱动 : v@0511.0 GLES加载 : 12 次 (失败: 0) Vulkan加载 : 3 次 (失败: 0) ... 🖥️ GPU内存使用 💾 全局总内存 : 512.00 MB 📊 进程总占用 : 312.48 MB 📈 内存使用率 : 61.0% 

CPU 报告（dumpsys_cpuinfo.py）：

📊 CPU 分析报告 - 2026-10-11 14:31:00 -------------------------------------------------- 📈 系统负载 1分钟 : 3.52 5分钟 : 2.89 15分钟 : 2.41 📌 状态: 🟢 负载平稳 🖥️ 总体 CPU 占用 总占用 : 68.2% 用户态 : 42.1% 内核态 : 26.1% 

存储报告（disk.py）：

📊 存储分析报告 - 2026-10-11 14:32:00 -------------------------------------------------- 📈 空间使用概况 📂 数据空间: 总容量: 109.23 GB 已使用: 85.67 GB (78.4%) 可 用: 23.57 GB (21.6%) 状 态: ⚠️ 紧张 🏆 Top 10 数据占用最多的应用 1. com.tencent.mm 数据: 12.34 GB (应用: 456.7 MB, 缓存: 890.2 MB) 2. com.android.chrome 数据: 3.21 GB ... 

自定义

你可以在每个脚本中修改以下常量：

SOURCE_DIR – 输入日志目录。

OUTPUT_DIR – 输出报告目录。

OOM_CN_MAP（meminfo）– OOM 分类的中文名称。

GPU_STATE_CN（gpuinfo）– GPU 状态描述。

CPU_STATE_CN（cpuinfo）– CPU 状态描述。

TOP_N 值 – 排行榜显示的数量（目前硬编码在函数内部，可根据需要调整）。

注意事项

所有脚本假定输入文件的格式与 Android dumpsys 命令输出的格式完全一致。若格式发生变化，解析可能失败。

disk.py 使用 json.loads 解析包名列表；请确保输入文件包含有效的 JSON 数组。

dumpsys_gpuinfo.py 可选地调用 ps 命令通过 PID 获取包名；在 Linux/macOS 上正常工作，Windows 可能需要调整。

报告以 UTF-8 纯文本生成，可在任何文本编辑器或终端中打开。

许可

本项目仅供学习和诊断用途，欢迎自由使用和修改。

Android System Dumpsys Analyzer

A collection of Python scripts to analyze Android system dumpsys outputs (memory, GPU, CPU, storage). These scripts automatically find the latest log files, parse them, and generate detailed human-readable analysis reports.

Scripts Overview

ScriptInput PatternOutput Descriptiondumpsys_meminfo.pydumpsys_meminfo_*.txtMemory usage report (RSS/PSS per process, OOM categories, bar charts)dumpsys_gpuinfo.pydumpsys_gpuinfo_*.txtGPU driver info, memory usage per PID, application details, work statisticsdumpsys_cpuinfo.pydumpsys_cpuinfo_*.txtCPU load average, per-process/thread CPU usage, faults, bar chartsdisk.pyapp_size_*.txtStorage partition usage, app sizes/data/cache breakdown, top consumers 

How to Use

1. Prepare Log Files

Place the corresponding dumpsys_*.txt or app_size_*.txt files in the directory specified by SOURCE_DIR.

Typical commands to obtain these logs on an Android device:

adb shell dumpsys meminfo > dumpsys_meminfo_YYYYMMDD_HHMMSS.txt adb shell dumpsys gpuinfo > dumpsys_gpuinfo_YYYYMMDD_HHMMSS.txt adb shell dumpsys cpuinfo > dumpsys_cpuinfo_YYYYMMDD_HHMMSS.txt adb shell dumpsys diskstats > app_size_YYYYMMDD_HHMMSS.txt 

2. Configure Paths

Edit each script’s configuration section at the top:

SOURCE_DIR = "/storage/emulated/0/文档/日志/状态" # where your log files are stored OUTPUT_DIR = "/storage/emulated/0/文档/文档/txt/内容分析" # where reports will be saved 

Adjust these paths to match your environment.

3. Run the Scripts

No extra dependencies – only standard Python libraries are used (os, re, glob, json, datetime, subprocess).

python3 dumpsys_meminfo.py python3 dumpsys_gpuinfo.py python3 dumpsys_cpuinfo.py python3 disk.py 

Each script will print progress messages and the final output file path.

4. View Reports

Generated reports are plain text files with .txt extension, named like:

dumpsys_meminfo_analysis_20261011_143022.txt dumpsys_gpuinfo_analysis_20261011_143030.txt dumpsys_cpuinfo_analysis_20261011_143035.txt storage_dumpsys_diskstats_analysis_20261011_143040.txt 

They contain formatted tables, bar charts, and analysis suggestions.

Sample Output (Excerpt)

Memory Report (dumpsys_meminfo.py):

📊 内存分析报告 - 2026-10-11 14:30:00 -------------------------------------------------- 🖥️ 总体内存概况 总 RAM: 5.69 GB 空闲 RAM: 892.1 MB 已用 RAM: 4.81 GB 📌 内存状态: 🟡 内存较为紧张，可清理缓存 🏆 RSS 进程占用排行 (Top 15，总占用 4.32 GB) 1 com.android.systemui 287.4 MB 6.5% 2 com.google.android.gms 245.1 MB 5.5% ... 

GPU Report (dumpsys_gpuinfo.py):

🎮 GPU 分析报告 - 2026-10-11 14:30:05 -------------------------------------------------- 📦 驱动信息 稳定驱动 : v@0511.0 GLES加载 : 12 次 (失败: 0) Vulkan加载 : 3 次 (失败: 0) ... 🖥️ GPU内存使用 💾 全局总内存 : 512.00 MB 📊 进程总占用 : 312.48 MB 📈 内存使用率 : 61.0% 

CPU Report (dumpsys_cpuinfo.py):

📊 CPU 分析报告 - 2026-10-11 14:31:00 -------------------------------------------------- 📈 系统负载 1分钟 : 3.52 5分钟 : 2.89 15分钟 : 2.41 📌 状态: 🟢 负载平稳 🖥️ 总体 CPU 占用 总占用 : 68.2% 用户态 : 42.1% 内核态 : 26.1% 

Storage Report (disk.py):

📊 存储分析报告 - 2026-10-11 14:32:00 -------------------------------------------------- 📈 空间使用概况 📂 数据空间: 总容量: 109.23 GB 已使用: 85.67 GB (78.4%) 可 用: 23.57 GB (21.6%) 状 态: ⚠️ 紧张 🏆 Top 10 数据占用最多的应用 1. com.tencent.mm 数据: 12.34 GB (应用: 456.7 MB, 缓存: 890.2 MB) 2. com.android.chrome 数据: 3.21 GB ... 

Customization

You can modify the following constants in each script:

SOURCE_DIR – input log directory.

OUTPUT_DIR – output report directory.

OOM_CN_MAP (meminfo) – OOM category Chinese names.

GPU_STATE_CN (gpuinfo) – GPU state descriptions.

CPU_STATE_CN (cpuinfo) – CPU state descriptions.

TOP_N values – number of items shown in rankings (currently hardcoded, adjustable inside functions).

Notes

All scripts assume the input files follow the exact format produced by dumpsys on Android. If the format changes, parsing may fail.

The disk.py script uses json.loads for package lists; ensure the input file contains valid JSON arrays.

The dumpsys_gpuinfo.py script optionally calls ps command to resolve package names by PID; it works on Linux/macOS but may require adjustments on Windows.

Reports are generated in UTF-8 plain text; they can be opened in any text editor or terminal.

License

This project is provided for educational and diagnostic purposes. Feel free to use and modify.
