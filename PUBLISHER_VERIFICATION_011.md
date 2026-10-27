# RoboBrain2.5-8B-NV 发布方完整验证记录（Session011）

## 1. 简介

本分支保存真实完整评测和失败结果，当前精度门槛未通过，不作为已达标项目投递。原开发源码、README、上游许可和历史文件保留。

## 2. 环境

SCNet 华中一区 A 区，BW 64 GB × 1，DTK26.04，Torch2.10.0，vLLM0.18.1 DAS。各运行实际参数、run_id 和日志以 archives 中的原始回执为准。

## 3. 适配与协议

未修改 checkpoint、标签或 tokenizer；数据集固定 revision，保留所有错误回答、超长回答与失败轮次。两项完整评测使用各自发布方可核实的基线，不混用不同 checkpoint。

## 4. 代码与复现

原 serving 代码保留在仓库原位置。`publisher011/tools` 保存本轮实际评测、启动与停止控制器、原生诊断及上游 scorer；`publisher011/archives` 保存完整响应、协议、阶段日志和性能结果，原 ZIP CRC 已核验。所有新文件由 `publisher011-manifest.json` 逐项封存。

## 5. 功能与诊断

原生 Transformers 固定 48 输入对照：47 个生成文本完全一致，48 个 prompt token 数一致。该小样本只诊断框架路径，不能替代完整准确率。

## 6. 完整准确率

CV-Bench 全部 2,638 条；两次完整评测均为 88.16%，发布基线 94.58%，门槛 92.58%，未通过。FlagEval source-weighted 指标：ADE 78.04、COCO 86.09、Omni3D 94.25，2D 82.06，最终 88.16。第二轮改用 RoboBrain2.5 非 thinking 提示、768-token，未拼接两轮答案。

来源：[固定 NV 模型卡](https://huggingface.co/BAAI/RoboBrain2.5-8B-NV/blob/7ae187cc62e45cfa1c5904903a8f017f11b2037b/README.md)、[官方代码](https://github.com/FlagOpen/RoboBrain2.5)、[技术报告](https://arxiv.org/abs/2601.14352)。

## 7. 性能

原始 ZIP 中完整保留已执行的 c1/c4、各两轮、共 96 个固定样本性能请求。性能成功不代表准确率通过；不把不同提示、不同生成预算或原生诊断当作可获得优化奖励的同负载性能对比。

## 8. 当前状态

`publisher_numeric_comparison_pass=false`，`submitted=false`。代码保存至 zhl-2022 私有分支，仅是开发与评测备份，不是最终赛事表单提交。后续若修正实现，必须重新运行声明的数据和完整评测，保留本轮不利结果。
