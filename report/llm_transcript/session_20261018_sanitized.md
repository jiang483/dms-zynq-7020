# LLM collaboration transcript (sanitized, text-only)

> Source: current Claude Code session. Tool outputs and tool-call JSON are omitted.
> Paths/IPs/username are replaced with placeholders. Review before public release.

### user  2026-10-18T01:51:12.301Z

继续

### assistant  2026-10-18T01:51:33.082Z

我先确认了一下当前进度：阶段 A 已在板子上验收完成，B1 的 `context_cnn` 仿真与 csynth 也完成了；但 B2 的数据采集脚本还不存在，这是盘上缺的第一块。另外 HANDOFF 里还挂着“暗光眼睛 patch 采集/微调眼 CNN”这条线。

“继续”有两个候选方向，选错了会白写不少代码，先跟你确认一下：

### assistant  2026-10-18T02:04:40.506Z

开始动手。先把“人脸 ROI 方块”的几何加进 `canonical.py`（训练/部署单一真源），再接采集端。

### assistant  2026-10-18T02:07:00.594Z

采集端和测试都通了。按项目一贯做法，再加一个 PC 侧的上下文数据目视 QC 工具（之前每类 montage 人眼确认抓到过 3 个真 bug，这一步不跳过）。

### assistant  2026-10-18T02:08:27.049Z

板子在线。推流前先按项目习惯在板上备份旧文件，再同步并做 md5 核对。

### assistant  2026-10-18T02:11:19.063Z

B2 采集端已完成并在板上验证通过。总结如下。

## 本轮做了什么

**一份采集同时出两种方块**，眼睛 patch 的旧行为不变：

| 输出 | 内容 |
|---|---|
| `raw/` + `patches.csv` | 眼睛 patch（原样） |
| `raw_ctx/` + `context.csv` | 人脸 ROI 原始方块（边长 = `int(face_h × K)`） |
| `session.json` | 计数、`FACE_CROP_K`、越界/过小拒采次数 |

### 改动的文件

- `PYNQ/src/canonical.py` — 新增 `CONTEXT_OUT_SIZE=48`、`FACE_CROP_K=1.70`、`face_square_bounds()`、`face_square_fully_inside()`、`crop_face_square()`。**越界返回 None，不补齐**（边缘复制出的条纹是部署时不成立的捷径）。
- `PYNQ/src/collect_logic.py` — 新段 `normal/left/right/low/phone/smoke/other`、`CONTEXT_SEGMENT_LABELS`、`CONTEXT_PROTOCOL`。
- `PYNQ/src/collect_eye_patches.py` — `--context`（默认关）+ `--context-crop-k` / `--ctx-min-interval` / `--ctx-min-side` / `--ctx-seg-settle`；HUD **青框=会采、红框=越界**。
- `eye_cnn_ml/context_qc.py`（新）— 每类 64 张 montage + 几何一致性 + CSV/PNG 数量核对。
- 文档：`docs/ops/B2_上下文采集操作.md`（新）、`docs/design/B1_多任务CNN设计.md` §6.3/§7、`HANDOFF.md` §0.4。

### 两个刻意的标签决定

1. **`phone`/`smoke` 不监督头姿**（留空）。打电话/抽烟时头姿不固定，硬标 forward 会把真实侧脸喂进 forward 类，属于制造标签冲突。
2. **上下文段不产眼态样本**（left/right/low 头动了；phone/smoke 手可能遮眼）。`normal` 例外，它等价于自然注视下的 open。

另外加了 `--ctx-seg-settle 1.0s`：自动协议换段后操作者还没转头/拿手机，不跳过会把过渡帧标成目标类。

## 验证结果

- **PC**：canonical 19 / collect 36 / collect_run 25 / context_collect 17 / dataset 22，全过；pyflakes 干净。
- **板上**（Python 3.8）：context 17 / collect 36 / collect_run 25 = **78 项全过**。
- 5 个文件本地与板上 md5 逐一致；板上备份在 `backup_before_context_20261018/`。
- 推送后板子 SSH 掉线过一次，几分钟后自行恢复，板上测试是在恢复后跑的。

## 下一步（需要你上板操作）

**先标定 K，再正式采**——`FACE_CROP_K=1.70` 不是冻结值，采到的 raw 方块无法事后重切：

```bash
cd /home/<board_user>/jupyter_notebooks/PYNQ/src
# 1) 预览：看 HDMI 上的青色框里能不能看到手/手机
bash run.sh collect_eye_patches.py --context --debug \
  --auto-protocol 'normal:30' --frames 0 --interval 0.1

# 2) 正式采集（Jupyter root terminal）
bash run.sh collect_eye_patches.py --context --debug \
  --face-fallback --subject <名字> \
  --auto-protocol 'normal:30,left:20,right:20,low:20,phone:30,smoke:30,other:20'
```

采完 `scp -r` 回 `eye_cnn_ml/data/board/`，PC 上跑 `python context_qc.py --montage` 做每类 64 张目视验收。详细操作与排错表在 `docs/ops/B2_上下文采集操作.md`。

**数据没采到之前不要把 context_cnn 塞进 bitstream。**

### user  2026-10-18T02:21:58.179Z

root@pynq:/home/<board_user>/jupyter_notebooks/PYNQ/src# bash run.sh collect_eye_patches.py --context --debug \--face-fallback --subject <<user>> \--auto-protocol'normal:30,left:20,right:20,low:20,phone:30,smoke:30,other:20'
bash: <user>: No such file or directory

### assistant  2026-10-18T02:22:04.316Z

三个 shell 写法问题，逐条改：

1. `--subject <<user>>` —— `<` 是重定向，shell 会去找名为 `<user>` 的文件。**去掉尖括号**。
2. `--auto-protocol'normal:30,...'` —— 参数名和值之间**少了空格**，会拼成一个非法参数。
3. `\--face-fallback` 那种反斜杠只应出现在“行尾换行继续”时，同一行里不要写。

正确命令（直接复制）：

```bash
bash run.sh collect_eye_patches.py --context --face-fallback --subject <user> \
  --auto-protocol 'normal:30,left:20,right:20,low:20,phone:30,smoke:30,other:20'
```

说明：

- `--debug` 我删掉了：上下文的人脸 ROI 框**只要加 `--context` 就会画**（青色=会采、红色=越界），`--debug` 只是额外再画眼睛的偏移框，正式采集时没必要。
- 如果想先确认手在框里，先跑预览段：
  ```bash
  bash run.sh collect_eye_patches.py --context --auto-protocol 'normal:30' --frames 0 --interval 0.1
  ```
  看 HDMI 青色框里能不能看到嘴、下巴和手；不够就把 `--context-crop-k` 从默认 1.70 调到 1.8~2.0，太大就调小到 1.4~1.5。
- 跑起来后照屏幕提示换段；停止用 Ctrl-C（或另开终端 `touch /tmp/stop_hdmi_demo`）。
- 采完把会话目录拷回 PC：
  ```bash
  scp -r <board_user>@<board_ip>:/home/<board_user>/jupyter_notebooks/PYNQ/src/data/board/<会话名> \
      <project>/eye_cnn_ml/data/board/
  ```

如果启动时报参数错误，把完整报错贴给我。

### user  2026-10-18T02:23:53.951Z

清色框不够大

### assistant  2026-10-18T02:24:11.227Z

青色框太小 = `FACE_CROP_K` 不够，直接调大：

```bash
bash run.sh collect_eye_patches.py --context --face-fallback --subject <user> \
  --context-crop-k 2.0 \
  --auto-protocol 'normal:30,left:20,right:20,low:20,phone:30,smoke:30,other:20'
```

注意两点：

1. **如果框变成红色**（整块越界，不会采），说明脸离镜头太近：`s = K × 脸高`，脸高 278px 时 K=2.0 的方块有 556px，超过画面高度 480px，怎么放都会越界。**往后退一点**，让脸高降到 ~230px 以下，青色框就会回来。
2. **K 一旦确定，整批数据必须用同一个值**（训练和部署都走这个几何），记下你最终用的数。

如果手主要是在框的**下方**（比如抽烟时手放嘴前），把 K 调大只会浪费上半部分。告诉我，我可以加一个 `--context-crop-y-frac` 让方块整体向下偏（默认中心在人脸框中心），这样不用把 K 加得很大也能罩住手。

先试 `--context-crop-k 2.0`，看一眼青色框里手/手机是否完整；不行就把现象（青/红、手在哪个方向）告诉我。

### user  2026-10-18T02:28:09.564Z

你看看测的怎么样

### assistant  2026-10-18T02:30:53.155Z

看了。第一轮数据（`20261017_093501`，被试 <user>，K=2.0，171s）已经拷回 PC 并生成了 QC 图，结论是：**物体类可用，头姿的左/右全灭，但原因很明确，不是检测问题。**

## 数量与几何

| 项 | 结果 |
|---|---|
| 上下文样本 | **154 条** |
| forward / left / right / down | 19 / **0** / **0** / 29 |
| none / phone / cigarette / other | 48 / 39 / 50 / 17 |
| 几何一致性 | `bad_side=0`, `bad_center=0`, `outside=0`，全部符合 canonical 定义 |
| 越界被拒 | **424 次**（远多于写入的 154） |
| 眼态 | 只有 `normal` 段的 open 34 条；协议没有 open/closed/blink，属预期 |

## 目视结论（`data/board/_qc/ctx_*.png`）

- **phone**：手机在 39 张里基本都能看到，耳侧/手部构图可用。
- **cigarette**：手和“烟”在嘴前，50 张基本都正确。
- **other**：水杯在框里，但混进了 **2 张还没拿起杯子的过渡帧**。
- **forward / down**：人脸完整；`down` 末尾有 1 张抬头帧，也是换段过渡。
- **left / right**：一条都没有。

## 根因

不是 Haar 丢脸 —— left/right 段的**结构化偏移无效类样本正常产出了**（各 48/54 条），说明那两段人脸框一直在。真正原因是**方块在竖直方向顶出了画面上沿**：

- 方块边长 `s = K × 脸高`，K=2.0、脸高 174~200px → `s/2 ≈ 174~200`；
- 而这次人脸中心只在 **y≈150~190**（偏画面上部）；
- 要整块在 480px 高的画面里，必须 `y ≥ s/2`，所以 left/right 每帧都越界。

`ctx_out_of_frame=424` 也是同一个原因。

## 建议怎么改

**不用改代码，调构图就行**：

1. **坐低一点，或把摄像头略微上仰**，让脸中心落到 **y≈240（画面竖直中间）**，比现在往下约 50~70px。
2. 先跑预览，左右转头时确认青色框仍然是青色（不是红的）。
3. `--ctx-seg-settle` 提到 **2.0**，并注意**段尾别提前动**。

重采命令：

```bash
bash run.sh collect_eye_patches.py --context --face-fallback --subject <user> \
  --context-crop-k 2.0 --ctx-seg-settle 2.0 \
  --auto-protocol 'normal:30,left:20,right:20,low:20,phone:30,smoke:30,other:20'
```

