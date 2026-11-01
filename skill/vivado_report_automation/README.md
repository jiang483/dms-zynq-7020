# Skill C：Vivado 资源/时序/复现报告自动化

## 适用场景

Vivado 2025.2/2026.1 工程已经跑完 `impl_1`，需要：

- 从 `design_1_wrapper_utilization_placed.rpt` 提取 LUT/FF/BRAM/DSP；
- 从 `design_1_wrapper_timing_summary_routed.rpt` 提取 `clk_fpga_0` / `cam_pclk`
  的 WNS/WHS；
- 生成报告里的 Markdown 表；
- 校验最终交付的 `design_1.bit` / `.hwh` 是否就是这一版（md5/大小）。

不适用于：没有跑完实现的工程；报告格式被版本改写的场景（解析器需要更新）。

## 使用方法

```bash
python parse_vivado_reports.py \
  --util <...>/design_1_wrapper_utilization_placed.rpt \
  --timing <...>/design_1_wrapper_timing_summary_routed.rpt \
  --out resource_timing.md

python check_artifacts.py --bit design_1.bit --hwh design_1.hwh \
  --expect-bit-md5 <hash> --expect-hwh-md5 <hash>
```

## 已验证效果

在本项目 2026-10-18 的 `context_cnn` 集成上，解析结果与手工读数一致：

| 资源 | 值 |
|---|---|
| LUT as Logic | 35,236 / 53,200 = 66.23% |
| FF | 41,438 / 106,400 = 38.95% |
| Block RAM Tile | 81.5 / 140 = 58.21% |
| DSP | 140 / 220 = 63.64% |
| clk_fpga_0 | WNS +0.134 / WHS +0.023 ns |
| cam_pclk | WNS +8.818 ns |

**2026-10-24 交付版**（同一套解析脚本）：LUT **38,134 (71.68%)**、
`clk_fpga_0` **WNS +0.186 / WHS +0.026 ns**、`cam_pclk` WNS +8.242 ns。
资源/时序会随综合策略变化，**脚本的价值是每次从报告读回真值**，不是记住某一版数字。

## 失效条件

- 报告文件名/表头随 Vivado 版本变化：解析器按固定列位置，需更新。
- `impl_1` 未完成或报告被截断：脚本会报错，不要拿缺表当 0。
- md5 校验只证明文件未变，不证明时序/功能正确；两者都要看。

## 来源

- 本项目从 `impl_1` 报告核对资源/时序时，发现旧材料里的 “BRAM 46” 是错的，
  实际 28 tiles（20%）→ 后续 context 集成到 81.5 tiles（58.2%）；
- `build_bitstream.tcl` 的 Tcl 方括号坑（`[${grp}]` 被当命令替换）导致
  “bitstream 写完但没导出”；因此报告自动化必须把“流程完成”和“时序通过”
  分开检查。
