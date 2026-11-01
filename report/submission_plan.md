# 2026 嵌赛（AMD 自主选题赛道）提交形态与差距分析

> 来源：赛事官方赛题说明（AMD 自主选题赛道，4 页，3.3 节）。
> 结论先行：**功能已经够，最终形态要按“工程包 + 技能包 + 设计报告”重做包装**。
> **2026-10-25 状态：提交结构、技能包、设计报告、LLM 协作记录均已成包；
> 本文件保留为当时的差距分析，下表状态列已按 10-25 更新。**

---

## 1. 比赛硬要求（与我们有直接关系的）

| 项 | 要求 | 我们的状态 |
|---|---|---|
| 组别 | 大三 → **初级组**；可用 Zynq-7000 | ✅ ZYNQ-7020 |
| 工具 | Vivado/Vitis **2026.1** | ✅ 2026.1 |
| 板级 | **必须板上跑通并提供实测输出** | ✅ 已有大量实测 |
| 提交 | 工程源码 + 仿真/验证 + 综合/实现报告 + 上板工程/脚本/实测 + 可复现构建 | ✅ 已按结构整理（10-25 整包同步） |
| 技能包 | `skill/` + README；**通用 PYNQ Skill 加分** | ✅ 3 个通用 Skill + README |
| 大模型协作 | 提交提示词、模型回答、自我纠错轨迹、智能体工作流 | ✅ `llm_collaboration.md` + 脱敏会话节选 |
| 设计报告 | 背景/创新、框图、软硬件划分、优化前后对比、LLM 协作、Skill 提炼、复现 | ✅ `design_report.md` |
| 目录命名 | **目录/文件名纯英文小写/数字/下划线/连字符，不得中文/空格/特殊字符** | ✅ 包内 0 个非 ASCII 文件名 |
| 开源 | 强烈建议 GitHub/Gitee，MIT 或 Apache-2.0 | ⚠️ MIT 已附；数据集/模型的许可在 README 单独声明，不随包再分发 |

**评分权重**：

| 评测项 | 权重 | 我们的抓手 |
|---|---:|---|
| 创新性与应用价值 | **30** | 双 PL CNN 的商用车 DMS；Face ID/遮挡/录像/哈希/活体 |
| 性能与资源优化效果 | 20 | 32→64 位 AXI、Haar minSize、CNN 2.4/4.7ms、资源/时序前后对比 |
| 功能正确性与完整性 | 20 | 逐位比对、盲验证、80 项 DMS 测试、板上实测 |
| 大模型协作与技能包 | **15** | **待提炼** |
| 文档质量与可复现性 | **15** | 开发日志很全，但未成“从零复现”的 README/报告 |

> 初级组考察侧重“逻辑设计、状态机、时序约束、接口协议”，**报告不能只讲 AI**；
> 要把 AXI/VDMA、HLS、时序、状态机、板级调试写成主线，AI 是应用亮点。

---

## 2. 最终形态建议（推荐）

**作品名（展示用）**：PYNQ 双 CNN 商用车驾驶员状态监测（DMS）
**一句话**：在 ZYNQ-7020 上用两个自研 HLS CNN + 完整 PS 事件/遥测/录像链，
做可演示、可复现、逐位可验的 DMS；同时沉淀一套**通用 PYNQ 加速器集成/验证技能包**。

### 2.1 提交仓库结构（全英文命名）

```text
dms_zynq7020/
├── README.md                 # 项目简介 + 从零复现步骤 + 目录对照
├── src/
│   ├── hls/                  # eye_cnn / context_cnn / img_preproc / video_box / eye_pipeline
│   ├── ps/                   # PYNQ/src（Python 驱动、demo、采集、遥测、录像）
│   └── vivado/               # BD Tcl、add/refresh/build 脚本
├── sim/                      # C 仿真、PC 单测、金标准向量、逐位比对结果
├── build/                    # build_ip / build_csim / build_bitstream + 综合/实现报告
├── board/                    # bit/hwh、run.sh、demo 命令、实测输出、截图
├── data/                     # 小样本测试数据 + manifest（不放大数据集）
├── skill/                    # ★ 通用 PYNQ 技能包（见 §3）
└── report/
    ├── design_report.md      # 设计报告（按评分项组织）
    ├── llm_collaboration.md  # 提示词/回答/自我纠错/智能体工作流
    ├── skill_extraction.md   # 技能包提炼过程与边界
    └── llm_transcript/       # 脱敏后的会话记录（可压缩/节选）
```

