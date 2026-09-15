# 动态关系场景与参考检查

`scripts/motion_scene.py --spec <JSON> --output <新MP4> [--font <字体文件>]` 输出1280×720、25fps的无声视频，2—60秒；依赖Pillow和现有FFmpeg。默认Windows微软雅黑。使用时根据实际口播调整节点和连线出现时间。

输入例子见 [照护关系](../assets/motion-scenes/care.json)、[概念对照](../assets/motion-scenes/contrast.json)、[支持关系](../assets/motion-scenes/support.json)。它们是原创示意模板，不是用户视频的完整分镜或已核实政策事实。

- title/eyebrow/footer：标题、眉题、页脚。theme为dark或paper。
- nodes：id、label、detail、icon（person/clock/home）、x/y/w/h、at。节点从at开始，用0.55秒轻移与淡入。正文标签最多10字符、说明16字符，并检查实际字体宽度；节点不能相互重叠。
- edges：from/to是节点id，start/end是线条两端坐标[x,y]，label可空，at为开始画线时刻。0.75秒逐步画出连线，然后出现箭头和标签。连线不能早于其两端节点开始出现；实际是否避开其他内容仍需检查。
- statements：text、x/y、at、size，按指定时间出现结论或比较符号。文字最多22字符，检查横向字宽。不会自动根据台词决定含义。
- 节点、结论出现后保留到片尾；最后留出完整关系的阅读时间。背景为确定性网格，无外部图片或AI依赖。

把结果作为render.py的video overlay加入原声计划，或作为B-roll素材。无声图解不替换原口播声音。覆盖原字幕前，先准备对应区间的校对字幕。其他尺寸需要重新布局或完整缩入，不能直接裁掉图节点。

此工具支持二维图标、短文字、连线生长和节点入场，不是复杂人物抠图、透视摄影拼贴、3D空间、资料自动搜索或自动配音。可以与真实资料和情境素材混用，不应成为每段唯一的视觉样式。

`scripts/reference_review.py --plan <已验证的渲染计划JSON> --output <新报告JSON>` 统计叠层时长并给出审片提示。它识别不了原片自带的B-roll、一个视频内部的内容或实际审美，不给“复刻率”。按reference-production.md完成编辑判断。
