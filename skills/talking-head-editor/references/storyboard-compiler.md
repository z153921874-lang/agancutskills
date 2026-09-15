# 分镜转换为可执行计划

分镜和素材准备完成后，运行 `scripts/compile_storyboard.py --storyboard <JSON> --output-dir <新目录>`。输出plan.json、editorial.json和source-map.json；再执行 `scripts/render.py --plan <新目录>/plan.json --output <新MP4>`。输出目录必须不存在。依赖与渲染器相同，不需新模型。

```json
{
  "canvas":{"width":1920,"height":1080,"fps":25},
  "assets":{
    "mechanism":{"source":"assets/cycle/stage-03.png","role":"illustration","provenance":"本项目按校对稿制作的机制示意"}
  },
  "scenes":[
    {"id":"explain","source":"input.mp4","start":10,"end":16,
     "task":"解释机制","takeaway":"观众看懂三个节点之间的循环",
     "keywords":[{"text":"循环如何形成","start":0,"end":1.5}],
     "visuals":[{"asset":"mechanism","start":1.5,"end":6,"layout":"full"}]}
  ]
}
```

示例路径与时间是占位，必须替换为项目真实素材。canvas可选width/height/fps/font；未提供则沿用渲染器默认值，制作时应显式写原片或用户指定比例。顶层只接受canvas/assets/scenes。

## 时间与素材规则

- scenes数组顺序就是成片顺序；start/end为源视频秒数。每段id唯一，task和takeaway由编辑明确填写，工具不会自己判断语义。
- 支持每段zoom_end；其他渲染效果在输出plan.json中按render-plan.md添加。不要把不存在的效果名写进分镜。
- keywords与visuals的start/end是**本段开头起算**的秒数，不是源片或全片时间。visuals缺时间时覆盖全段；长度采用渲染器按帧取整的结果，避免重复手算累计误差。
- assets可以跨多个scene重复使用，适合后段调用前面卡片。role为evidence或illustration，provenance记录可追溯来源或明确的unknown；字段填写完整不代表证据已核实。
- 图片保持为图片，视频通过source_start定位素材片段；叠层音轨不混入。路径相对于分镜文件所在目录，输出计划写成绝对路径。
- layout仅支持full/card_left/card_right。默认fit:contain完整缩入，可能产生留白；可显式fit:cover填满并中心裁切；左右卡片是固定布局，不自动检测人脸。竖屏复杂图解需重排，不能盲目填满。
- 同一位置的叠层或关键词时间相交会报错；全屏叠层也不能与另一叠层交叉。需要复杂分层时明确编辑输出plan，不将此简化工具误当作渲染器全部能力。
- 缺少素材默认报错。只有该visual写了`"fallback":"talking_head"`才保留原口播，并在editorial.json记录回退。无效asset引用、未知布局、超时长不会自动回退。处理完警告后再交付。

## 字幕与视觉验收

keywords是强调词，不是完整对白。源视频有内嵌字幕时，全屏资料可能盖住它们；必须保留字幕区域，或从校对词级转录重建对白。用输出source-map.json调用map_captions.py，将结果按render-plan.md加入texts（kind为caption），避免字幕缺失或重复。

默认关键词在画面上部，不保证避开所有资料标题；实际看图后调整位置。工具只验证时间、路径和部分冲突，不验证观点、来源真实性、裁切是否合适、画面美观或听觉同步。

v2.4验证：实际完成分镜→计划→3.96秒合成；12项检查包括帧取整、关键词映射、缺失/未知素材、重复段ID、越界时间、关键词/画面冲突、未知布局、明确回退、拒绝覆盖，以及视频叠层原音未混入。测试素材为合成音视频，不能据此声称已完成真人全片试听。


v2.5：visuals可指定fit:contain/cover，默认contain。keywords可指定animation:fade/pop/none，默认fade；长强调词与可能不足的阅读时间写入warnings，含义和限制见visual-polish.md。关键词时间、素材定位等原格式保持兼容。

v2.7：visuals 可传 rotation、rotation_end、move_duration、easing，范围与渲染器一致。复杂照片组合、分阶段透明度及文字 outline 在生成的 plan.json 中设置；转换器仍只支持已有三种布局，不自动做焦点判断。