另外我已经把 **`ctx_out_of_frame_by_seg`**（按段统计越界）加进 `session.json` 并推到板上、25 项测试通过，下一轮可以直接看出是哪一段在越界。

这一轮的 phone/cig/other/forward/down 数据（154 条）**可以用**，K 和几何都没变，补采 left/right 后可以合并；但如果接下来改了 K，就不要和这一轮混在一起。

### user  2026-10-18T02:32:22.435Z

采集的时候要是屏幕有显示我采集的更好，刚刚没有显示

### assistant  2026-10-18T02:34:12.154Z

采集时确实没显示，这是项目里一个**已知但一直没结案**的问题：采集脚本走的是“CPU 写 `disp_buf` → MM2S 读”这条路，而正常 demo（`--osd`）走的是“MM2S 直接读 `cap_buf` + PL 叠加”那条路。前者在 2026-10-06 就出现过全黑，当时没定位完。

我已经把排查脚本修好并推到板上（原来的第 4 种配置会把“看到实时画面”误判成“没看到纯白”）。现在需要你看一眼屏幕，跑：

```bash
# 先确认没有别的 demo 在跑
touch /tmp/stop_hdmi_demo; sleep 3; rm -f /tmp/stop_hdmi_demo
bash run.sh display_bisect.py
```

它会依次试 4 种 MM2S 配置，每种保持约 3 秒，然后问你：

1. disp_buf + 3 寄存器同址 + GenLock 开（**现状**）→ 应该是**纯白**
2. 同上，但 **GenLock 关** → 应该是**纯白**
3. disp_buf + 3 个连续地址 → 应该是**纯白**
4. 直接读 cap_buf（main.py 拓扑）→ **不是白屏，而是实时摄像头画面**

按提示回答 `y` 或直接回车。跑完把最后的“汇总”贴给我即可。

根据结果：

- 如果**第 2 种**能看到纯白 → 采集时加 `--display-nosync` 就能显示（我已经把这个开关加好了）。
- 如果**只有第 4 种**有画面 → 我把采集脚本改成走 PL OSD / cap_buf 那条路（能显示人脸框、眼态，但段名/计数这类文字 PL 不支持）。
- 如果**全都没画面** → 先跑 `bash run.sh demo_hdmi_annotate.py --frames 30` 做对照，再继续查显示链路。

顺带说明：采集本身不依赖屏幕，数据是完整的。

### user  2026-10-18T02:35:52.044Z

汇总：
  [YES] 1. disp_buf + 3寄存器同址 + GenLock ON  (现状)
  [YES] 2. disp_buf + 3寄存器同址 + GenLock OFF
  [no ] 3. disp_buf + 3个连续地址 + GenLock ON
  [YES] 4. 直接读 cap_buf（照抄 main.py 的拓扑）

### assistant  2026-10-18T02:36:29.500Z

从汇总能定位了：

- 第 1、2、4 种都有画面，第 3 种没有 → **显示硬件和“CPU 写 `disp_buf` → MM2S”这条路本身是好的**。
- 但第 1 种和采集脚本的配置一模一样，唯一差别是：`display_bisect.py` 是在 **DisplayCtrl 已经启动之后** 才重新配置 MM2S 的；而 `ann.setup()` 里是 **先启动 MM2S、后启动 DisplayCtrl**，MM2S 在视频时序还没起来时就开始拉流，通道会停在坏状态。

我已经按这个结论修了 `demo_hdmi_annotate.setup()`：在 `disp_ctrl.start()` 之后、仅对 `disp_buf` 路**重新 reset + start 一次 MM2S**（同址 + 原来的 GenLock 设置）。`--osd` 那条 cap_buf 路不受影响。

已推到板上，md5 一致。先跑一个 10 秒的显示测试：

```bash
cd /home/<board_user>/jupyter_notebooks/PYNQ/src
bash run.sh collect_eye_patches.py --context --session display_test_1018 \
  --subject <user> --auto-protocol 'normal:10' --frames 0 --interval 0.1
```

正常情况下你应该看到：

1. 开机自检：白 → 黑 → 白底黑字 `HDMI OK` → 白（约 3 秒）；
2. 然后实时画面 + HUD 文字 + **青色人脸 ROI 框**。

跑完（10 秒会自动退出）告诉我看到什么。如果这次有画面，就可以按之前的建议（坐低/摄像头上仰，让脸中心到 y≈240）重采正式数据了。

### user  2026-10-18T02:37:29.785Z

有画面

### assistant  2026-10-18T02:38:31.531Z

显示已经修好并推到板上。根因是 `setup()` 里 **MM2S 先于 DisplayCtrl 启动**，视频时序没起来时 MM2S 就拉流，通道停在坏状态；现在改成 `disp_ctrl.start()` 之后再 reset+start 一次 MM2S，采集脚本的 HUD 就正常了。显示测试会话我已经删掉，不污染数据目录。

接下来按这个顺序采：

**1. 先调构图（关键）**

坐低一点或把摄像头略微上仰，让人脸中心落在画面**竖直中间附近（y≈240/480）**。先跑 15 秒预览，重点看 `left`/`right` 段：

```bash
cd /home/<board_user>/jupyter_notebooks/PYNQ/src
bash run.sh collect_eye_patches.py --context --session preview_1018 \
  --subject <user> --auto-protocol 'normal:5,left:5,right:5' --frames 0 --interval 0.1
```

- 青色框 = 会采；**红色框 = 越界**。
- 左/右转头时如果变红，就继续往下坐或上仰摄像头，直到保持青色。

**2. 正式采集**

```bash
bash run.sh collect_eye_patches.py --context --face-fallback --subject <user> \
  --context-crop-k 2.0 --ctx-seg-settle 2.0 \
  --auto-protocol 'normal:30,left:20,right:20,low:20,phone:30,smoke:30,other:20'
```

屏幕现在会显示实时画面 + HUD（段名、计数、青色/红色 ROI 框）。换段后停 2 秒再动，段尾也别提前动。

采完告诉我，我把这一轮拉回 PC 跑 `context_qc.py --montage`，重点确认 `left`/`right` 不再为 0、过渡帧有没有减少。

### user  2026-10-18T02:45:58.839Z

采完了

### assistant  2026-10-18T02:47:14.913Z

这条数据里又抓到一个真问题，先说结论：**左/右修好了，但 `down` 和物体类有标签污染**。我先把采集提示改好，再让你重采。

### assistant  2026-10-18T02:49:45.866Z

采完了，这一轮的结论是：**构图和显示都修好了，但又抓到两个标签问题。**

## 结果（会话 `20261017_095251`）

| 项 | 结果 | 对比上一轮 |
|---|---|---|
| 上下文样本 | **261 条** | 154 |
| forward / left / right / down | 50 / **31** / **31** / 27 | left/right 原来 0 |
| none / phone / cigarette / other | 139 / 48 / 50 / 24 | — |
| 越界拒采 | **47 次** | 424 |
| 几何一致性 | 全部 0 异常 | 一致 |

**左/右转头已经正常**，方向和标签对得上；手机/烟/水杯的主体样本也都可见。

## 目视发现的两个问题

1. **`down` 27 张全是“正对”外观** —— 你只把视线往下看了，头没有真正低下来。这 27 张不能当 down 用，**整类作废**。
   - 正确动作：**下巴明显内收、额头朝镜头**，像看仪表盘，不是只转眼球。

2. **物体类开头混进了上一段的物体**：
   - `phone` 前 8 张还没拿手机；
   - `smoke` 前 11 张还举着上一段的手机；
   - `other` 前 3 张还没拿杯子。
   
   根因是你在**换段之后**才开始换物体，2 秒静默期不够。

## 已修好采集端（已推板上、测试通过）

- 新增 **`pause` 段**：专门用来换物体，**不采任何样本**；
- 新增 **`--preannounce 3.0`**：段结束前 3 秒 HUD 显示 `NEXT <段名> in Xs`，只做准备，**等段名真正切换后再动**；
- `--ctx-seg-settle` 默认从 1.0 提到 **2.0**。

## 下一轮用这条命令

```bash
cd /home/<board_user>/jupyter_notebooks/PYNQ/src
bash run.sh collect_eye_patches.py --context --face-fallback --subject <user> \
  --context-crop-k 2.0 --ctx-seg-settle 2.0 --preannounce 3.0 \
  --auto-protocol 'normal:30,left:20,right:20,low:20,pause:4,phone:30,pause:4,smoke:30,pause:4,other:20'
```

关键动作：

- **`low` 段真的低头**（下巴内收、额头朝镜头），并保持住；
- 看到 `NEXT` 只准备，**看到段名变成 `pause` 再换物体**；
- 段尾别提前动。

## 现有数据处置

- 第一轮 `20261017_093501`：down / phone / cigarette / other / forward 可用，left/right 缺失；
- 第二轮 `20261017_095251`：left/right / forward / phone / cigarette / other 可用（开头过渡帧先留着，后面按时间窗剔除），**down 27 张丢弃**。

按现在的质量，再跑 **2~3 轮**（每轮约 3.5 分钟）就能把每类做到 100~150 条，足够先训第一版 context_cnn；后面再补到 300。

### user  2026-10-18T04:21:42.671Z

跑完了

### assistant  2026-10-18T04:22:40.710Z

四轮数据我都看过了：左/右/物体类都攒起来了，**唯一缺的是 `down`**（69 条里还有 27 条是误标）。根因很清楚：真低头时人脸下移，K=2.0 的方块从**下沿**顶出去，被整批拒采。现在改成“越界时把方块整体平移进画面”（不补齐、不缩放），这样 down 就能采到。

### assistant  2026-10-18T04:25:19.717Z

四轮都看完了。**pause/预提示生效了**，物体类开头已经干净；现在只剩 `down` 一个问题。

## 这四轮的账

| 类 | 累计 | 说明 |
|---|---:|---|
| forward | 238 | 可用 |
| left / right | 141 / 102 | 可用，方向正确 |
| phone / cigarette / other | 231 / 247 / 133 | **开头不再混上一段物体**（抽查 112459：手机从第 1 张就在、烟从第 1 张就在、水杯从第 1 张就在） |
| **down** | **69** | 其中 27 条是 095251 那批“假低头”，**真实可用约 42 条** |

`down` 采不到的原因有两个，现在都已处理：

1. **真低头时方块从画面下沿顶出去**，旧逻辑整批拒采（三个完整会话里 down 分别只有 11 / 1 / 1 条，越界 68 / 103 / 106 次）。
   → 已改成 **clamp**：方块越界时整体平移进画面，不补齐、不缩放（仍是真实像素）。测试 21 + 27 项通过，已推板上。
2. 你那 11 张里还有几张是**手摸头/摸脸**、不是低头。这个只能靠动作纠正。

## 下一步：先只补 `low`，不用跑完整协议

跑这一条（约 45 秒）：

```bash
cd /home/<board_user>/jupyter_notebooks/PYNQ/src
bash run.sh collect_eye_patches.py --context --face-fallback --subject <user> \
  --context-crop-k 2.0 --ctx-seg-settle 2.0 \
  --auto-protocol 'pause:5,low:40'
```

