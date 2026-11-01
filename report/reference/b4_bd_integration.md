# B4 · ContextNet 的 BD 集成与上板

> 2026-10-18。B3 的权重已通过 C 仿真逐位验证；这里把它接进 PL。
> 工程：`V2_ov5640_hdmi/ov5640_hdmi.xpr`。
> ⚠️ 本文是**当时**的集成记录（bit `f06cf252…`、LUT 35,236 / WNS +0.134）。
> 2026-10-24 为 ContextNet 换权重重出了 bitstream，**交付版**为
> bit `75a9dee4…`、LUT 38,134（71.68%）/ WNS +0.186 —— 以
> `report/design_report.md` §3.4 与 `build/reports/` 为准。

---

## 1. 拓扑

```text
PS Haar（640x480 灰度）→ canonical.canonical_context_input()
    → context_cnn_accel_0/patch_in（DDR，2304 B）
    → context_cnn_accel_0（PL，~4.56 ms）
    → logits_out（DDR，8 × int32）
    → PS：0..3 头姿 / 4..7 手持物

AXI-Lite : ps7_0_axi_periph/M07_AXI  -> context_cnn_accel_0/s_axi_control
           地址 0x41A00000（0x41900000 是 axi_timer_0）
AXI 主口 : context_cnn_accel_0/m_axi_gmem -> axi_smc/S04_AXI -> S_AXI_HP0
```

`ps7_0_axi_periph` NUM_MI = **8**，`axi_smc` NUM_SI = **5**。

---

## 2. 构建顺序（不能颠倒）

```bash
cd hls
sh build_csim.sh context_cnn              # 1) 权重 + 整数语义先过
build_ip.bat context_cnn                  # 2) 重新打包 IP（训练权重）
cd ../V2_ov5640_hdmi
vivado -mode batch -source add_context_cnn.tcl          # 3) 改 BD
vivado -mode batch -source refresh_context_cnn_ip.tcl   # 4) 确认不是旧权重
vivado -mode batch -source build_bitstream.tcl          # 5) 综合/实现/时序/导出
```

⚠️ 工具实际在 `C:\AMDDesignTools\2026.1\`（不是 D 盘）；
license 文件（按本机安装位置配置，不随仓库分发）。

⚠️ `build_ip.bat` 必须用 `.\build_ip.bat` 调用（本机设置了
`NoDefaultCurrentDirectoryInExePath=1`，cmd 不搜索当前目录）。

---

## 3. 宽度校验（读生成网表，不看 GUI）

`add_context_cnn.tcl` 在 `generate_target` 之后解析
`ov5640_hdmi.gen/.../hw_handoff/design_1.hwh`：

| 端口 | 宽度 | 说明 |
|---|---|---|
| S00_AXI | 64 | VDMA MM2S |
| S01_AXI | 64（只查 **wdata**） | VDMA S2MM，**没有 rdata** |
| S02_AXI | 32 | eye_cnn |
| S03_AXI | **64** | img_preproc（P2 已把 m_axi 修为 64） |
| S04_AXI | 32 | context_cnn |
| M00_AXI | 64 | → S_AXI_HP0 |

> 第一次校验把 S03 期望写成 32、把 S01 查成 rdata，误报过一次。
> **S01 是写通道，查 `wdata`；S03 是 64。** 以生成网表为准。

---

## 4. IP 版本校验

`refresh_context_cnn_ip.tcl` 比较项目内副本与 `ip_repo` 的 4 个 ROM 文件：

- `context_weights_l2_b_ROM_AUTO_1R.dat`
- `l4_b` / `l6_b`
- `Pipeline_VITIS_LOOP_216_2_context_weights_l6_w_ROM_AUTO_1R.dat`

大小不一致 → 说明项目还在用**旧权重**，不能出 bitstream。
2026-10-18 实测 4 个全部一致。

---

## 5. 上板文件

需要 scp 到板上 `~/jupyter_notebooks/PYNQ/` / `PYNQ/src/`：

```text
PYNQ/design_1.bit                  （build_bitstream.tcl 自动导出）
PYNQ/design_1.hwh
PYNQ/src/context_cnn.py
PYNQ/src/demo_context.py
PYNQ/src/tests/test_context_cnn_hw.py
PYNQ/src/context_cnn_model/quant_ref.py
PYNQ/src/context_cnn_model/weights.npz
PYNQ/src/context_cnn_model/weights_meta.json
PYNQ/src/context_cnn_model/context_export_meta.json
```

板上（Jupyter root terminal，不要加 sudo）：

```bash
cd ~/jupyter_notebooks/PYNQ/src
bash run.sh tests/test_context_cnn_hw.py --hw
bash run.sh demo_context.py --frames 200 --compare-golden
bash run.sh demo_context.py --frames 0 --interval 0.1
```

判据：

- `test_context_cnn_hw.py --hw`：**20/20 条随机输入与 numpy 金标准逐位相同**；
  延迟中位约 4.6 ms。
- `demo_context.py --compare-golden`：逐位比对 0 不一致。
- 屏幕上能看到人脸框和 `pose/obj` 两行结论。

---

## 5.1 实测结果（2026-10-18）

- `build_bitstream.tcl`：**WNS +0.134 ns / WHS +0.023 ns**（时序过，余量很薄）；
  `cam_pclk` +8.748 / `clk_fpga_0` +0.134。
- placed：LUT 35,236（66.2%）、FF 41,438（39.0%）、BRAM 81.5 tiles（58.2%）、
  DSP 140（63.6%）。
- 板上 `tests/test_context_cnn_hw.py --hw`：
  **20/20 随机输入逐位相同**；**4.728 ms（中位）/ 4.734 ms（均值）**。
- overlay MD5：bit `f06cf2520e787a1db6d2b4b05aba4092`，
  hwh `e25a1db15826e1e394255c13fd56a4a6`。

## 6. 排错

| 现象 | 先查 |
|---|---|
| overlay 里没有 `context_cnn_accel_0` | bit/hwh 没换；PYNQ 只加载 PL，确认两个文件一起拷 |
| `ap_done` 2 s 不置起 | M07_ACLK/ARESETN、S04_AXI、FCLK0 是否 100MHz、地址是否 0x41A00000 |
| 硬件 logits 与金标准不一致 | 先确认 `weights.npz` 与 `context_weights.h` 同源（`context_export_meta.json`）；再查 IP 是否旧 revision |
| WNS 为负 | 看 `impl_1/...timing_summary_routed.rpt` 的 `clk_fpga_0`；按 B1 §4：`II=2` → 拆 AXI → 降频 |
| 综合报 `module not found` | 不要删 `.gen/`；跑 `update_compile_order -fileset sources_1` |
