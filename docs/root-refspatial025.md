# RefSpatial200 根入口候选

本候选将完整 RefSpatial200 接到根 `verify.py`，替代尚未配置分题材料的旧通用 delegate。它仍调用固定的 `evaluate_refspatial017.py`，不改变请求、解码、作者评分器或0–1000坐标到像素的规则。

## 数据与来源

- 数据：原公开 location100 + placement100，共200条，403个载荷。仓库自带的 `publisher021/refspatial200-reprodata.zip` 包含完整RGB、mask、注释和逐文件SHA。
- 数据 ZIP SHA256：`e4fdf64db04eedfb61a2f6847f9e12f0329e1034af42e8785edbce45c0583bde`。
- 作者源代码：`publisher025/author-sources`，三个原始文件沿用原017输入包，由原 evaluator 的三个固定 Git blob SHA 校验。评分和提示来自固定的 RoboRefer 源码，RoboBrain 推理源码用于核对坐标约定；保留原文件字节与版权。`098de7c8785277e5d3b3270d13863c8ac85a6852`是公开数据集 revision，不是这三个源码文件的共同提交。
- 生成阶段只发送 RGB 和问题；mask及答案仅用于本地评分。
- `scripts/prepare_refspatial_data025.py` 仅在仓库的 `runtime/refspatial025/data` 中准备数据，严格检查路径、重复条目、清单、403个载荷和已有目录；不访问网络，不启动GPU。

## 复现

```bash
bash run.sh --run-id YOUR_UNIQUE_RUN_ID
bash env_check.sh
bash smoke.sh
python3 verify.py --selfcheck
python3 verify.py --output /absolute/new/refspatial-evaluation
bash stop.sh --run-id YOUR_UNIQUE_RUN_ID
```

`--output`必须是新的目录。显式`--data`可使用已有固定数据目录，但仍由原 evaluator 校验全部输入。`--rescore`可只在CPU上复算200条原始预测，不进行模型请求。

根环境入口补齐原完整测试使用的DTK路径、系统Python、43200秒原服务边界及完整模型路径served-name；task launcher、兼容补丁、native driver、模型权重和采样不变。模型仍位于平台原数据盘路径，不写进新镜像层。当前候选的根入口GPU复跑尚待现有Robo性能结束并确认清理后执行；本文件不代表新增完整交付或已提交。
