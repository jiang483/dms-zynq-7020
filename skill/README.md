# PYNQ Accelerator Skills

> 这三个 Skill 是从本项目（ZYNQ-7020 + PYNQ 的 DMS）开发过程中沉淀出来的，
> **不与 DMS 题目绑定**：换一个 HLS 网络、换一块 PYNQ 板，仍然可用。
> 每个目录的 README 都写明：适用场景、使用方法、已验证效果、失效条件、
> 以及是从哪些失败/观察中总结出来的。

| Skill | 解决什么 | 目录 |
|---|---|---|
| A. PYNQ HLS 加速器集成与逐位验证 | HLS IP 挂进 BD、AXI 地址/位宽/复位、IP 锁定与旧权重、PC/HLS 逐位比对 | `pynq_hls_accel_integration/` |
| B. PYNQ VDMA 稳定采集/显示 | 帧撕裂、CPU 中转显示黑屏、MM2S 启动顺序、DMA 退出未停 | `pynq_vdma_stable_capture/` |
| C. Vivado 资源/时序/复现报告自动化 | 从 impl 报告自动出资源/时序表、bit/hwh 校验、复现检查 | `vivado_report_automation/` |

## 快速选择

- 新加一个 HLS IP，不知道从哪开始 → **A**。
- 摄像头画面撕裂 / CPU 写显示缓冲黑屏 / 退出后板子内存被 DMA 写坏 → **B**。
- 要写报告里的资源/时序表，或要检查“这次 bitstream 到底是不是新权重” → **C**。

## 共同原则

1. **先验证语义，再上板**：C 仿真/PC 金标准 → 逐位比对 → 再综合。
2. **读生成物，不信 GUI**：BD 参数、AXI 位宽、IP revision 都要从
   `.hwh` / `.gen` / ROM 文件读回来核对。
3. **失败要显式报错**：脚本在关键断言失败时退出，不要“看起来成功”。
4. **板上调试很贵**：把可自动判定的检查（逐位、寄存器、md5）放到板端脚本里。