- 所有目录/文件名**只用小写英文、数字、`_`、`-`**；
  中文只放在文件正文里。
- 当前工作工程保留不动；提交包用**复制+重命名**生成，避免破坏主线。
- `data/` 不放 CEW/MRL/板上 2190 行全量（许可/体积）；放小样本 + 采集/下载脚本。
- 许可证：代码 **MIT 或 Apache-2.0**；SFace/OpenCV/CEW/MRL 的许可在 README 里单独声明，
  不随仓库再分发受限数据/模型。

---

## 3. 技能包（15% + PYNQ 加分的关键）

技能包必须**不与本队 DMS 题目绑定**，换题/换板仍可用。建议 3 个：

### Skill A：PYNQ HLS 加速器集成与逐位验证

- 内容：
  - `add_<ip>.tcl` 模板：扩 `ps7_0_axi_periph` / SmartConnect、补 `Mxx_ACLK/ARESETN`、
    连 `Sxx_AXI`、分配地址、**生成网表后宽度断言**；
  - `refresh_<ip>.tcl`：`update_ip_catalog` + `upgrade_ip` + ROM 文件大小比对，
    防止“综合了旧权重”；
  - PS 驱动模板：MMIO 偏移、64 位指针、`ap_ctrl_hs` 轮询、CMA 释放；
  - 逐位验证：随机 int8 输入，硬件 vs `quant_ref.py` 金标准，`!=` 比对。
- 已验证：eye_cnn / context_cnn 两套；context 20/20 板上逐位相同。
- 适用场景/失效条件：任何 HLS IP 挂到 PYNQ；不适用于 `ap_ctrl_none` 自由运行 IP
  （标量锁存问题）。

### Skill B：PYNQ VDMA 稳定采集/显示

- 内容：
  - 帧撕裂检测与**双读一致**采集；
  - MM2S/DisplayCtrl **启动顺序**（先 DisplayCtrl、后 reset+start MM2S）；
  - `display_selftest` 满屏色块自检；
  - 退出必须 `vdma.stop()`，否则 DMA 持续写已释放内存。
- 已验证：OV5640 + VDMA + HDMI；采集/显示/撕裂 A/B。
- 适用场景/失效条件：PS 中转显示、独立 disp_buf；不适用于 PL 直出 OSD。

### Skill C：Vivado 资源/时序/复现报告自动化

- 内容：
  - 从 `impl_1` 报告自动提取 WNS/WHS、LUT/FF/BRAM/DSP；
  - 与基线对比生成 Markdown 表；
  - 校验 bit/hwh md5、IP revision、生成物宽度；
  - 一键复现脚本（Vivado 2026.1 batch）。
- 已验证：本次 context 集成的 WNS +0.134/资源表就是这样得到的。
- 适用场景：任何 Vivado 工程；失效条件：报告路径/版本变化需改解析。

每项 `skill/<name>/README.md` 写清：**适用场景、使用方法、已验证效果、
失效条件、从哪些失败中总结**（评分明确要求）。

---

## 4. 大模型协作记录（15%）

比赛要求：**提示词、模型回答、自我纠错轨迹、智能体工作流**。

现有素材：
- 当前会话原始记录：`<llm_session>.jsonl`（约 21MB）；
- 历史会话：`13d4b5e6...jsonl`、`da088d9e...jsonl` 等；
- 开发日志 / `docs/` 里有大量“判断依据/踩坑/自我纠错”。

提交建议：
1. `report/llm_collaboration.md`：按“任务 → 提示词 → 模型回答 → 验证/纠错 → 结论”
   摘 8~12 个代表性片段，例如：
   - native 人脸检测 160 vs 320 的定位与修正；
   - IP 锁定/旧权重（`refresh_*_ip.tcl`）的发现；
   - SmartConnect NUM_SI 扩口的宽度校验；
   - VDMA 启动顺序导致黑屏；
   - context 右耳手机 margin 抖动与阈值/release；
   - 逐位比对的假 PASS（激活全 0）。
