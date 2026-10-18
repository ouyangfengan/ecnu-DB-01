# 简化问卷系统

当前已实现账号、问卷管理、填写提交、统计结果和浏览器前端。不包含未提交草稿自动保存或填写断点续填。浏览器打开 `/ui/` 使用前端，或打开 `/docs` 测试接口。

问卷的接口、字段示例、状态和跳转语义见 [问卷管理接口.md](问卷管理接口.md)。账号接口约定保持不变，见本文后续章节。

填写进度、答案校验、提交保存和幂等重试见 [填写模块接口.md](填写模块接口.md)。同一用户在同一问卷使用相同 `requestId` 和相同内容重试，返回原提交成功结果，包括问卷已关闭或截止后的重试。

整卷、单题统计及内容分页见 [统计结果接口.md](统计结果接口.md)。统计按成功提交份数计数，仅所有者可查看；每个响应使用同一个快照事务，内容按提交时间、提交 ID 升序排列，不返回填写者身份。

AI 协作的提示词摘录、代码产出、人工审定和使用说明见 [AI使用日志与说明.md](AI使用日志与说明.md)。

项目目标、系统与 MongoDB 设计、跳转和校验逻辑、AI 使用过程及测试结果的汇总见 [项目完成报告.docx](项目完成报告.docx)。

## 环境与启动

- Python 3.11 及以上；开发验证使用 Python 3.11。
- FastAPI 0.115.12、Uvicorn 0.34.2、PyMongo 4.12.1，完整依赖见 `requirements.txt`。
- 本地 MongoDB；所有用户和会话数据都存 MongoDB，不需要关系数据库或 Redis。
- 问卷跨文档操作使用事务，需要 MongoDB 副本集；本地单节点即可。原有账号接口仍兼容 standalone MongoDB。

### 本地单节点副本集

若已有 MongoDB 副本集，直接使用其连接串。若当前使用 standalone，建议另建一个实例，不修改当前数据目录或终止现有进程。下面示例使用独立目录及端口 `27018`，目录位置可自行调整。

在第一个 PowerShell 窗口启动：

```powershell
New-Item -ItemType Directory -Path "F:\MongoDB\data\survey_rs_new" -Force
mongod --dbpath "F:\MongoDB\data\survey_rs_new" --port 27018 --bind_ip 127.0.0.1 --replSet surveyRS
```

在第二个窗口首次初始化：

```powershell
mongosh "mongodb://127.0.0.1:27018/?directConnection=true" --eval "rs.initiate({_id: 'surveyRS', members: [{_id: 0, host: '127.0.0.1:27018'}]})"
mongosh "mongodb://127.0.0.1:27018/?replicaSet=surveyRS" --eval "db.hello().isWritablePrimary"
```

第二条命令应返回 `true`。以后启动同一数据目录时仍需带 `--replSet surveyRS`，但不再执行初始化。单节点仅提供本地事务能力，不提供多节点容灾。

新实例有独立数据库，旧实例中的账号不会自动复制过去；代码没有修改或清空旧数据。已有数据迁移需另行操作，不能让两个运行中的实例共享同一数据目录。

### 启动 API

在项目根目录打开 PowerShell，使用你指定的 Python 环境安装：

```powershell
conda activate database
python -m pip install -r requirements.txt
$env:MONGODB_URI = "mongodb://127.0.0.1:27018/?replicaSet=surveyRS"
$env:MONGODB_DATABASE = "questionnaire"
$env:PUBLIC_BASE_URL = "http://127.0.0.1:8000"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

以上是运行指令，项目不会自动安装到 Conda 环境。启动前需启动 MongoDB；应用启动时会检查连接并建立索引。连接失败则启动失败，不会自动切换成内存数据库。

打开 `http://127.0.0.1:8000/docs`。为兼容账号模块，未设置 `MONGODB_URI` 时仍默认连接 `mongodb://127.0.0.1:27017`，数据库名默认 `questionnaire`。使用上面的独立实例时必须显式设置连接串。源码通过环境变量读取配置，不自动加载 `.env` 文件。连接字符串中的认证信息不应提交到仓库。

