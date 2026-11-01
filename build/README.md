# Build / Reproduce

## 工具

- Vivado / Vitis **2026.1**（推荐；2025.2 也可，报告里注明）
- Vitis 的 `v++` 路径：`<Vitis>/bin/v++.bat`
- Python 3.8（板端）/ 3.11（PC 训练）

## ⚠️ Windows 路径长度（先看这条）

Vivado 2018.x~2026.1 在 Windows 上仍受 **MAX_PATH 260 字符**限制。本工程的
`context_cnn` 生成物里有很深的 `.gen/.../Pipeline_VITIS_LOOP_155_1_...bkb.dat`，
把包解压到太长的工作目录（例如很深的 Desktop/OneDrive 路径）会在
`generate_target` 报：

```text
ERROR: [Common 17-680] Path length exceeds 260-Byte maximum allowed by Windows
```

**对策（任选其一）**：
1. 解压到短路径，例如 `C:\dms_zynq7020`（推荐，实测可完整构建）；
2. 用 `subst X: C:\长路径\dms_zynq7020` 映射成短盘符；
3. Windows 10/11 启用长路径（组策略 `LongPathsEnabled=1`），Vivado 是否生效
   取决于版本，**不保证**。

## 顺序（不要颠倒）

```bash
# 1) HLS 语义先过（不需要 Vitis；csim_stubs 兜底）
cd src/hls && sh build_csim.sh all

# 2) 打包 IP 到 src/vivado/project/ip_repo
cd src/hls
.\build_ip.bat eye_cnn
.\build_ip.bat img_preproc
.\build_ip.bat video_box
.\build_ip.bat context_cnn
REM 前面加 .\ 是为了兼容设置了 NoDefaultCurrentDirectoryInExePath 的机器

# 3) ★ 把所有新 IP 升级进 BD 并生成一次 target（干净 checkout 必做）
cd ../vivado/project
vivado -mode batch -source ../refresh_all_ip.tcl

# 4) 重新出 bitstream（会 generate_target + synth + impl + 时序检查）
vivado -mode batch -source ../build_bitstream.tcl
```

`build_ip.bat` 里的 `IP_REPO` 已指向 `..\vivado\project\ip_repo`；
`VPP` 默认 `C:\AMDDesignTools\2026.1\Vitis\bin\v++.bat`，路径不同时改文件顶部。

## 关键约束

- **不要删 `.gen/`**：删了会丢 BD wrapper 的编译顺序，综合可能报
  `module not found`。`build_bitstream.tcl` 现在会在 `generate_target` 后
  自动检查并补登记 `design_1_wrapper.v`（干净 checkout 首次打开时 Vivado
  会丢掉这个文件条目，这是实际踩过的断链）。
- **每次 `build_ip` 之后**必须让 BD 里的 IP 实例升级。单独改一个 kernel 时
  跑对应的 `src/vivado/refresh_*_ip.tcl`；干净 checkout / 一次重建多个时
  跑 `refresh_all_ip.tcl`。**四个实例必须一起解锁后再 `generate_target`**，
  否则 BD 整体仍锁、产物为空，单个脚本会误报 FAIL。
- `build_bitstream.tcl` 会检查 `WNS/WHS`；**为负时不要烧板**。
  失败先看 `impl_1/design_1_wrapper_timing_summary_routed.rpt` 的
  `clk_fpga_0` 路径。
- `src/vivado/*.tcl` 的 `proj_dir` 不再写死绝对路径：**脚本同级的 `project/`
  优先，否则用 `[pwd]`**。从 `src/vivado/project/` 或 `src/vivado/` 运行都可以
  （已在包内用 Tcl 实测四种工作目录都能定位到 `ov5640_hdmi.xpr`）。
  `build_ip.bat` 的 `IP_REPO` 先找开发布局 `..\V2_ov5640_hdmi\ip_repo`，
  不存在则用包布局 `..\vivado\project\ip_repo`。`build_bitstream.tcl` 按脚本
  自身位置推导输出目录，默认写到仓库根 `board/`（可用 `PYNQ_BOARD_DIR` 覆盖）。

## ✅ 干净目录复现实测（2026-10-25，当前交付包）

在**空目录** `C:\dmsclean\dms_zynq7020`（短路径，见上面的 MAX_PATH 说明）里，
从包内源码完整跑通。这是**换了 10-24 ContextNet 权重之后**的验证：

