# ContextNet 弃权阈值（margin）标定

> 2026-10-18 · 脚本 `eye_cnn_ml/calibrate_context_margin.py`
> 数据：2 折按会话划分的验证集；输出 `eye_cnn_ml/out/context_margin_fold{0,1}.json`
> 目标：给 `PYNQ/src/context_logic.py` 的 `ContextConfig` 默认值提供可复现依据。

## 1. 为什么不能凭经验定

`context_logic.py` 的阈值是**量化后的 int32 logit 差**（top1 − top2），
不是概率、也不是浮点差：

- 换权重、换量化尺度后，同一个数值的含义会变；
- 两个头（头姿 / 手持物）的 margin 分布完全不同；
- 手持物内部四类的代价也不对称：phone 漏报影响演示，cigarette 误报会
  在正常驾驶时反复触发 `smoking`。

所以必须用**每折自己的量化规格**在**该折没见过的会话**上扫描。

## 2. 方法

```bash
python calibrate_context_margin.py --fold 0   # 用 out_hls_fold0/weights.npz
python calibrate_context_margin.py --fold 1   # 用 out_hls_fold1/weights.npz
```

- 验证会话来自 ckpt 的 `meta.val_sessions`（与训练时的划分完全一致）；
- 逐条走 `quant_ref.QuantSpec.forward()`，得到板上同款的 8 个 int32 logits；
- `margin = top1 − top2`，`argmax` 决定预测类；
- 按**预测类**选择阈值（部署配置：none=1 / phone=500 / cigarette=1500 / other=1500）；
- 事件误报代理只看“确实会报”的帧（margin ≥ 阈值）。

## 3. 头姿阈值扫描

| T | fold0 覆盖 | fold0 准确 | fold1 覆盖 | fold1 准确 |
|---:|---:|---:|---:|---:|
| 0 | 1.000 | 0.903 | 1.000 | 0.955 |
| 200 | 0.931 | 0.946 | 1.000 | 0.955 |
| 300 | 0.900 | 0.970 | 0.996 | 0.959 |
| **500** | **0.876** | **0.978** | **0.993** | **0.958** |
| 800 | 0.803 | 0.986 | 0.978 | 0.969 |
| 1500 | 0.625 | 0.988 | 0.888 | 0.975 |

`T=500` 时两折的每类召回：

| 类 | fold0 | fold1 |
|---|---:|---:|
| forward | 0.847 | 1.000 |
| left | 0.758 | 0.937 |
| right | 0.920 | 0.827 |
| down | 1.000 | 1.000 |

**事件误报代理**：真实 forward 却被判成 left/right/down 且 margin ≥ 500：

- fold0：3/118 = **2.5%**
- fold1：0/82 = **0%**

结论：**pose_margin = 500**。再往下（200/300）正常正对帧会被低 margin 的
左右转带成 `distraction`；再往上（800+）left/right 召回掉得比准确率涨得快。
单帧召回下降对事件影响有限，因为部署要求连续 1.5 s。

## 4. 手持物阈值扫描

| T | fold0 覆盖 | fold0 准确 | fold1 覆盖 | fold1 准确 |
|---:|---:|---:|---:|---:|
| 0 | 1.000 | 0.684 | 1.000 | 0.725 |
| **500** | **0.794** | **0.731** | **0.773** | **0.819** |
| 1000 | 0.632 | 0.755 | 0.628 | 0.865 |
| **1500** | 0.535 | 0.791 | 0.445 | 0.907 |

**按部署配置**（none=1 / phone=500 / cigarette=1500 / other=1500）：

| 类 | fold0 接受率 | fold0 召回 | fold1 接受率 | fold1 召回 |
|---|---:|---:|---:|---:|
| none | 0.954 | 0.942 | 0.989 | 0.989 |
| phone | 0.648 | 0.538 | 0.493 | 0.444 |
| cigarette | 0.757 | 0.528 | 0.474 | 0.169 |
| other | 0.754 | 0.268 | 0.524 | 0.386 |

**为什么 phone 用 500、cigarette/other 用 1500**：

| 阈值 | fold0 非烟→烟误报 | fold1 非烟→烟误报 |
|---:|---:|---:|
| 500 | 18/760 = **2.37%** | 37/840 = **4.40%** |
| 1500 | 3/760 = **0.39%** | 1/840 = **0.12%** |

- phone 的 margin 在板上右耳实测只有 500~824，且会掉到 809/913；
  阈值 1000 会让候选在中间被 reset，2 s hold 永远攒不够 → **500**；
- cigarette 在正常场景的假阳 margin 可达 948/956，统一 500 会误报抽烟
  → **1500**；
- `other` 是 catch-all，本身召回就低（fold0 0.268），1500 + 弃权
  是“宁可 unknown 不硬报”的明确选择，符合产品口径。

## 5. 事件级回放：单帧召回不等于事件触发

单帧 recall 回答不了“连续 hold 秒才报”的问题。新增
`eye_cnn_ml/eval_context_events.py`：把采集数据按 `t` 排序，逐帧调用
**板上同一个** `ContextState.update()`，再按采集段（left/right/low/phone/
smoke/normal/other）统计触发、延迟与误报。

### 5.1 当前默认值的问题（pose500 / phone500 / cig1500 / hold2.0）

