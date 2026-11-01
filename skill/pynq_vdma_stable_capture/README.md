# Skill B：PYNQ VDMA 稳定采集/显示

## 适用场景

Zynq-7000 + PYNQ，OV5640/其他视频源 → `v_vid_in_axi4s` → **VDMA S2MM** → DDR
（多个 frame store）→ CPU 读取；CPU 写另一块 DDR → **VDMA MM2S** → HDMI。

典型症状：

- 画面每隔几帧出现一条“上半旧帧、下半新帧”的撕裂带；
- CPU 写显示缓冲后屏幕全黑，但回读内存完全正确；
- 进程退出后板子随机 segfault / `free(): invalid pointer` / sshd 掉线。

## 使用方法

1. 采集：用 `read_store_stable()`，不要裸读；它读两遍、逐字节相同才采信。
2. 显示：如果 CPU 写 `disp_buf`、MM2S 读 `disp_buf`，**先启动 DisplayCtrl，
   再 reset+start MM2S**；不要在 `vdma.start(BOTH)` 后直接依赖 MM2S。
3. 开机用 `display_selftest()` 推满屏色块，让人眼确认整条显示链是活的。
4. 退出必须调用 `shutdown()`：`vdma.stop()`、`disp_ctrl.stop()`、释放缓冲。
5. 需要核对 MM2S 读哪块内存时，用 `read_mm2s_addrs()` 回读起始地址寄存器。

## 已验证效果

- 60 对连续全帧读中 **20 对（33%）** 抓到撕裂，变化带中位 97 行；
  双读平均约 1.5 次读、循环时间 +32 ms（约 −10.7% FPS）。
- MM2S 启动顺序修复后，CPU 中转显示的满屏色块和实时画面正常；
  修改前自检色块全黑，而内存回读逐字节一致。
- `S2MM_PARK_PTR(0x38)` 实测恒为 0，**不要用它查当前帧号**。

## 失效条件

- **PL 直出 OSD**（MM2S 直接读 `cap_buf`）时，不要用 `disp_buf.present()`；
  这是另一条路径。
- 帧几何/字节序不同（RGB/BGR、stride 不为 `W*BPP`）时需要改 `FRAME_BYTES`/shape。
- 自由运行 `ap_ctrl_none` IP 的 FIFO 可能反压；与本 Skill 无关，但会伪装成视频卡死。
- 强杀进程后 VDMA 仍可能运行；必须 `vdma.stop()` 或重启板子。

## 来源

- `tear_check.py`：三个 store 各 9.5 Hz、28.5 fps，33% 撕裂；
- 2026-10-03 强杀后 VDMA 遗留运行，导致 Jupyter 卡死 + HDMI 黑屏；
- 2026-10-06 `verify()` 的“回读内存一致”误判：**回读只证明 CPU 写对了，
  不证明 MM2S 送进了显示管线**；
- 2026-10-18 `display_bisect.py`：MM2S 必须在 DisplayCtrl 之后 reset+start。