浏览器前端地址为 `http://127.0.0.1:8000/ui/`，与 API 同源运行。首次使用可在前端注册账号。已发布问卷的界面填写链接形如 `http://127.0.0.1:8000/ui/?survey=<访问标识>`；接收者登录后即可作答。后端返回的原始 `/surveys/access/<访问标识>` 仍是 JSON API 地址，不是浏览器页面。修改 API 端口时应使用当前浏览器实际打开的源；界面复制链接会按当前源重新生成。

前端支持注册、登录、退出，创建和分页查看本人问卷，草稿题目增改、题型限制与跳转规则、设置截止时间、发布和关闭；填写时按服务端路径逐题校验，支持返回修改和幂等重试；创建者可查看整卷、单题统计及填空内容分页。登录凭证保存在当前浏览器标签页的 `sessionStorage`，关闭标签页即丢弃；提交重试标识与原请求体在该标签页暂存，成功后清除。

前端刻意保持简单：不提供题目删除/排序、未提交答题自动保存、断点续填、实名答卷明细或统计导出。填写端和创建者都需要登录；匿名设置仅控制创建者能否从其他明细功能查看身份，不改变登录要求。题目校验与权限仍由后端执行。

## 数据与安全

### Users

`_id`、`username`、`password_hash`、`created_at`。

- `username` 去除首尾空白后为 1-50 个字符，允许中文，区分大小写，建立唯一索引。
- 密码不去除首尾空格；缺失、`null`、空字符串及纯空白密码均视为空。注册时长度为 6-12 个 Python 字符，不是 UTF-8 字节数。
- 密码使用 Argon2id 加盐哈希，不存明文，不返回哈希。
- 并发注册同名账号时，由唯一索引保证只有一次注册成功。

### Sessions

`_id`、`user_id`、`token_hash`、`created_at`、`expires_at`。

- 使用 32 字节安全随机数生成 URL-safe 凭证；只返回凭证原文，不写入数据库或日志。
- MongoDB 仅保存凭证 SHA-256 哈希。随机凭证具有高熵，不使用用户密码式的低熵输入。
- `user_id` 唯一索引保证单账号只有一条会话；登录原子替换凭证，新凭证生效时旧凭证失效。并发登录以最后完成的数据库写入为准，不以客户端收到响应的先后为准。
- `token_hash` 有唯一索引；`expires_at` 有 TTL 索引。鉴权仍显式检查过期时间，不依赖延迟执行的 TTL 删除。
- 所有时间按 UTC 保存为 BSON Date；接口时间使用带时区的 ISO 8601 字符串。
- 登录成功后有效期为 72 小时。需认证接口在认证通过且业务成功（HTTP 2xx 且 `code = 0`）后，更新为当前时间加 72 小时；失败和公开接口不续期。
- 退出删除当前会话，不续期。重复退出、被顶替的凭证、无效或过期凭证统一视为未登录。
- 续期使用带凭证哈希和未过期条件的 `$max` 更新，不使用 `upsert`，不会缩短期限或恢复已退出、已被替换的会话。
- 已通过认证的在途请求可能在退出或新登录后完成，但无法续期旧凭证。撤销登录不会中断正在执行的业务操作。

注册和登录属于公开接口，登录不会自动复用客户端传入的旧凭证。凭证属于 Bearer 凭证，持有者即可使用；部署到非本机环境时必须使用 HTTPS，并避免在 URL 中传递凭证。本模块未扩展验证码、登录限流或找回密码。

## API

成功和失败均使用 `{"code": ..., "msg": "...", "data": {...}}`；HTTP 状态码与业务错误码不同，前端应分别读取。

### POST /auth/register

公开接口，JSON 请求体：

```json
{"username":"alice","password":"secret"}
```

成功为 HTTP 200：

```json
{"code":0,"msg":"ok","data":{"user_id":"MongoDB ObjectId 字符串","created_at":"2026-10-17T12:00:00+00:00"}}
```

### POST /auth/login

公开接口，请求体与注册相同。登录不重复限制密码长度，只检查非空和字符串类型，再验证密码。

成功为 HTTP 200：