| 动作 | 触发率 | 说明 |
|---|---:|---|
| distraction（left/right/low） | **9/10** | 延迟中位约 2~3 s |
| phone_call | **8/10** | 延迟中位 10 s 量级，个别段 20 s+ |
| smoking | **5/10** | 一半真烟段完全没触发 |
| normal 段 | **0 误报** | — |

诊断逐帧序列后确认：**不是采样空洞，也不是单帧毛刺**（3/5 帧中值滤波
没有改善）。真烟段的 cigarette margin 大量落在 500~800，1500 直接弃权；
phone 段则在 phone/cig/none 之间短断，2.0 s hold 被一次 unknown 打断。

### 5.2 扫描结果（两折合并，10 个 smoke 段 / 10 个 phone 段）

| 配置 | smoking | phone_call | distraction | 非目标段 smoking 误报 |
|---|---:|---:|---:|---:|
| pose500 / phone500 / **cig1500** / hold2.0 | 5/10 | 8/10 | 9/10 | 0 |
| pose500 / phone500 / cig1000 / hold1.5 | 5/10 | 9/10 | 9/10 | 1 |
| pose500 / phone500 / **cig600** / **hold1.5** | **10/10** | **9/10** | 9/10 | 1 |

跳变点在 **600**：800 只有 6/10，600 直接 10/10。代价是 other 段
（举水杯）多 1 次 `smoking` 误报（约 12 分钟数据里 1 次）；
`normal` 段仍 **0 误报**。

⚠️ **延迟数字的解读**：早期会话（093501 / 112108 / 112459）采集时还没有
`pause`/`--preannounce`，段起点早于操作者真正把物体举到位，所以整段延迟会
出现 10~24 s 的假象；有 `pause` 的会话（115306 / 115929）是 **1.7 / 1.8 s**。
比较配置时只看**相对变化**，绝对延迟必须用板上的受控 A/B 测。

### 5.3 最终默认值（已写入 `context_logic.ContextConfig`）

| 参数 | 旧 | 新 | 依据 |
|---|---:|---:|---|
| `pose_margin` | 500 | 500 | 3 节扫描 |
| `obj_margin`（phone） | 500 | 500 | 5/5~9/10 触发，再降收益小 |
| `obj_cig_margin` | 1500 | **600** | smoke 5/10 → 10/10 |
| `obj_other_margin` | 1500 | 1500 | catch-all，宁可 unknown |
| `obj_hold` | 2.0 | **1.5** | 逐帧短断导致 2.0 s 攒不够 |
| `pose_hold` | 1.5 | 1.5 | 回放延迟 1.6~3.9 s |

`demo_eye_perclos.py` 的 argparse 默认值已同步（原 cig 默认写的是 1200，
与 `ContextConfig` 的 1500 也不一致，这次一起统一成 600）。

### 5.4 板上 A/B 结果（2026-10-18）

真实摄像头、640×480、`--context-stride 5`、`--face-fallback` 开：

| 场景 | 时长 | 结果 |
|---|---:|---|
| normal | 174 s | **0 事件**（287 行） |
| smoke | 24 s | **`smoking` 触发**，cigarette margin 中位 2233 |
| phone（贴右耳） | 20 s | **`phone_call` 全程**，28/34 帧 phone；无 distraction |
| pose（右转） | 34 s | **`distraction` 触发**（right margin 1614）；左转时脸出画，未采到有效帧 |
| cup（举水杯） | 20 s | ❌ 杯子被判成 phone/cigarette，同时触发 `phone_call` + `smoking` |

★★ **A/B 抓到的真 bug**：pose 段右转连续保持 5 s、margin 995~2552，
但 `distraction` 没触发。根因不是阈值，而是**转头时 Haar/fallback 会短暂
丢脸**：demo 对拿不到人脸框的帧调用 `update(now, None)`，旧状态机把每帧
None 当成“条件不满足”，候选计时被清零。这些 None 帧不写 CSV，所以离线
回放看不出来。

修复（`context_logic.ContextState.update`）：新增 `no_obs_reset=2.0 s`，
**短暂无观测只冻结候选、不清零**；超过 2 s 才重置；已 active 的事件仍按
`release` 结束。新增两个回归测试。修复后板上 pose 段正常触发。

**演示口径**：举水杯/纸杯会误报，演示脚本不包含该动作；手持物头的
`other`/杯状物是已知弱点，写在局限里。

## 6. 复现与回归

```bash
cd eye_cnn_ml
python calibrate_context_margin.py --fold 0
python calibrate_context_margin.py --fold 1
python eval_context_events.py --fold 0     # 事件级回放
python eval_context_events.py --fold 1
```

换权重后必须重跑两份；阈值是 int32 logit 差，不能沿用旧值。

## 7. 局限

- 验证集是**会话级留出**，不是跨人留出；板上真实场景的事件级误报率仍需
  Week 2 的摄像头 A/B 实测（本标定只给出单帧代理指标）。
- fold0/fold1 的 `cigarette` 召回差异很大（0.528 vs 0.169），说明手持物头
  对会话/光照敏感；这也是当前方案用 1.5 s hold + 弃权兜底的原因。
- `other` 的召回不可用作验收指标（catch-all 且训练多样性有限）。
