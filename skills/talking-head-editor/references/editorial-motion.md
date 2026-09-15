# 分阶段照片合成工具

`scripts/editorial_motion.py` 提供 Pillow 画布函数，供项目合成脚本逐帧调用。依赖已有 Python、Pillow、NumPy；本模块不读取媒体、不下载素材、不生成音频、不写最终 MP4。需由项目脚本提供帧和校对后的时间，再用现有 FFmpeg 环境编码。不能给 render.py 的 JSON 填入这些函数名。

## 可调用接口

- `ease(value)`：输入阶段进度，平滑限制在 0–1。
- `paper_surface(size=(720,1280), dark=False, seed=73)`：静态浅色或深色细网格底图。预先生成后逐帧复制，避免逐帧重采样噪点造成闪烁。
- `photo_card(canvas, picture, center, size, angle=0, opacity=1, border=9, fit='contain')`：按比例装入照片，边框和阴影一起旋转。`size` 是旋转前内部图区；旋转后的边界会扩张，调用方需检查是否越界。默认 contain 保留全图，cover 只用于允许裁切的情境图；素材内字幕/标识不能因 cover 被裁掉。
- `growing_line(canvas, points, progress, color='#718168', width=3, arrow=False)`：按线长逐段显现连线；进度到 1 后保持完成形状。箭头只在完成时绘出。连线含义由分镜给出，不识别关系。
- `focus_window(picture, center, scale=1)`：围绕像素落点做二维局部取景，自动限制取景框在素材内，返回原尺寸。`scale >= 1`。字幕最后叠在画布上，避免随局部推近被裁切或缩放。

均是二维合成，没有自动抠像、真 3D、AI 视频运动、自动找焦点或自动识别口播重音。聚焦中心必须从实际素材检查后指定。

## 用于项目的示例

```python
from editorial_motion import ease, photo_card, growing_line

# canvas 为每一帧的 RGBA 底图，photo 为已确认来源和裁切的照片。
p = ease((t - shot_start) / 0.45)
photo_card(canvas, photo,
           center=(840 - 400*p, 640),
           size=(330, 550), angle=4*(1-p), fit='contain')
growing_line(canvas, [(130, 380), (440, 380), (440, 425)],
             ease((t-shot_start-0.55)/0.35), arrow=True)
```

这里的 0.45、0.55、0.35 秒仅是起调值，需随原声改；不是参考片测量结果。照片先入场停稳，再连线。内容早于对应口播时先修时间，不靠延长模糊隐藏。

整图退成卡片可在短阶段将照片尺寸从全画布插值至目标尺寸，再保持；局部放大可以只变焦一次后停住。浅底阶段对白用深字，深底阶段用浅字；背景切换期间也要检查实际对比度。

## 实测范围

本次测试与代表段记录在 validation.md 的 v2.8 部分。几何与进度测试只验证函数行为；实际短片选帧检查才验证具体构图。二者都不等于自动语义理解或完整主观试听。
