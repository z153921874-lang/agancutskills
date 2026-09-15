# 本机运行环境配置

仓库不绑定作者的个人路径。使用前检查当前机器的解释器、FFmpeg、中文字体、可选依赖和模型；不要把历史验证当作本机已安装的证明。

## 基础剪辑

- Python 3.10+，建议项目虚拟环境。基础依赖见仓库根目录 requirements.txt。
- FFmpeg 需具备 libass、libx264 和 AAC 支持。工具依次使用显式 `--ffmpeg`、PATH 或 imageio_ffmpeg。
- 计划中的 `font` 是本机可用的字体名称。图解和动态场景工具的 `--font` 是字体文件路径；Windows 默认值为 `C:/Windows/Fonts/msyh.ttc`，其他系统显式传入实际中文字体文件。
- 跟踪需要额外安装 OpenCV；图解和照片合成使用 Pillow、NumPy。

## 识别与抠像（可选）

- faster-whisper 用于本地语音识别，ONNX Runtime 用于 RVM 抠像；不包含在基础 requirements.txt 内。
- 可在项目单独目录安装可选依赖，通过相应工具的 `--dependency-dir` 指定。
- Whisper 和 RVM 模型需自行取得到本地，并通过 `--model` 指定。来源与推理接口见 [识别与人物工具](intelligence.md)。
- 工具只加载明确指定的本地模型，不隐式下载。GPU 可用性须实际验证，不根据显卡型号推断。

历史项目验证过 CPU 识别与抠像、FFmpeg 7.1 和 Windows 中文字体。仓库不携带模型、运行环境或用户视频，安装 skill 不等于上述环境已经就绪。
