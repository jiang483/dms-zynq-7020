# HLS IP 集成检查清单

## 上板前（PC）

- [ ] C 仿真通过，且**不是假 PASS**：用例 logits 互不相同；反向对照（改一个参数）会失败。
- [ ] `build_ip.bat <kernel>` 成功，`ip_repo/<ip>/component.xml` 时间戳是新的。
- [ ] `add_hls_ip_template.tcl` 的 `CONFIGURE` 与当前 BD 一致（MI/SI 数量、地址不冲突）。
- [ ] `refresh_hls_ip_template.tcl` 打印 **All checked ROM files match ip_repo**。
- [ ] `build_bitstream.tcl` 的 `clk_fpga_0` WNS/WHS 都 ≥0；失败不要烧板。
- [ ] 导出 `design_1.bit` + `.hwh`，记录 md5。

## 板上

- [ ] overlay 里能看到 `<inst>`（`ol.ip_dict`）。
- [ ] `read_ptr('in')` / `read_ptr('out')` 等于分配的 CMA 物理地址。
- [ ] 随机 int8 输入跑硬件 vs numpy 金标准，**逐位相同**（不是容差）。
- [ ] `ap_done` 在超时内置起；失败先查 FCLK=100MHz、Mxx_ACLK/ARESETN、地址。
- [ ] 退出时调用 `close()` 释放 CMA；确认 VDMA/加速器已停。
- [ ] 记录延迟中位/均值（含 MMIO 轮询开销）。

## 报告

- [ ] 资源/时序表来自 `impl_1` 报告，不是 csynth 估计。
- [ ] 写明 bit/hwh md5、IP revision、标定/权重来源。
- [ ] 写明失效条件（如 `ap_ctrl_none`、AXI >64 bit、PS HP 口不可用）。