2. `report/llm_transcript/`：脱敏后的 JSONL/文本（去掉路径中的用户名、IP、密钥），
   可只保留关键会话并压缩。
3. 工作流说明：Plan → Explore → Implement → Test → Review → Fix；
   哪些环节由模型完成、哪些由人拍板、如何验证模型输出。

⚠️ 不要只贴“问答截图”；评委要看**自我纠错轨迹**：哪条结论被实测推翻、如何改。

---

## 5. 设计报告（15%）建议结构

1. **选题背景与创新点**：商用车 DMS 的实际问题；单目 + 7020 无 DPU 的约束；
   双自研 HLS CNN + 完整证据链。
2. **设计原理与功能框图**：按实际数据流（OV5640→VDMA→DDR→PS→两个 CNN→事件→
   遥测/录像/OSD），标清 PL/PS 边界、AXI 地址、DDR 搬运。
3. **软硬件划分依据**：为什么眼态/上下文放 PL；为什么上下文用 PS 裁剪（不改
   `img_preproc`）；为什么 Face ID 异步低频。
4. **优化过程（前后对比表）**：
   - 模式0 AXI 32→64 位：10.70→8.88 ms；
   - Haar minSize 20→30：168.5→122.6 ms，无脸循环 138.8→13.45 ms；
   - CNN：eye 2.33 ms / context 4.56 ms；
   - 资源/时序：context 前后 LUT 51.5→66.2%、BRAM 33.6→58.2%、
     DSP 39.1→63.6%、WNS +0.228→+0.134；
   - 系统：context off 9.9 FPS / on 7.5 FPS（如实写）。
5. **功能正确性**：C 仿真逐位、板上 20/20、PERCLOS 盲验证、DMS 80 项、
   哈希链/录像、遮挡/离岗。
6. **大模型协作**：摘要 + 指向 `llm_collaboration.md`。
7. **技能包提炼**：从哪些失败中总结、如何验证、边界。
8. **复现说明**：从零步骤、工具版本、IP repo、bit/hwh、板端命令、预期输出。
9. **局限**：单目、低光闭眼、object 侧向数据偏置、FAR/FRR 未认证、RTC。

---

## 6. 时间线调整（重要）

原计划 W2 主要做 margin/真实场景；现在必须把 **Skill/报告/提交结构**提前：

| 周 | 原计划 | 调整后 |
|---|---|---|
| W1 | context 集成 | ✅ 已完成；再补 cigarette/left/right/down 验收 |
| W2 | margin/真实场景 | **50% 提交包骨架 + Skill A/B/C**；50% 验收/可选 FPS |
| W3 | 端到端验证 | **设计报告 + LLM 记录 + 复现脚本 + 提交包**；演示视频 |
| W4 | 彩排 | 只修 bug；从零复现一次；提交 |

**取舍**：object 补数据/FPS ROI tracking 都是“锦上添花”；
Skill + 报告 + 复现是 30% 的硬分，优先级更高。

---

## 7. 立即可做的清单

1. **建提交包骨架**（英文名，从当前工程复制/重命名，不破坏主线）：
   `README.md`、`src/`、`sim/`、`build/`、`board/`、`data/`、`skill/`、`report/`。
2. **写 `skill/README.md` + 3 个 Skill**：优先 A（HLS 集成/逐位）和 B（VDMA），
   它们已有完整脚本和实测证据；C 是报告自动化，最容易补。
3. **整理 `report/llm_collaboration.md`**：从当前 JSONL 摘 8~12 段，
   标出“模型建议 → 实测结果 → 修正”。
4. **写 `report/design_report.md`**：先用 `docs/materials/答辩材料骨架.md` 的四张表，
   再补“优化前后对比表”和“复现步骤”。
5. **处理命名/许可**：提交包内全英文；代码 MIT/Apache-2.0；
   CEW/MRL/SFace 只写获取方式，不打包。
6. **复现验证**：换一个干净目录，按 README 从零跑
   `build_csim → build_ip → build_bitstream → 板端 demo`。

> 结论：**不要再加新功能**。当前功能足以支撑 30% 创新 + 20% 性能 + 20% 正确性；
> 把 15% Skill + 15% 文档/复现做扎实，才是最终形态的胜负手。
