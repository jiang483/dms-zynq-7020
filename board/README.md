# Board Package

## 文件

```text
design_1.bit   # 2026-10-24 构建（换 ContextNet 权重后重出）；md5 75a9dee4828273e39371d56d88f9fe47
design_1.hwh   # md5 cfafa2575787d07dcb119a70def70bbb
run.sh         # PYNQ 启动包装（source venv/xrt）
measured/      # 实测截图/数据流图/上位机截图
```

## 部署

板上 root（Jupyter terminal）：

```bash
mkdir -p ~/jupyter_notebooks/PYNQ/src
# 把 design_1.bit / design_1.hwh 放到 ~/jupyter_notebooks/PYNQ/
# 把 src/ps/* 放到 ~/jupyter_notebooks/PYNQ/src/
cd ~/jupyter_notebooks/PYNQ/src
bash run.sh demo_eye_perclos.py --osd --classifier cnn --osd-native-haar \
  --face-detect-scale 2 --face-stride 8 --face-fallback \
  --context --context-stride 5 --osd-time --osd-tz-hours 8 \
  --frames 0 --interval 0.1
```

停止：Ctrl-C，或另开终端 `touch /tmp/stop_hdmi_demo`。
**启动新程序前先确认没有旧 demo**；VDMA 未停会持续写已释放内存。

## 启动前

- 校时（OSD/录像时间）：`bash tools/sync_board_clock.sh`（PC 侧运行，
  通过 SSH 用 PC 的 UTC epoch 校板）；板载 RTC 默认偏约 5 小时。
- Face ID 可选：把 `face_id_db.npz`、SFace ONNX、libfacedetection `.so`
  放到 `/home/xilinx/models/` / `/home/xilinx/lib/`；没有时 Face ID 初始化
  失败会降级，眼态/context/事件不受影响。
- 相机对准驾驶位；`--face-detect-scale 2` 在 native 路等价于 320 检测
  （代码内已折算）。

## 实测输出

- `test_context_cnn_hw.py --hw`：20/20 随机输入逐位相同，4.73 ms/次。
- `demo_eye_perclos.py --context`：context 关 9.9 FPS；开 7.4~7.8 FPS。
- 右耳手机 5 s：`context_log.csv` 中 `phone_call` 触发（t=449.4~453.2）。
- DMS 阶段 A：遮挡/离岗/录像/哈希链/活体 80 项测试、板上验收。

## 诊断

```bash
bash run.sh tests/test_context_cnn_hw.py --hw
bash run.sh tests/test_faceid_engine.py --images '/path/*.jpg'
python3 tests/test_canonical.py
```

`snapshots/context_log.csv` 会记录每次 context 推理的 pose/obj/margin/events。
