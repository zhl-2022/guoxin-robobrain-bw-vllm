# RoboBrain2.5-8B-NV on BW + native vLLM

完整 RefSpatial location100 + placement100 的固定根入口实测为 **65.0%**，原轮为63.0%；两轮完整分母和所有失败记录保留。六档两轮12份原生性能报告、608条测量请求已逐文件独立核验。本报告对应的准确率、根入口和性能均已实测；光合固定代码、最终环境镜像、评审访问和赛事提交状态由随报告的外部交付清单记录，只有真实提交记录才表示已投递。

## 1. 简介

模型为 [BAAI/RoboBrain2.5-8B-NV](https://huggingface.co/BAAI/RoboBrain2.5-8B-NV)，固定 revision `7ae187cc62e45cfa1c5904903a8f017f11b2037b`。本件为T02、单卡BW、BF16、原生vLLM适配。只采用一个完整公开小型基准：RefSpatial原版location和placement共200条；可选Unseen77不在本次选定范围内，未按模型答案挑选样本。

最终环境镜像约定名称 `guoxin-robobrain-vl-bw030`，tag `dtk2604-vllm018-robo-final-20261028`；代码项目约定 `guoxin-robobrain-bw-vllm-final-session037`。这些名称不代替平台成功回执，实际ID、固定commit、区域状态和附件SHA以外部清单核对。历史光合15916/15944及旧开发报告不作本件最新投递版本。

### 最终提交材料绑定（Session037）

原有全部资料保留；本次整理不重新采样、不改变推理或判分源码；新增最终准备链路的真实功能验收。实际发布版本和评审获取状态由 `CURRENT_SUBMISSION_STATE037.json` 及外部提交清单记录；尚未完成的门禁不写成通过。

| 项目 | 固定引用 |
| --- | --- |
| 光合代码项目 | [项目入口](https://developer.sourcefind.cn/codes/ghu_30ebea88e/guoxin-robobrain-bw-vllm-final-session037) |
| SCNet镜像 | [实际镜像详情](https://www.scnet.cn/ui/console/index.html?#/image-management/detail/2115288588905746433) |
| 固定镜像tag | `dtk2604-vllm018-robo-final-20261028` |
| 已实测前版代码 | `7e893f5b77394fa52b8881dc27fb8ad61d884173` |
| 本次材料分支 | `codex/submission-ready037-final`，以外部清单的完整commit为准 |

2026-10-28实际读取的[官方评审口径](https://bvjoh3z2qoz.feishu.cn/wiki/OkLBws6uWiG1Q0kpHLKcxXLmnif#R69kd07YCoqDlsxp0V5cDwM1ntL)明确：没有官方精度数据的部分模型可以不做精度，并点名RoboBrain2.5-8B-NV。该例外不免功能、性能和可复现交付。既有RefSpatial200及其他历史结果全部保留。


## 2. 验证环境

| 项目 | 实测值 |
| --- | --- |
| 平台 | SCNet华中一区A区，BW64GB×1；具体BW后缀未独立建立 |
| Python / DTK | Python3.10.12 / DTK26.04 |
| Torch | 2.10.0+das.opt1.dtk2604.20260325.g6b060a |
| vLLM | 0.18.1+das.fa71803.dtk2604；vllm-hcu0.18.1+das.dtk2604 |
| Transformers / tokenizers | 5.5.0 / 0.22.2 |
| Triton | 3.6.0+gitc73250c4.staging |
| 原生压测客户端 | 独立SGLang0.5.12；仅作OpenAI chat图像客户端，不替换平台Torch |

完整根环境记录在 `env.log`。其脚本不从配置字段推断运行容器digest；最终平台镜像身份另有实际UI回执。模型检查点在数据盘，不复制约17.54GB权重到新系统盘镜像层。根启动先复用并核对原文件；缺失时按13个固定ModelScope文件revision、size和SHA下载同一内容，HF原模型revision与原8个预检文件和其余运行小文件已对齐，见 `publisher030/model-download-lock.json`。

## 3. 适配与评分

原生Qwen3VL架构的视觉head72路径使用 `robobrain_vision_math_compat.VisionMathCompat`，原driver、task launcher、兼容补丁、evaluator和作者评分器保持实测字节。默认配置为TP1、BF16、32768上下文、max-num-seqs4、gpu-memory-utilization0.85、enforce-eager、每请求最多两张1024×1024图像、video0；完整实际配置位于原始runtime文件，不能用 `env.log` 中的候选字段代替。

新封装相对实际GPU根入口 `f5cc42d64f0143fa2f25a63d513c69a44c1f55d1` 只新增模型文件准备和交付证据。模型准备不导入GPU框架，采用已存在的固定下载器，拒绝越界路径、symlink及覆盖不同最终文件；缺失时只下载上述固定内容。新增准备路径的计划、目录门禁、真实已存13个文件的全SHA复核及镜像客户端2664文件检查均有CPU原件；未声称又完成一次全模型下载或新镜像独立Notebook的GPU复跑。本轮从SCNet试取固定小文件发生连接超时，未修改网络；本机对同一官方配置文件HTTP200和SHA相符。离线时须使用已提供的数据盘检查点，不能把下载计划当作新下载成功。

数据revision `098de7c8785277e5d3b3270d13863c8ac85a6852`；评分/提示源码固定 `Zhoues/RoboRefer` commit `d97a995ad28376720a4c8beb64915c58ed16c844` 的RoboBrain分支，三个源文件的Git blob随仓库检查。模型0..1000坐标按原图宽高换算为像素，越界不裁剪，解析异常/非法框计零且不排除样本，mask和答案不发给模型。

## 4. 服务启动脚本

从仓库根目录执行；同一实例先确认此前自有模型已清理，每次采用唯一UUID：

```bash
bash run.sh --run-id YOUR_UNIQUE_32_HEX_RUN_ID
bash env_check.sh
bash smoke.sh
python3 verify.py --selfcheck
python3 verify.py --output /absolute/new/refspatial-evaluation
bash bench.sh --plan
bash bench.sh
bash stop.sh --run-id YOUR_UNIQUE_32_HEX_RUN_ID
```

根入口会加载同一DTK环境。准确率数据ZIP含403个固定载荷，缺失时只解压到本仓库 `runtime/refspatial025/data` 并校验全部文件；不联网替换样本。模型准备 `scripts/prepare_image_model030.py --plan-only` 不读服务端路径或启动GPU；真实准备校验数据盘文件，不改模型配置和采样。

性能客户端优先使用已实测数据盘 `/root/private_data/sglang-client-004c/bin/python`；缺失时使用镜像预置 `/opt/guoxin/robo-client025/bin/python`，也可显式设置 `ROBOBRAIN_CLIENT_PYTHON`。镜像项目路径为 `/opt/guoxin-robo030/project`；环境镜像不包含数据盘权重。离开平台环境时仍需匹配同一DTK/vLLM安装，不能把普通CPU机的计划成功当作BW模型实测。

## 5. Smoke 测试

2026-10-28 03:09–03:14UTC，原性能服务全部结束且清理后，从固定f5cc42d的精确1098文件ZIP新建根目录并重算模型8个原核心文件SHA，执行launch、environment、smoke、selfcheck、bench-plan、完整200条verify、stop，七阶段均退出0。原件在 `publisher030/root-result-originals.zip`；完整原归档SHA `4db560cbf7cee6fa731884f52643b0b1d7d7d4967afc28c809a8f98ef458d2df` 另行保留。

七项功能检查全部通过：health、模型身份、单图、多图、多轮首问和追问、图像SSE。功能检查不评分空间正确性。完整200条准确率另有200个唯一原始响应ID，图像SHA、重建请求SHA、UTF8响应SHA、实际模型名和作者CPU重新评分全部核对，200条均正常stop，无length截断、解析异常或排除。


### 最终准备链路的实际验收（2026-10-28）

在此前模型已清理的原A卡上，从固定源版本的精确归档解压到独立新目录，15:44至15:47UTC完成六个阶段：压测客户端help、自检、根启动、环境检查、七项功能smoke、自有stop，退出码全部为0。启动前13个模型文件逐一核对size/SHA并复用；实际配置与已完成200条根评测逐键一致，仅目录和run UUID不同。功能七项为health、模型名、单图、多图、多轮首问/追问及图像SSE，全通过；最后七个模型端口关闭。

本次实际使用默认数据盘SGLang客户端，未冒充执行了镜像备用客户端；未重新下载完整检查点、创建新Notebook或重新测量完整精度/性能。镜像备用客户端的文件与上游源码检查仍由原镜像封装回执证明。六阶段原始日志、完整实际config/final state及独立审计放在`publisher037/final-preparation-replay/INDEX.json`所列原字节文件；完整主归档仍另行保留。首次缺失模型的下载命令、固定文件来源与SHA锁仍随本版代码提供，下载与复用的证据范围分别披露。

从已固定环境镜像使用光合本版源码，在新目录解压并执行本章根命令。镜像内部`/opt/guoxin-robo030/project`保留当时版本；当前README、附件、清单和代码以本次光合完整commit为准，无须再次保存镜像。本次精确Git文件集合以根`publisher-delivery-manifest030.json`为准，保留的旧清单为对应历史快照。

## 6. 精度测评

采用发布论文RefSpatial NV基线60.50%。按满分100的绝对2pt容差，下限58.50%；较严的相对2%下限59.29%也通过。发布论文未固定该公开数据revision和完整GPU评测配置，本报告明确披露所选revision、提示分支及坐标转换。

准确率解码：temperature0、top_p1、seed42、max_tokens768、HTTP并发4。完整输入、原始响应及评分数据不删减。

| 完整轮次 | location100 | placement100 | 总200 | 排除 |
| --- | ---: | ---: | ---: | ---: |
| 原完整轮 | 67.0% | 59.0% | 63.0% | 0 |
| 固定根入口新GPU轮 | 67.0% | 63.0% | 65.0% | 0 |

根 `verify_result.json` 与原始输出及本地独立作者评分器复算一致；新轮较58.50%下限高6.50个百分点，较59.29%下限高5.71个百分点。没有通过重复抽取成功样本提高成绩。原轮数据在 `publisher021`，新轮请求、响应和复核在 `publisher030`。

此前完整CV-Bench2638为88.16%，低于92.58%；完整RoboSpatial-Home350为62.1312%，低于71.03%。两项失败及全部原件继续保留在 `publisher016`，不改写成通过。

## 7. 性能参考

使用固定原生SGLang0.5.12 OpenAI chat图像压测器，随机文本目标4096/16384 token、随机1024×1024JPEG、输出预算1024、客户端并发1/8/64，每档两轮；每轮分别8/16/128条测量请求，共12份报告、608条，预热另外保留。报告第二轮指标如下，与根 `bench/round2.jsonl` 一致，第一轮在 `bench/round1.jsonl`，12个原始JSONL在 `bench/native/`。

| 文本目标 | 并发 | 测量请求 | 秒数 | 输出token/秒 | 平均TTFT毫秒 | P99 TTFT毫秒 | 平均TPOT毫秒 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 4096 | 1 | 8 | 369.227968 | 22.186835 | 966.967262 | 1252.169475 | 44.169195 |
| 4096 | 8 | 16 | 195.101398 | 83.976846 | 38369.932033 | 52011.804928 | 46.095181 |
| 4096 | 64 | 128 | 1647.660481 | 79.550369 | 582061.111860 | 777238.650271 | 48.110367 |
| 16384 | 1 | 8 | 424.134638 | 19.314622 | 7477.771600 | 8789.814320 | 44.513173 |
| 16384 | 8 | 16 | 307.150360 | 53.341953 | 70386.259257 | 103004.401130 | 64.566532 |
| 16384 | 64 | 128 | 2584.870365 | 50.707379 | 924366.490394 | 1233438.507846 | 68.392311 |

服务四序列上限会在高客户端并发时排队，TTFT包含队列等待。目标文本长度不等于分词往返后的实际输入长度；完整文本/视觉token分解和各数组随原生原件提供，不能把目标长度写成全部请求的精确wire长度。

完整矩阵由镜像前四组48条和镜像结束后八组560条组成；模型、核心源码、native wrapper、客户端版本/源码及实际服务config逐键相同，仅task目录和UUID不同。镜像保存重叠的旧4K/c64中断组完整保留并隔离，没有重跑四组正常分数。固定根入口只执行bench计划，未重采样608条性能。

原生产者对顶层 `request_rate=Infinity` 报格式错误；独立审核只规范化该一个字段为字符串inf，逐份校验退出0、reaped、文件SHA、请求数组和指标公式。原始JSONL不改写。原生output_lens可能来自流usage或请求预算fallback，本报告不据此额外宣称所有wire生成恰好1024 token或所有SSE终止帧已被独立认证。此为该配置性能记录，不代替主办方正式性能验收。

## 8. 注意事项

- 完整数值、根入口实测、材料、镜像新实例复现、评审访问、主办方验收及表单提交分别记录；没有真实提交成功页面就保持 `submitted=false`。
- 原两个Notebook按授权保留，只停止自有模型进程；不改平台计时、看门狗、最大关闭时间或其他实例。模型计时已结束后才封装本件镜像，不重写历史Kimi gate。
- 镜像使用环境、完整数据、代码与固定客户端；17.54GB权重留在数据盘或从固定官方源取回。不绕过15GB新层门禁；真实区域可用回执、代码commit和报告/ZIP哈希在外部清单闭合。
- 本版新增独立干净代码目录的实际准备、启动、环境、功能与清理验收；未另建Notebook或重复200条精度/608条性能，也未把镜像fallback客户端说成此次已执行。
- 仓库和镜像默认私有，跨账号评审访问尚未独立验证；提供实际链接，未擅自公开资产或推断外部账号权限。
- 上游许可、版权声明和历史失败保留；新编适配代码保留版权，没有增加全仓开源许可证。旧README/开发metadata为其生成时点记录，最新交付版本以外部清单和固定Git树为准。