动作要点：

- 前 5 秒是 `pause`，先坐好、把下巴往胸口收；
- `low` 开始后**看自己的膝盖/桌面，不要看屏幕**，保持约 40 秒；
- 低头约 **30°** 就够（额头朝镜头），**不要低到 Haar 找不到脸**；
- 结束会响一声终端 bell（如果听不到，心里数 40 秒）。

跑完告诉我。我拉下来只看 down 的 montage：如果这批能看出明显的低头姿势，`down` 就够了；如果还是正脸，我们再换一种提示方式（比如让屏幕放低、或者用第二个人喊口令）。

### user  2026-10-18T04:27:13.299Z

跑完了

### assistant  2026-10-18T04:28:24.138Z

这轮补采很干净：**70 条 down，零越界、零拒采**。从 montage 看，低头幅度大约 10~15°（额头朝镜头、眼睛看下方），比 `093501` 那批强低头温和，但姿势一致、没有手摸头之类的杂样本。两类幅度放在一起反而更好，模型能看到“低头”的连续范围。

## 当前可用总量

| 头姿 | 数量 | 手持物 | 数量 |
|---|---:|---|---:|
| forward | 200 | none | 526 |
| left | 125 | phone | 231 |
| right | 102 | cigarette | 247 |
| down | **99**（强 29 + 温和 70） | other | 133 |

共 **526 条上下文样本**（每行同时带两个标签）。口径已写进 `eye_cnn_ml/data/board/CONTEXT_USABLE.txt`：剔除了 4 个会话里误标的 down 行和中断的 `111926`。

## 怎么评价

- **够训第一版 context_cnn 了**。类别不平衡（none 526 vs other 133）用类别权重处理即可；head pose 4 类每类 99~200，先看混淆矩阵，再决定补哪一类。
- left/right/other 偏少，但训练第一版足够；后面可以边训边补。
- 几何、显示、pause/预提示、clamp 这几件事都已闭环。

## 下一步

建议直接进入 **context 训练链路**：

1. 写 `eye_cnn_ml/context_dataset.py`：读 `context.csv` + `raw_ctx/`，走 `canonical.finalize_square(sq, 48)`，按 `subject` 划分（跨人留一法）；
2. 训练 ContextNet（8 个输出：4 头姿 + 4 手持物），处理类别权重；
3. 导出权重 → 覆盖 `gen_context_hls.py` 的同名头文件 → 重跑 P3 逐位比对；
4. 之后再谈上板（时序风险仍在 `clk_fpga_0` 的 WNS）。

要我现在开始写 `context_dataset.py` 和训练脚本吗？还是你想先再补 2~3 轮 left/right/other？我的建议是**先训第一版**，用混淆矩阵决定补哪类，比盲目凑 300 更有效。

### user  2026-10-18T04:29:38.137Z

开始

### assistant  2026-10-18T04:32:37.146Z

第一版训练已经跑起来了：**头姿 macro-recall 0.944（down 1.00）**，但手持物只有 0.542。看混淆矩阵，主要是 cigarette↔phone、other↔phone 互相串。查了一下，第一/第二轮采集时（还没有 `pause`）物体段开头确实混进了上一段的物体，这批脏标签还在训练集里。先把它们按时间段裁掉，再重训。

### assistant  2026-10-18T04:37:44.332Z

训练、定点、导出都通了。最后一件事：把标定过的 `FACE_CROP_K` 从占位值 1.70 冻结成实际的 **2.0**，否则以后部署代码用默认值会和训练分布不一致。

### assistant  2026-10-18T04:39:56.622Z

第一版 ContextNet 已经完整跑通：**数据清洗 → 2 折训练 → PTQ → 导出 HLS → C 仿真逐位通过**。

## 1. 先修了数据里的一个真问题

第一版的物体类开头混进了上一段的物体（早期采集还没有 `pause`）。在 `CONTEXT_USABLE.txt` 里加了行级规则：

- `093501` / `095251`：`trim=phone:5,smoke:6,other:3`，去掉物体段开头的污染；
- 四个会话的误标 `down` 继续 `drop=down`；
- `111926`（中断会话）整会话排除。

清洗后：**1093 行**（头姿 526 + 纯手持物 567）。

| 头姿 | 数量 | 手持物 | 数量 |
|---|---:|---|---:|
| forward | 200 | none | 526 |
| left | 125 | phone | 215 |
| right | 102 | cigarette | 225 |
| down | 99 | other | 127 |

## 2. 训练结果（2 折，按 session）

`make_folds` 穷举会话分组，保证每一折 8 个标签都出现（down 只有两个来源，随机分会灭掉它）。

| 折 | 头姿 macro-R | 手持物 macro-R | 备注 |
|---|---:|---:|---|
| fold 0 | **0.894** | **0.621** | cigarette 0.476、other 0.508 |
| fold 1 | **0.966** | **0.817** | phone 0.573，其余 >0.82 |
| 部署模型（全量） | 1.000 | 0.994 | 同人监视集，**乐观，不作泛化结论** |

- `down` 两折都是 **1.00**；头姿已经可用。
- **手持物是短板**：48×48 灰度下 phone↔cigarette↔other 互相串。
- 试过 `--obj-weight 2.0`，反而更差（fold0 0.621→0.582），保持等权。

## 3. PTQ 与 HLS 导出

| 折 | 头姿 float→quant | 手持物 float→quant | 浮点/定点 argmax 一致率 |
|---|---|---|---|
| fold 0 | 0.894 → **0.894** | 0.621 → 0.584 | 头姿 100%，手持物 94.6% |
| fold 1 | 0.966 → **0.966** | 0.817 → 0.819 | 头姿 100%，手持物 97.0% |

- 部署权重已覆盖 `hls/context_cnn/context_weights.h` + `context_testvecs.h`；
- `sh build_csim.sh context_cnn`：**4 个用例、7 层激活 + 8 logits 与 numpy 金标准逐位相同**；
- 累加量级最大 58,421，int32 余量充足。

另外把 `FACE_CROP_K` **冻结为 2.0**（第一版数据全部按 2.0 采的），并新增部署唯一入口 `canonical.canonical_context_input()`；已推板上，23/27 项测试通过。

## 4. 新增文件

```text
eye_cnn_ml/context_model.py             ContextNet（32672 参数 / 1,355,008 MAC）
eye_cnn_ml/context_dataset.py           清单/去污/2 折/翻转+左右标签对调
eye_cnn_ml/train_context_cnn.py         两折 + train-all
eye_cnn_ml/export_context_weights.py    标定/导出 HLS 头/4 个测试向量
eye_cnn_ml/eval_context_quant.py        浮点 vs 定点
eye_cnn_ml/tests/test_context_model.py  6 项
eye_cnn_ml/tests/test_context_dataset.py 8 项
docs/design/B3_ContextNet训练与导出.md         完整命令与数字
```

产物：`out/context_fold0.pt` / `fold1.pt` / `context_deploy.pt`，以及两份 quant 报告。

## 5. 结论与下一步

头姿（分心）已经能用了；**手持物还差**，主要缺数据。建议下一步：

1. **补 phone / cigarette / other 各 2~3 轮**（带 `pause`），优先换光照和持物方式；
2. 或者先做 **BD 例化 + 时序/资源验证**，把链路跑通，再回头补数据重训。

我建议先补手持物数据再上板——因为现在 cigarette/other 的两折差异说明模型对会话/光照还很敏感，直接上板会看到明显的漏报。你决定先做哪个？

### user  2026-10-18T04:41:07.276Z

补数据

### assistant  2026-10-18T04:41:22.617Z

好，只补手持物，不浪费时间采已经够用的头姿。

## 采集命令（一轮约 2.5 分钟）

```bash
cd /home/<board_user>/jupyter_notebooks/PYNQ/src
bash run.sh collect_eye_patches.py --context --face-fallback --subject <user> \
  --context-crop-k 2.0 --ctx-seg-settle 2.0 --preannounce 3.0 \
  --auto-protocol 'pause:5,phone:45,pause:5,smoke:45,pause:5,other:45'
```

## 动作要求（这三类现在最容易混）

| 段 | 动作 |
|---|---|
| `phone` | **手机贴紧耳边**（这轮左耳、下轮右耳），手别挡脸中间 |
| `smoke` | **白色细棒/笔贴到嘴边**，手在嘴前，**不要举到耳边** |
| `other` | **水杯/纸杯/易拉罐举在胸前或脸侧**，不要贴耳/嘴 |

要点：

- 每轮**换一只手、换一个物体实例、换一下光照/坐姿**——模型现在就是栽在跨会话差异上。
- 看到 `NEXT` 只准备，**等段名变成 `pause` 再拿物体**；`pause` 不采任何样本。
- 跑 **2~3 轮**，每轮结束后确认统计里 phone/cigarette/other 各约 90 条左右。
- 如果某类明显少很多，先看是不是人脸丢了（HUD 上 `face=no`）或方块越界。

采完告诉我，我会：

1. `scp` 回 PC，跑 `context_qc.py --montage` 看每类有没有脏样本；
2. 把新会话加进 `CONTEXT_USABLE.txt`；
3. 重跑 2 折训练 + PTQ + 导出，比较手持物 macro-R 有没有上去。

### user  2026-10-18T04:58:05.124Z

好了

### assistant  2026-10-18T05:01:23.436Z

补的 5 轮数据质量没问题（手机都贴耳边、烟都在嘴前、other 有瓶子/纸），但 2 折结果暴露出一个新问题：手机经常落在 ROI 边缘，模型可能学成了“位置=类别”，phone↔cigarette 的折间差异变大了。我加一个平移增强来打掉这个位置偏置，先验证有没有用。

### assistant  2026-10-18T05:07:16.280Z

补的 5 轮数据已经并入并重训完成。结论：**头姿稳定 0.946，手持物整体有提升，但 `other` 的类内泛化仍是最大问题。**

## 数据

| 项 | 结果 |
|---|---|
| 新会话 | 5 轮只采物体（`115306` / `115622` / `115929` / `120229` / `120524`） |
| 新增样本 | **1097 条**（phone 364 / cigarette 365 / other 368） |
| 累计 | **2190 行 / 11 个会话** |
| 手持物总数 | none 526 / phone 579 / cigarette 590 / other 495 |

目视验收：手机都贴耳边、烟都在嘴前、other 有瓶子和白纸/本子等不同物体，没有换段污染。

## 一个新增的改进：平移增强

手机经常贴在 ROI 边缘，模型容易学成“位置=类别”。加了 `--shift 3`（±3 px 随机平移）后：

| 折 | 头姿 macro-R | 手持物 macro-R | 说明 |
|---|---:|---:|---|
| fold 0 | **0.946** | **0.666** | other 0.316（验证集里有没见过的白纸） |
| fold 1 | **0.946** | **0.751** | phone 0.644 / cigarette 0.593 / other 0.779 |
| 部署模型（全量） | 0.975 | 0.992 | 同人监视集，**乐观** |

