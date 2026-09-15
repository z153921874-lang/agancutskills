# 本地识别、跟踪、抠像

脚本不含在线API，不上传用户媒体。下载模型/安装依赖单独处理，不能执行时隐式进行。当前机器路径见 [local-runtime.md](local-runtime.md)。ZIP不包含第三方库和权重，迁移后需配置。

## 语音识别

```text
python <skill>/scripts/transcribe.py --input <video> --model <local-model-dir> --output <project>/transcript.json --start 0 --duration 30 --language zh --vocabulary "黑洞 视界 宇航员" --dependency-dir <optional-package-dir>
```

需要faster-whisper。model必须是本地含model.bin的目录，local_files_only=True。默认CPU/int8、4线程；CUDA/cuDNN环境验证通过后才指定--device cuda --compute-type float16。显卡存在不代表GPU推理已验证。

输出segments、词级words/probability、分组captions、长间隔gap_candidates和SRT。所有时间为源时间，含--start偏移。--max-chars默认22，--max-seconds默认4；分组不保证语义断句正确。

20秒中文访谈实测能转录及生成词时间，但“往”被写为“网”、“视界”被写为“世界”。看原字幕并回听修正，不能自动据此删否定或生成科学结论。间隔可能含反应/音效/呼吸，不直接全删。

接口依据：[faster-whisper官方仓库](https://github.com/SYSTRAN/faster-whisper)。

## 人物标签

```text
python <skill>/scripts/track.py --input <video> --output <project>/track.json --start 185 --duration 3 --box 440 40 300 290 --canvas 646 484 --label-offset -12
```

需要OpenCV TrackerMIL。box是观察源起点帧后确定的[x,y,w,h]，不要照搬示例坐标。boxes为源像素；keyframes为画布标签中心。canvas遵循保持比例居中加边；label-offset是画布像素。

逐帧跟踪，默认每0.12秒记录关键点。无身份识别和可靠置信度；可能识别切镜并停止，但不能保证。任何failure或漂移需重新选框。使用keyframes前核对源区间、首尾时长和画布；基础画面另做推拉/裁剪时不能直接复用。

## 实验性抠像

```text
python <skill>/scripts/matte.py --input <video> --model <rvm_mobilenetv3_fp32.onnx> --output <project>/subject.mov --start 185 --duration 3 --width 646 --outline 2 --glow 5 --color "#FFE36B" --dependency-dir <optional-package-dir>
```

需要OpenCV、NumPy、ONNX Runtime、本地RVM fp32模型。CPU执行并循环传递连续帧状态。单次最长120秒，建议按镜头分段。--crop X Y W H限定画面范围，不等于指定人物身份分割。

输出无声qtrle/ARGB透明MOV和matte.json。作为overlay时保留底图原声。outline为输出像素外扩宽度，glow为模糊半径；MOV可能较大。

已在3秒双人访谈上目视確認透明人物、描边、发光和文字遮挡关系，但前景背对镜头的人也被保留。发丝、手指、快速动作、服装近背景色和多人遮挡仍需检查。模型可能影响字幕与标识，应在最终合成中保护原有标识，不能把它们的残留当作抠像正确依据。

接口依据：[RVM作者推理文档](https://github.com/PeterL1n/RobustVideoMatting/blob/master/documentation/inference.md)。模型来源：[作者v1.0.0发布页](https://github.com/PeterL1n/RobustVideoMatting/releases/tag/v1.0.0)。使用时保留来源和许可信息，技能ZIP不分发权重和第三方库。