| 步骤 | 结果 |
|---|---|
| `.\build_ip.bat`（4 个） | eye 1m27s / img_preproc 56s / video_box 32s / context 1m10s，全部装入包内 `ip_repo` |
| `refresh_all_ip.tcl` | 4 个实例 locked 1→0；**47 个 ROM 副本校验 0 问题**（升级前 47 个不匹配） |
| `build_bitstream.tcl` | **SYNTHESIS OK / IMPLEMENTATION OK / TIMING MET**，Vivado 退出码 **0** |
| 时序 | **WNS +0.274 / WHS +0.034 ns**；`clk_fpga_0` **+0.274**、`cam_pclk` +8.403 |
| 资源 | LUT **38,087（71.59%）** / FF 41,800（39.29%） / BRAM 81.5（58.21%） / DSP 140（63.64%） |
| 导出 | `board/design_1.bit` + `.hwh`；bit 与 impl 产物 md5 一致（`de23540f…`） |

完整日志摘要（每条命令的输出与资源读数）：`reports/cleanroom_20261025.txt`。

**与包内预置产物的关系**：包内 `board/design_1.bit` 是 **10-24 工程内构建、已上板
逐位验证**的 `75a9dee4…`；本次干净目录重建得到 `de23540f…`，**md5 不同是 Vivado
嵌入时间戳导致的正常现象**，功能一致性由两处保证：HLS 4 用例逐位 C 仿真 +
47 个 ROM 校验。资源/时序与预置报告（LUT 38,134 / WNS +0.186）差异在
place/route 运行噪声量级。

本次复现额外修掉的断链（已写回本包）：

- `build_bitstream.tcl` / `export_overlay.tcl` 的 `pynq_dir` 原来只认开发布局
  `../PYNQ`；包布局下会写到不存在的 `src/vivado/PYNQ` 并报错。
  现在：开发布局写 `PYNQ/`，包布局写包根 `board/`，并支持 `PYNQ_BOARD_DIR` 覆盖。
- Windows 260 字符路径限制（见上），已在包内实测并给出三种对策。

## 干净目录复现实测（2026-10-18）

把提交包复制到一个**空目录**（删掉 `__pycache__`、`src/hls/build`、`.gen/.runs/.cache`，
并把预置的 `board/design_1.bit/.hwh` 移到一边），按上面的顺序执行：

| 步骤 | 结果 |
|---|---|
| `sh build_csim.sh all` | 5/5 kernel 逐位 PASS |
| PS 单测 | canonical 19 / context_logic 13 / context_collect 23 / collect 36 / collect_run 27 / telemetry_proto 18 / face_id PASS |
| ML 单测 | context_model 6 / context_dataset 9 / quant_ref 18 / model 8 / export 9 / context_spec 6 / calibrate_margin 7 |
| 上位机 | dashboard 24 / replay_state 5 |
| `build_ip.bat`（4 个） | 全部成功，装入 `ip_repo` |
| `refresh_all_ip.tcl` | 4 个实例 locked 1→0，生成 47 个 ROM 产物，校验全匹配 |
| `build_bitstream.tcl` | synth OK / impl OK / **WNS +0.100 / WHS +0.050**，导出新 bit+hwh |
| 新构建资源 | LUT 35,188 (66.14%) / FF 41,784 (39.27%) / BRAM 81.5 (58.21%) / DSP 140 (63.64%) |

⚠️ 上表是 **2026-10-18** 那次干净目录复现的记录（当时预置报告为
LUT 35,236 / WNS +0.134）。此后 **2026-10-24** 为 ContextNet 换权重重新出了
bitstream，包内预置报告与 `board/design_1.bit` 已更新为
**LUT 38,134（71.68%）/ WNS +0.186 / WHS +0.026**；两次构建的综合策略与
工具状态不同，资源差异不是功能差异。功能一致性一律以 **HLS 逐位 C 仿真**
与**板上逐位比对**为准。

复现中修掉的两个断链（已写回本包）：

1. 干净 checkout 里 `build_ip` 会重装 IP，BD 的 4 个实例变 locked；
   只跑单个 `refresh_*_ip.tcl` 时其余 3 个仍锁着 → `generate_target` 不产出。
   新增 `refresh_all_ip.tcl`：先升级全部 4 个实例，再统一 reset/generate。
2. 干净 checkout 首次打开工程时，`$PGENDIR/.../hdl/design_1_wrapper.v`
   尚不存在，Vivado 会把该文件条目从 `sources_1` 丢掉；`generate_target`
   写出 `.v` 后没有人重新登记 → synth 报 `module 'design_1_wrapper' not found`。
   `build_bitstream.tcl` 现在会检测并 `add_files` 补登记。

另外补齐了包内遗漏的 BD 自动生成 IP
`design_1_ps7_0_axi_periph_imp_auto_pc_0/…xci`（缺它时 Vivado 打开工程会
报 `Could not find an IP with XCI file by name`，虽能自动迁移，但会多一次警告）。

## 报告

`build/reports/` 含本次实测：

- `design_1_wrapper_utilization_placed.rpt`
- `design_1_wrapper_timing_summary_routed.rpt`

用 `skill/vivado_report_automation/scripts/parse_vivado_reports.py` 可以把它们
转成 Markdown 表（见 `report/design_report.md` §4）。
