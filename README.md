# RoboBrain2.5-8B-NV on BW + native vLLM（RefSpatial 根入口候选）

完整 RefSpatial200 原轮已得到63.0%并独立复核。当前补齐可移植根入口，完整200数据/作者源码自检和原200条响应的根入口CPU复算均通过；新根入口GPU复跑仍待现有性能结束清理。`technical_delivery_complete=false`、`submitted=false`，旧CV-Bench与RoboSpatial失败原件保留。

## 1. 简介

固定 `BAAI/RoboBrain2.5-8B-NV` revision `7ae187cc62e45cfa1c5904903a8f017f11b2037b`，采用 BW64GB、BF16、原生vLLM。所选准确率范围为原版 RefSpatial location100 + placement100，不含可选Unseen77。

## 2. 验证环境

SCNet 华中一区A区单卡，DTK26.04、native vLLM0.18.1，沿用已测试的32768上下文、四序列上限及head72 VisionMathCompat。原轮和当前性能均使用固定运行核心 `a1304dad3fe762691735c7fe03beffb8efcffd21`。新候选只补根入口和数据准备，task launcher、driver、模型、兼容补丁与采样不变；环境以每轮`env_check.sh`真实日志为准。尚未封装本候选最终镜像。

## 3. 适配与评分

公开数据 revision `098de7c8785277e5d3b3270d13863c8ac85a6852`，全部200条图像、mask及问题均已核对。原作者评分器固定 `Zhoues/RoboRefer` commit `d97a995ad28376720a4c8beb64915c58ed16c844`，未修改源码；提示词使用其RoboBrain分支。模型返回0..1000坐标，明确换算为像素，不裁剪越界值，非法输出计零，不排除答案。图像与题目发送模型，评分mask保留本地。

## 4. 服务启动脚本

根入口实际命令如下；运行前先确认先前自有模型已清理，使用唯一UUID。`stop.sh`仍按run-id身份只停止本轮自有服务。

```bash
bash run.sh --run-id YOUR_UNIQUE_RUN_ID
bash env_check.sh
bash smoke.sh
python3 verify.py --selfcheck
python3 verify.py --output /absolute/new/refspatial-evaluation
bash stop.sh --run-id YOUR_UNIQUE_RUN_ID
```

完整200条数据ZIP随仓库保存，403个载荷逐项校验，缺失时仅解压到本仓库`runtime/refspatial025/data`；不下载新数据或调用GPU。作者三个源码文件随仓库保存并检查固定Git blob SHA。`verify.py --rescore`可在CPU上完整复算旧200条预测。详细边界见[根入口说明](docs/root-refspatial025.md)。

## 5. Smoke 测试

原轮真实服务、环境和smoke已执行。候选根`verify.py --selfcheck`完整检查200条数据、RGB/mask、作者源码、坐标边界、越界和非法框，返回0；全部200个无坐标答案计0且保持完整分母的原CPU诊断也保留。CPU自检不是GPU精度。新的根服务smoke与GPU准确率仍待实际复跑。

## 6. 精度测评

完整200条原轮63.0%，location100为67.0%、placement100为59.0%，零排除、零解析异常、零length终止。全部200个图像、请求、原始UTF8响应及作者评分器已独立复核；本候选根入口CPU重算相同63.0%。原件`publisher021/session017-robo-refspatial001.zip`，数据`publisher021/refspatial200-reprodata.zip`。新的根入口GPU复跑尚未完成，不能把CPU重算称为新的模型轮次。

发布论文Table2中NV基线60.50%，按满分100的绝对2pt容差为58.50%；较严的相对2%下限59.29%也通过。发布论文未固定公开数据revision及完整GPU评测配置，所选公开数据revision、原提示分支和坐标适配均披露。

此前CV-Bench全部2638条为88.16%，低于92.58%门槛。RoboSpatial-Home全部350条mask-v2为62.1312%，低于71.03%；完整原件及独立复核位于 `publisher016`。这两项失败继续披露，见 `ROBOSPATIAL_VALIDATION_016.md`。

## 7. 性能参考

现有同配置原生性能仍在A上运行，已经独立核验8组320条（旧4组48加新4组272），完整目标为六档两轮12组608条；此候选尚不能标记完整矩阵。镜像保存重叠的中断组及其原件保留，不计入有效组。已完成有效组不重跑。

旧汇总器只因顶层`request_rate Infinity`误报格式异常，固定独立审核仅规范化这一处；正常退出0、reaped、请求数组、来源和哈希均单独核对。原生client的output_lens可能来自usage或指定长度fallback，不能据其声称独立认证每条wire生成恰好1024 token、SSE终止或正式赛事性能验收。

## 8. 注意事项

当前为待GPU复跑的固定根入口候选；完整交付仍需12/608性能闭合、新根入口GPU实测、最终报告、固定光合与镜像材料。原两台Notebook按用户要求保留，只停止自身模型服务。评测计时中不进行镜像保存，不修改模型参数或采样；不覆写运行原件，不将失败重采样成通过。旧README原文保留在 `docs/README-robospatial016-historical.md`。新编代码保留版权，上游保留原许可，没有增加新全仓许可证。
