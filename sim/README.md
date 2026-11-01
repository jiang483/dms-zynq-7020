# Simulation / Verification

## HLS C 仿真（不需要 Vitis）

```bash
cd ../src/hls
sh build_csim.sh all
```

`csim_stubs/` 提供 `hls_stream.h` / `ap_int.h` / `ap_axi_sdata.h` 的最小桩；
装了 Vitis 的机器上会优先使用真头文件，行为不变。

覆盖：

- `eye_cnn`：8 个用例、7 层激活 + logits 与 numpy 金标准逐位相同；
- `context_cnn`：4 个用例、7 层激活 + 8 logits 逐位相同；
- `img_preproc`：模式1 24/24、模式0 0/76800 差异；
- `video_box`：OSD 两拍协议/时间区外逐位不变；
- `eye_pipeline`：片上 patch/逐位 logits + 反向对照。

## PC 单元测试

需要 numpy + OpenCV（`test_collect_run` / `test_face_id_logic` 会 import cv2）。

```bash
cd ../src/ps
python tests/test_canonical.py
python tests/test_context_logic.py
python tests/test_context_collect.py
python tests/test_collect.py
python tests/test_collect_run.py
python tests/test_telemetry_proto.py
python tests/test_face_id_logic.py
python tests/test_replay_state.py
python upper/tests/test_dashboard_logic.py
```

## 训练/量化代码测试

```bash
cd ../src/ml
python tests/test_context_model.py
python tests/test_context_dataset.py
python tests/test_quant_ref.py
python tests/test_model.py
python tests/test_export.py
python tests/test_context_spec.py
python tests/test_calibrate_margin.py
python tests/test_dataset.py   # 需要完整数据，仓库未附
```

## 逐位比对的判据

- 硬件 vs `quant_ref.py` 金标准：**`!=` 比对，无容差**；
- 随机 int8 输入覆盖负值/饱和/边界；
- 防“假 PASS”：用例 logits 不能全相同；反向对照（改一个参数）必须失败。

## 提交包内复现记录（2026-10-18）

在 `dms_zynq7020/` 干净目录内直接执行：

| 项 | 结果 |
|---|---|
| `sh build_csim.sh all` | **5/5 kernel PASS**（eye_cnn 8 用例 / context_cnn 4 / img_preproc 24+2 / video_box 5 / eye_pipeline 24 + 反向对照） |
| `src/ps` 单元测试 | canonical 19 / context_logic 10 / context_collect 23 / collect 36 / collect_run 27 / telemetry_proto 18 / face_id PASS |
| `src/ml` 单元测试 | context_model 6 / context_dataset 9 / quant_ref 18 / model 8 / export 9 / context_spec 6 |

环境：Windows 11 + MinGW g++ 15.2.0；Python 3.11 + torch 2.14 CPU + numpy + OpenCV 4.14。
`src/ml` 的脚本现在会自动定位 `../ps`，不再需要 `PYTHONPATH`。

## 提交包内复现记录（2026-10-25，整包同步后）

在 `dms_zynq7020/src/ps` 直接运行（Python 3.11，无需板子）：

| 套件 | 结果 |
|---|---|
| canonical / collect / collect_run | 19 / 36 / 27 PASS |
| context_logic / context_collect | 15 / 23 PASS |
| fatigue_logic / perclos / occlusion | 25 / 22 / 21 PASS |
| integrity / recorder / liveness | 11 / 15 / 14 PASS |
| telemetry / telemetry_proto | 9 / 18 PASS |
| face_id_logic / alert_logic / stranger_snapshot / enroll_pose / dms_face | PASS |
| upper `test_dashboard_logic` | 31 PASS |
| `test_context_cnn`（PC 金标准路径） | 5 PASS |
| ML：context_model / context_dataset / quant_ref | 6 / 14 / 18 PASS |
| ML：model / export / context_spec / dataset | 8 / 9 / 6 / 22 PASS |

### 表 1f 的原始数值

`sim/verification/context_20261024/`：

- `p1b_old.json` / `p1b_new.json`：P1b 真烟/真手机在新旧模型上的混淆矩阵；
- `quant_new_val5.json`：5 会话 float/quant 一致率（头姿 97.30% / 手持物 94.85%）；
- `quant_new_n3p1b.json`：两个留出会话 142/142 = 100% 逐位一致。

复现脚本：`src/ml/eval_context_fp.py`（N3 误报）、
`src/ml/_exp/eval_holdout_recall.py`（P1b 召回）、
`src/ml/eval_context_quant.py`（量化一致率）；
硬负样本切半对照在 `src/ml/_exp/hardneg_{split,control}.py`。
⚠️ 这些脚本需要板上采集数据（`data/board/`），提交包按许可只放脚本、不放全量数据。
