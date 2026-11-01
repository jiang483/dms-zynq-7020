# Data

本目录只放**小样本**，用于冒烟/展示，不包含完整训练集。

```text
samples/
  context/   # 31 张 context raw ROI + samples.csv（pose/object 标签）
  eye/       # 20 张眼睛 patch + samples.csv（open/closed/invalid/off_*）
```

## 未包含的数据（许可/体积原因）

| 数据 | 用途 | 获取方式 |
|---|---|---|
| CEW（闭眼整脸） | 跨人闭眼 | 按 CEW 官方许可获取，运行 `src/ml/build_cew.py` |
| MRL Eyes | 红外预训练 | 按 MRL 官方许可获取 |
| 板上完整采集（数万条） | 部署域微调 | 用 `src/ps/collect_eye_patches.py` 自行采集 |
| SFace ONNX / libfacedetection `.so` | 可选 Face ID | 按上游许可获取/构建 |

## 采集与清洗

- 眼睛 patch：`collect_eye_patches.py`，段 + 逐帧证据双重标签；
- context ROI：`--context` 同一帧额外存 `raw_ctx/` + `context.csv`；
- 清洗规则：`src/ps/collect_logic.py`、`src/ml/context_dataset.py`、
  `report/reference/` 里的 B2/B3 文档。

## 标签口径

- 眼睛：`open / closed / invalid`（invalid 映射 UNKNOWN，不计入 PERCLOS）；
- context：头姿 `forward/left/right/down`，手持物 `none/phone/cigarette/other`；
- `context.csv` 的 `label_pose`/`label_object` 可有一个为空（另一头缺失）。