```json
{"code":0,"msg":"ok","data":{"token":"随机凭证","username":"alice"}}
```

之后访问需认证接口时设置：

```text
Authorization: Bearer <token>
```

在 `/docs` 中可点击 `Authorize`，只填写 token 值。

### POST /auth/logout

无需请求体，必须携带以上请求头。成功为 HTTP 200：

```json
{"code":0,"msg":"退出成功","data":{}}
```

### 失败响应

参数校验先于数据库查询和密码认证执行，因此漏填不会返回 `4011`。

| 情况 | HTTP | code | msg |
| --- | --- | --- | --- |
| 用户名或密码缺失、null、空字符串、纯空白 | 400 | 4001 | 用户名/密码不能为空 |
| 用户名或密码不是字符串 | 400 | 4001 | 用户名/密码必须为字符串 |
| 去除首尾空白后的用户名超过 50 个字符 | 400 | 4001 | 用户名长度应为 1–50 个字符 |
| 注册密码长度不在 6-12 个字符 | 400 | 4001 | 密码长度应为 6-12 个字符 |
| JSON 语法错误 | 400 | 4001 | 请求体必须是有效的 JSON |
| 请求体不是 JSON 对象 | 400 | 4001 | 请求体必须是 JSON 对象 |
| 用户名已占用 | 409 | 4090 | 该用户名已被注册 |
| 登录用户名不存在或密码错误 | 401 | 4011 | 用户名或密码错误 |
| 需登录接口的凭证缺失或失效 | 401 | 4010 | 请先登录 |
| 不存在的路径 | 404 | 4040 | 不存在 |
| 请求方法错误 | 405 | 4001 | 请求方法不允许 |
| 运行中数据库故障 | 503 | 5000 | 服务暂不可用，请稍后重试 |
| 未预期内部异常 | 500 | 5000 | 服务器内部错误 |

`4030` 用于问卷管理和统计等接口的所有者权限检查。`5000` 仅用于基础设施或内部异常，避免误报成用户参数错误；错误响应不包含密码、凭证、堆栈和数据库连接详情。

## 后续接口如何复用认证

后续需认证的 JSON 接口，使用 `AuthenticatedRoute` 路由类和 `require_user` 依赖；前者负责成功后续期，后者返回 MongoDB 用户 ID：

```python
from fastapi import APIRouter, Depends
from app.auth import AuthenticatedRoute, require_user
from app.errors import success

router = APIRouter(route_class=AuthenticatedRoute)

@router.get("/example")
def example(user_id=Depends(require_user)):
    return success({"user_id": str(user_id)})
```

示例没有注册进当前应用。只有 `require_user` 而没有 `AuthenticatedRoute` 时只认证、不续期。流式响应不在当前统一 JSON 响应约定内。

## 测试

测试使用真实 MongoDB，不用内存模拟。每个测试建立独立随机名数据库 `questionnaire_test_<uuid>`，结束后只删除该测试数据库，不修改业务数据库；测试账号需有创建和删除测试数据库的权限。

```powershell
$env:TEST_MONGODB_URI = "mongodb://127.0.0.1:27018/?replicaSet=surveyRS"
$env:PYTHONDONTWRITEBYTECODE = "1"
python -m pytest -q
```

测试覆盖：

- 注册正常流程、哈希存储、索引、用户名规范化、中文与大小写。
- 注册和登录分别测试漏填、空值、纯空白、错误类型及非法 JSON。
- 注册密码 5/6/12/13 字符边界，密码首尾空格保留。
- `4001` 参数错误与 `4011` 账号密码错误的区分，登录失败不撤销已有会话。
- 新登录使旧凭证失效、退出立即失效、重复退出、精确到期边界。
- 成功请求滑动续期，失败和公开请求不续期，过期凭证不能续期。
- 并发注册、并发登录、在途请求与退出/新登录交错时不恢复旧会话。
- 测试用受保护路由仅存在于测试应用，不会暴露在正式服务中。
- 填写路径重算、四类答案校验、返回修改清除旧答案、跳过的必答题不误报。
- 匿名设置、重复填写限制、同请求重试成功、同标识不同内容冲突。
- 并发提交与关闭、截止的事务协调，以及幂等索引和每人限一次索引。
- 整卷和单题统计、零计数选项、多选回答数与选项次数的区分。
- 按提交时间和 ID 稳定分页、基于全部有效答案的平均值、重复内容保留。
- 匿名和权限隔离，以及统计读取过程中插入真实新提交时的快照一致性。

