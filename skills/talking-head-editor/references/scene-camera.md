# 场景镜头工具：scene_camera.py

独立 Pillow 模块，供项目合成器逐帧调用。支持大画布取景、显式关键帧、对象尺寸/位置/透明度/模糊；不识别语义、不生成媒体、不输出音频，也不是 render.py 新JSON接口。

## 接口

`Track(keys, fields)`：每个关键帧有秒数 `time`、相同的数值字段和可选 `ease`。支持 `smooth`、`linear`、`hold`，作用于该帧到下一帧的区间。`hold` 在下一关键帧时刻切换。首尾之外保持端点。`at(t)` 返回字段值。数值必须有限，时间非负且严格递增，未知字段/缓动拒绝。

`Camera(world_size, output_size, keys)`：关键帧字段为 `x,y,width,height`，表示世界画布中的取景矩形。`view(world,t)` 返回取景图；`project((x,y),t)` 将世界坐标映射到视口坐标。每个矩形须在画布内，比例须与输出一致，否则拒绝。平滑插值保持此比例和边界。移动或推近应在明确时点停止，通过相同位置的后续关键帧保持阅读。

`AssetTrack(asset_id,picture,keys,fit='contain')`：关键帧字段为 `x,y,width,height,opacity,blur`。`draw(rgba_canvas,t)` 按轨迹合成同一个静态图。`asset_id` 必须非空；默认完整等比例容纳，显式 `cover` 允许裁切。透明度0–1，模糊半径0–64（源图像素）。素材可移出画布并被裁切；调用方负责边缘/来源信息。它不生成不同机位，也不使画中人物活动。

## 例：总览、局部、返回

```python
from scene_camera import Camera
camera = Camera((1600,900), (800,450), [
    dict(time=0,x=0,y=0,width=1600,height=900),
    dict(time=1,x=0,y=0,width=1600,height=900),
    dict(time=1.7,x=400,y=225,width=800,height=450),
    dict(time=3,x=400,y=225,width=800,height=450),
    dict(time=3.7,x=0,y=0,width=1600,height=900),
    dict(time=5,x=0,y=0,width=1600,height=900),
])
frame = camera.view(world_image, t)
# 在这里再叠对白，避免对白跟着世界画布缩放。
```

关键帧必须根据实际讲述和图中落点填写；示例时长不来自参考视频测量。不要用文件名或字段名自动推断左右轴线、因果或眼神方向。

v3.0新增模块的几何及图像行为测试和28.13秒真实口播示范见 validation.md。模块不包含用户素材、生成图片、模型和本机字体。完整AI视频、动作匹配、自动导演规划、3D摄影机和完整声音审片不在本接口范围内。
