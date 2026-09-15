# v2 渲染计划

Python 3.10+；FFmpeg带libass/libx264/AAC。通过 --ffmpeg 指定程序，或PATH/imageio_ffmpeg查找。JSON不能写外部命令、滤镜表达式或ASS控制串。

```text
python <skill>/scripts/render.py --plan <project>/plan.json --output <project>/final.mp4 --check
python <skill>/scripts/render.py --plan <project>/plan.json --output <project>/final.mp4
```

拒绝覆盖已有交付物。单次编码拼接音视频；剪段时长按帧取整，--check返回source_map。输出MP4、source-map、render.json、前/后景ASS；有对应文字时才生成SRT。

## 总体

```json
{"version":2,"width":1080,"height":1920,"fps":30,"font":"Microsoft YaHei",
 "clips":[{"source":"原片.mp4","start":2,"end":8}],
 "texts":[],"effects":[],"overlays":[],"audio":[]}
```

路径相对计划目录或绝对路径。clips时间为源时间，其余start/end为成片时间。坐标为输出像素。输出宽高为偶数。默认保持源比例、居中加边。

## clips

```json
{"source":"原片.mp4","start":2,"end":8,"zoom":1,"zoom_end":1.15,
 "focus_x":0.5,"focus_y":0.5,"focus_x_end":0.55,"focus_y_end":0.45,
 "gain":1,"fade_in":0.04,"fade_out":0.08}
```

zoom为1–3；focus为0–1的归一化中心，属于加边后的画布。起末值线性插值，end省略则固定。推拉可能裁切字幕/标识，先检查。fade_in/out是原声秒数，不是视频转场，默认0。

## texts

```json
{"start":0,"end":3,"text":"重点信息","kind":"emphasis","size":72,
 "color":"#FFE36B","x":540,"y":250,"pop":true,
 "fade_in":0.08,"fade_out":0.25,"animation_duration":0.3,
 "rotation":-5,"rotation_end":0,"layer":"front"}
```

- kind：caption或emphasis，默认靠下/靠上；明确指定安全坐标更可靠。
- pop：小→略大→正常；slide_from:[x,y]从指定位置滑到x,y；animation_duration控制弹出/滑入时长。
- rotation/rotation_end为初末倾斜角；只有rotation时固定倾斜。fade单位秒。
- layer:front在所有叠层上方；behind在底图处理后、所有overlays之前。
- keyframes：`[{"time":0,"x":100,"y":90},{"time":3,"x":150,"y":100}]`，time相对文字起点，严格递增且覆盖0至全时长。逐段线性移动；不能组合pop/slide/淡入淡出/动态旋转。
- ASS保留动画，SRT只有文字时间。缺字体可能回退，需检查。
- v2.7：outline 为 0–10 的描边宽度，默认 2；outline_color 为 #RRGGBB，默认黑色。浅底深字用 outline:0，避免糊成黑块；不自动判断背景。

## effects（按数组顺序处理底图）

```json
{"type":"spotlight","start":0,"end":3,"x":500,"y":600,
 "x_end":600,"y_end":600,"radius_x":180,"radius_y":240,"dim":0.65,"feather":0.2}
```

椭圆内部保持亮度，周边压暗。end坐标省略则固定；feather是边缘过渡宽度相对半径的比例。底图内嵌字幕也可能被压暗，需规避或另置前景。

```json
{"type":"blur","start":3,"end":6,"sigma":15}
```

模糊整个底图；之后叠锐利卡片或透明人物，不是自动只模糊背景。

## overlays

```json
{"source":"人像.png","start":3,"end":6,"x":80,"y":400,
 "width":400,"height":500,"x_end":100,"y_end":400,
 "crop":[100,50,600,750],"border":4,"border_color":"#FFFFFF",
 "corner_radius":24,"opacity":1,"fade_in":0.2,"fade_out":0.2}
```

图片自动still；视频需source_start，源时长至少覆盖end-start。overlay音轨不混入，避免双重人声。crop是源像素[x,y,w,h]，先裁再按比例填满卡片并居中裁掉多余部分。x_end/y_end线性移动；数组顺序为叠放顺序。支持PNG和qtrle MOV的透明度；普通MP4的黑背景不能当成透明。

## audio

```json
{"source":"音乐.wav","source_start":0,"start":0,"duration":6,
 "gain":0.12,"fade_in":0.5,"fade_out":1}
```

source_start为音频源时间，start为成片时间。不自动循环或找音乐；默认不按人声压低，显式duck:true可启用。按gain混入并限幅，需回听；淡入淡出之和不能超过duration。


v2.1：外部音轨可加 `"duck": true`，让该轨由原片混合音轨驱动压低。默认 false；用于配乐，不宜用于每个音效。原片若已混有音乐或噪声，也会触发压低，详见 finishing.md。


## v2.5 叠层细节

overlays增加fit（cover默认，contain完整缩入）、pad_color（contain留白颜色，默认#101B26）、easing（linear默认，smooth平滑起止）、move_duration（位移耗时，默认整个叠层时长；结束后停在x_end/y_end）。其他时间区间仍是成片时间，move_duration是从叠层start起的持续秒数。现有clips推拉与文字动画不受这两个运动参数影响。示例：`{"fit":"contain","easing":"smooth","move_duration":0.7}`，与现有source/start/end/尺寸位置字段一起使用。

## v2.7 照片旋转

overlays 可加 rotation/rotation_end（-20 至 20 度，默认 0，末值默认同初值）。旋转和位移共用 move_duration/easing，到时保持末值。width/height 是整个运动期间恒定的外框；内部按最大旋转范围等比缩小，保留卡角。fit:contain 才同时保留原图全部内容。角度 0 不启用额外旋转处理。示例补充字段：`{"rotation":-5,"rotation_end":0,"move_duration":0.7,"easing":"smooth"}`。这是二维旋转；文字的旋转仍按文字全时长变化，不使用此处 move_duration。
