# PYNQ Dual-CNN Driver Monitoring System (ZYNQ-7020)

> 2026 全国大学生嵌入式芯片与系统设计竞赛（AMD 自主选题赛道，初级组）
> 作品：基于 ZYNQ-7020 + PYNQ 的商用车驾驶员状态监测（DMS）。

## 1. 作品简介

在 **ZYNQ-7020** 上实现一套可演示、可复现、逐位可验的 DMS：

- **眼态 CNN（EyeNet-3C）**：32×32 灰度 → 闭/睁/无效，PERCLOS + 微睡眠报警；
- **上下文 CNN（ContextNet）**：48×48 人脸 ROI → 头姿 4 类 + 手持物 4 类，
  用于分心、抽烟、打电话；
- **Face ID（可选）**：libface 5 点 + SFace 128-D，异步低频；多成员/授权名单；
  **支持正/左/右多姿态模板**（约 30°，按身份取最大余弦）；
- **OSD 身份**：PL 字模直接在 HDMI 右上角画 `DRIVER` / `STRANGER`（+ 陌生人红框）；
- **DMS 事件**：镜头遮挡、离岗、疲劳、分心、phone_call、smoking；
- **软件报警**：四类事件合并状态机 → OSD 红框闪烁 + 终端 + 上位机横幅/声音；
- **证据链**：时间戳 OSD + 事件 pre/post 录像（MJPEG）+ SHA-256 哈希链；
  **陌生人抓拍**单独一条链（30 s 限频，只拍“可验证人脸且未授权”）；
- **上位机**：TCP 遥测 + PyQt 实时面板（视频/PERCLOS/眼态/身份/上下文/报警）；
- **活体**：眨眼/转头挑战，区分“照片/视频欺骗”。

核心工程点：两个自研 HLS 加速器、int8 定点契约、PL/PS 软硬件划分、
VDMA 稳定采集/显示、逐位金标准比对、板级时序/资源收敛。

## 2. 硬件与工具

| 项 | 型号/版本 |
|---|---|
| 开发板 | 领航者 V2，**xc7z020clg400-2** |
| 摄像头 | OV5640（DVP，640×480 BGR565→888） |
| 显示 | HDMI（VTC + DVI/TMDS） |
| 工具 | Vivado / Vitis **2026.1** |
| 板端 | PYNQ 2.7，Python 3.8，OpenCV |
| 训练（PC） | PyTorch CPU，numpy，OpenCV |

## 3. 关键指标（实测）

| 项 | 结果 |
|---|---|
| 眼 CNN 延迟 | **2.42 ms/眼**（PL @100 MHz） |
| Context CNN 延迟 | **4.73 ms/次**（PL，含 MMIO 轮询） |
| Context 逐位验证 | **20/20 随机 int8 输入与 numpy 金标准相同** |
| 头姿 macro-recall | **0.9284**（交付模型，5 会话选模验证集；10-18 两折为 0.9457/0.9457） |
| 手持物 macro-recall | **0.6737**（同上；10-18 两折为 0.6661/0.7511） |
| Context 误报抑制 | 正脸手空留出 76 帧：旧模型 **76/76** → 新模型 **0/76** |
| 真烟召回（留出） | **31/33 = 93.9%**（旧模型 33/33） |
| PERCLOS 盲验证 | 正常段 **0 报警**；疲劳段 **6/6** 真闭眼段 |
| 主循环 | context 关 **9.9 FPS**；context 开 **7.4~7.8 FPS** |
| 整设计资源（10-24 交付版） | LUT **71.68%** / FF 38.96% / BRAM **58.21%** / DSP 63.64% |
| 时序（10-24 交付版） | **WNS +0.186 ns / WHS +0.026 ns**（clk_fpga_0） |

## 4. 目录结构

```text
.
├── src/
│   ├── hls/       # eye_cnn / context_cnn / img_preproc / video_box / eye_pipeline
│   ├── ps/        # PYNQ Python：驱动、demo、采集、遥测、录像、上位机
│   ├── ml/        # PC 训练/量化/导出（PyTorch + numpy）
│   └── vivado/    # BD Tcl、Vivado 工程、ip_repo
├── sim/           # C 仿真、PC 单测、逐位比对入口
├── build/         # 构建脚本 + impl_1 资源/时序报告
├── board/         # bit/hwh、run.sh、实测截图/记录
├── data/          # 小样本测试数据（不包含完整数据集）
├── skill/         # ★ 3 个通用 PYNQ Skill（比赛要求）
└── report/        # 设计报告、大模型协作记录、Skill 提炼
```

## 5. 复现步骤（从零）

### 5.1 PC 侧验证

```bash
# HLS C 仿真（不需要 Vitis；使用 hls/csim_stubs）
cd src/hls && sh build_csim.sh all

# PS 单元测试（PC，Python 3.11 或板端 3.8）
# 需要 numpy + OpenCV；下列命令在装有 opencv-python 的环境里执行。
cd ../ps && python tests/test_canonical.py
python tests/test_context_logic.py
python tests/test_context_collect.py
python tests/test_collect.py
python tests/test_collect_run.py
python tests/test_telemetry_proto.py
python tests/test_face_id_logic.py
python tests/test_dms_face.py
python tests/test_alert_logic.py
python tests/test_stranger_snapshot.py
python tests/test_enroll_pose.py
python upper/tests/test_dashboard_logic.py
```

