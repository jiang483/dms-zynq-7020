# B3 · ContextNet 训练、定点化与导出（2026-10-18 第二版）

> 数据：B2 采集（**11 个会话，2190 行**，其中带头姿标签 526 行）。
> 代码：`eye_cnn_ml/context_dataset.py` / `context_model.py` /
> `train_context_cnn.py` / `export_context_weights.py` / `eval_context_quant.py`。
> 权重已覆盖 `hls/context_cnn/context_weights.h`，C 仿真逐位通过。

---

## 1. 数据口径

| 项 | 值 |
|---|---|
| 会话 | 11 个：原 6 个 + 5 轮只采手持物（`115306` / `115622` / `115929` / `120229` / `120524`） |
| 总行数 | **2190**（每行至少带一个标签） |
| 头姿 | forward 200 / left 125 / right 102 / down 99 |
| 手持物 | none 526 / phone 579 / cigarette 590 / other 495 |
| 污点处理 | `CONTEXT_USABLE.txt`：4 个会话 `drop=down`；`093501`/`095251` `trim=phone:5,smoke:6,other:3`；`111926` 整会话排除 |

`context_dataset.py --stats` 会打印当前口径与两折会话分组。

## 2. 划分

只有一名被试，按 **session** 做 2 折（`make_folds` 穷举分组，保证每一折
8 个标签都出现）：

| 折 | 验证会话 | 验证集 down |
|---|---|---|
| fold 0 | 093501 / 112108 / 112459 / 115306 / 115929 | 29（强低头） |
| fold 1 | 095251 / 112830 / 113619 / 115622 / 120229 / 120524 | 70（温和低头） |

`down` 只有两个来源，普通随机划分很容易让训练集或验证集完全没有 down；
`make_folds` 穷举分组正是为了避免这一点。

## 3. 训练

```bash
# 两折（诚实估计）
python train_context_cnn.py --fold 0 --epochs 60 --out out
python train_context_cnn.py --fold 1 --epochs 60 --out out
# 部署模型（全部数据）
python train_context_cnn.py --train-all --epochs 60 --out out
```

- 损失：两个头各自 CE（缺失标签 `-100` + `ignore_index`），等权相加。
- 增强：**水平翻转 + left/right 标签对调**（只翻图会污染两类）；
  **随机平移 ±3 px**（`--shift 3`，默认开）—— 补数据后发现手机经常贴在
  ROI 边缘，平移用来打掉"位置=类别"的捷径。
- 选 epoch：`(pose_macro_recall + obj_macro_recall)/2`；`--train-all` 存最后一轮。
- 实测 `--obj-weight 2.0` 在旧数据上反而更差（fold 0 obj 0.621→0.582），保持 1.0。

### 结果（浮点，验证会话）

| 折 | 头姿 macro-R | 手持物 macro-R | 备注 |
|---|---:|---:|---|
| fold 0 | **0.946** | **0.666** | other 0.316（验证集里有"白纸"这种没见过的 other 物体） |
| fold 1 | **0.946** | **0.751** | phone 0.644、cigarette 0.593、other 0.779 |
| 部署模型（全量，同人监视集） | 0.975 | 0.992 | **乐观，不作泛化结论** |

- 头姿稳定在 0.94~0.95，down 两折都是 1.00。
- 手持物 2 折平均 **0.709**（补数据 + 平移增强前是 0.719，但旧数据更少、
  验证集更简单；这版的绝对难度更高）。phone 比上一版稳，cigarette/other
  仍有明显折间波动。
- **`other` 是 catch-all**：验证集里出现训练集没见过的物体（白纸/本子）时
  recall 会掉到 0.32 —— 这是类别定义本身的问题，不是标签错。部署时
  对"未知物体"应有置信度门（margin 小就不要报 other）。

## 4. 定点化（PTQ）

```bash
python export_context_weights.py --ckpt out/context_fold0.pt --out out_hls_fold0
python eval_context_quant.py --ckpt out/context_fold0.pt \
    --spec out_hls_fold0/weights.npz
```

| 折 | 头姿 float→quant | 手持物 float→quant | 浮点/定点 argmax 一致率 |
|---|---|---|---|
| fold 0 | 0.946 → 0.932 | 0.666 → 0.673 | 头姿 98.5%，手持物 95.1% |
| fold 1 | 0.946 → 0.946 | 0.751 → 0.735 | 头姿 100%，手持物 93.5% |

头姿 PTQ 掉 0~1.4 个点；手持物 ±0.7~1.6 个点。argmax 一致率 93.5%~100%，
对 8 类小模型属于可接受范围。

量化规格（部署权重）：`e_in/e_w/S_L` 全部是整数，`|acc|` 最大 63,182，
int32 余量充足。

## 5. 导出到 HLS

```bash
# 用部署权重（全量训练）覆盖骨架阶段的随机权重
python export_context_weights.py --ckpt out/context_deploy.pt \
    --out ../hls/context_cnn --testvecs 4
# 逐层逐位比对
cd ../hls && sh build_csim.sh context_cnn
```

实测：**4 个用例、7 层激活 + 8 logits 与 numpy 金标准逐位相同**。
`hls/context_cnn/context_weights.h` 现在是训练权重（`context_export_meta.json`
记录了 ckpt 与标定集）。

## 6. 测试

```bash
python tests/test_context_model.py     # 6 项：预算 32672/1,355,008、无 BN/Dropout
python tests/test_context_dataset.py   # 9 项：清单/丢弃/trim/划分/翻转/平移
```

## 7. 下一步

1. **补 `other` 的物体多样性**：现在 other 有瓶子、白纸/本子；再补
   纸杯/易拉罐/手机盒等。`other` 是 catch-all，验收集里出现没见过的物体时
   recall 只有 0.32 —— 这是当前最大的类内泛化问题。
2. 上板前先确认 `context_cnn_accel` 的资源与时序（B1 §4 的 WNS 风险）。
3. PS 侧接线：`canonical.canonical_context_input(gray, face_box)` 是唯一入口
   （K=2.0、越界 clamp、48×48、int8），**不要自己再写一遍裁剪**。
4. 输出映射：logits[0:4] → 头姿，logits[4:8] → 手持物；argmax + margin；
   margin 小时（尤其 other）按 unknown 处理，不要硬报。
5. 如果 other 补数据后仍不达标，再考虑升级输入（64×64 或彩色）——
   那会改变 HLS 预算，需要重新 csynth/impl。