只运行原有账号测试可使用 `python -m pytest tests/test_auth.py -q`，不要求副本集。问卷集成测试发现 standalone 时会明确失败，不跳过或伪装成功。

### 账号模块历史验证

2026-10-17，在 Python 3.11.16、MongoDB 8.3.11 独立实例上执行：`57 passed`，耗时 11.03 秒。`pip check` 通过；OpenAPI 正确列出三个账号接口及退出接口的 Bearer 认证。

测试有一条 Starlette 调用 AnyIO 旧别名的依赖弃用警告，不影响测试通过。依赖安装在系统临时目录中的隔离环境，未改动现有 `database` Conda 环境；测试库已清理，临时 MongoDB 已正常关闭。正式运行仍需按前文配置环境并启动本地 MongoDB。

### 问卷模块验证

2026-10-17，使用独立 MongoDB 8.3.11 单节点副本集执行完整测试：`146 passed`，耗时 42.85 秒，其中包括原账号模块 57 项回归。仍有上述一条依赖弃用警告。`pip check` 通过；OpenAPI 中 9 个问卷操作均声明 Bearer 认证。

覆盖问卷权限隔离、列表不查题目、四类题目限制、跳转目标与互斥、截止边界、发布冻结、失败事务回滚、并发添加与发布，以及发布和编辑竞争。独立 standalone 实例另行验证：注册、登录、退出正常，问卷事务操作明确返回配置提示且不留下部分修改。未操作用户原有 MongoDB 实例。

### 填写模块验证

2026-10-18，使用独立单节点 MongoDB 副本集执行最终全量测试：`237 passed`，耗时 74.90 秒，包含原有 146 项回归和新增 91 项测试。仍只有上述一条第三方依赖弃用警告；`pip check` 通过。

验证了实际路径与必答、多选和数字边界、纯空白与非法文本编码、匿名设置、未提交进度不落库、同请求并发重试返回同一成功结果、同标识不同内容冲突、限填一次并发约束、不同用户和问卷隔离、截止或关闭后成功请求重试，以及提交和关闭竞争时的回滚。

新增接口为 `POST /surveys/access/{access_token}/progress` 和 `POST /surveys/access/{access_token}/submit`，均要求 Bearer 认证。测试使用临时独立数据库，不修改用户原有 MongoDB 实例或 Conda 环境。

### 统计模块验证

2026-10-18，使用独立单节点 MongoDB 副本集执行完整回归：`273 passed`，耗时 96.48 秒，包括原有 237 项和新增 36 项统计测试。仍只有上述一条第三方依赖弃用警告，`pip check` 通过。

覆盖整卷与单题一致口径、四类答案、零计数、有效回答分母、稳定分页、极端有限数字平均值、旧记录、所有者权限、身份字段不泄露和业务数据只读。三组并发测试在不同读取阶段暂停统计并通过真实填写接口插入新提交，验证本次响应保留原快照、下次请求看到新数据。

新增 `GET /surveys/{form_id}/statistics` 和 `GET /surveys/{form_id}/questions/{question_id}/statistics`，OpenAPI 均声明 Bearer 认证。测试数据库已自动清理，不修改用户原有 MongoDB 实例或 Conda 环境。

## 六类验收与四部分报告

新增 88 条带独立编号的验收用例，覆盖创建问卷、添加题目、跳转逻辑、校验、提交问卷和统计六类。步骤、输入、预期输出在 `qa/cases.py` 中预先定义；实际结果由脚本执行后填入，失败、跳过和未执行不会写成通过。

配置独立测试副本集后，在项目根目录执行：

```powershell
$env:TEST_MONGODB_URI = "mongodb://127.0.0.1:27132/?replicaSet=acceptanceTest"
$env:PYTHONDONTWRITEBYTECODE = "1"
python -m qa.run_tests
```

