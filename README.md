中文版

Android Dumpsys 日志解析工具箱

一套用于解析 Android dumpsys 日志的 Python 脚本集合。每个脚本针对特定的子系统（内存、CPU、GPU、存储等），将原始日志转换为结构化、可读的分析报告。

适用于需要快速从 dumpsys 原始输出中提取关键信息的 Android 开发者、测试人员和性能工程师。

工作流程

采集日志 – 在设备上执行对应的 adb 命令，捕获 dumpsys 输出。

保存到目录 – 将日志文件保存到本地文件夹（默认为当前目录）。

运行脚本 – 执行对应子系统的解析脚本。

获取报告 – 脚本生成带时间戳的报告文件，内含解析后的数据。

每个脚本遵循相同的模式：

读取符合特定命名规则的日志文件

解析关键指标

输出清晰可读的报告

前置条件

Python 3.6+

无需外部依赖（所有脚本仅使用 Python 标准库）

Android 设备或模拟器（需开启 adb 调试）

可用脚本

脚本用途输入文件模式
dumpsys_meminfo.py解析内存使用信息dumpsys_meminfo_*.txt
dumpsys_gpuinfo.py解析 GPU 性能数据dumpsys_gpuinfo_*.txt
dumpsys_cpuinfo.py解析 CPU 频率与状态dumpsys_cpuinfo_*.txt
disk.py解析磁盘/存储使用统计disk_*.txt 

欢迎贡献更多脚本，详见下方贡献指南。

快速开始

1. 采集日志

通过 USB 连接设备，执行以下命令。每条命令会保存带时间戳的日志文件，避免覆盖之前的采集结果。

# 内存 adb shell dumpsys meminfo > "dumpsys_meminfo_$(date +%Y%m%d_%H%M%S).txt" # GPU adb shell dumpsys gfxinfo > "dumpsys_gpuinfo_$(date +%Y%m%d_%H%M%S).txt" # CPU adb shell dumpsys cpuinfo > "dumpsys_cpuinfo_$(date +%Y%m%d_%H%M%S).txt" # 存储 adb shell dumpsys diskstats > "disk_$(date +%Y%m%d_%H%M%S).txt" 

⚠️ 重要提示：文件名中的时间戳是必需的。脚本依赖 YYYYMMDD_HHMMSS 格式的时间戳来识别和排序日志文件。缺少时间戳可能导致文件冲突或解析错误。

2. 运行脚本

python3 dumpsys_meminfo.py 

默认情况下，每个脚本扫描当前目录下匹配的日志文件。可通过修改脚本顶部的常量来配置输入/输出路径。

3. 查看报告

报告以带时间戳的文本文件形式保存在输出目录中。示例：

meminfo_report_20261011_143022.txt 

自定义配置

每个脚本顶部都有可配置的常量：

INPUT_DIR – 日志文件所在目录（默认：./）

OUTPUT_DIR – 报告输出目录（默认：./）

文件命名匹配模式

直接用文本编辑器打开脚本修改即可。

添加新脚本

本工具箱设计为可扩展的。要添加新的解析器：

参照现有脚本的模式创建新的 .py 文件

定义输入文件的命名规则

使用标准库实现解析逻辑

更新本 README 的脚本表格

欢迎贡献代码！详情请参阅 CONTRIBUTING.md。

注意事项

脚本期望日志严格按照快速开始部分所示的方式采集。格式差异可能导致解析失败。

disk.py 内部使用 json.loads()，请确保日志文件包含有效的 JSON 结构。

dumpsys_gpuinfo.py 在解析过程中会调用系统 ps 命令。

所有脚本均假设为单设备环境。多设备场景请在 adb 命令中指定序列号。

文件名中的时间戳格式 YYYYMMDD_HHMMSS 是必需的，缺少正确时间戳的文件可能导致脚本拒绝处理或产生异常结果。

许可证

MIT 许可证 — 详见 LICENSE 文件。

English Version

Android Dumpsys Log Parser Toolkit

A collection of Python scripts for parsing Android dumpsys logs into human-readable reports. Each script targets a specific subsystem (memory, CPU, GPU, storage, etc.) and outputs structured analysis results.

Designed for Android developers, testers, and performance engineers who need to quickly extract insights from raw dumpsys output.

How It Works

Collect logs – Run the corresponding adb command on your device to capture dumpsys output.

Save to directory – Place the log files in a local folder (default: current directory).

Run a script – Execute the parser for the subsystem you want to analyze.

Get report – The script generates a timestamped report file with parsed data.

Each script follows the same pattern:

Reads log files matching a specific naming pattern

Parses key metrics

Outputs a clean, readable report

Prerequisites

Python 3.6+

No external dependencies (all scripts use only standard library)

Android device or emulator with adb access enabled

Available Scripts

ScriptPurposeInput Patterndumpsys_meminfo.pyParse memory usage infodumpsys_meminfo_*.txtdumpsys_gpuinfo.pyParse GPU profiling datadumpsys_gpuinfo_*.txtdumpsys_cpuinfo.pyParse CPU frequency/statsdumpsys_cpuinfo_*.txtdisk.pyParse disk/storage usage statsdisk_*.txt 

More scripts welcome — see Contributing below.

Quick Start

1. Collect Logs

Connect your device via USB and run the following commands. Each command saves a timestamped log file to prevent overwriting previous captures.

# Memory adb shell dumpsys meminfo > "dumpsys_meminfo_$(date +%Y%m%d_%H%M%S).txt" # GPU adb shell dumpsys gfxinfo > "dumpsys_gpuinfo_$(date +%Y%m%d_%H%M%S).txt" # CPU adb shell dumpsys cpuinfo > "dumpsys_cpuinfo_$(date +%Y%m%d_%H%M%S).txt" # Disk / Storage adb shell dumpsys diskstats > "disk_$(date +%Y%m%d_%H%M%S).txt" 

⚠️ Important: Timestamps in filenames are required. Scripts rely on the YYYYMMDD_HHMMSS pattern to identify and sort log files. Missing timestamps may cause file collisions or parsing errors.

2. Run a Script

python3 dumpsys_meminfo.py 

By default, each script scans the current directory for matching log files. You can configure input/output paths by editing the constants at the top of each script.

3. View Report

Reports are saved as timestamped text files in the output directory. Example:

meminfo_report_20261011_143022.txt 

Customization

Each script has configurable constants at the top:

INPUT_DIR – Directory containing log files (default: ./)

OUTPUT_DIR – Directory for generated reports (default: ./)

File name patterns for log matching

Open the script in any text editor to adjust these values.

Adding New Scripts

This toolkit is designed to be extensible. To add a new parser:

Create a new .py file following the existing pattern

Define input file naming convention

Implement parsing logic using only standard library

Update this README's script table

Contributions are welcome! See CONTRIBUTING.md for details.

Notes

Scripts expect logs to be captured exactly as shown in the Quick Start section. Format variations may cause parsing errors.

disk.py uses json.loads() internally; ensure your log file contains valid JSON-like structures.

dumpsys_gpuinfo.py calls the system ps command during parsing.

All scripts assume a single-device environment. For multi-device setups, specify the serial number in adb commands.

Timestamp format YYYYMMDD_HHMMSS in filenames is mandatory. Files without proper timestamps may be rejected or produce incorrect results.

License

MIT License — see LICENSE for details.