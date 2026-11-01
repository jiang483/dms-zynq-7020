# Skill A：PYNQ HLS 加速器集成与逐位验证

## 适用场景

把一个 **HLS 生成的 AXI-Lite + AXI-Master IP** 挂到 PYNQ Zynq-7000 的 BD 上：

- IP 有 `s_axi_control`（ap_ctrl_hs）和 `m_axi_gmem`；
- 已有 `axi_smc`（SmartConnect → HP0）和 `ps7_0_axi_periph`；
- 需要新增一个 AXI-Lite 从口 + 一个 AXI 主口；
- 需要确保综合用的是**新权重/新 IP revision**。

不适用于：`ap_ctrl_none` 自由运行 IP（标量锁存问题）、AXI Master 位宽 >64 bit、
需要新增 PS HP 口的场景（PS7 配置在 BOOT.BIN 里，PYNQ Overlay 改不了）。

## 使用方法

1. 复制 `scripts/add_hls_ip_template.tcl`，改顶部 `CONFIGURE` 区
   （项目路径、VLNV、实例名、地址、现有 MI/SI 数量、期望位宽）。
2. `vivado -mode batch -source add_hls_ip_template.tcl`。
   脚本会备份 BD，并在 **generate_target 后读 `.hwh`** 校验现有 AXI 位宽，
   位宽变化立刻退出。
3. 复制 `scripts/refresh_hls_ip_template.tcl`，设置 IP 目录/实例名；
   每次 `build_ip` 之后运行它：`update_ip_catalog → upgrade_ip →
   reset/generate → ROM 大小比对`。**不要用裸 `reset_run synth`**，
   项目会继续综合旧副本。
4. PS 驱动从 `scripts/hls_driver_template.py` 改：
   设置 `N_IN/N_OUT/寄存器偏移`，在板端先用**随机输入**跑硬件 vs 金标准。
5. 按 `checklists/integration_checklist.md` 逐项打勾。

## 已验证效果

在本项目 `eye_cnn_accel` / `context_cnn_accel` 上：

- 两套 IP 都通过 `add_*_tcl` + `refresh_*_tcl` 集成；
- `context_cnn` 板上 **20/20 条随机 int8 输入逐位相同**，4.73 ms/次；
- 资源/时序（2026-10-24 交付版）：LUT **71.68%**、BRAM **58.21%**、DSP **63.64%**，
  WNS **+0.186 ns** / WHS +0.026 ns。

## 失效条件 / 常见坑

| 坑 | 症状 | 处理 |
|---|---|---|
| 新 MI 口的 `Mxx_ACLK/ARESETN` 没接 | 寄存器全 0、IP 永不启动、**不报错** | 扩 NUM_MI 后立刻接时钟/复位 |
| SmartConnect 扩 NUM_SI 后现有端口位宽被重算 | 视频路静默变窄 | `generate_target` 后读 `.hwh` 断言 S00/S01/M00 |
| 项目内 IP 副本锁定 | `build_ip` 后综合仍用旧权重；板上逐位比对与旧版完全相同 | `update_ip_catalog` + `upgrade_ip` + ROM 大小比对 |
| BD 参数覆盖（如 `C_M_AXI_GMEM_DATA_WIDTH=32`） | IP 默认 64、实例却是 32，带宽减半 | 从生成网表读回参数/位宽 |
| `ap_ctrl_none` | 标量只在复位时采一次；ap_done 不置起 | 改用 `ap_ctrl_hs` + 轮询 |
| 64 位指针寄存器 | 只写低 32 位，DDR 地址高位丢失 | 低/高两个字都写，回读校验 |
| CMA 缓冲未释放 | 反复运行后分配失败/系统异常 | `close()` 中 freebuffer |

## 来源

这些不是“设计出来的最佳实践”，而是本项目踩过的真实失败：
M04/M05/M06 复位漏接、`refresh_eye_cnn_ip.tcl` 的 IP 锁定、P2 的 32 位
AXI 覆盖、`ap_ctrl_none` 的 FIFO 死锁、板上 20/20 逐位比对。
