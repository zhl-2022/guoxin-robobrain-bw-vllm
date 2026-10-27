# RoboBrain2.5-8B-NV on BW + native vLLM（RefSpatial 接续候选）

当前为完整200条 RefSpatial 的接续与私有备份分支，新一轮尚未启动 GPU，`technical_delivery_complete=false`、`submitted=false`。旧CV-Bench与RoboSpatial失败原件保留。

## 1. 简介

固定 `BAAI/RoboBrain2.5-8B-NV` revision `7ae187cc62e45cfa1c5904903a8f017f11b2037b`，采用 BW64GB、BF16、原生vLLM。下一准确率范围为原版 RefSpatial location100 + placement100，不含可选Unseen77。

## 2. 验证环境

SCNet 华中一区A区单卡，DTK26.04、native vLLM0.18.1，沿用已测试的32768上下文、四序列上限及head72 VisionMathCompat。新队列待Kimi结束清理后从固定旧源码Git `a1304dad3fe762691735c7fe03beffb8efcffd21` 启动；新轮环境和GPU日志尚未产生，未封装新镜像。

## 3. 适配与评分

公开数据 revision `098de7c8785277e5d3b3270d13863c8ac85a6852`，全部200条图像、mask及问题均已核对。原作者评分器固定 `Zhoues/RoboRefer` commit `d97a995ad28376720a4c8beb64915c58ed16c844`，未修改源码；提示词使用其RoboBrain分支。模型返回0..1000坐标，明确换算为像素，不裁剪越界值，非法输出计零，不排除答案。图像与题目发送模型，评分mask保留本地。

## 4. 启动与接续

实际队列 PID43964，等待 A 的 Kimi performance005 PID38105 和固定入口复跑 PID43060结束并完成清理。之后执行根启动、环境检查、smoke与完整200条；准确率通过才执行原生六档负载、两轮性能。只停止自身服务，不关闭Notebook或干预其他模型。

固定输入包 `publisher019/session017-refspatial-queue001.zip`，412个文件，SHA256 `b337960b56b5e26e2282db68c2614031357f7167e75b0cc0806e9face602ae5a`。新分支是接续代码备份，尚未将RefSpatial替换为最终根verify入口。

## 5. 功能自检

全部200条数据与作者源码的CPU自检返回0，远端导入及自检成功；坐标边界、越界和非法框已检查。全部200个无坐标答案的CPU评分为0且分母保持200，只验证评分流程，不计模型精度。见 `publisher019/refspatial-grader-selfcheck.json`。

## 6. 完整精度

新RefSpatial模型分数尚未产生。发布论文Table2中NV基线60.50%，按满分100的绝对2pt容差为58.50%；数据revision与提示/坐标适配差异会在正式报告保留，不宣称发布方完整评测配置均已公开。

此前CV-Bench全部2638条为88.16%，低于92.58%门槛。RoboSpatial-Home全部350条mask-v2为62.1312%，低于71.03%；完整原件及独立复核位于 `publisher016`。这两项失败继续披露，见 `ROBOSPATIAL_VALIDATION_016.md`。

## 7. 性能

新候选尚未开始性能测试。原350条轮的96次短性能请求不能替代新配置六档两轮原生矩阵。新准确率若通过，再保存实际608次测量请求及12份原生报告、所有失败和独立校验；不伪填未执行结果。

## 8. 交付状态与版权

当前只是代码、输入和CPU验证备份。正式交付仍需真实准确率与性能、根入口重放、八章最终报告、光合固定版本和超算镜像。旧README原文保留在 `docs/README-robospatial016-historical.md`。新编代码保留版权，上游保留原许可，没有增加新全仓许可证。