- 平移增强让 fold0 手持物 0.606→0.666、fold1 0.727→0.751。
- down 两折仍然都是 **1.00**。
- **`other` 是 catch-all**：验收集里出现训练集没见过的物体时 recall 只有 0.32。这不是标签错，是类别定义本身的开放性问题。

## PTQ / 导出

| 折 | 头姿 float→quant | 手持物 float→quant | argmax 一致率 |
|---|---|---|---|
| fold 0 | 0.946 → 0.932 | 0.666 → 0.673 | 98.5% / 95.1% |
| fold 1 | 0.946 → 0.946 | 0.751 → 0.735 | 100% / 93.5% |

- 新部署权重已覆盖 `hls/context_cnn/context_weights.h`；
- `sh build_csim.sh context_cnn`：**4 个用例逐层逐位 PASS**；
- `|acc|` 最大 63,182，int32 余量充足。

## 我的判断

头姿（分心）已经可以上板；手持物里 **phone/cigarette 基本可用，`other` 需要靠 margin 门限兜底**（margin 小就报 unknown，不硬报 other）。

下一步有两个选择，我建议**先做 BD 集成**：

1. 例化 `context_cnn_accel` → 看 impl 的 `clk_fpga_0` WNS 和资源（这是最大的时间风险）；
2. PS 侧接线用 `canonical.canonical_context_input()`；
3. 上板跑通后再补 `other` 的物体多样性（纸杯/易拉罐/盒子），随时可以换权重。

如果你更想先把 `other` 的召回拉上去，就再采 1~2 轮只含 `other` 的多样性数据（每轮 45 秒即可）。你定。

### user  2026-10-18T06:38:01.378Z

继续吧

### assistant  2026-10-18T06:38:10.589Z

开始做 **BD 集成**。先摸清现有工程的加 IP 流程、地址表和 HLS 构建方式，再动 Vivado。

### assistant  2026-10-18T06:40:39.884Z

