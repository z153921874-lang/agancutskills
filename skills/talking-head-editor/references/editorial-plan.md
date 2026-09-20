# 整片计划、源时间关键词与审片

v2.9 新增 `scripts/plan_editorial.py`。用于已有精剪 source-map 的混合口播规划与返修，解决只设计几个亮点、关键词沿用错误时间、用技术检查冒充完整审片的问题。不下载模型、不识别语义或声学重音，不改变既有成片。

## 整片规划

先确定保留的原声与实际 source-map，再覆盖完整成片。每个 scene 写清：任务结果 `takeaway`、关注点 `focus`、进入方式 `entry`、退出理由 `exit`、素材标识 `assets`。时长与节点使用真实素材，不能为了满足结构硬套故事起承转合。

角色 `role` 可为 host、broll、evidence、metaphor、relationship、comparison。真人的作用包括提问、判断、转折、情绪和反应，不设置固定真人比例；资料/关系画面应在当前句子确实需要时进入。检查是否整片只有一种固定模板，也不要为了版式数量制造无意义变化。

后段回调注明前段 scene ID 和新的比较意义。素材 ID 相交只证明引用了同一对象，不保证观众能认出，也不证明关系正确；仍需看片。

## 命令

```text
python <skill>/scripts/plan_editorial.py --plan <project>/editorial-plan.json --source-map <project>/source-map.json --output-dir <project>/review-v1 --video <project>/final.mp4 --copy-video
```

输出目录必须尚不存在。`--video` 可省略；提供视频时生成审片网页并记录视频 SHA256。`--copy-video` 复制视频至审片目录并使用相对链接，适合双击 HTML 或本地服务器预览；省略时页面引用原文件绝对路径，移动原文件会导致无法播放。审片目录可能包含用户视频和本地路径，不随 skill 发布。

## 计划格式

```json
{
  "fps":25,
  "duration":4,
  "scenes":[
    {"id":"intro","start":0,"end":2,"role":"host",
     "takeaway":"提出具体问题","focus":"人物表情","entry":"原声起句","exit":"进入解释","assets":[]},
    {"id":"explain","start":2,"end":4,"role":"metaphor",
     "takeaway":"看懂原话比喻","focus":"物体与动作","entry":"比喻词出现","exit":"回到回答","assets":["metaphor-image"]}
  ],
  "cues":[
    {"id":"keyword","scene":"explain","clip_index":1,
     "source_start":20.2,"source_end":20.8,"text":"关键词",
     "timing_basis":"subtitle_verified","evidence":"根据校对的短句字幕定位，待回听",
     "hold":0.8,"lead":0}
  ]
}
```

这里假设 source-map 第二段将源片 20–22 秒放到成片 2–4 秒。`clip_index` 从 0 开始，显式指定源片片段，重复使用同一段时仍能区分。scene 时间是成片秒数，cue 的 source_start/source_end 是源片秒数。

### 时间规则

- scene 必须按序无缝覆盖完整成片；source-map 也须连续且输出节点对齐帧网格。当前仅支持 1:1 时间映射，允许一次帧取整误差；变速不能套用这条公式。
- 关键词需完整保留在指定 clip 内且属于该 scene。涉及删掉的源词、切穿词或跨剪口时拒绝，不把残存音节当成完整关键词。
- 默认 lead=0，入场向后取整到下一帧，不抢在给定词时间前出现。显式提前超过一帧会提示复核，不把“先出字”一律判错；需说明它是否破坏铺垫。
- hold 是期望停留，不能穿过指定 scene 或 clip 末尾。被截短时提示处理：删冗余字、改版式或重新考虑剪口，不能默默让字幕跨段。
- timing_basis：word_verified 为编辑已核对词级时间；subtitle_verified 为短句字幕定位；asr_unverified 为未校对识别结果。后两者保留回听提示；工具不会把填写依据自动变成事实证明。

## 输出怎样接入现有工具

`emphasis.json` 是基础渲染器可以使用的 texts 数组片段，使用成片秒数。将其合并进经过检查的 plan.json，再按 render-plan.md 设计字号、坐标和层次；它不是完整 plan，不应覆盖既有对白 captions。默认坐标来自基础渲染器，不能当作自动避脸排版。

`review.json` 保留场景、解析后的关键词、警告和检查队列。重复焦点、缺素材标识、回调对象不一致等只是提示，不输出相似度或审美评分。

`审片.html` 可定位播放每个分镜、关键词前后、剪口两侧和全片；可记录待检查/已检查通过/需要修改及意见，并导出 JSON。初始全部待检查；点播放不自动通过。页面播放结束依赖浏览器 timeupdate 事件，定位用于主观复核，不是逐帧标注工具。

## 审片到返修

先连续观看理解整片，再定位问题；或先修明显剪口再连续回看。记录具体时点、现象、原因和修改办法，不只写“不高级”。保持观察和推断分开，比如“字先出现”是观察，“有意铺垫”要结合上下文判断。

修改计划后输出新版本，再重新生成审片目录；导出记录绑定原视频与计划哈希，不沿用旧文件的通过状态。读取审片记录时先核对哈希，再处理需修改项目；不能把页面里用户选了通过当成自动审美/声学测量。

没有可用的主观试听能力时，继续完成规划、合成和技术检查，并明确哪些听觉项目仍待审；不默认要求用户逐段批准才能继续工作。生成一份待审清单本身不算完成听觉验收。