### 5.2 构建 bitstream

> ⚠️ **解压到短路径**（如 `C:\dms_zynq7020`）。Vivado 在 Windows 上受 260 字符
> 路径限制，路径过深时 `generate_target` 会报 `[Common 17-680] Path length
> exceeds 260-Byte`；详见 `build/README.md`。

```bash
# 1) 打包 HLS IP（会安装到 src/vivado/project/ip_repo）
cd src/hls
.\build_ip.bat context_cnn
.\build_ip.bat eye_cnn
.\build_ip.bat img_preproc
.\build_ip.bat video_box
REM 前面的 .\ 兼容 NoDefaultCurrentDirectoryInExePath；无参运行会建全部 4 个

# 2) ★ 把新 IP 全部升级进 BD（干净 checkout 必须先做）
#    单个 refresh_<kernel>_ip.tcl 只升级自己；其余 3 个仍锁着时 BD 整体仍锁，
#    generate_target 不产出。refresh_all_ip.tcl 一次升级 4 个再统一生成。
cd ../vivado/project
vivado -mode batch -source ../refresh_all_ip.tcl

# 3) 出 bitstream（脚本会自动 generate_target 并补登记 BD wrapper）
vivado -mode batch -source ../build_bitstream.tcl
```

`build_bitstream.tcl` 会做：generate_target → synth → impl → 时序检查 →
导出 `design_1.bit/.hwh` 到 `board/`。**WNS/WHS 为负时不要烧板。**

### 5.3 板上运行

```bash
# 把 board/design_1.bit/.hwh 和 src/ps/ 拷到板上 PYNQ 目录
cd ~/jupyter_notebooks/PYNQ/src

# 眼态/PERCLOS + PL OSD + 时间戳 + 上下文
bash run.sh demo_eye_perclos.py \
  --osd --classifier cnn --osd-native-haar \
  --face-detect-scale 2 --face-stride 8 --face-fallback \
  --context --context-stride 5 \
  --osd-time --osd-tz-hours 8 --frames 0 --interval 0.1
```

`--osd` 走 PL OSD（眼框/眼态/PERCLOS/时间/DRIVER）；context 的 pose/object
在终端和上位机显示。`--context` 默认关，不传时与旧行为逐位相同。

### 5.4 数据采集（可选）

```bash
bash run.sh collect_eye_patches.py --context --face-fallback --subject <name> \
  --auto-protocol 'normal:30,left:20,right:20,low:20,pause:4,phone:30,pause:4,smoke:30,pause:4,other:20'
```

采集脚本的协议、标签守卫、去重/去污规则见 `src/ps/collect_logic.py` 与
`report/reference/`。

## 6. 数据与模型许可（重要）

- 本仓库**不包含** CEW / MRL 数据集，也不包含 SFace ONNX、libfacedetection
  二进制、板端采集的完整数据；只放 `data/samples/` 的小样本。
- CEW/MRL 请按各自官方许可获取；SFace/OpenCV 模型按上游许可使用。
- **Face ID 是可选支路**：没有上述模型时，眼态/PERCLOS/context/DMS 事件
  仍可运行（启动时 Face ID 初始化失败会降级，不会带崩主循环）。

## 7. 技能包（比赛要求）

`skill/` 下 3 个**通用 PYNQ Skill**（不与本题绑定）：

1. `pynq_hls_accel_integration/` —— HLS IP 集成、IP 锁定/旧权重、逐位验证；
2. `pynq_vdma_stable_capture/` —— 帧撕裂、CPU 中转显示、MM2S 启动顺序、DMA 退出；
3. `vivado_report_automation/` —— 资源/时序/bit-hwh 校验与报告表生成。

每项 README 写明适用场景、使用方法、验证效果、失效条件与来源失败。

## 8. 设计报告与大模型协作

- `report/design_report.md` —— 背景/创新、框图、软硬件划分、优化前后对比、
  正确性、复现、局限；
- `report/llm_collaboration.md` —— 提示词/模型回答/自我纠错轨迹；
- `report/skill_extraction.md` —— 技能包提炼过程与边界；
- `report/reference/` —— context CNN 设计/训练/上板细节。

## 9. 已知局限

- 单目摄像头无法可靠区分“抢方向盘”和“弯腰捡东西”（需要 CAN/方向盘转矩）；
- 真实低光闭眼仍受单眼低对比度限制（默认双眼规则；单眼规则会抬误报）；
- 手持物头跨会话/侧向数据偏置，`other` 是 catch-all；当前用 margin 弃权；
- Face ID 阈值是小样本工程值，**不是商用 FAR/FRR/PAD 认证**；
- 板载 RTC 不准，每次上电需校时；量产应加 NTP/DS3231；
- context 开启时主循环约 7.5 FPS（320 Haar 开销），未做 face ROI tracking。

## 10. 许可证

代码采用 **MIT License**（见 `LICENSE`）。数据集/第三方模型不在本仓库许可范围内，
按其上游许可使用。
