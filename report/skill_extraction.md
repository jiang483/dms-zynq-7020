# 技能包提炼过程

> 目标：把“本项目里踩过的坑”提炼成**换题/换板仍可用**的 PYNQ Skill，
> 并写清适用场景、使用方法、已验证效果、失效条件与提炼来源。
> 三个 Skill 的代码/模板在 `skill/`。

---

## 1. 提炼方法

```text
失败/观察
  → 复现（最小实验，确认不是偶发）
  → 归因（读生成网表/报告/内存，区分“配置对/内容错”）
  → 泛化（去掉本题的 IP 名/地址/数据，留下条件与判据）
  → 模板（脚本/清单）
  → 在第二个实例上验证（本项目用 eye_cnn + context_cnn 两个 IP）
  → 写失效条件（哪些情况下这个经验不成立）
```

**“在第二个实例上验证”是关键**：只在 context_cnn 上成立的经验，可能只是
这个 IP 的巧合；eye_cnn 与 context_cnn 的位宽/通道/地址都不同，
两者都过才写成 Skill。

---

## 2. Skill A：HLS 加速器集成与逐位验证

| 来源失败/观察 | 提取出的规则 | 验证 |
|---|---|---|
| `add_cam_iic.tcl` 扩 MI 后 `M03_ACLK/ARESETN` 没接，寄存器全 0、IP 不启动、无报错 | 扩 `NUM_MI` 后必须接新 `Mxx_ACLK/ARESETN` | eye_cnn（M04）、img_preproc（M05）、context（M07）三次复现/修复 |
| `build_ip` 后综合仍用旧 IP：实例 LOCKED，ROM 与 ip_repo 不同 | `update_ip_catalog` + `upgrade_ip` + ROM 大小比对 | `refresh_eye_cnn_ip.tcl` / `refresh_context_cnn_ip.tcl`；修复前后 ROM 比对 |
| BD 实例存了 `C_M_AXI_GMEM_DATA_WIDTH=32` 参数覆盖，IP 默认 64 | 从生成 `.hwh`/wrapper 读回实际位宽，不读 GUI | 模式0 10.70→8.88 ms，逐字节等价 PASS |
| 扩 SmartConnect `NUM_SI` 可能重算现有端口位宽 | generate_target 后断言 S00/S01/S02/S03/M00 位宽 | context 集成；第一次断言写错（S01 rdata/S03 32）后修正 |
| `ap_ctrl_none` 的标量只在复位采一次、FIFO 满后 ap_done 不置起 | CNN 一律 `ap_ctrl_hs`；自由运行 IP 用 AXI-Stream/连续流 | eye_cnn/context_cnn 的 ap_done 轮询；img_preproc 的 FIFO 死锁定位 |
| 硬件与 PC 金标准“差不多”但没人能证明 | 随机 int8 输入 + `!=` 逐位比对；用例 logits 不能全相同 | eye_cnn 8 用例、context 4 用例 C 仿真；板上 20/20 |

**边界**：不适用于 `ap_ctrl_none` 自由运行 IP、AXI >64 位、需要新增 PS HP
口的场景（PS7 配置在 BOOT.BIN，PYNQ Overlay 改不了）。

---

## 3. Skill B：VDMA 稳定采集/显示

| 来源失败/观察 | 提取出的规则 | 验证 |
|---|---|---|
| 60 对连续全帧读中 20 对（33%）撕裂，变化带中位 97 行 | 读两遍、逐字节相同才采信；不要用 `S2MM_PARK_PTR`（恒 0） | `tear_check.py` A/B；双读平均 1.5 次、+32 ms（−10.7% FPS） |
| CPU 写 `disp_buf`、MM2S 读另一块，屏幕全黑；地址/回读都对 | 先 `DisplayCtrl.start()`，再 reset+start MM2S；用 `display_selftest` 色块确认 | `display_bisect.py` 4 种配置；用户反馈 1/2/4 有画面 |
| 回读显示缓冲 == 写入帧，仍全黑 | 回读只证明 CPU 写对，不证明 MM2S 送显示 | 满屏色块自检推翻旧结论 |
| 强杀进程后 DMA 仍运行，Jupyter 卡死/HDMI 黑/随机 segfault | 退出必须 `vdma.stop()`、`disp_ctrl.stop()`、释放缓冲；停止用 stop 文件 | 2026-10-03 事故复现；恢复需重启 |
| `setup()` 预填 0.5s 可能填到未初始化 CMA（纯黑） | `wait_valid_frame` 轮询到有效内容，不用固定 sleep | 预填修复；`MIN_VALID_MAX=16` |

**边界**：PL 直出 OSD（MM2S 读 `cap_buf`）是另一条路径；不同帧几何/字节序
需要改 `FRAME_BYTES`/shape。

---

## 4. Skill C：Vivado 资源/时序/复现报告自动化

| 来源失败/观察 | 提取出的规则 | 验证 |
|---|---|---|
| 旧材料写 “BRAM 46”，实际报告 28 tiles（20%） | 所有资源数字从 `impl_1` 报告读，不手抄 | `parse_vivado_reports.py` |
| `build_bitstream.tcl` 的 `[${grp}]` 被 Tcl 当命令替换，bitstream 写完但没导出 | 流程完成 ≠ 时序通过 ≠ 已导出；三步分开检查 | 2026-10-15/10-17 两次事故；脚本用 `format` |
| “bitstream 是新的”无法证明 | 记录 bit/hwh md5、IP revision、ROM 大小 | `check_artifacts.py`；本项目 md5 f06cf... |
| 报告表与实测对不上（Haar 49.4 vs 134~221 ms） | 表格每项标来源/口径；内容相关指标要带“什么图” | 答辩材料 §3 订正 |

**边界**：Vivado 版本/报告布局变化时解析器需更新；md5 只证明文件未变，
不证明功能/时序正确。

---

## 5. 通用性检查（换题/换板）

| 问题 | 回答 |
|---|---|
| 换一个 HLS 网络 | Skill A 的模板只依赖 VLNV/地址/MI-SI 数量，换网络只改 CONFIGURE |
| 换一块 PYNQ 板 | Skill B 只依赖 VDMA/frame store/MM2S 语义；改 `FRAME_BYTES` 即可 |
| 换一个 Vivado 工程 | Skill C 只依赖报告文件名/列位置；换版本时改解析 |
| 不换题但换演讲者 | 三个 README 都写了“使用方法 + 失效条件”，不需要知道 DMS 细节 |

---

## 6. 提交与验证

- `skill/<name>/README.md`：每个 Skill 的完整说明；
- `skill/<name>/scripts/`：可直接复制的模板/脚本；
- `skill/pynq_hls_accel_integration/checklists/`：上板前检查清单；
- Skill C 的脚本已在本项目报告上实测（`report/design_report.md` §3.4 的表
  就是它生成的）。
