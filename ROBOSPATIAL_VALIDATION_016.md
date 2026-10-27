# RoboSpatial-Home 全部350条补充验证（Session016）

当前未达到投递准确率门槛，保留真实失败结果。

固定 NV checkpoint `7ae187cc62e45cfa1c5904903a8f017f11b2037b`；数据为 `chanhee-luke/RoboSpatial-Home` revision `538c38882b5fec5155eeb555d17bc8b244e06a3a`，完整350条 RGB 输入。没有把答案 mask 发送给模型。

固定 FlagEvalMM `fef27ec696c532d12f0db389bcbbf79eab0e4c41` 的 norm1k 评分器，`accuracy`（mask-v2）为62.1312%，`accuracy_ori`（polygon）为44.2857%。本模型发布基线73.03%，绝对2pt门槛71.03%，本轮未达标。兼容性56/105、配置99/123，context mask分数62.4592592593/122。

完整原件 `publisher016/session014-robo-spatial-full015.zip`，SHA256 `67a2195246f7c9101332146e6654e716f56d20827cc30ff0b7c92dc0c9bd4f33`。全部350条请求、图片、预测、公开评分器、配置身份及另96次性能请求均已独立复核。所有预测最长107生成token，没有 length 截断，不以增加生成预算解释本次精度下降。

此前 CV-Bench2638 的88.16%失败结果继续保留。性能请求成功不代表准确率通过；`submitted=false`。本分支只是代码和评测备份，不代表赛事投递成功。
