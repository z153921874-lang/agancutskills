# agancutskills

**阿甘的口播剪辑 Skill：从真人讲话，到有重点、有画面、有叙事的成片。**

适合知识讲解、生活口播、商品介绍和混合讲述视频。由 AI 助手根据原话规划剪口、关键词、素材与视觉关系，再调用本地工具完成合成。

[下载 v2.8](https://github.com/z153921874-lang/agancutskills/archive/refs/tags/v2.8.0.zip) · [技能入口](skills/talking-head-editor/SKILL.md) · [功能与边界](skills/talking-head-editor/references/capabilities.md) · [反馈与需求](https://github.com/z153921874-lang/agancutskills/issues)

## 能做什么

- **先把话剪顺**：按语义整理重复、停顿和旁支，保留有效的情绪与反应。
- **让重点看得见**：对白字幕与关键词分层，关键词按讲述顺序出现。
- **让抽象概念可见**：结合实拍动作、照片、资料、对照或关系图；AI 辅助图用于明确标注的示意场景。
- **让素材参与叙事**：局部聚焦、照片退成卡片、连线逐步出现、前文素材回调比较。
- **输出可检查的结果**：MP4、剪辑计划、源时间映射和相应字幕；高级画面通过独立合成模块制作。

这是一套给 AI 助手使用的技能与本地工具，不是双击即用的独立软件。没有承诺任意素材一键生成成熟成片。

## v2.8 的重点

从“每句话配一张图”，进一步走向“先建立对象，再显示关系，最后聚焦重点”。

| 常见问题 | 对应做法 |
|---|---|
| 真人头顶总有重复标题 | 判断、反应、自嘲段减少附加大字 |
| 每张素材都在缓慢推近 | 指定阅读目标，聚焦后停住 |
| 图、字、连线第一帧全部出现 | 按原声逐步建立画面 |
| 后段只重复播放旧素材 | 带回旧对象，参与新的状态比较 |
| 效果越多越看不懂 | 先判断视觉任务，再选择效果 |

新增模块通过 14 项行为检查，并用真实口播制作了 17.16 秒代表段进行选帧检查。范围与未验证项见[验证记录](skills/talking-head-editor/references/validation.md)。用户原片、参考视频和第三方素材不随仓库分发。

## 安装与使用

1. 下载仓库 ZIP 并解压，或执行 `git clone https://github.com/z153921874-lang/agancutskills.git`。
2. 将 `skills/talking-head-editor` 整个目录放入助手的 skills 目录。Codex 的个人技能通常放在 `~/.codex/skills/`，自定义 `CODEX_HOME` 时使用对应目录。
3. 在新任务中调用 `$talking-head-editor`，给出本地口播路径与需求。

例如：

> 使用 $talking-head-editor 剪辑这段口播。先按原话梳理信息，再设计关键词、相关实拍素材和抽象概念的示意画面。真人段保留表情，避免每句话都加大标题。检查代表段后完成成片，并附上素材来源。

联网找素材、生成图片和调用外部服务取决于宿主助手提供的工具及你的授权；本仓库不包含这些服务的账号或额度。

## 本地工具环境

Python 3.10+，以及带 libass、libx264 和 AAC 支持的 FFmpeg。建议在项目虚拟环境中安装：

```bash
python -m venv .venv
# 激活虚拟环境后：
python -m pip install -r requirements.txt
```

渲染器会从 PATH 查找 FFmpeg，支持 `--ffmpeg` 指定路径，也可使用 imageio-ffmpeg 提供的程序。字体、可选语音识别和抠像模型需另行配置，见[运行环境](skills/talking-head-editor/references/local-runtime.md)。

[基础计划示例](examples/plan.json)需先修改素材路径、截取时间与字体：

```bash
python skills/talking-head-editor/scripts/render.py --plan examples/plan.json --output outputs/final.mp4 --check
python skills/talking-head-editor/scripts/render.py --plan examples/plan.json --output outputs/final.mp4
```

示例只演示基础剪辑与关键词。复杂关系画面需要先设计素材并调用独立合成工具，不能把 v2.8 模块函数名填入基础 JSON。

## 当前边界

- 基础渲染器为 v2.7，skill 制作规则与独立合成工具为 v2.8。
- 识别、跟踪和人物抠像是可选能力，需要模型与环境；复杂遮挡和发丝不保证稳定。
- AI 图片加二维推拉不等于生成式视频；没有自动真 3D 或恢复参考片工程的能力。
- 选帧和音量检查不等于完整审片与试听。仍需校对原话、素材关系、字幕和声音。
- 默认不操作剪映界面，不自动购买素材或发布视频。

## 下载、更新与合作

当前版本公开提供下载。欢迎收藏仓库，并在 Issues 提交适用场景和反馈。

目前未配置付费订阅、收款或自动授权服务，也未指定开源许可证。商业授权与合作条款由项目作者后续另行明确。

第三方依赖遵循各自许可证。用户自行引入的视频、字体、照片、音乐和模型需遵守对应来源的使用条件。