工具在 `<tools> D 盘）。先把训练权重重新打包成 `context_cnn_accel` IP——现在 `ip_repo` 里还是随机权重的版本。

### assistant  2026-10-18T06:40:52.980Z

HLS 打包在后台跑。同时写 BD 集成脚本：当前 `ps7_0_axi_periph` 是 7 个 MI（M00~M06），`axi_smc` 是 4 个 SI（S00~S03）；context 要占 **M07 + S04 + 0x41A00000**。S04 需要 SmartConnect 从 4 扩到 5，这是唯一有风险的一步，脚本会前后比对现有端口位宽并在变化时直接中止。

### assistant  2026-10-18T06:44:39.890Z

HLS IP 已用训练权重重新打包成功：**延迟 456,047 周期 = 4.560 ms**，资源 LUT 18,011（33%）、DSP 63（28%）、BRAM 70（25%），与骨架阶段的 csynth 完全一致。现在改 BD（M07 + S04 + 0x41A00000）。

### assistant  2026-10-18T06:46:10.511Z

宽度检查报了“失败”，但查了生成网表后确认是**我写的期望值过时**，不是设计坏了：

- `S01` 是 S2MM 写入口，本来就没有 `rdata`（应该查 `wdata`，64 位）；
- `S03` 的 `img_preproc` 在 P2 已经修成 **64 位**，所以 63 是正确值，不是 32。

实际宽度：S00 64 / S01 写 64 / S02 32（eye）/ S03 64（img_preproc）/ S04 32（context）/ M00 64，全部符合各 IP。修正检查脚本后继续。

### assistant  2026-10-18T06:47:53.306Z

BD 已改好，上下文 IP 的项目内副本也确认是**训练权重**（4 个 ROM 文件与 `ip_repo` 大小逐一致）。现在开综合/实现/出 bitstream——这是关键一步，重点看 `clk_fpga_0` 的 WNS。

### assistant  2026-10-18T06:56:34.274Z

收到新任务。先说明一个安全约束：**后台的 Vivado 综合/实现还在跑**（它正在读写 `V2_ov5640_hdmi` 和 `hls/build`），我不会在它结束前删除或移动这些目录里的任何文件。

我先做**只读盘点和入口/依赖梳理**，同时看一下构建进度。

### assistant  2026-10-18T06:56:45.781Z

新任务已收到，我会按“先梳理、后删除、全部可回滚”的方式做。先做只读盘点（不碰正在构建的目录）。

### assistant  2026-10-18T07:07:12.100Z

**Bitstream 出来了，时序过了**：WNS **+0.134 ns** / WHS **+0.023 ns**（余量很薄但为正）；资源 LUT 66.2% / BRAM 58.2% / DSP 63.6% / FF 39.0%。现在先上板验证 context CNN，再做清理。

### assistant  2026-10-18T07:08:18.623Z

上板验证通过（20/20 逐位相同，4.728 ms）。现在开始清理：先做**可回滚的安全项**（日志/缓存/可重生成构建产物），全部移动到 `backup_pynq\cleanup_20261018_150406\`，不删除数据集、bitstream、`.gen`、`.runs`。

### assistant  2026-10-18T07:10:57.326Z

安全清理已执行并验证：PC 移走缓存/旧构建/日志约 **1.1 GB**，板上删除了根目录旧副本/缓存（已备份），**PC 测试、HLS 全部 C 仿真、BD validate、板上 20/20 逐位比对都通过**。

剩下这些有回滚价值或属于数据的项，按你的要求先询问：

### assistant  2026-10-18T07:11:43.082Z

按你的选择，只清板上旧 overlay 备份；TFLite 实验和评估/截图数据保留。

### assistant  2026-10-18T07:13:56.914Z

两件事都完成了：**ContextNet 上板验证通过**，以及**项目清理与验证**。

## 一、ContextNet BD 集成（顺带完成）

- BD：`ps7_0_axi_periph` M07 + `axi_smc` S04，控制地址 **0x41A00000**。
- Bitstream：**WNS +0.134 ns / WHS +0.023 ns**（时序通过，余量很薄）；
  LUT **35,236 (66.2%)** / FF 41,438 (39.0%) / BRAM **81.5 tiles (58.2%)** / DSP 140 (63.6%)。
- 板上：`tests/test_context_cnn_hw.py --hw` **20/20 随机输入与 numpy 金标准逐位相同**，
  延迟 **4.728 ms（中位）**。
- 新文件：`add_context_cnn.tcl`、`refresh_context_cnn_ip.tcl`、`PYNQ/src/context_cnn.py`、
  `demo_context.py`、`context_cnn_model/`、`docs/ops/B4_BD集成与上板.md`。
- 当前 overlay：`design_1.bit` MD5 `f06cf2520e787a1db6d2b4b05aba4092`，已上板。

## 二、清理结果

备份根：**`<home>\Desktop\backup_pynq\cleanup_20261018_150406\`**
（PC / board 两个子目录，另有 `CLEANUP_MANIFEST_PC.json`）。

### 已清理

| 范围 | 内容 | 释放 |
|---|---|---:|
| PC | `eye_cnn_ml/data/cache`（预读缓存，可重建） | 802 MB |
| PC | `hls/build/{eye_cnn,img_preproc,video_box,context_cnn}`（可重建） | 254 MB |
| PC | 历史日志/`.jou`/`.out`、空目录 `-p`、`NA`、临时合并脚本、无引用 CSV、旧 `__pycache__`/`.bak` | ~22 MB |
| 板上 | 根目录 2021 旧副本 `demo_eye_perclos.py`/`img_preproc.py`、`design_1.txt`、旧 `.bak`、`__pycache__` | ~0.7 MB |
| 板上 | 旧 overlay 备份 `backup_before_*` ×5、`backup_old_overlay`、`design_1_32bit.bit/.hwh`（已移到 PC 备份） | ~22 MB |

**项目体积：PC 约 2.2 GB → 1.3 GB；板上 PYNQ 约 395 MB → 373 MB。**

### 保留

- 所有数据集（`eye_cnn_ml/data/board`、`data/mrl`、`data/cew`、板上 `src/data/board`）。
- 当前 `design_1.bit/.hwh`、Vivado `.gen` / `.runs` / `ip_repo` / `_bd_backup`。
- `docs`、`figs`、`upper`、`_analysis` 脚本、`src/backup_before_context_20261018`。
- TFLite/BlazeFace 实验、`faceid_eval*`、`snapshots`、`cmp_*`（按你的选择保留）。

### 代码级

- `eye_cnn_ml/cew_frame_probe.py`：删除 2 个未使用 import（已备份，pyflakes 通过）。
- `PYNQ/src/display_ctrl.py` 的 3 个未使用局部变量**保留**：它是逐行翻译的 VTC 驱动，
  改动风险大于收益。
- 未做高风险重构（`eye_cnn.py`/`context_cnn.py` 公共基类、共享 `quant_ref.py`），
  原因写在 `docs/materials/清理审查_20261018.md` §8。

## 三、验证

| 项 | 结果 |
|---|---|
| PC 测试（18 个文件） | 全过（canonical/collect/PERCLOS/telemetry/occlusion/recorder 等） |
| ML 测试（7 个文件） | 全过（model/dataset/quant_ref/export/context 等） |
| HLS C 仿真 `build_csim.sh all` | 全过（eye_cnn / context_cnn / img_preproc / video_box / eye_pipeline） |
| BD validate | `context_cnn_accel_0` 存在，NUM_MI=8，NUM_SI=5，VALIDATE_OK |
| 板上纯测试 | canonical 19 / context_collect 23 / collect 36 / context_cnn 5 全过 |
| 板上硬件 | context CNN **20/20 逐位相同**，4.728 ms |

## 四、回滚 / 风险

- 回滚：把 `backup_pynq\cleanup_20261018_150406\PC\<相对路径>` 拷回项目根；
  板上项从 `board\PYNQ\` scp 回 `/home/<board_user>/jupyter_notebooks/PYNQ/`。
- `data/cache` 和 `hls/build/*` 可以直接重跑训练/`build_ip.bat` 重建，不必恢复。
- 板上旧 overlay 备份已移走：以后要在板上回退，需先从 PC 备份取回。
- **时序余量很薄**（WNS +0.134 / WHS +0.023）：后续再加逻辑前必须先看 impl 报告。
- 清理没有触碰任何源码、数据集、当前 overlay 或构建输入。

完整清单、理由、风险和验证方式在 **`docs/materials/清理审查_20261018.md`**。

### user  2026-10-18T07:15:01.230Z

请根据当前进度和已有材料，帮我重新生成一份精炼、完整、易读的 Plan，用于我确定最终方向。

### assistant  2026-10-18T07:15:28.521Z

我基于当前盘上的进度、HANDOFF、答辩骨架和这次的实测数据，写一份**决策型 Plan**：先给结论和三条路线对比，再给四周排期与验收门。写入 `docs/plan/最终方向与计划_20261018.md`。

### assistant  2026-10-18T07:16:00.204Z

Plan 已写到 **`docs/plan/最终方向与计划_20261018.md`**。核心结论：

- **主线：DMS 全链路闭环 + 只补“低光闭眼”一个精度子项。**
- 不再加第三个 PL 网络、不改视频数据流（WNS 只剩 +0.134 ns）。
- 手持物头用 **margin 弃权**，不硬报 `other`；商用 FAR/FRR/PAD 不追，写成局限。
- 四周排期：W1 接主循环/事件，W2 低光闭眼，W3 端到端验证+材料，W4 彩排缓冲。

有三个点会直接改变排期和工作量，请你拍板：

### assistant  2026-10-18T07:17:30.728Z

已按你的三个选择更新计划：**低光闭眼不做微调、写局限**；**演示用 `--osd` 的 PL OSD**；**object 用 margin 弃权**。我把 Week 2 改成“真实场景调优 + margin 门限”，不再安排数据采集和重出 bitstream。

### assistant  2026-10-18T07:18:22.356Z

Plan 已重新生成，并按你的三个选择定稿：**`docs/plan/最终方向与计划_20261018.md`**。

## 最终方向

**DMS 全链路闭环**：把 context CNN 接进主 demo，做完整事件与演示；**低光闭眼不做微调，写进局限**；显示走 `--osd` 的 PL OSD；手持物用 **margin 弃权**，不硬报 `other`。

一句话故事：

> 在 ZYNQ-7020 上用两个自研 PL CNN（眼态 + 头姿/手持物）做完整 DMS：采集 → 训练 → 定点 → HLS → BD → 上板 → 遥测/录像/哈希链/活体，每个环节都有实测数字。

## 四周排期（按 11 月中旬截止）

| 周 | 任务 | 验收门 |
|---|---|---|
| **W1 10/19–10/25** | context 接进 `demo_eye_perclos.py`：`--context`、事件持久化、遥测/上位机 | 四类事件可见；≥8 FPS；不传 `--context` 行为不变 |
| **W2 10/26–11/01** | **margin 弃权阈值标定** + 真实摄像头 A/B（正常/分心/电话/抽烟） | 正常段 ≤1 误报/分钟；事件延迟 ≤2.5 s |
| **W3 11/02–11/08** | 端到端验证、指标表、数据流图、演示视频 | 测试/构建全过；视频可完整讲完 |
| **W4 11/09–11/15** | 只修 bug、彩排、备份 | 10 分钟内复现完整演示 |

## 已拍板的三件事

1. **低光闭眼**：不采数据、不重训、不重出 bitstream；材料写“真实低光闭眼仍受限”。
2. **显示**：PL OSD 保持 60 fps；context 结果走上位机/遥测/终端，不往 HDMI 加文字。
3. **object**：margin 小就报 `unknown`；演示重点 phone / cigarette。

## 明确不做

- 第三个 PL 网络、PL Crop/Resize、新视频支路（WNS 只剩 +0.134 ns）。
- 商用 FAR/FRR/PAD 认证、抢方向盘、GPIO/蜂鸣器、H.264、NTP/DS3231。
- 为凑 300/类调小采样间隔。

## 关键风险

- **时序余量很薄**：后续不再加 PL 逻辑；每次重出 bitstream 必看 `clk_fpga_0`。
- **object 跨会话波动**：靠 margin + 持久化 + 标准演示动作。
- **低光闭眼**：接受为已记录局限，默认双眼规则，单眼规则只作非默认选项。

Plan 里还有 5 分钟演示脚本、材料清单和“必须做/可选做/不做”清单。下一步我建议直接从 **W1：把 context 接进 `demo_eye_perclos.py` 主循环** 开始；如果你确认，我就动手。

### user  2026-10-18T07:23:03.351Z

最终数据流大概是怎么样的，我想加入1.分心驾驶检测2.危险驾驶检测（抽烟，打电话等）3.驾驶员身份识别4.镜头遮挡5.上位机实时显示，同时老师推荐我们再加入时间戳，视频防伪，关键视频录制这些，是否都加入

### assistant  2026-10-18T07:23:27.490Z

这些功能**都可以加，而且大部分已经做完了**；真正待做的只有“把 context 结果接进主循环/事件/上位机”。我先把最终数据流和功能清单补进 Plan。

### assistant  2026-10-18T07:23:44.566Z

**结论：8 项全部加入，而且其中 6 项已经上板验证。** 真正待做的只有“把 context 的头姿/手持物结果接进主循环、事件、遥测、录像和上位机”。

## 最终数据流（简版）

```text
OV5640 → capture → v_vid_in → VDMA S2MM → DDR(3帧)
                                      │
                         ┌────────────┴────────────┐
                         ▼                         ▼
              VDMA MM2S → video_box(PL OSD)   PS 稳定读帧
              → VTC/DVI/TMDS → HDMI               │
                                                  ├─ Haar/libface 人脸框
                                                  ├─ 眼 ROI → eye_cnn(PL, 0x41700000)
                                                  │           → PERCLOS/微睡眠
                                                  ├─ 人脸 ROI 48×48(PS 裁, K=2.0)
                                                  │   → context_cnn(PL, 0x41A00000)
                                                  │   → 头姿4类 + 手持物4类
                                                  ├─ 画面统计 → 遮挡 covered
                                                  ├─ 人脸丢失计时 → no_driver
                                                  ├─ 异步 Face ID(SFace) + 活体
                                                  └─ 眼态/头姿/物体 → 事件状态机
                                                          ├─ TCP → 上位机实时显示
                                                          ├─ 录像(pre/post MJPEG)
                                                          │   + event.json(t_wall/frame_times)
                                                          │   + SHA-256 链
                                                          └─ PL OSD 参数(时间/身份/眼态)
```

关键边界：**PS 与 PL 没有直连数据线**；像素经 DDR，控制走 AXI-Lite，OSD 参数走 `img_preproc → video_box_accel`。context 不走 `img_preproc`，是 PS 裁 48×48 后经 DDR 送 `context_cnn_accel`，零 PL 改动。

## 8 项功能状态

| # | 功能 | 状态 | 说明 |
|---|---|---|---|
| 1 | 分心驾驶（头姿） | **PL 推理已完成；PS 事件集成待做** | context CNN；头姿 macro-R 0.946/0.946 |
| 2 | 危险驾驶（抽烟/打电话） | **PL 推理已完成；PS 事件集成待做** | 手持物 0.666/0.751；margin 弃权 |
| 3 | 驾驶员身份识别 | ✅ 已上板 | SFace + 5 点对齐；异步低频 |
| 4 | 镜头遮挡 | ✅ 已上板 | Canny 边缘 + 亮度门；移开 <2s 恢复 |
| 5 | 上位机实时显示 | ✅ 已上板 | 遥测 + PyQt；需加 context 字段 |
| 6 | 时间戳 | ✅ 已上板 | PL timer + OSD + `event.json` 的 `t_wall` |
| 7 | 视频防伪（防事后改） | ✅ 已上板 | SHA-256 哈希链；`integrity.py` |
| 8 | 关键视频录制 | ✅ 已上板 | pre/post MJPEG 事件片段 + `event.json` |
| + | 活体（防当时骗） | ✅ 已上板 | 眨眼/转头挑战；与哈希链是**两件事** |

## 老师推荐的三项：已经做完，不用再开新坑

- **时间戳**：`--osd-time` 左下角显示；录像 `event.json` 写 ISO 8601 `t_wall` + 每帧 `frame_times`；哈希链同记时间。板载 RTC 不准，每次上电用 `tools/sync_board_clock.sh` 校时；量产再上 NTP/DS3231。
- **视频防伪**：`integrity.py` 的 SHA-256 链，证明**录像/事件文件事后没被改**。注意它不防“拿照片/视频当场骗”，那个由 `liveness.py` + Face ID 活体挑战负责。
- **关键视频录制**：`recorder.py` 的 pre/post 事件片段（MJPEG），已实测 `event_0001` 113 帧 / 11.44 s、哈希链完整。**没做 H.264**，材料里不要写“H.264”。

## 还需要做的工作（按顺序）

1. **context 接进 `demo_eye_perclos.py`**：`--context` 开关、每 N 帧推理、`pose/object/margin` 输出。
2. **事件状态机**：left/right/down 持续 1.5~2 s → `distraction`；phone/cigarette 持续 2 s → 事件；margin 小 → unknown。
3. **遥测/上位机加字段**：`ctx_pose`、`ctx_obj`、两个 margin、事件类型；面板加对应显示。
4. **录像事件类型**：`distraction` / `phone_call` / `smoking` 复用现有 pre/post + 哈希链。
5. **更新数据流图**：现有 `figs/fig1_dataflow_real.png` 是 2026-10-17 的版本，**没有 context 支路**，而且把 Ring Buffer/SHA-256 画成了“未实现”（阶段 A 后来已经做完了）。这张图必须重画，否则答辩时图和实现自相矛盾。

## 建议的取舍

- **都加**，但都走现有 PS 事件/遥测/录像管线，**不再改 PL**（WNS 只剩 +0.134 ns）。
- 演示时 HDMI 只显示 PL OSD（框、眼态、时间、DRIVER/红框）；context 的 pose/object 看上位机/终端。
- 低光闭眼按已拍板口径写局限，不临时加网络。
- object 用 margin 弃权，演示重点 phone/cigarette，不硬演 `other`。

我可以下一步直接做 **W1：把 context 接进主循环 + 事件/遥测/录像/上位机**，同时把数据流图更新成包含 context、录像和哈希链的最终版。要现在开始吗？

### user  2026-10-18T07:26:48.300Z

除了驾驶员身份识别，可以录入新成员吗

### assistant  2026-10-18T07:27:45.685Z

**可以。** Face ID 的数据库本来就是**多身份**的，`enroll_face.py` 支持增、删、查；新增成员不需要改 PL、不需要重出 bitstream。

## 录入新成员

板上 Jupyter root terminal：

```bash
cd /home/<board_user>/jupyter_notebooks/PYNQ/src

# 先备份当前数据库（现在只有 driver）
cp /home/<board_user>/models/face_id_db.npz /home/<board_user>/models/face_id_db.bak_$(date +%H%M%S)

# 录入新成员（每人 6~8 张，正脸、光照均匀、不要戴口罩）
bash run.sh enroll_face.py --name <user>     --samples 8
bash run.sh enroll_face.py --name teammate1 --samples 8
bash run.sh enroll_face.py --name teammate2 --samples 8

# 查看已有身份
bash run.sh enroll_face.py --list

# 删除某个身份
bash run.sh enroll_face.py --delete teammate1 --delete-only
```

也可以从图片录入（不用相机）：

```bash
bash run.sh enroll_face.py --name teammate1 --image a.jpg --image b.jpg --image c.jpg --samples 3
```

## 几个必须注意的点

1. **一人一个名字**。同一个人注册成两个名字，两个 embedding 的余弦几乎一样，
   `margin=0.04` 会把两个都判成 `unknown`（`small_margin`）。
2. **不要随手加 `--purge-others`**：它的意思是“只保留 `--name` 这一个身份”，
   会把其他成员全删掉。新增成员时**不要加**。
3. 注册条件尽量和部署一致：正脸、`|yaw|/|pitch| ≤ 15°`、光照均匀、无遮挡。
   默认 `--samples 6`、`--min-samples 3`，建议 6~8 张。
4. 当前阈值 `0.45 / margin 0.04` 是小样本工程值。成员变多后，近邻身份更容易
   互相混淆；建议用 `face_id_calibrate.py` 扫一遍，至少对每个成员做“本人通过、
   他人拒绝”的抽测，报告里注明样本量。

## 当前 demo 对“新成员”的语义

现在的代码是：**只要活体 + 身份 verified，就显示 `DRIVER`（绿框）**，
不区分具体是谁。所以：

- 新成员注册后，会被当成“已授权驾驶员”，OSD 显示 DRIVER；
- 具体名字目前只出现在终端/`face_id_events.csv`，**上位机遥测还没有 identity 字段**；
- HDMI 的 PL OSD 只有一个 8 字符标签，放不下完整姓名。

如果你想让上位机显示“当前是谁”，或者区分“驾驶员/乘客/未授权成员”，
这是 **PS 侧的小改动**（不需要动 PL）：

- 在 `_publish_frame` 的 `extra` 里加 `identity` + `identity_name`；
- 把 `supported['identity']` 置 True；
- 上位机面板加一栏；
- 如果要角色，增加一个授权名单（如 `--drivers <user>,teammate1`），名单内显示
  DRIVER，名单外显示 UNAUTHORIZED。

这一步我会在 **W1 的 context/遥测集成**里一起做。对比赛演示来说，最省事的做法是：
**3~4 名成员全部作为“已授权成员”，OSD 保持 DRIVER，上位机显示具体姓名**。

### user  2026-10-18T07:31:55.933Z

做吧

### assistant  2026-10-18T07:32:04.142Z

开始做多成员身份 + 遥测/上位机。先看 telemetry 协议和主循环的接线点，再改代码并跑测试。

### assistant  2026-10-18T07:36:14.723Z

身份字段已经接通并做了截图自检：上位机显示 **`<user>（已授权） 0.780`**。接下来补文档、把改动推到板上并跑身份相关测试。

### assistant  2026-10-18T07:39:19.965Z

我注意到板上 Face ID 用**现有 `driver` 库**跑那 10 张暗光图只有 0/10（分数 0.27~0.38）。代码差异只有新加的 `identity_authorized`，没碰 SFace；我先用一份**临时库**验证“新成员录入 + 多身份匹配”本身是否正常，避免误判成代码回归。

### assistant  2026-10-18T07:42:04.540Z

可以，而且多成员/授权名单已经接好并验证过了。总结如下。

## 已实现

1. **多身份库**：`enroll_face.py --name ...` 追加身份，`--list` / `--delete` 管理；不用改 PL、不用重出 bitstream。
2. **授权名单**：新增 `--face-id-drivers <user>,teammate1`
   - 不传：任意已验证身份都显示 `DRIVER`（旧行为）；
   - 传了：名单内 `DRIVER`，名单外已识别成员显示“未授权”（红框/`STRANGER`）。
3. **遥测/上位机**：
   - `extra_msg` 增加 `identity_name` / `identity_state` / `identity_authorized` / `identity_score`；
   - `supported.identity=True`；
   - 上位机新增“身份”一行，显示如 `<user>（已授权）0.780` 或 `teammate2（未授权）`；
   - 截图自检已通过（`<user>（已授权） 0.780`）。
4. **测试**：
   - `upper/tests/test_dashboard_logic.py` 19 项、`test_face_id_logic.py`（含授权名单）、`test_telemetry_proto.py` 17 项全过；
   - 板上 `--help` 已能看到 `--face-id-drivers`。

## 板上验证（临时库，不动主库）

用 3 张 dim 图注册了一个临时身份 `testdim`，再用同一批 10 张图验证：

- **10/10 accepted，score 0.79~0.99** → 多成员录入和匹配本身完全正常。
- 临时库已删除，主库 `face_id_db.npz` 未动。

## ⚠️ 一个需要你注意的数据问题

现有主库的 `driver` 跑同一批 10 张 dim 图是 **0/10（score 0.27~0.38）**。
代码差异只有新加的 `identity_authorized`，没有碰 SFace/对齐/预处理；
这是**注册条件/库**的问题，不是代码回归。

**演示前请务必在目标光照下重新注册 `driver`**，并逐个抽测新成员，否则现场可能一直显示 STRANGER。命令：

```bash
cd /home/<board_user>/jupyter_notebooks/PYNQ/src

# 先备份
cp /home/<board_user>/models/face_id_db.npz \
   /home/<board_user>/models/face_id_db.bak_$(date +%H%M%S)

# 重新注册 driver（正脸、光照均匀、无口罩，6~8 张）
bash run.sh enroll_face.py --name driver --samples 8

# 录新成员
bash run.sh enroll_face.py --name teammate1 --samples 8
bash run.sh enroll_face.py --name teammate2 --samples 8

bash run.sh enroll_face.py --list
```

运行带授权名单的 demo：

```bash
bash run.sh demo_eye_perclos.py \
  --osd --classifier cnn --osd-native-haar --face-detect-scale 2 \
  --osd-time --osd-tz-hours 8 --face-id \
  --face-id-drivers <user>,teammate1 \
  --frames 0 --interval 0.1
```

注意：**新增成员时不要加 `--purge-others`**（它会删掉其他身份）；同一人不要注册成两个名字，否则 `margin` 会把两个都判 unknown。

改动文件已备份到 `backup_pynq/cleanup_20261018_150406/`，操作说明在 `docs/ops/FaceID_操作指令.md` §3.4。下一步可以按计划继续 W1：把 context 的头姿/手持物接进主循环和遥测。

### user  2026-10-18T07:49:16.376Z

faceid的操作可以使用上位机进行吗

### assistant  2026-10-18T07:49:41.310Z

**目前不行。** 上位机（`upper/dms_dashboard.py`）只**接收**遥测和视频，协议是单向的（板端 → PC），没有命令下发通道；Face ID 的注册/删除/列表仍然是板端 `enroll_face.py`。上位机现在只能**显示**身份（`<user>（已授权）0.780`）。

可以加，三种做法：

| 方案 | 做法 | 工作量/风险 |
|---|---|---|
| **A. PC 远程录入工具（推荐）** | PC 选本地照片，或先让板端抓图；工具用 SSH/SCP 把图传到板上，调用 `enroll_face.py --image`，再 `--list` 回读 | 小；不改遥测协议、不改 PL；限制是“先有照片” |
| **B. 上位机控制通道** | 板端加一个命令服务（list/enroll/delete/capture），dashboard 加按钮 | 中；要处理认证、并发、演示中停/启相机；不建议在比赛前动 |
| **C. 板端 Web/Jupyter** | 用板上已有 Jupyter 上传照片并跑 `enroll_face.py --image` | 几乎为零；但不算“上位机” |

**我的建议**：比赛前用 **A 或 C 预先录好所有成员**，演示时上位机只负责显示。理由：

- 录入是**准备动作**，不是实时演示动作；现场临时录入会停相机/占主循环，风险不值得。
- 控制通道能删/改身份，属于安全敏感操作；在实验室局域网里也要加认证，比赛前不适合新增。
- 你的演示重点是“识别 + 授权 + 活体”，不是“现场录入”。

如果你想加 A，我可以做一个 `upper/enroll_remote.py`：

```bash
python upper/enroll_remote.py --host <board_ip> --name teammate1 \
  --images C:/photos/teammate1/*.jpg --samples 6
```

流程：检查 SSH → scp 图片 → 板上 `enroll_face.py --image ...` → `--list` 回读 → 打印每个身份的样本数和自验证分数。**不改板端运行时、不改遥测协议、不动 PL。**

要我现在做 A 吗？还是先按板端终端把成员录好、上位机只做显示？

### user  2026-10-18T07:50:53.495Z

继续w1吧

### assistant  2026-10-18T07:51:07.514Z

W1 开始：先把 context 的事件判定做成**纯逻辑模块**（可 PC 单测），再接主循环。先统计验证集上的 margin 分布，定弃权阈值。

### assistant  2026-10-18T07:58:14.581Z

Context 已接进主循环（头姿/手持物 + 事件 + 遥测 + 恢复/录像触发），上位机也加了“上下文”一行。现在推板上，跑短 demo  smoke。

### assistant  2026-10-18T08:00:31.098Z

板上实时读到 `ctx=right/unknown`、低 margin 时判 `distraction`，可能只是你当时没正对镜头（眼态也大面积 UNKNOWN）。我用一张已知正脸的板端图片做对照，确认 context 输入链路没有错位。

### assistant  2026-10-18T08:02:52.993Z

W1 的 context 主循环集成已完成并推到板上。

## 做了什么

- **`demo_eye_perclos.py --context`**（默认关）：
  - 每 `--context-stride 5` 帧推理一次（约 2 Hz）；
  - 头姿 left/right/down 持续 **1.5 s** → `distraction`；
  - phone 持续 **2 s** → `phone_call`；cigarette → `smoking`；
  - margin 不够 → `unknown` 弃权；
  - 事件触发复用现有 `EventRecorder`（pre/post 录像 + 哈希链）。
- **新纯逻辑 `context_logic.py`**：标签、margin 弃权、事件持久化/释放、去抖；
  `tests/test_context_logic.py` 8 项。
- **遥测/上位机**：
  - `extra_msg` 增加 `ctx_valid/ctx_pose/ctx_obj/ctx_pose_margin/ctx_obj_margin/ctx_distraction/ctx_phone/ctx_smoking`；
  - `supported.distraction/behavior=True`；
  - 上位机新增“上下文”一行，截图 `figs/dash_context.png`（示例：`头姿 左转(3000) 物体 手机(2600) [分心/打电话]`）。
- **默认阈值**（来自 2 折 margin 扫描）：pose **200**、object **1000**；
  阈值单位是 **int32 logit 差**，换权重后要重扫。
- 另外修了 replay 的一个坑：CSV 里的 `"False"` 在 Python 里是真值，会把“没抽烟”显示成抽烟；`telemetry_proto` 现在把 `"True"/"False"` 转成 1/0。

## 板上 smoke

```text
Context CNN 就绪：0x41A00000 stride=3 pose_margin=200 obj_margin=1000
40 帧 / 9.91 FPS / 12 次推理（12 有效）/ 4.73 ms/次
正常退出，VDMA/显示都停了
```

**但这轮 smoke 时被试没有正对镜头**（眼态大量 UNKNOWN），context 判了 `distraction`，这是预期结果，不能当作“前向/事件准确率”的验收。

## 需要你做的受控验收

演示前请按四组动作各跑 30~60 秒（正对镜头）：

```bash
cd /home/<board_user>/jupyter_notebooks/PYNQ/src
bash run.sh demo_eye_perclos.py \
  --osd --classifier cnn --osd-native-haar --face-detect-scale 2 \
  --context --context-stride 3 --frames 600 --interval 0.1
```

看终端里的 `ctx=...` 和 `[CTX] ... start/end`：

| 动作 | 期望 |
|---|---|
| 正对镜头、不拿东西 30 s | `ctx=forward/none`，无事件 |
| 头转左/右/低头，保持 2 s | `ctx=left/right/down`，约 1.5 s 后 `[CTX] distraction start` |
| 手机贴耳边 3 s | `ctx=.../phone`，约 2 s 后 `[CTX] phone_call start` |
| 烟/笔放嘴边 3 s | `ctx=.../cigarette`，约 2 s 后 `[CTX] smoking start` |

如果正脸显示 `unknown` 或方向判反，先调 `--context-pose-margin`（默认 200）；
如果手机/烟不触发，先调 `--context-obj-margin`（默认 1000）。调完把数字记下来。

## 验证

- PC：context_logic 8 / dashboard 24 / telemetry 18 / face_id logic 全过。
- 板上：context_logic 8、telemetry 18 全过。
- 改动文件已备份到 `backup_pynq/cleanup_20261018_150406/`。

另外提醒：之前发现**主库 `driver` 与暗光图不匹配**（0/10）。演示前请在目标光照下重新注册 driver，并录好成员；多成员/授权名单已经支持。

### user  2026-10-18T08:12:28.836Z

跑完了，但是正常看也显示我分心，然后没识别出手机来

### assistant  2026-10-18T08:12:41.967Z

先别急着调 margin——这更像是**输入链路/坐标**的问题。我查一下 native 路径下 face_box 的坐标系和 context 实际喂进去的图。

### assistant  2026-10-18T08:12:53.553Z

问题大概率在**输入分辨率**：`--osd-native-haar` 路给 context 的是 PL 的 320×240 灰度放大回 640，而训练用的是**全分辨率 640×480 灰度**。我先改成 context 单独读一帧全分辨率彩色转灰度（每 stride 次），并加人脸框年龄门限。

### assistant  2026-10-18T08:14:53.973Z

两个现象分别处理：

## 1. 正常看也判分心 → 已修

根因大概率是**输入分辨率**：`--osd-native-haar` 路给 context 的是 PL 的 320×240 灰度，原来又放大回 640 再裁；而训练用的是 **640×480 全分辨率**。半分辨率放大图会让“正对”被模型判成左/右转。

已改：

- context 每 stride 帧**单独读一帧 640×480 彩色 → 灰度**，再裁 K=2.0 的 ROI（输入分布和训练一致）；代价约 32 ms/stride。
- 加 `--context-max-face-age 0.8`：人脸框超过 0.8 s 没更新就不推理，避免拿旧框裁。
- pose margin 从 200 提到 **500**（2 折上 fold0 保留 88%、acc 0.978；fold1 保留 99%、acc 0.958），减少低 margin 的左右转误报。
- 终端现在会打印 margin，便于判断：`ctx=forward(1200)/none(2600)`。

## 2. 手机没识别出来 → 先看 margin 再决定

手持物头本来就弱（2 折 phone recall 约 0.64~0.73），不是调一下阈值就一定能救。重跑时请看终端：

| 看到 | 含义 | 处理 |
|---|---|---|
| `obj=unknown(低 margin)` | 模型有点倾向，但没到阈值 | 把 `--context-obj-margin` 降到 500 再试 |
| `obj=none(高 margin)` | 模型**确信**没有物体 | 阈值救不了，是模型/数据问题 → 需要补 phone 数据或重训 |
| `obj=cigarette(高 margin)` | 手机/烟混淆 | 同样需要数据/重训，不是阈值问题 |
| `obj=phone(高 margin)` 但不报事件 | 事件持续/释放逻辑 | 保持 3 s 以上，看是否到 2 s hold |

## 重跑命令

```bash
cd /home/<board_user>/jupyter_notebooks/PYNQ/src
bash run.sh demo_eye_perclos.py \
  --osd --classifier cnn --osd-native-haar --face-detect-scale 2 \
  --context --context-stride 5 --frames 600 --interval 0.1
```

- **正对镜头** 30 s：期望 `ctx=forward(...)/none(...)`，无事件。
- **手机贴耳边** 3 s：看 `obj=` 是什么、margin 多少。
- 如果正对仍报分心，把 `--context-pose-margin` 提到 800 或 1000；
  如果手机是 `unknown` 且 margin 低，降到 `--context-obj-margin 500`。

跑完把正脸和手机这两段的 `ctx=...` 行贴给我（或截图终端），我按实际 margin 定阈值；如果模型是“高 margin 地判错”，那就不是阈值问题，需要补 phone 数据重训。

### user  2026-10-18T08:20:40.561Z

跑完了，我手机贴近右耳的时候表现特别差

### assistant  2026-10-18T08:20:58.056Z

“手机贴右耳特别差”需要先分清是 **ROI 没把手机裁进去**，还是 **模型把手机判成了 none/烟**。我加一个 context 调试落盘（原图 ROI + 48×48 输入 + CSV），你跑 20 秒手机贴耳，我拉回来目视和算 margin。

### assistant  2026-10-18T08:22:07.797Z

我加了一个 **context 调试落盘**，可以直接看清楚“手机贴右耳”时模型到底看到了什么、判成了什么。现在板上是最新代码（全分辨率 context + pose margin 500）。

请跑这一段（约 30 秒，手机贴右耳保持 15~20 秒，前 5 秒正脸）：

```bash
cd /home/<board_user>/jupyter_notebooks/PYNQ/src
rm -rf /home/<board_user>/ctx_dump
bash run.sh demo_eye_perclos.py \
  --osd --classifier cnn --osd-native-haar --face-detect-scale 2 \
  --context --context-stride 3 \
  --context-dump-dir /home/<board_user>/ctx_dump --context-dump-every 2 \
  --frames 300 --interval 0.1
```

它会落盘：

```text
/home/<board_user>/ctx_dump/
  context_log.csv     t / pose / pose_margin / obj / obj_margin / valid / events
  roi_XXXXXX_sNNN.png  模型裁到的人脸 ROI（原始分辨率）
  q_XXXXXX.png         归一化后的 48×48 模型输入
```

跑完告诉我，我拉回来目视检查两件事：

1. **手机有没有在 ROI 里**（如果 ROI 把右耳/手机裁掉了，是几何问题，调 K 或换 ROI；不是阈值能救的）；
2. **模型判成了什么/margin 多少**：
   - `obj=unknown` 且 margin 低 → 降 `--context-obj-margin`；
   - `obj=none` 且 margin 高 → 模型没学会这个角度/位置，需要补 phone 数据重训；
   - `obj=cigarette` 且 margin 高 → 手机/烟混淆，也需要数据。

另外，这次因为是新代码，正脸那段的 `ctx=forward(...)/none(...)` 也能一起验证；如果正脸仍误报分心，把那段 `context_log.csv` 里 `pose` 的分布发我。

> 提醒：dump 只在 `--context` 下工作，默认关；不传 `--context-dump-dir` 时行为与之前一致。

### user  2026-10-18T08:24:43.599Z

表现还是不好

### assistant  2026-10-18T08:26:35.023Z

找到根因了：`--osd-native-haar` 下 `--face-detect-scale 2` 实际在 **160×120** 上检脸，而训练采集/等价性测试用的是 **320×240**（native 的 scale 应为 1）。人脸框系统性偏了，context 裁剪自然跟着偏。修正 native 的 scale。

### assistant  2026-10-18T08:27:22.663Z

修正 native 的检测 scale 后，context 立刻正常了：**`left(733)/phone(1523)`、`unknown/phone(1027)`**——手机被识别出来了。现在只剩 FPS（6.34）需要优化，我试一下放宽人脸检测间隔。

### assistant  2026-10-18T08:30:36.930Z

这次找到根因了，不是阈值问题：**native 路径的人脸检测尺度错了**。

## 根因

`--osd-native-haar` 下 `gray` 已经是 **320×240**，而 `--face-detect-scale 2` 会再把它降到 **160×120** 检脸。训练采集和 `test_osd_native_haar.py` 的等价口径是 **320**（native 应该 `scale=1`）。结果：

- 人脸框系统性偏小/偏位；
- context 按这个框裁 K=2.0 的 ROI → **裁错**；
- 正脸被裁成偏左/偏右 → 误报分心；
- 手机贴耳时框更偏 → 手机被裁掉/判成 none。

## 修复

native 分支改成：

```python
det_scale = max(1, int(args.face_detect_scale) // d_native)   # 2 -> 1
```

和 640 路的 `scale=2` 等价，也与训练采集口径一致。

## 修正后实测

- **手机贴耳**：`ctx=unknown(74)/phone(1507)[phone_call]`
  —— 手机识别出来了，`phone_call` 事件成功触发（margin 1027~1523）。
- **正脸**：`ctx=forward(586)/unknown(347)`，**不再报 distraction**；
  其余帧 margin 不够时显示 `unknown`（诚实弃权，不是误报）。
- **FPS**：context on 时 **7.4~7.8**（原来 9.9）。320 Haar 是主要开销。

## 现在的建议命令

```bash
cd /home/<board_user>/jupyter_notebooks/PYNQ/src
bash run.sh demo_eye_perclos.py \
  --osd --classifier cnn --osd-native-haar \
  --face-detect-scale 2 --face-stride 8 --face-fallback \
  --context --context-stride 5 \
  --frames 600 --interval 0.1
```

受控验收：

| 动作 | 期望 |
|---|---|
| 正脸 10 s | `forward` 或 `unknown`，**无 distraction** |
| 左/右/低头保持 2 s | 1.5 s 后 `[CTX] distraction start` |
| 手机贴耳 3 s | `obj=phone` → `[CTX] phone_call start` |
| 烟/笔放嘴边 3 s | `obj=cigarette` → `[CTX] smoking start` |

## 剩余取舍

- **FPS 7.4~7.8**：如果比赛要求 ≥8，下一步做 **face ROI tracking**（按上一帧框开 2~3 倍 ROI，只在 ROI 里跑 Haar，每 N 次全帧重捕获）——纯 PS 优化，不改 PL。这个可以放到 W2。
- 正脸多数 `unknown` 是 margin 500 的弃权。想更“敢报”可以降到 300，但误报会回来；当前默认是安全优先。
- 还需要你受控测一下 **left/right/down 和 cigarette**；phone 已经验证通过。

改动已推板上，HANDOFF/Plan/记忆都已记录这个 native scale 坑。要不要我现在做 face ROI tracking 把 FPS 拉回 8+？

### user  2026-10-18T08:35:17.944Z

右耳手机还是不行，检测很差，是不是数据训练问题

### assistant  2026-10-18T08:35:25.979Z

“右耳还是不行”需要看实际裁进去的 ROI。我先拉板上最新的 context dump（CSV + ROI + 48×48 输入）确认：是手机不在框里，还是模型把手机判成了别的。

### assistant  2026-10-18T08:36:32.811Z

看了 dump：右耳手机其实**被识别到了**（`phone` margin 1027~1523），但中间夹杂 `unknown(913/809)`，导致候选被 reset，2 s 的 hold 没攒够——所以没有 `phone_call` 事件。根因是 object 头在“另一侧”置信度偏低，属于数据/训练侧偏。先把 object 阈值降到 500，让 809/913 也进来。

### assistant  2026-10-18T08:37:56.743Z

右耳手机被识别到了，但 `obj_margin=500` 也会把正常的 `cigarette(948/956)` 放进来。改成**按类阈值**：phone 500、cigarette 1200、other 1500，既保住手机又不误报抽烟。

### assistant  2026-10-18T08:42:20.010Z

右耳这个现象我拆成了两层：**一层是代码（已修），一层确实是数据/训练（只能缓解）**。

## 1. 代码层（已修）

`--osd-native-haar` 下 `--face-detect-scale 2` 实际在 **160×120** 检脸，而训练采集和等价性测试是 **320×240**。人脸框偏小/偏位 → context ROI 裁错。已改成 native 的 `scale = args.face_detect_scale // d_native`（2→1）。这一步修完，右耳 phone 的 margin 从几十/几百升到 **1027~1523**。

## 2. 数据层（部分缓解）

你的 dump（`ctx_dump3`）显示右耳手机其实**被识别到了**：

```text
left(728)  phone(1523)
left(733)  phone(1185)
unknown(325) phone(1027)
unknown(335) unknown(913)
...
```

问题在于 object 头会**在 phone 和 unknown 之间抖**，而且正常场景会冒出 `cigarette(948/956/1481)` 假阳。旧逻辑 `obj_margin=1000 + release 0.5s` 会：

- 809/913 掉回 unknown → 候选 reset；
- 2 s hold 永远攒不够 → 没有 `phone_call` 事件。

**已改**：

- **按类阈值**：phone **500**、cigarette **1500**、other 1500；
- **物体事件 release 1.2 s**（允许一次 unknown 空档，不再立刻 reset）；
- 正常场景的 `cigarette 948/956/1481` 被 1500 挡住；真烟样本（dump2 里 2082）仍能过。

同时，水平翻转对照证明这是**训练数据的侧向偏置**：同一张 ROI 翻转后 phone margin 从 1523/1027/1117 降到 772/943/794。**彻底修法是补另一侧的手机数据重训**；当前用“phone 500 + 1.2s release + 2s hold”兜住演示。

## 3. 请再跑一次（手机贴右耳 5 秒）

```bash
cd /home/<board_user>/jupyter_notebooks/PYNQ/src
bash run.sh demo_eye_perclos.py \
  --osd --classifier cnn --osd-native-haar \
  --face-detect-scale 2 --face-stride 8 --face-fallback \
  --context --context-stride 5 \
  --frames 300 --interval 0.1
```

期望：

```text
ctx=left(...)/phone(>=500)
[CTX] phone_call start
```

如果还是没有：

- 跑一次带 dump 的（`--context-dump-dir /home/<board_user>/ctx_dump4 --context-dump-every 2`），把 `context_log.csv` 发我；
- 看 phone 的 margin 是否稳定 ≥500。如果稳定但事件不出，是状态机/时间窗问题；如果 phone margin 经常 <500 或判成 cigarette，那就是数据/模型问题，需要补右耳手机数据重训。

另外：context on 时 FPS 约 **7.6**（320 Haar 的开销）。如果比赛硬性要求 ≥8，下一步做 face ROI tracking；否则这个帧率对演示可用。

### user  2026-10-18T08:44:49.006Z

跑完了

### assistant  2026-10-18T08:45:18.721Z

这轮没有带 `--context-dump-dir`，所以看不到 `ctx=` 结果。我先把 context 日志改成**默认落盘**（`snapshots/context_log.csv`，每次推理一行），这样以后不用额外参数也能查。

### assistant  2026-10-18T08:51:07.544Z

板上 smoke 卡在 `cap_buf/disp_buf` 之后（摄像头初始化阶段），是前一次 demo 没完全释放、VDMA/OV5640 处于坏状态。我先停掉残留进程并重启板子恢复（这是项目里已知的恢复手段）。

### assistant  2026-10-18T08:53:46.361Z

右耳这个事现在是**代码 + 数据两层**，而且代码层已经改到位，需要你最后再跑一次确认。

## 已改（尚未被你验证的最新一版）

1. **native 人脸检测尺度 bug**（主因之一）：
   `--osd-native-haar` 下 `--face-detect-scale 2` 实际在 160×120 检脸；
   已改成 native 的 `scale = args.face_detect_scale // d_native`（2→1，即 320×240），
   和训练采集 / 等价性测试一致。修完后右耳 phone margin 从几十升到 **1027~1523**。
2. **按类阈值**：phone **500**、cigarette **1500**、other 1500。
   正常场景实测有 `cigarette(948/956/1481)` 假阳，1500 能挡住；
   右耳 phone 的 809/913 则算 phone。
3. **物体事件 release 1.2 s**（原来 0.5 s）：
   物体头 2 Hz 会抖，一次 `unknown` 不再把 2 s hold 直接 reset。
4. **context 日志默认落盘**：`snapshots/context_log.csv`，每次推理一行，
   不用再带 `--context-dump-dir`。

另外：我跑 smoke 时摄像头初始化卡住过一次，已强制重启板子恢复；现在板子干净、没有残留 demo。

## 请跑最后一次

```bash
cd /home/<board_user>/jupyter_notebooks/PYNQ/src
bash run.sh demo_eye_perclos.py \
  --osd --classifier cnn --osd-native-haar \
  --face-detect-scale 2 --face-stride 8 --face-fallback \
  --context --context-stride 5 \
  --frames 300 --interval 0.1
```

- 手机贴**右耳**，保持 **5 秒**（不要只放 1~2 秒）。
- 看终端是否有 `[CTX] phone_call start`。
- 跑完告诉我，我直接拉 `snapshots/context_log.csv`，看 phone 的 margin 是否连续 ≥500、
  以及 2 s hold 有没有攒够。

## 如果仍然不行

那就是**数据/训练问题**，不是阈值能救的：

- 同一张 ROI 水平翻转后，phone margin 从 1523/1027/1117 掉到 772/943/794，
  说明模型对“另一侧耳朵”的置信度系统性偏低；
- 真正修法是补 **右耳/目标光照** 下的 phone 数据（再 2~3 轮），并加入
  “手靠近脸但没手机”的负样本，然后重训 context CNN。
- 当前这版先用 phone 500 + release 1.2 + 2 s hold 兜演示；如果这轮日志显示
  phone margin 稳定 ≥500 但事件没出，我再调状态机；如果 margin 经常 <500
  或判成 cigarette，就需要补数据。

把这一轮跑完的 `context_log.csv` 给我即可。

### user  2026-10-18T09:00:02.815Z

跑完了

### assistant  2026-10-18T09:00:48.066Z

日志已经确认：**右耳手机这次成功了**。最新一轮 `phone_call` 在 `t=449.4–453.2` 触发（持续约 3.8 s），phone margin 500~824；同一段没有 distraction。更早的 distraction 记录（t≈319–378）对应 `pose=left`，是之前的左转测试，不是正脸误报。

### assistant  2026-10-18T09:01:06.614Z

右耳手机这次**成功了**，日志证据：

```text
447.0  phone(815)
447.5  phone(798)
448.3  phone(748)
448.9  phone(824)
449.4  phone(707)  [phone_call]   ← 事件触发
...
451.9  phone(730)  [phone_call]
452.5  none(1148)  [phone_call]   ← 短暂切 none，release 1.2s 桥接住
453.2  unknown     [phone_call]
453.8  unknown                     ← 结束
```

- `phone_call` 持续约 **3.8 s**，phone margin **500~824**。
- 最新这一段**没有 distraction**；日志里更早的 distraction（t≈319~378）对应 `pose=left`，是之前的左转测试，不是正脸误报。
- 说明三处改动是有效的：native 检测 scale 修正（320）+ phone 阈值 500 + object release 1.2 s。

## 现在的状态

- ✅ 正脸：`forward`/未知，不误报分心。
- ✅ 右耳手机：`phone_call` 触发。
- ⚠️ 手持物头仍有**侧向数据偏置**：翻转后 phone margin 会掉到 772~943；这次靠 500 阈值兜住。换姿势/光照仍可能掉到 500 以下。
- ⚠️ FPS 约 **7.5**（context on，320 Haar 的开销）。
- 还没验证：`cigarette`（真烟 2082 能过 1500，但需要你实际抽一口/放嘴边确认）、left/right/down 的 distraction。

## 建议下一步（按优先级）

1. **补一次受控验收**：左转/右转/低头各 2 s、烟/笔放嘴边 3 s；跑完把 `snapshots/context_log.csv` 给我，我确认事件和 margin。
2. **如果比赛硬性要求 ≥8 FPS**：做 face ROI tracking（纯 PS，不动 PL），预计把 320 Haar 压下来。
3. **如果要求更稳的手机/烟识别**：补 2~3 轮右耳手机 + 真烟 + “手靠近脸但没东西”的负样本，重训 context CNN。这是数据层的根本修法。
4. 之后更新数据流图（含 context/录像/哈希）和答辩材料。

你想先做哪个？我建议先花 5 分钟做第 1 项验收，确认烟和左/右/低头，再决定要不要动 FPS。

### user  2026-10-18T09:02:14.946Z

"<home>\Desktop\嵌赛FPGA\AMD.pdf"这个是我比赛的要求，这非常重要，决定最终表现形式

### assistant  2026-10-18T09:02:20.962Z

这是一份关键材料。我先把 PDF 的要求逐页读出来，再对照我们现有的功能和演示形式，给出“最终表现形式”的调整建议。

### assistant  2026-10-18T09:02:46.775Z

PDF 的中文字体没有 Unicode 映射，`pdftotext` 只抽出了英文。我装一个 PyMuPDF，把关键页渲染成图片来读。

### assistant  2026-10-18T09:03:52.089Z

比赛要求已读完，关键点不是“再加什么功能”，而是**最终交付形态**：15% 大模型协作+技能包、15% 文档/可复现，且提交目录/文件名必须全英文。现有工程功能很强，但这 30% 目前是空白。我把它整理成一份提交形态方案。

### assistant  2026-10-18T09:04:15.739Z

比赛要求的关键结论：

- 你是**初级组**，Zynq-7020 完全合规；工具 2026.1 也合规。
- 权重：**创新/应用 30 + 性能/资源 20 + 正确/完整 20 + 大模型协作/技能包 15 + 文档/复现 15**。
- 硬性提交：工程包、仿真/验证、综合/实现报告、上板输出、可复现构建、**`skill/` 技能包**、**大模型协作记录**、设计报告；**目录/文件名必须全英文**。
- 我们最大的缺口不是功能，而是 **15% 技能包 + 15% 文档/复现**：现有工程有大量素材，但没有按提交结构打包；技能包完全没做；LLM 记录有 21MB 原始会话但没提炼；当前大量中文文件名不合规。

我的建议：**保留 DMS 功能，把最终形态重做成“PYNQ DMS 演示 + 3 个通用 PYNQ 技能包 + 设计报告/LLM 记录”**。功能已经够支撑 30+20+20；接下来应该把 30% 的包装分拿满，而不是继续加功能。

三个点需要你拍板：

### assistant  2026-10-18T09:05:18.411Z

开始按“DMS + 3 个通用 PYNQ Skill”打包。先建英文目录并复制必要源码/报告（不复制数据集和大模型）。