URI 是示例，要求对应测试实例已启动。默认运行原有回归、六类验收和报告工具自测，生成 [测试用例与执行报告.md](测试用例与执行报告.md) 及 `测试结果/<运行编号>/` 下的归档和完整 JSON 证据。每次运行保留独立目录，不覆盖上一轮失败证据。

仅运行六类验收可用 `python -m qa.run_tests --scope acceptance`。完整说明及单例复现命令见 [测试说明.md](测试说明.md)。业务接口不变，也没有新增依赖。

2026-10-18 最终通过报告入口运行：`373 passed`，耗时 159.26 秒，包括六类验收 88 条、原有回归 273 项、报告工具自测 12 项。仍只有原先的一条第三方依赖弃用警告，`pip check` 通过。报告的四部分数量、原始 API 证据和执行版本源码摘要均已核对。

最终轮次为 `20261018T015449330470Z-5906d2`。报告中的实际结果由该轮执行数据生成，保留此前轮次归档；没有修改业务代码或既有接口。

上述 373 项为历史实测结果，不包含之后新增的 3 项前端静态资源测试。本次仓库整理环境未安装 `pytest`，因此这 3 项未能重跑。

## 文件结构

```text
app/
  main.py       应用工厂、数据库生命周期、统一错误处理
  config.py     配置和账号参数限制
  schemas.py    注册与登录参数校验
  security.py   密码哈希、随机凭证与时间函数
  database.py   MongoDB 索引
  auth.py       三个账号接口、认证依赖、成功后续期
  surveys.py    问卷管理路由
  survey_service.py  问卷事务、权限和状态
  survey_schemas.py  问卷与题目输入模型
  question_rules.py  题型能力注册表及配置、跳转互斥校验
  filling.py    填写进度和提交路由
  filling_schemas.py  答案列表及 requestId 输入模型
  answer_engine.py  答案校验、实际路径重算和请求规范化
  filling_service.py  提交事务、幂等重试和重复提交控制
  statistics.py  整卷和单题统计路由
  statistics_service.py  统计权限、共享快照事务和结果组织
  statistics_pipeline.py  题型统计注册表、MongoDB 聚合及稳定分页
frontend/
  index.html  浏览器前端入口
  app.js      原生 JavaScript 界面及 API 交互
  style.css   基础响应式样式
tests/
  test_frontend.py  静态页面托管和 API 路径兼容测试
  test_auth.py  真实 MongoDB 集成测试
  test_surveys.py  问卷管理及并发事务集成测试
  test_question_rules.py  跳转和题目限制的边界测试
  test_answer_engine.py  答案类型、空值、跳转与路径校验
  test_filling.py  填写提交、幂等及并发集成测试
  test_statistics.py  统计口径、分页、权限与并发快照集成测试
  test_acceptance.py  六类独立编号的参数化验收测试
  test_reporting.py  报告真实性、脱敏和历史保留自测
qa/
  cases.py       六类用例的步骤、输入与预期输出
  scenarios.py   实际 API 流程、数据库检查和并发控制
  evidence.py    请求、响应及断言取证与脱敏
  pytest_plugin.py  收集各测试阶段的实际结果
  reporting.py   Markdown 报告与 JSON 证据生成
  run_tests.py   执行入口和环境、代码版本记录
```

完整集合字段保留在 `数据库字段草稿.md`。新增 `revision` 用于问卷事务串行化；旧账号数据不需迁移，问卷缺少 `revision` 时首次修改会自动建立该字段。

填写模块使用 `Responses` 保存完成的提交，新增请求标识、内容摘要、匿名及次数限制标记；部分唯一索引兼容缺少新字段的旧记录。每次新提交会更新问卷内部 `revision` 来协调关闭竞争，但不改变已发布内容。

统计模块只读 `Question_forms`、`Questions`、`Responses`，不建立统计缓存或改写旧答卷。新增普通索引 `form_question_oldest` 支持题目过滤和内容排序。文本、数字明细通过单题接口分页查看全部；不论问卷是否匿名，统计接口都不返回填写者身份，当前没有实名答卷详情接口。
