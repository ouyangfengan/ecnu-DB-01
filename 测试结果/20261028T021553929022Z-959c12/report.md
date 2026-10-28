# 测试用例与执行报告

- 运行编号：`20261028T021553929022Z-959c12`
- 开始时间（UTC）：2026-10-28T02:15:53.929022+00:00
- 结束时间（UTC）：2026-10-28T02:26:18.043089+00:00
- pytest/运行器退出码：`0`
- 六类验收：共 88 条；通过 88。
- 原有回归：通过 509。
- 报告工具自测：通过 12。
- [本次完整执行证据 JSON](evidence.json)，包含每次请求、响应、检查值、pytest 节点及准备/执行/清理阶段结果。

## 环境与执行约定

```json
{
  "python": "3.11.16",
  "platform": "Windows-10-10.0.22000-SP0",
  "pytest": "8.3.5",
  "fastapi": "0.115.12",
  "pymongo": "4.12.1",
  "scope": "all",
  "logical_clock": "2100-01-01T00:00:00+00:00（按用例显式推进）",
  "transport": "FastAPI TestClient，进程内 HTTP；真实 MongoDB 副本集",
  "mongodb": "8.3.11",
  "replica_set": "surveyRS",
  "hosts": [
    "127.0.0.1:27018"
  ],
  "pytest_arguments": [
    "<项目根目录>\\tests",
    "-q",
    "--tb=short",
    "-c",
    "<项目根目录>\\pytest.ini",
    "--rootdir",
    "<项目根目录>"
  ]
}
```

使用 pytest、FastAPI TestClient 和真实 MongoDB 副本集；HTTP 在进程内经过实际路由、鉴权和业务逻辑，不需要启动 Uvicorn。
每条 API 用例使用独立随机名测试库。公共前置步骤通过注册、登录接口准备 owner、reader；凭证和密码在证据中隐藏。
业务时钟固定从 2100-01-01T00:00:00Z 开始，截止场景显式推进注入时钟；报告开始/结束时间是真实执行时间，不与业务时钟混用。
接口正常成功为 HTTP 200/code=0；4001→HTTP 400，4010→401，4030→403，4040→404，4090→409。脚本同时断言 HTTP 和业务码。
输入中的 `<form_id>`、`<q1>`、`<token>`、`<A>` 等为准备接口实际返回的 ID、问卷链接标识或选项 ID，不是登录凭证。完整实际输入及响应见逐次请求证据。
错误场景返回预期错误码属于测试通过；pytest 断言失败、环境准备或清理错误、跳过和未执行均不算通过。
下列实际结果只使用本次执行记录。准备请求也列出；表格过长值仅缩略展示，原始 JSON 保留完整内容。源码 SHA-256 摘要存于 JSON，可核对执行版本。

## 分类汇总

| 类别 | 用例数 | 本次结果 |
| --- | ---: | --- |
| 创建问卷测试 | 8 | 通过 8 |
| 添加题目测试 | 14 | 通过 14 |
| 跳转逻辑测试 | 15 | 通过 15 |
| 校验测试 | 26 | 通过 26 |
| 提交问卷测试 | 17 | 通过 17 |
| 统计测试 | 8 | 通过 8 |

## 运行警告

- DeprecationWarning：The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.

## 创建问卷测试

### CRE-001 正常创建及默认字段

脚本节点：`tests/test_acceptance.py::test_acceptance[CRE-001]`

#### 步骤

1. 准备 owner、reader 两个账号并登录；未登录场景不携带凭证。
2. 调用 POST /surveys，随后查询本测试库中的 Question_forms。
3. 成功场景核对默认字段、所有者和返回链接；失败场景检查未写入问卷。

#### 输入

```json
{
  "method": "POST",
  "path": "/surveys",
  "role": "owner",
  "json": {
    "title": "  验收问卷  "
  }
}
```

#### 预期输出

- HTTP 200，code=0。
- 成功时返回合法 form_id 和链接，保存为 draft、默认非匿名且不允许多次填写；失败时问卷数为 0。

#### 实际结果

**通过**；阶段总耗时 0.981 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 执行 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Question_forms 记录数 | 1 | 1 | 符合 |
| 返回合法问卷 ID | true | true | 符合 |
| 访问链接格式 | true | true | 符合 |
| Question_forms.title | "验收问卷" | "验收问卷" | 符合 |
| Question_forms.status | "draft" | "draft" | 符合 |
| Question_forms.description | "" | "" | 符合 |
| Question_forms.allow_anonymous | false | false | 符合 |
| Question_forms.allow_multiple_submissions | false | false | 符合 |
| Question_forms.deadline | null | null | 符合 |
| Question_forms.owner_id | "6ae15adb962dcf769e33e8f3" | "6ae15adb962dcf769e33e8f3" | 符合 |

### CRE-002 标题未提供

脚本节点：`tests/test_acceptance.py::test_acceptance[CRE-002]`

#### 步骤

1. 准备 owner、reader 两个账号并登录；未登录场景不携带凭证。
2. 调用 POST /surveys，随后查询本测试库中的 Question_forms。
3. 成功场景核对默认字段、所有者和返回链接；失败场景检查未写入问卷。

#### 输入

```json
{
  "method": "POST",
  "path": "/surveys",
  "role": "owner",
  "json": {}
}
```

#### 预期输出

- HTTP 400，code=4001。
- 成功时返回合法 form_id 和链接，保存为 draft、默认非匿名且不允许多次填写；失败时问卷数为 0。

#### 实际结果

**通过**；阶段总耗时 0.952 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 执行 | `POST /surveys` | 400 | {"code": 4001, "msg": "title：缺少必填字段"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Question_forms 记录数 | 0 | 0 | 符合 |

### CRE-003 标题为空白

脚本节点：`tests/test_acceptance.py::test_acceptance[CRE-003]`

#### 步骤

1. 准备 owner、reader 两个账号并登录；未登录场景不携带凭证。
2. 调用 POST /surveys，随后查询本测试库中的 Question_forms。
3. 成功场景核对默认字段、所有者和返回链接；失败场景检查未写入问卷。

#### 输入

```json
{
  "method": "POST",
  "path": "/surveys",
  "role": "owner",
  "json": {
    "title": " \t "
  }
}
```

#### 预期输出

- HTTP 400，code=4001。
- 成功时返回合法 form_id 和链接，保存为 draft、默认非匿名且不允许多次填写；失败时问卷数为 0。

#### 实际结果

**通过**；阶段总耗时 0.983 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 执行 | `POST /surveys` | 400 | {"code": 4001, "msg": "标题必须是非空字符串"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Question_forms 记录数 | 0 | 0 | 符合 |

### CRE-004 标题长度 199 字

脚本节点：`tests/test_acceptance.py::test_acceptance[CRE-004]`

#### 步骤

1. 准备 owner、reader 两个账号并登录；未登录场景不携带凭证。
2. 调用 POST /surveys，随后查询本测试库中的 Question_forms。
3. 成功场景核对默认字段、所有者和返回链接；失败场景检查未写入问卷。

#### 输入

```json
{
  "method": "POST",
  "path": "/surveys",
  "role": "owner",
  "json": {
    "title": "问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问"
  }
}
```

#### 预期输出

- HTTP 200，code=0。
- 成功时返回合法 form_id 和链接，保存为 draft、默认非匿名且不允许多次填写；失败时问卷数为 0。

#### 实际结果

**通过**；阶段总耗时 0.947 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 执行 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Question_forms 记录数 | 1 | 1 | 符合 |
| 返回合法问卷 ID | true | true | 符合 |
| 访问链接格式 | true | true | 符合 |
| Question_forms.title | "问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问" | "问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问" | 符合 |
| Question_forms.status | "draft" | "draft" | 符合 |
| Question_forms.description | "" | "" | 符合 |
| Question_forms.allow_anonymous | false | false | 符合 |
| Question_forms.allow_multiple_submissions | false | false | 符合 |
| Question_forms.deadline | null | null | 符合 |
| Question_forms.owner_id | "6ae15ade962dcf769e33e900" | "6ae15ade962dcf769e33e900" | 符合 |

### CRE-005 标题长度 200 字

脚本节点：`tests/test_acceptance.py::test_acceptance[CRE-005]`

#### 步骤

1. 准备 owner、reader 两个账号并登录；未登录场景不携带凭证。
2. 调用 POST /surveys，随后查询本测试库中的 Question_forms。
3. 成功场景核对默认字段、所有者和返回链接；失败场景检查未写入问卷。

#### 输入

```json
{
  "method": "POST",
  "path": "/surveys",
  "role": "owner",
  "json": {
    "title": "问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问"
  }
}
```

#### 预期输出

- HTTP 200，code=0。
- 成功时返回合法 form_id 和链接，保存为 draft、默认非匿名且不允许多次填写；失败时问卷数为 0。

#### 实际结果

**通过**；阶段总耗时 0.997 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 执行 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Question_forms 记录数 | 1 | 1 | 符合 |
| 返回合法问卷 ID | true | true | 符合 |
| 访问链接格式 | true | true | 符合 |
| Question_forms.title | "问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问" | "问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问" | 符合 |
| Question_forms.status | "draft" | "draft" | 符合 |
| Question_forms.description | "" | "" | 符合 |
| Question_forms.allow_anonymous | false | false | 符合 |
| Question_forms.allow_multiple_submissions | false | false | 符合 |
| Question_forms.deadline | null | null | 符合 |
| Question_forms.owner_id | "6ae15adf962dcf769e33e905" | "6ae15adf962dcf769e33e905" | 符合 |

### CRE-006 标题长度 201 字

脚本节点：`tests/test_acceptance.py::test_acceptance[CRE-006]`

#### 步骤

1. 准备 owner、reader 两个账号并登录；未登录场景不携带凭证。
2. 调用 POST /surveys，随后查询本测试库中的 Question_forms。
3. 成功场景核对默认字段、所有者和返回链接；失败场景检查未写入问卷。

#### 输入

```json
{
  "method": "POST",
  "path": "/surveys",
  "role": "owner",
  "json": {
    "title": "问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问问"
  }
}
```

#### 预期输出

- HTTP 400，code=4001。
- 成功时返回合法 form_id 和链接，保存为 draft、默认非匿名且不允许多次填写；失败时问卷数为 0。

#### 实际结果

**通过**；阶段总耗时 0.966 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 执行 | `POST /surveys` | 400 | {"code": 4001, "msg": "title：字符串长度超出限制"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Question_forms 记录数 | 0 | 0 | 符合 |

### CRE-007 未登录创建

脚本节点：`tests/test_acceptance.py::test_acceptance[CRE-007]`

#### 步骤

1. 准备 owner、reader 两个账号并登录；未登录场景不携带凭证。
2. 调用 POST /surveys，随后查询本测试库中的 Question_forms。
3. 成功场景核对默认字段、所有者和返回链接；失败场景检查未写入问卷。

#### 输入

```json
{
  "method": "POST",
  "path": "/surveys",
  "role": null,
  "json": {
    "title": "验收问卷"
  }
}
```

#### 预期输出

- HTTP 401，code=4010。
- 成功时返回合法 form_id 和链接，保存为 draft、默认非匿名且不允许多次填写；失败时问卷数为 0。

#### 实际结果

**通过**；阶段总耗时 0.934 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 执行 | `POST /surveys` | 401 | {"code": 4010, "msg": "请先登录"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Question_forms 记录数 | 0 | 0 | 符合 |

### CRE-008 匿名字段不能用字符串代替布尔值

脚本节点：`tests/test_acceptance.py::test_acceptance[CRE-008]`

#### 步骤

1. 准备 owner、reader 两个账号并登录；未登录场景不携带凭证。
2. 调用 POST /surveys，随后查询本测试库中的 Question_forms。
3. 成功场景核对默认字段、所有者和返回链接；失败场景检查未写入问卷。

#### 输入

```json
{
  "method": "POST",
  "path": "/surveys",
  "role": "owner",
  "json": {
    "title": "问卷",
    "allow_anonymous": "true"
  }
}
```

#### 预期输出

- HTTP 400，code=4001。
- 成功时返回合法 form_id 和链接，保存为 draft、默认非匿名且不允许多次填写；失败时问卷数为 0。

#### 实际结果

**通过**；阶段总耗时 0.978 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 执行 | `POST /surveys` | 400 | {"code": 4001, "msg": "allow_anonymous：必须为布尔值"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Question_forms 记录数 | 0 | 0 | 符合 |


## 添加题目测试

### ADD-001 添加 single 题型

脚本节点：`tests/test_acceptance.py::test_acceptance[ADD-001]`

#### 步骤

1. 创建一份草稿问卷。
2. 调用添加题目接口，再读取题目数据库记录。
3. 检查题型、默认非必答、题目顺序及选择题的服务端选项 ID。

#### 输入

```json
{
  "method": "POST",
  "path": "/surveys/<form_id>/questions",
  "json": {
    "title": "验收题目",
    "type": "single",
    "options": [
      {
        "text": "A"
      },
      {
        "text": "B"
      },
      {
        "text": "C"
      }
    ]
  }
}
```

#### 预期输出

- HTTP 200、code=0；题目数为 1、order=1、required=false，选项 ID 由服务端生成。

#### 实际结果

**通过**；阶段总耗时 1.052 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 执行 | `POST /surveys/6ae15ae3962dcf769e33e918/questions` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Questions 记录数 | 1 | 1 | 符合 |
| 题型 | "single" | "single" | 符合 |
| 题目顺序 | 1 | 1 | 符合 |
| 默认非必答 | false | false | 符合 |
| 选项数量 | 3 | 3 | 符合 |
| 新选项 ID 有效 | true | true | 符合 |
| Questions.form_id | "6ae15ae3962dcf769e33e918" | "6ae15ae3962dcf769e33e918" | 符合 |

### ADD-002 添加 multiple 题型

脚本节点：`tests/test_acceptance.py::test_acceptance[ADD-002]`

#### 步骤

1. 创建一份草稿问卷。
2. 调用添加题目接口，再读取题目数据库记录。
3. 检查题型、默认非必答、题目顺序及选择题的服务端选项 ID。

#### 输入

```json
{
  "method": "POST",
  "path": "/surveys/<form_id>/questions",
  "json": {
    "title": "验收题目",
    "type": "multiple",
    "options": [
      {
        "text": "A"
      },
      {
        "text": "B"
      },
      {
        "text": "C"
      }
    ]
  }
}
```

#### 预期输出

- HTTP 200、code=0；题目数为 1、order=1、required=false，选项 ID 由服务端生成。

#### 实际结果

**通过**；阶段总耗时 0.996 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 执行 | `POST /surveys/6ae15ae4962dcf769e33e921/questions` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Questions 记录数 | 1 | 1 | 符合 |
| 题型 | "multiple" | "multiple" | 符合 |
| 题目顺序 | 1 | 1 | 符合 |
| 默认非必答 | false | false | 符合 |
| 选项数量 | 3 | 3 | 符合 |
| 新选项 ID 有效 | true | true | 符合 |
| Questions.form_id | "6ae15ae4962dcf769e33e921" | "6ae15ae4962dcf769e33e921" | 符合 |

### ADD-003 添加 text 题型

脚本节点：`tests/test_acceptance.py::test_acceptance[ADD-003]`

#### 步骤

1. 创建一份草稿问卷。
2. 调用添加题目接口，再读取题目数据库记录。
3. 检查题型、默认非必答、题目顺序及选择题的服务端选项 ID。

#### 输入

```json
{
  "method": "POST",
  "path": "/surveys/<form_id>/questions",
  "json": {
    "title": "验收题目",
    "type": "text"
  }
}
```

#### 预期输出

- HTTP 200、code=0；题目数为 1、order=1、required=false，选项 ID 由服务端生成。

#### 实际结果

**通过**；阶段总耗时 1.003 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 执行 | `POST /surveys/6ae15ae5962dcf769e33e92a/questions` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Questions 记录数 | 1 | 1 | 符合 |
| 题型 | "text" | "text" | 符合 |
| 题目顺序 | 1 | 1 | 符合 |
| 默认非必答 | false | false | 符合 |
| 填空题没有选项 | [] | [] | 符合 |
| Questions.form_id | "6ae15ae5962dcf769e33e92a" | "6ae15ae5962dcf769e33e92a" | 符合 |

### ADD-004 添加 number 题型

脚本节点：`tests/test_acceptance.py::test_acceptance[ADD-004]`

#### 步骤

1. 创建一份草稿问卷。
2. 调用添加题目接口，再读取题目数据库记录。
3. 检查题型、默认非必答、题目顺序及选择题的服务端选项 ID。

#### 输入

```json
{
  "method": "POST",
  "path": "/surveys/<form_id>/questions",
  "json": {
    "title": "验收题目",
    "type": "number"
  }
}
```

#### 预期输出

- HTTP 200、code=0；题目数为 1、order=1、required=false，选项 ID 由服务端生成。

#### 实际结果

**通过**；阶段总耗时 1.048 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 执行 | `POST /surveys/6ae15ae7962dcf769e33e930/questions` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Questions 记录数 | 1 | 1 | 符合 |
| 题型 | "number" | "number" | 符合 |
| 题目顺序 | 1 | 1 | 符合 |
| 默认非必答 | false | false | 符合 |
| 填空题没有选项 | [] | [] | 符合 |
| Questions.form_id | "6ae15ae7962dcf769e33e930" | "6ae15ae7962dcf769e33e930" | 符合 |

### ADD-005 题目标题为空

脚本节点：`tests/test_acceptance.py::test_acceptance[ADD-005]`

#### 步骤

1. owner 创建草稿；已发布场景先添加一题并发布。
2. 以指定身份调用添加接口。
3. 读取 Questions 数量和问卷 revision，检查成功写入或失败回滚。

#### 输入

```json
{
  "method": "POST",
  "path": "/surveys/<form_id>/questions",
  "role": "owner",
  "initial_status": "draft",
  "json": {
    "title": "",
    "type": "text"
  }
}
```

#### 预期输出

- code=4001，提示包含“非空”。
- 成功新增 1 题；失败不新增题目且 revision 不改变。

#### 实际结果

**通过**；阶段总耗时 0.914 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 执行 | `POST /surveys/6ae15ae7962dcf769e33e936/questions` | 400 | {"code": 4001, "msg": "标题必须是非空字符串"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Questions 记录数 | 0 | 0 | 符合 |
| Question_forms.revision | 0 | 0 | 符合 |

### ADD-006 题目缺少题型

脚本节点：`tests/test_acceptance.py::test_acceptance[ADD-006]`

#### 步骤

1. owner 创建草稿；已发布场景先添加一题并发布。
2. 以指定身份调用添加接口。
3. 读取 Questions 数量和问卷 revision，检查成功写入或失败回滚。

#### 输入

```json
{
  "method": "POST",
  "path": "/surveys/<form_id>/questions",
  "role": "owner",
  "initial_status": "draft",
  "json": {
    "title": "题目"
  }
}
```

#### 预期输出

- code=4001，提示包含“必填”。
- 成功新增 1 题；失败不新增题目且 revision 不改变。

#### 实际结果

**通过**；阶段总耗时 1.059 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 执行 | `POST /surveys/6ae15ae8962dcf769e33e93b/questions` | 400 | {"code": 4001, "msg": "type：缺少必填字段"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Questions 记录数 | 0 | 0 | 符合 |
| Question_forms.revision | 0 | 0 | 符合 |

### ADD-007 不支持的题型

脚本节点：`tests/test_acceptance.py::test_acceptance[ADD-007]`

#### 步骤

1. owner 创建草稿；已发布场景先添加一题并发布。
2. 以指定身份调用添加接口。
3. 读取 Questions 数量和问卷 revision，检查成功写入或失败回滚。

#### 输入

```json
{
  "method": "POST",
  "path": "/surveys/<form_id>/questions",
  "role": "owner",
  "initial_status": "draft",
  "json": {
    "title": "题目",
    "type": "matrix"
  }
}
```

#### 预期输出

- code=4001，提示包含“不支持”。
- 成功新增 1 题；失败不新增题目且 revision 不改变。

#### 实际结果

**通过**；阶段总耗时 1.289 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 执行 | `POST /surveys/6ae15aea962dcf769e33e940/questions` | 400 | {"code": 4001, "msg": "type：不支持的取值"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Questions 记录数 | 0 | 0 | 符合 |
| Question_forms.revision | 0 | 0 | 符合 |

### ADD-008 单选题缺少选项

脚本节点：`tests/test_acceptance.py::test_acceptance[ADD-008]`

#### 步骤

1. owner 创建草稿；已发布场景先添加一题并发布。
2. 以指定身份调用添加接口。
3. 读取 Questions 数量和问卷 revision，检查成功写入或失败回滚。

#### 输入

```json
{
  "method": "POST",
  "path": "/surveys/<form_id>/questions",
  "role": "owner",
  "initial_status": "draft",
  "json": {
    "title": "题目",
    "type": "single"
  }
}
```

#### 预期输出

- code=4001，提示包含“至少”。
- 成功新增 1 题；失败不新增题目且 revision 不改变。

#### 实际结果

**通过**；阶段总耗时 1.354 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 执行 | `POST /surveys/6ae15aeb962dcf769e33e945/questions` | 400 | {"code": 4001, "msg": "选择题至少需要两个选项"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Questions 记录数 | 0 | 0 | 符合 |
| Question_forms.revision | 0 | 0 | 符合 |

### ADD-009 多选题只有一个选项

脚本节点：`tests/test_acceptance.py::test_acceptance[ADD-009]`

#### 步骤

1. owner 创建草稿；已发布场景先添加一题并发布。
2. 以指定身份调用添加接口。
3. 读取 Questions 数量和问卷 revision，检查成功写入或失败回滚。

#### 输入

```json
{
  "method": "POST",
  "path": "/surveys/<form_id>/questions",
  "role": "owner",
  "initial_status": "draft",
  "json": {
    "title": "题目",
    "type": "multiple",
    "options": [
      {
        "text": "A"
      }
    ]
  }
}
```

#### 预期输出

- code=4001，提示包含“至少”。
- 成功新增 1 题；失败不新增题目且 revision 不改变。

#### 实际结果

**通过**；阶段总耗时 1.020 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 执行 | `POST /surveys/6ae15aec962dcf769e33e94b/questions` | 400 | {"code": 4001, "msg": "选择题至少需要两个选项"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Questions 记录数 | 0 | 0 | 符合 |
| Question_forms.revision | 0 | 0 | 符合 |

### ADD-010 单选题恰好两个选项

脚本节点：`tests/test_acceptance.py::test_acceptance[ADD-010]`

#### 步骤

1. owner 创建草稿；已发布场景先添加一题并发布。
2. 以指定身份调用添加接口。
3. 读取 Questions 数量和问卷 revision，检查成功写入或失败回滚。

#### 输入

```json
{
  "method": "POST",
  "path": "/surveys/<form_id>/questions",
  "role": "owner",
  "initial_status": "draft",
  "json": {
    "title": "题目",
    "type": "single",
    "options": [
      {
        "text": "A"
      },
      {
        "text": "B"
      }
    ]
  }
}
```

#### 预期输出

- code=0，返回新题目。
- 成功新增 1 题；失败不新增题目且 revision 不改变。

#### 实际结果

**通过**；阶段总耗时 0.984 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 执行 | `POST /surveys/6ae15aed962dcf769e33e952/questions` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Questions 记录数 | 1 | 1 | 符合 |
| 题型 | "single" | "single" | 符合 |
| 题目顺序 | 1 | 1 | 符合 |
| 默认非必答 | false | false | 符合 |
| 选项数量 | 2 | 2 | 符合 |
| 新选项 ID 有效 | true | true | 符合 |
| Questions.form_id | "6ae15aed962dcf769e33e952" | "6ae15aed962dcf769e33e952" | 符合 |

### ADD-011 文本最少长度大于最多长度

脚本节点：`tests/test_acceptance.py::test_acceptance[ADD-011]`

#### 步骤

1. owner 创建草稿；已发布场景先添加一题并发布。
2. 以指定身份调用添加接口。
3. 读取 Questions 数量和问卷 revision，检查成功写入或失败回滚。

#### 输入

```json
{
  "method": "POST",
  "path": "/surveys/<form_id>/questions",
  "role": "owner",
  "initial_status": "draft",
  "json": {
    "title": "题目",
    "type": "text",
    "validation": {
      "min_length": 3,
      "max_length": 1
    }
  }
}
```

#### 预期输出

- code=4001，提示包含“最小”。
- 成功新增 1 题；失败不新增题目且 revision 不改变。

#### 实际结果

**通过**；阶段总耗时 1.505 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 执行 | `POST /surveys/6ae15aef962dcf769e33e95a/questions` | 400 | {"code": 4001, "msg": "最小限制不能大于最大限制"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Questions 记录数 | 0 | 0 | 符合 |
| Question_forms.revision | 0 | 0 | 符合 |

### ADD-012 数字区间内没有合法整数

脚本节点：`tests/test_acceptance.py::test_acceptance[ADD-012]`

#### 步骤

1. owner 创建草稿；已发布场景先添加一题并发布。
2. 以指定身份调用添加接口。
3. 读取 Questions 数量和问卷 revision，检查成功写入或失败回滚。

#### 输入

```json
{
  "method": "POST",
  "path": "/surveys/<form_id>/questions",
  "role": "owner",
  "initial_status": "draft",
  "json": {
    "title": "题目",
    "type": "number",
    "validation": {
      "min_value": 0.1,
      "max_value": 0.9,
      "integer_only": true
    }
  }
}
```

#### 预期输出

- code=4001，提示包含“整数”。
- 成功新增 1 题；失败不新增题目且 revision 不改变。

#### 实际结果

**通过**；阶段总耗时 1.133 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 执行 | `POST /surveys/6ae15af0962dcf769e33e960/questions` | 400 | {"code": 4001, "msg": "数字范围内不存在符合整数限制的答案"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Questions 记录数 | 0 | 0 | 符合 |
| Question_forms.revision | 0 | 0 | 符合 |

### ADD-013 非所有者添加

脚本节点：`tests/test_acceptance.py::test_acceptance[ADD-013]`

#### 步骤

1. owner 创建草稿；已发布场景先添加一题并发布。
2. 以指定身份调用添加接口。
3. 读取 Questions 数量和问卷 revision，检查成功写入或失败回滚。

#### 输入

```json
{
  "method": "POST",
  "path": "/surveys/<form_id>/questions",
  "role": "reader",
  "initial_status": "draft",
  "json": {
    "title": "题目",
    "type": "text"
  }
}
```

#### 预期输出

- code=4030，提示包含“无权限”。
- 成功新增 1 题；失败不新增题目且 revision 不改变。

#### 实际结果

**通过**；阶段总耗时 1.041 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 执行 | `POST /surveys/6ae15af1962dcf769e33e966/questions` | 403 | {"code": 4030, "msg": "无权限"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Questions 记录数 | 0 | 0 | 符合 |
| Question_forms.revision | 0 | 0 | 符合 |

### ADD-014 已发布问卷禁止添加

脚本节点：`tests/test_acceptance.py::test_acceptance[ADD-014]`

#### 步骤

1. owner 创建草稿；已发布场景先添加一题并发布。
2. 以指定身份调用添加接口。
3. 读取 Questions 数量和问卷 revision，检查成功写入或失败回滚。

#### 输入

```json
{
  "method": "POST",
  "path": "/surveys/<form_id>/questions",
  "role": "owner",
  "initial_status": "published",
  "json": {
    "title": "题目",
    "type": "text"
  }
}
```

#### 预期输出

- code=4090，提示包含“发布后”。
- 成功新增 1 题；失败不新增题目且 revision 不改变。

#### 实际结果

**通过**；阶段总耗时 1.292 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15af2962dcf769e33e96b/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15af2962dcf769e33e96b/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/6ae15af2962dcf769e33e96b/questions` | 409 | {"code": 4090, "msg": "发布后不能修改问卷"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Questions 记录数 | 1 | 1 | 符合 |
| Question_forms.revision | 2 | 2 | 符合 |


## 跳转逻辑测试

### JMP-001 single 输入 'A' 跳转至 q3

脚本节点：`tests/test_acceptance.py::test_acceptance[JMP-001]`

#### 步骤

1. 依次创建 q1、必答文本 q2、必答文本 q3；q1 使用指定题型。
2. PATCH q1 配置输入中列出的跳转规则，然后发布。
3. POST progress，仅提供 q1 答案，检查下一题或结束标记。

#### 输入

```json
{
  "configuration": [
    {
      "condition": {
        "op": "eq",
        "value": "<A>"
      },
      "target": "<q3>"
    }
  ],
  "value": "A",
  "options": "A/B/C 对应 q1 返回的选项 ID",
  "method": "POST",
  "path": "/surveys/access/<token>/progress",
  "json": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": "A"
      }
    ]
  }
}
```

#### 预期输出

- HTTP 200、code=0。
- next_question=q3；end 时为 null 且 complete=true，否则 complete=false。

#### 实际结果

**通过**；阶段总耗时 1.239 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15af3962dcf769e33e971/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15af3962dcf769e33e971/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ae15af3962dcf769e33e971/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `PATCH /surveys/6ae15af3962dcf769e33e971/questions/6ae15af3962dcf769e33e972` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ae15af3962dcf769e33e971/publish` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 执行 | `POST /surveys/access/FG7mMXIucReu_qaMr4I9X8ep67jojdFL9KS9B51b0Ls/progress` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 下一题 | "6ae15af3962dcf769e33e977" | "6ae15af3962dcf769e33e977" | 符合 |
| 结束标记 | false | false | 符合 |
| Responses 记录数 | 0 | 0 | 符合 |

### JMP-002 single 输入 'B' 跳转至 q2

脚本节点：`tests/test_acceptance.py::test_acceptance[JMP-002]`

#### 步骤

1. 依次创建 q1、必答文本 q2、必答文本 q3；q1 使用指定题型。
2. PATCH q1 配置输入中列出的跳转规则，然后发布。
3. POST progress，仅提供 q1 答案，检查下一题或结束标记。

#### 输入

```json
{
  "configuration": [
    {
      "condition": {
        "op": "eq",
        "value": "<A>"
      },
      "target": "<q3>"
    }
  ],
  "value": "B",
  "options": "A/B/C 对应 q1 返回的选项 ID",
  "method": "POST",
  "path": "/surveys/access/<token>/progress",
  "json": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": "B"
      }
    ]
  }
}
```

#### 预期输出

- HTTP 200、code=0。
- next_question=q2；end 时为 null 且 complete=true，否则 complete=false。

#### 实际结果

**通过**；阶段总耗时 1.176 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15af4962dcf769e33e97c/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15af4962dcf769e33e97c/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ae15af4962dcf769e33e97c/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `PATCH /surveys/6ae15af4962dcf769e33e97c/questions/6ae15af4962dcf769e33e97d` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ae15af4962dcf769e33e97c/publish` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 执行 | `POST /surveys/access/GuMoSkNKq98dwsHaRouzIpnxhr9OE0HtDfwFSHkLc-g/progress` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 下一题 | "6ae15af4962dcf769e33e981" | "6ae15af4962dcf769e33e981" | 符合 |
| 结束标记 | false | false | 符合 |
| Responses 记录数 | 0 | 0 | 符合 |

### JMP-003 multiple 输入 ['B', 'A'] 跳转至 q3

脚本节点：`tests/test_acceptance.py::test_acceptance[JMP-003]`

#### 步骤

1. 依次创建 q1、必答文本 q2、必答文本 q3；q1 使用指定题型。
2. PATCH q1 配置输入中列出的跳转规则，然后发布。
3. POST progress，仅提供 q1 答案，检查下一题或结束标记。

#### 输入

```json
{
  "configuration": [
    {
      "condition": {
        "op": "exact",
        "value": [
          "<A>",
          "<B>"
        ]
      },
      "target": "<q3>"
    }
  ],
  "value": [
    "B",
    "A"
  ],
  "options": "A/B/C 对应 q1 返回的选项 ID",
  "method": "POST",
  "path": "/surveys/access/<token>/progress",
  "json": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": [
          "B",
          "A"
        ]
      }
    ]
  }
}
```

#### 预期输出

- HTTP 200、code=0。
- next_question=q3；end 时为 null 且 complete=true，否则 complete=false。

#### 实际结果

**通过**；阶段总耗时 1.204 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15af6962dcf769e33e987/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15af6962dcf769e33e987/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ae15af6962dcf769e33e987/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `PATCH /surveys/6ae15af6962dcf769e33e987/questions/6ae15af6962dcf769e33e988` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ae15af6962dcf769e33e987/publish` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 执行 | `POST /surveys/access/_cScXobL3HME7S1iOl_dm3zGbQqun6rgAGSz-QhKWjQ/progress` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 下一题 | "6ae15af6962dcf769e33e98d" | "6ae15af6962dcf769e33e98d" | 符合 |
| 结束标记 | false | false | 符合 |
| Responses 记录数 | 0 | 0 | 符合 |

### JMP-004 multiple 输入 ['A'] 跳转至 q2

脚本节点：`tests/test_acceptance.py::test_acceptance[JMP-004]`

#### 步骤

1. 依次创建 q1、必答文本 q2、必答文本 q3；q1 使用指定题型。
2. PATCH q1 配置输入中列出的跳转规则，然后发布。
3. POST progress，仅提供 q1 答案，检查下一题或结束标记。

#### 输入

```json
{
  "configuration": [
    {
      "condition": {
        "op": "exact",
        "value": [
          "<A>",
          "<B>"
        ]
      },
      "target": "<q3>"
    }
  ],
  "value": [
    "A"
  ],
  "options": "A/B/C 对应 q1 返回的选项 ID",
  "method": "POST",
  "path": "/surveys/access/<token>/progress",
  "json": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": [
          "A"
        ]
      }
    ]
  }
}
```

#### 预期输出

- HTTP 200、code=0。
- next_question=q2；end 时为 null 且 complete=true，否则 complete=false。

#### 实际结果

**通过**；阶段总耗时 1.114 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15af7962dcf769e33e992/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15af7962dcf769e33e992/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ae15af7962dcf769e33e992/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `PATCH /surveys/6ae15af7962dcf769e33e992/questions/6ae15af7962dcf769e33e993` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ae15af7962dcf769e33e992/publish` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 执行 | `POST /surveys/access/xg9i0UUy4wW0MyS0ktVtgIk6MPp8iU87G9vph-tYCBY/progress` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 下一题 | "6ae15af7962dcf769e33e997" | "6ae15af7962dcf769e33e997" | 符合 |
| 结束标记 | false | false | 符合 |
| Responses 记录数 | 0 | 0 | 符合 |

### JMP-005 multiple 输入 ['A', 'B', 'C'] 跳转至 q2

脚本节点：`tests/test_acceptance.py::test_acceptance[JMP-005]`

#### 步骤

1. 依次创建 q1、必答文本 q2、必答文本 q3；q1 使用指定题型。
2. PATCH q1 配置输入中列出的跳转规则，然后发布。
3. POST progress，仅提供 q1 答案，检查下一题或结束标记。

#### 输入

```json
{
  "configuration": [
    {
      "condition": {
        "op": "exact",
        "value": [
          "<A>",
          "<B>"
        ]
      },
      "target": "<q3>"
    }
  ],
  "value": [
    "A",
    "B",
    "C"
  ],
  "options": "A/B/C 对应 q1 返回的选项 ID",
  "method": "POST",
  "path": "/surveys/access/<token>/progress",
  "json": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": [
          "A",
          "B",
          "C"
        ]
      }
    ]
  }
}
```

#### 预期输出

- HTTP 200、code=0。
- next_question=q2；end 时为 null 且 complete=true，否则 complete=false。

#### 实际结果

**通过**；阶段总耗时 1.034 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15af8962dcf769e33e99d/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15af8962dcf769e33e99d/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ae15af8962dcf769e33e99d/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `PATCH /surveys/6ae15af8962dcf769e33e99d/questions/6ae15af8962dcf769e33e99e` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ae15af8962dcf769e33e99d/publish` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 执行 | `POST /surveys/access/W-IbHsHqclav-KsC-seJfFAi4MCy2DeCrCmlEu0TBsg/progress` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 下一题 | "6ae15af8962dcf769e33e9a2" | "6ae15af8962dcf769e33e9a2" | 符合 |
| 结束标记 | false | false | 符合 |
| Responses 记录数 | 0 | 0 | 符合 |

### JMP-006 number 输入 4.9 跳转至 q3

脚本节点：`tests/test_acceptance.py::test_acceptance[JMP-006]`

#### 步骤

1. 依次创建 q1、必答文本 q2、必答文本 q3；q1 使用指定题型。
2. PATCH q1 配置输入中列出的跳转规则，然后发布。
3. POST progress，仅提供 q1 答案，检查下一题或结束标记。

#### 输入

```json
{
  "configuration": [
    {
      "condition": {
        "op": "lt",
        "value": 5
      },
      "target": "<q3>"
    },
    {
      "condition": {
        "op": "gte",
        "value": 5
      },
      "target": "end"
    }
  ],
  "value": 4.9,
  "options": "A/B/C 对应 q1 返回的选项 ID",
  "method": "POST",
  "path": "/surveys/access/<token>/progress",
  "json": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": 4.9
      }
    ]
  }
}
```

#### 预期输出

- HTTP 200、code=0。
- next_question=q3；end 时为 null 且 complete=true，否则 complete=false。

#### 实际结果

**通过**；阶段总耗时 1.030 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15af9962dcf769e33e9a8/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15af9962dcf769e33e9a8/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ae15af9962dcf769e33e9a8/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `PATCH /surveys/6ae15af9962dcf769e33e9a8/questions/6ae15af9962dcf769e33e9a9` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ae15af9962dcf769e33e9a8/publish` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 执行 | `POST /surveys/access/J4Fdf7jgCP5ZgylS88W4SnDXQJ9xA7rdOYp82Oxjnls/progress` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 下一题 | "6ae15af9962dcf769e33e9ab" | "6ae15af9962dcf769e33e9ab" | 符合 |
| 结束标记 | false | false | 符合 |
| Responses 记录数 | 0 | 0 | 符合 |

### JMP-007 number 输入 5 跳转至 end

脚本节点：`tests/test_acceptance.py::test_acceptance[JMP-007]`

#### 步骤

1. 依次创建 q1、必答文本 q2、必答文本 q3；q1 使用指定题型。
2. PATCH q1 配置输入中列出的跳转规则，然后发布。
3. POST progress，仅提供 q1 答案，检查下一题或结束标记。

#### 输入

```json
{
  "configuration": [
    {
      "condition": {
        "op": "lt",
        "value": 5
      },
      "target": "<q3>"
    },
    {
      "condition": {
        "op": "gte",
        "value": 5
      },
      "target": "end"
    }
  ],
  "value": 5,
  "options": "A/B/C 对应 q1 返回的选项 ID",
  "method": "POST",
  "path": "/surveys/access/<token>/progress",
  "json": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": 5
      }
    ]
  }
}
```

#### 预期输出

- HTTP 200、code=0。
- next_question=end；end 时为 null 且 complete=true，否则 complete=false。

#### 实际结果

**通过**；阶段总耗时 1.048 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15afa962dcf769e33e9b0/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15afa962dcf769e33e9b0/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ae15afa962dcf769e33e9b0/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `PATCH /surveys/6ae15afa962dcf769e33e9b0/questions/6ae15afa962dcf769e33e9b1` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ae15afa962dcf769e33e9b0/publish` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 执行 | `POST /surveys/access/KJpfoSoBI0Pd-fzJSLxfHZmMGX8KJi8yn5z3u2725S4/progress` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 下一题 | null | null | 符合 |
| 结束标记 | true | true | 符合 |
| Responses 记录数 | 0 | 0 | 符合 |

### JMP-008 number 输入 5.1 跳转至 end

脚本节点：`tests/test_acceptance.py::test_acceptance[JMP-008]`

#### 步骤

1. 依次创建 q1、必答文本 q2、必答文本 q3；q1 使用指定题型。
2. PATCH q1 配置输入中列出的跳转规则，然后发布。
3. POST progress，仅提供 q1 答案，检查下一题或结束标记。

#### 输入

```json
{
  "configuration": [
    {
      "condition": {
        "op": "lt",
        "value": 5
      },
      "target": "<q3>"
    },
    {
      "condition": {
        "op": "gte",
        "value": 5
      },
      "target": "end"
    }
  ],
  "value": 5.1,
  "options": "A/B/C 对应 q1 返回的选项 ID",
  "method": "POST",
  "path": "/surveys/access/<token>/progress",
  "json": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": 5.1
      }
    ]
  }
}
```

#### 预期输出

- HTTP 200、code=0。
- next_question=end；end 时为 null 且 complete=true，否则 complete=false。

#### 实际结果

**通过**；阶段总耗时 1.164 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15afb962dcf769e33e9b8/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15afb962dcf769e33e9b8/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ae15afb962dcf769e33e9b8/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `PATCH /surveys/6ae15afb962dcf769e33e9b8/questions/6ae15afb962dcf769e33e9b9` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ae15afb962dcf769e33e9b8/publish` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 执行 | `POST /surveys/access/bVVbC3bU9SO4vQf52V2rVHkZu6OofsdtmCI3up8WmT0/progress` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 下一题 | null | null | 符合 |
| 结束标记 | true | true | 符合 |
| Responses 记录数 | 0 | 0 | 符合 |

### JMP-009 禁止跳向自身

脚本节点：`tests/test_acceptance.py::test_acceptance[JMP-009]`

#### 步骤

1. 创建数字 q1、数字 q2、文本 q3，另建问卷中的一题用于跨问卷场景。
2. 自跳配置 q1→q1；逆向配置 q2→q1；跨卷/不存在使用对应 ID；重叠使用 lte 5 和 gte 5。
3. PATCH 保存规则并读取原题和 revision，确认失败未修改配置。

#### 输入

```json
{
  "method": "PATCH",
  "path": "/surveys/<form_id>/questions/<source_id>",
  "case": "self",
  "ordinary_condition": {
    "op": "eq",
    "value": 1
  },
  "overlap_conditions": [
    {
      "op": "lte",
      "value": 5
    },
    {
      "op": "gte",
      "value": 5
    }
  ]
}
```

#### 预期输出

- HTTP 400、code=4001；规则列表仍为空，revision 不变。

#### 实际结果

**通过**；阶段总耗时 1.048 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15afc962dcf769e33e9c0/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15afc962dcf769e33e9c0/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ae15afc962dcf769e33e9c0/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ae15afc962dcf769e33e9c4/questions` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 执行 | `PATCH /surveys/6ae15afc962dcf769e33e9c0/questions/6ae15afc962dcf769e33e9c1` | 400 | {"code": 4001, "msg": "只能跳转到后续题目或 end"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Questions.jump_rules | [] | [] | 符合 |
| Question_forms.revision | 3 | 3 | 符合 |

### JMP-010 禁止向前题跳转

脚本节点：`tests/test_acceptance.py::test_acceptance[JMP-010]`

#### 步骤

1. 创建数字 q1、数字 q2、文本 q3，另建问卷中的一题用于跨问卷场景。
2. 自跳配置 q1→q1；逆向配置 q2→q1；跨卷/不存在使用对应 ID；重叠使用 lte 5 和 gte 5。
3. PATCH 保存规则并读取原题和 revision，确认失败未修改配置。

#### 输入

```json
{
  "method": "PATCH",
  "path": "/surveys/<form_id>/questions/<source_id>",
  "case": "backward",
  "ordinary_condition": {
    "op": "eq",
    "value": 1
  },
  "overlap_conditions": [
    {
      "op": "lte",
      "value": 5
    },
    {
      "op": "gte",
      "value": 5
    }
  ]
}
```

#### 预期输出

- HTTP 400、code=4001；规则列表仍为空，revision 不变。

#### 实际结果

**通过**；阶段总耗时 1.063 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15afd962dcf769e33e9cb/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15afd962dcf769e33e9cb/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ae15afd962dcf769e33e9cb/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ae15afd962dcf769e33e9cf/questions` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 执行 | `PATCH /surveys/6ae15afd962dcf769e33e9cb/questions/6ae15afd962dcf769e33e9cd` | 400 | {"code": 4001, "msg": "只能跳转到后续题目或 end"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Questions.jump_rules | [] | [] | 符合 |
| Question_forms.revision | 3 | 3 | 符合 |

### JMP-011 禁止跨问卷目标

脚本节点：`tests/test_acceptance.py::test_acceptance[JMP-011]`

#### 步骤

1. 创建数字 q1、数字 q2、文本 q3，另建问卷中的一题用于跨问卷场景。
2. 自跳配置 q1→q1；逆向配置 q2→q1；跨卷/不存在使用对应 ID；重叠使用 lte 5 和 gte 5。
3. PATCH 保存规则并读取原题和 revision，确认失败未修改配置。

#### 输入

```json
{
  "method": "PATCH",
  "path": "/surveys/<form_id>/questions/<source_id>",
  "case": "foreign",
  "ordinary_condition": {
    "op": "eq",
    "value": 1
  },
  "overlap_conditions": [
    {
      "op": "lte",
      "value": 5
    },
    {
      "op": "gte",
      "value": 5
    }
  ]
}
```

#### 预期输出

- HTTP 400、code=4001；规则列表仍为空，revision 不变。

#### 实际结果

**通过**；阶段总耗时 1.050 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15afe962dcf769e33e9d6/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15afe962dcf769e33e9d6/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ae15afe962dcf769e33e9d6/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ae15afe962dcf769e33e9da/questions` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 执行 | `PATCH /surveys/6ae15afe962dcf769e33e9d6/questions/6ae15afe962dcf769e33e9d7` | 400 | {"code": 4001, "msg": "跳转目标不存在或不属于当前问卷"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Questions.jump_rules | [] | [] | 符合 |
| Question_forms.revision | 3 | 3 | 符合 |

### JMP-012 禁止不存在的目标

脚本节点：`tests/test_acceptance.py::test_acceptance[JMP-012]`

#### 步骤

1. 创建数字 q1、数字 q2、文本 q3，另建问卷中的一题用于跨问卷场景。
2. 自跳配置 q1→q1；逆向配置 q2→q1；跨卷/不存在使用对应 ID；重叠使用 lte 5 和 gte 5。
3. PATCH 保存规则并读取原题和 revision，确认失败未修改配置。

#### 输入

```json
{
  "method": "PATCH",
  "path": "/surveys/<form_id>/questions/<source_id>",
  "case": "missing",
  "ordinary_condition": {
    "op": "eq",
    "value": 1
  },
  "overlap_conditions": [
    {
      "op": "lte",
      "value": 5
    },
    {
      "op": "gte",
      "value": 5
    }
  ]
}
```

#### 预期输出

- HTTP 400、code=4001；规则列表仍为空，revision 不变。

#### 实际结果

**通过**；阶段总耗时 1.065 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15aff962dcf769e33e9e1/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15aff962dcf769e33e9e1/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ae15aff962dcf769e33e9e1/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ae15aff962dcf769e33e9e5/questions` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 执行 | `PATCH /surveys/6ae15aff962dcf769e33e9e1/questions/6ae15aff962dcf769e33e9e2` | 400 | {"code": 4001, "msg": "跳转目标不存在或不属于当前问卷"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Questions.jump_rules | [] | [] | 符合 |
| Question_forms.revision | 3 | 3 | 符合 |

### JMP-013 拒绝在边界 5 重叠的规则

脚本节点：`tests/test_acceptance.py::test_acceptance[JMP-013]`

#### 步骤

1. 创建数字 q1、数字 q2、文本 q3，另建问卷中的一题用于跨问卷场景。
2. 自跳配置 q1→q1；逆向配置 q2→q1；跨卷/不存在使用对应 ID；重叠使用 lte 5 和 gte 5。
3. PATCH 保存规则并读取原题和 revision，确认失败未修改配置。

#### 输入

```json
{
  "method": "PATCH",
  "path": "/surveys/<form_id>/questions/<source_id>",
  "case": "overlap",
  "ordinary_condition": {
    "op": "eq",
    "value": 1
  },
  "overlap_conditions": [
    {
      "op": "lte",
      "value": 5
    },
    {
      "op": "gte",
      "value": 5
    }
  ]
}
```

#### 预期输出

- HTTP 400、code=4001；规则列表仍为空，revision 不变。

#### 实际结果

**通过**；阶段总耗时 1.107 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b00962dcf769e33e9ec/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b00962dcf769e33e9ec/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ae15b00962dcf769e33e9ec/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ae15b00962dcf769e33e9f0/questions` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 执行 | `PATCH /surveys/6ae15b00962dcf769e33e9ec/questions/6ae15b00962dcf769e33e9ed` | 400 | {"code": 4001, "msg": "同一题的跳转规则必须互斥"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Questions.jump_rules | [] | [] | 符合 |
| Question_forms.revision | 3 | 3 | 符合 |

### JMP-014 跳过必答题不误报

脚本节点：`tests/test_acceptance.py::test_acceptance[JMP-014]`

#### 步骤

1. 建立必答单选 q1、必答文本 q2/q3，配置 q1 选 A 跳到 q3，再发布。
2. 修改场景先用 B、旧答案、末题答案调用 progress，确认经过三题。
3. 发送 q1=A、q2=旧答案、q3=末题答案，检查 progress 后提交并读取保存答案。

#### 输入

```json
{
  "initial": null,
  "updated": [
    "A",
    "旧答案",
    "末题答案"
  ],
  "paths": [
    "/surveys/access/<token>/progress",
    "/surveys/access/<token>/submit"
  ]
}
```

#### 预期输出

- 两接口均 code=0；discarded_question_ids 仅包含 q2。
- 保存答案只含 q1、q3，不要求被跳过的必答 q2，也不保存其旧值。

#### 实际结果

**通过**；阶段总耗时 1.362 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b02962dcf769e33e9f7/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b02962dcf769e33e9f7/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ae15b02962dcf769e33e9f7/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `PATCH /surveys/6ae15b02962dcf769e33e9f7/questions/6ae15b02962dcf769e33e9f8` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ae15b02962dcf769e33e9f7/publish` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 执行 | `POST /surveys/access/WiNjR-xWd4ScN7SD0Cqqm8YqBdWozjVjpyjF1VRaTrs/progress` | 200 | {"code": 0, "msg": "ok"} |
| 26 | 执行 | `POST /surveys/access/WiNjR-xWd4ScN7SD0Cqqm8YqBdWozjVjpyjF1VRaTrs/submit` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 清除跳过题目 | ["6ae15b02962dcf769e33e9fc"] | ["6ae15b02962dcf769e33e9fc"] | 符合 |
| 实际路径答案 | [{"question_id": "6ae15b02962dcf769e33e9f8", "value": "6ae15b02962dcf769e33e9f9"}, {"question_id": "6ae15b02962dcf769e33e9fd", "value": "末题答案"}] | [{"question_id": "6ae15b02962dcf769e33e9f8", "value": "6ae15b02962dcf769e33e9f9"}, {"question_id": "6ae15b02962dcf769e33e9fd", "value": "末题答案"}] | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |
| Responses.answers | [{"question_id": "6ae15b02962dcf769e33e9f8", "value": "6ae15b02962dcf769e33e9f9"}, {"question_id": "6ae15b02962dcf769e33e9fd", "value": "末题答案"}] | [{"question_id": "6ae15b02962dcf769e33e9f8", "value": "6ae15b02962dcf769e33e9f9"}, {"question_id": "6ae15b02962dcf769e33e9fd", "value": "末题答案"}] | 符合 |

### JMP-015 修改答案后清理旧路径

脚本节点：`tests/test_acceptance.py::test_acceptance[JMP-015]`

#### 步骤

1. 建立必答单选 q1、必答文本 q2/q3，配置 q1 选 A 跳到 q3，再发布。
2. 修改场景先用 B、旧答案、末题答案调用 progress，确认经过三题。
3. 发送 q1=A、q2=旧答案、q3=末题答案，检查 progress 后提交并读取保存答案。

#### 输入

```json
{
  "initial": [
    "B",
    "旧答案",
    "末题答案"
  ],
  "updated": [
    "A",
    "旧答案",
    "末题答案"
  ],
  "paths": [
    "/surveys/access/<token>/progress",
    "/surveys/access/<token>/submit"
  ]
}
```

#### 预期输出

- 两接口均 code=0；discarded_question_ids 仅包含 q2。
- 保存答案只含 q1、q3，不要求被跳过的必答 q2，也不保存其旧值。

#### 实际结果

**通过**；阶段总耗时 1.410 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b03962dcf769e33ea03/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b03962dcf769e33ea03/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ae15b03962dcf769e33ea03/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `PATCH /surveys/6ae15b03962dcf769e33ea03/questions/6ae15b03962dcf769e33ea04` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ae15b03962dcf769e33ea03/publish` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 执行 | `POST /surveys/access/SvvKjPI420ph37UKQrD2NL7TBzAtcNlWHpIkaBYL-q4/progress` | 200 | {"code": 0, "msg": "ok"} |
| 25 | 执行 | `POST /surveys/access/SvvKjPI420ph37UKQrD2NL7TBzAtcNlWHpIkaBYL-q4/progress` | 200 | {"code": 0, "msg": "ok"} |
| 30 | 执行 | `POST /surveys/access/SvvKjPI420ph37UKQrD2NL7TBzAtcNlWHpIkaBYL-q4/submit` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 修改前经过三题 | 3 | 3 | 符合 |
| 清除跳过题目 | ["6ae15b03962dcf769e33ea08"] | ["6ae15b03962dcf769e33ea08"] | 符合 |
| 实际路径答案 | [{"question_id": "6ae15b03962dcf769e33ea04", "value": "6ae15b03962dcf769e33ea05"}, {"question_id": "6ae15b03962dcf769e33ea09", "value": "末题答案"}] | [{"question_id": "6ae15b03962dcf769e33ea04", "value": "6ae15b03962dcf769e33ea05"}, {"question_id": "6ae15b03962dcf769e33ea09", "value": "末题答案"}] | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |
| Responses.answers | [{"question_id": "6ae15b03962dcf769e33ea04", "value": "6ae15b03962dcf769e33ea05"}, {"question_id": "6ae15b03962dcf769e33ea09", "value": "末题答案"}] | [{"question_id": "6ae15b03962dcf769e33ea04", "value": "6ae15b03962dcf769e33ea05"}, {"question_id": "6ae15b03962dcf769e33ea09", "value": "末题答案"}] | 符合 |


## 校验测试

### VAL-001 必答文本空字符串

脚本节点：`tests/test_acceptance.py::test_acceptance[VAL-001]`

#### 步骤

1. 创建指定类型、限制的单题问卷并发布。
2. 以 reader 调用 progress，再绕过客户端直接以相同答案调用 submit。
3. 检查两次响应、提示和 Responses 数量；合法留空不保存空答案项。

#### 输入

```json
{
  "question": {
    "title": "验收题目",
    "type": "text",
    "validation": {
      "required": true
    }
  },
  "value": "",
  "options": "选择题使用 A/B/C 三项，执行时替换为真实 ID",
  "progress": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": ""
      }
    ]
  },
  "submit": {
    "requestId": "<用例编号>",
    "answers": [
      {
        "question_id": "<q1>",
        "value": ""
      }
    ]
  }
}
```

#### 预期输出

- progress 和 submit 均 code=4001，HTTP 400。
- 提示包含“必答”。
- 本次测试 Responses 数量为 0。

#### 实际结果

**通过**；阶段总耗时 1.311 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b05962dcf769e33ea0f/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b05962dcf769e33ea0f/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/RJXg07-keZIb7tSNvS0f1jDIfSikNtrfLrKCbq7G5W8/progress` | 400 | {"code": 4001, "msg": "第 1 题：该题为必答题"} |
| 17 | 执行 | `POST /surveys/access/RJXg07-keZIb7tSNvS0f1jDIfSikNtrfLrKCbq7G5W8/submit` | 400 | {"code": 4001, "msg": "第 1 题：该题为必答题"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 0 | 0 | 符合 |

### VAL-002 必答文本 null

脚本节点：`tests/test_acceptance.py::test_acceptance[VAL-002]`

#### 步骤

1. 创建指定类型、限制的单题问卷并发布。
2. 以 reader 调用 progress，再绕过客户端直接以相同答案调用 submit。
3. 检查两次响应、提示和 Responses 数量；合法留空不保存空答案项。

#### 输入

```json
{
  "question": {
    "title": "验收题目",
    "type": "text",
    "validation": {
      "required": true
    }
  },
  "value": null,
  "options": "选择题使用 A/B/C 三项，执行时替换为真实 ID",
  "progress": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": null
      }
    ]
  },
  "submit": {
    "requestId": "<用例编号>",
    "answers": [
      {
        "question_id": "<q1>",
        "value": null
      }
    ]
  }
}
```

#### 预期输出

- progress 和 submit 均 code=4001，HTTP 400。
- 提示包含“必答”。
- 本次测试 Responses 数量为 0。

#### 实际结果

**通过**；阶段总耗时 1.247 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b06962dcf769e33ea15/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b06962dcf769e33ea15/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/rfcLVr1CjopnIEitteEiqBIBTEahyCvbwXFL_SfK26c/progress` | 400 | {"code": 4001, "msg": "第 1 题：该题为必答题"} |
| 17 | 执行 | `POST /surveys/access/rfcLVr1CjopnIEitteEiqBIBTEahyCvbwXFL_SfK26c/submit` | 400 | {"code": 4001, "msg": "第 1 题：该题为必答题"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 0 | 0 | 符合 |

### VAL-003 必答文本纯空白

脚本节点：`tests/test_acceptance.py::test_acceptance[VAL-003]`

#### 步骤

1. 创建指定类型、限制的单题问卷并发布。
2. 以 reader 调用 progress，再绕过客户端直接以相同答案调用 submit。
3. 检查两次响应、提示和 Responses 数量；合法留空不保存空答案项。

#### 输入

```json
{
  "question": {
    "title": "验收题目",
    "type": "text",
    "validation": {
      "required": true
    }
  },
  "value": " \t ",
  "options": "选择题使用 A/B/C 三项，执行时替换为真实 ID",
  "progress": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": " \t "
      }
    ]
  },
  "submit": {
    "requestId": "<用例编号>",
    "answers": [
      {
        "question_id": "<q1>",
        "value": " \t "
      }
    ]
  }
}
```

#### 预期输出

- progress 和 submit 均 code=4001，HTTP 400。
- 提示包含“必答”。
- 本次测试 Responses 数量为 0。

#### 实际结果

**通过**；阶段总耗时 1.295 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b07962dcf769e33ea1b/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b07962dcf769e33ea1b/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/MGFbjIUz_OfqHFhk8AMBKtaPgTgB28scbHa7ve58XHA/progress` | 400 | {"code": 4001, "msg": "第 1 题：该题为必答题"} |
| 17 | 执行 | `POST /surveys/access/MGFbjIUz_OfqHFhk8AMBKtaPgTgB28scbHa7ve58XHA/submit` | 400 | {"code": 4001, "msg": "第 1 题：该题为必答题"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 0 | 0 | 符合 |

### VAL-004 选答文本可留空

脚本节点：`tests/test_acceptance.py::test_acceptance[VAL-004]`

#### 步骤

1. 创建指定类型、限制的单题问卷并发布。
2. 以 reader 调用 progress，再绕过客户端直接以相同答案调用 submit。
3. 检查两次响应、提示和 Responses 数量；合法留空不保存空答案项。

#### 输入

```json
{
  "question": {
    "title": "验收题目",
    "type": "text",
    "validation": {}
  },
  "value": "",
  "options": "选择题使用 A/B/C 三项，执行时替换为真实 ID",
  "progress": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": ""
      }
    ]
  },
  "submit": {
    "requestId": "<用例编号>",
    "answers": [
      {
        "question_id": "<q1>",
        "value": ""
      }
    ]
  }
}
```

#### 预期输出

- progress 和 submit 均 code=0，HTTP 200。
- progress 标记完成，提交返回 ID 和时间。
- 本次测试 Responses 数量为 1。

#### 实际结果

**通过**；阶段总耗时 1.253 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b08962dcf769e33ea21/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b08962dcf769e33ea21/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/WYD5K4XuPD9lobK5WtIUq0aORknR-ilgbS_u2YougG8/progress` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/WYD5K4XuPD9lobK5WtIUq0aORknR-ilgbS_u2YougG8/submit` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |
| 完整路径已结束 | true | true | 符合 |
| 提交返回字段 | ["response_id", "submitted_at"] | ["response_id", "submitted_at"] | 符合 |
| 非空答案项数量 | 0 | 0 | 符合 |

### VAL-005 必答多选无最少数仍不能空

脚本节点：`tests/test_acceptance.py::test_acceptance[VAL-005]`

#### 步骤

1. 创建指定类型、限制的单题问卷并发布。
2. 以 reader 调用 progress，再绕过客户端直接以相同答案调用 submit。
3. 检查两次响应、提示和 Responses 数量；合法留空不保存空答案项。

#### 输入

```json
{
  "question": {
    "title": "验收题目",
    "type": "multiple",
    "validation": {
      "required": true
    }
  },
  "value": [],
  "options": "选择题使用 A/B/C 三项，执行时替换为真实 ID",
  "progress": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": []
      }
    ]
  },
  "submit": {
    "requestId": "<用例编号>",
    "answers": [
      {
        "question_id": "<q1>",
        "value": []
      }
    ]
  }
}
```

#### 预期输出

- progress 和 submit 均 code=4001，HTTP 400。
- 提示包含“必答”。
- 本次测试 Responses 数量为 0。

#### 实际结果

**通过**；阶段总耗时 1.284 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b0a962dcf769e33ea28/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b0a962dcf769e33ea28/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/NC-pTlk9NmBMuIjcLLCv1hVZTWAvRZ-jQiR0oR9Hxo0/progress` | 400 | {"code": 4001, "msg": "第 1 题：该题为必答题"} |
| 17 | 执行 | `POST /surveys/access/NC-pTlk9NmBMuIjcLLCv1hVZTWAvRZ-jQiR0oR9Hxo0/submit` | 400 | {"code": 4001, "msg": "第 1 题：该题为必答题"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 0 | 0 | 符合 |

### VAL-006 必答多选默认选一项有效

脚本节点：`tests/test_acceptance.py::test_acceptance[VAL-006]`

#### 步骤

1. 创建指定类型、限制的单题问卷并发布。
2. 以 reader 调用 progress，再绕过客户端直接以相同答案调用 submit。
3. 检查两次响应、提示和 Responses 数量；合法留空不保存空答案项。

#### 输入

```json
{
  "question": {
    "title": "验收题目",
    "type": "multiple",
    "validation": {
      "required": true
    }
  },
  "value": [
    "A"
  ],
  "options": "选择题使用 A/B/C 三项，执行时替换为真实 ID",
  "progress": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": [
          "A"
        ]
      }
    ]
  },
  "submit": {
    "requestId": "<用例编号>",
    "answers": [
      {
        "question_id": "<q1>",
        "value": [
          "A"
        ]
      }
    ]
  }
}
```

#### 预期输出

- progress 和 submit 均 code=0，HTTP 200。
- progress 标记完成，提交返回 ID 和时间。
- 本次测试 Responses 数量为 1。

#### 实际结果

**通过**；阶段总耗时 1.154 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b0b962dcf769e33ea31/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b0b962dcf769e33ea31/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/_ly5_ESMchIfNpyHLoM8J2usLlH-mXBWV0tacDaWgG0/progress` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/_ly5_ESMchIfNpyHLoM8J2usLlH-mXBWV0tacDaWgG0/submit` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |
| 完整路径已结束 | true | true | 符合 |
| 提交返回字段 | ["response_id", "submitted_at"] | ["response_id", "submitted_at"] | 符合 |
| 非空答案项数量 | 1 | 1 | 符合 |

### VAL-007 多选重复选项

脚本节点：`tests/test_acceptance.py::test_acceptance[VAL-007]`

#### 步骤

1. 创建指定类型、限制的单题问卷并发布。
2. 以 reader 调用 progress，再绕过客户端直接以相同答案调用 submit。
3. 检查两次响应、提示和 Responses 数量；合法留空不保存空答案项。

#### 输入

```json
{
  "question": {
    "title": "验收题目",
    "type": "multiple",
    "validation": {}
  },
  "value": [
    "A",
    "A"
  ],
  "options": "选择题使用 A/B/C 三项，执行时替换为真实 ID",
  "progress": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": [
          "A",
          "A"
        ]
      }
    ]
  },
  "submit": {
    "requestId": "<用例编号>",
    "answers": [
      {
        "question_id": "<q1>",
        "value": [
          "A",
          "A"
        ]
      }
    ]
  }
}
```

#### 预期输出

- progress 和 submit 均 code=4001，HTTP 400。
- 提示包含“重复”。
- 本次测试 Responses 数量为 0。

#### 实际结果

**通过**；阶段总耗时 1.020 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b0c962dcf769e33ea3b/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b0c962dcf769e33ea3b/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/u0-_EVvHuBH-XP1yNYUTd9wRTSsEZloSRop5X_pmpP8/progress` | 400 | {"code": 4001, "msg": "第 1 题：不能重复选择同一选项"} |
| 17 | 执行 | `POST /surveys/access/u0-_EVvHuBH-XP1yNYUTd9wRTSsEZloSRop5X_pmpP8/submit` | 400 | {"code": 4001, "msg": "第 1 题：不能重复选择同一选项"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 0 | 0 | 符合 |

### VAL-008 多选不存在选项

脚本节点：`tests/test_acceptance.py::test_acceptance[VAL-008]`

#### 步骤

1. 创建指定类型、限制的单题问卷并发布。
2. 以 reader 调用 progress，再绕过客户端直接以相同答案调用 submit。
3. 检查两次响应、提示和 Responses 数量；合法留空不保存空答案项。

#### 输入

```json
{
  "question": {
    "title": "验收题目",
    "type": "multiple",
    "validation": {}
  },
  "value": [
    "missing"
  ],
  "options": "选择题使用 A/B/C 三项，执行时替换为真实 ID",
  "progress": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": [
          "missing"
        ]
      }
    ]
  },
  "submit": {
    "requestId": "<用例编号>",
    "answers": [
      {
        "question_id": "<q1>",
        "value": [
          "missing"
        ]
      }
    ]
  }
}
```

#### 预期输出

- progress 和 submit 均 code=4001，HTTP 400。
- 提示包含“不存在”。
- 本次测试 Responses 数量为 0。

#### 实际结果

**通过**；阶段总耗时 1.098 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b0d962dcf769e33ea44/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b0d962dcf769e33ea44/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/yKvZlb-09SEWlFxSf68MH9Qts5xsIC8-OuGtE8-hnCg/progress` | 400 | {"code": 4001, "msg": "第 1 题：选项不存在"} |
| 17 | 执行 | `POST /surveys/access/yKvZlb-09SEWlFxSf68MH9Qts5xsIC8-OuGtE8-hnCg/submit` | 400 | {"code": 4001, "msg": "第 1 题：选项不存在"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 0 | 0 | 符合 |

### VAL-009 单选不存在选项

脚本节点：`tests/test_acceptance.py::test_acceptance[VAL-009]`

#### 步骤

1. 创建指定类型、限制的单题问卷并发布。
2. 以 reader 调用 progress，再绕过客户端直接以相同答案调用 submit。
3. 检查两次响应、提示和 Responses 数量；合法留空不保存空答案项。

#### 输入

```json
{
  "question": {
    "title": "验收题目",
    "type": "single",
    "validation": {}
  },
  "value": "missing",
  "options": "选择题使用 A/B/C 三项，执行时替换为真实 ID",
  "progress": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": "missing"
      }
    ]
  },
  "submit": {
    "requestId": "<用例编号>",
    "answers": [
      {
        "question_id": "<q1>",
        "value": "missing"
      }
    ]
  }
}
```

#### 预期输出

- progress 和 submit 均 code=4001，HTTP 400。
- 提示包含“不存在”。
- 本次测试 Responses 数量为 0。

#### 实际结果

**通过**；阶段总耗时 1.003 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b0e962dcf769e33ea4d/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b0e962dcf769e33ea4d/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/7BEBIWNh1LBEVWXS-01mEVHGYlniVBhf6sNmIIi_qRw/progress` | 400 | {"code": 4001, "msg": "第 1 题：选项不存在"} |
| 17 | 执行 | `POST /surveys/access/7BEBIWNh1LBEVWXS-01mEVHGYlniVBhf6sNmIIi_qRw/submit` | 400 | {"code": 4001, "msg": "第 1 题：选项不存在"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 0 | 0 | 符合 |

### VAL-010 文本不能提交数字

脚本节点：`tests/test_acceptance.py::test_acceptance[VAL-010]`

#### 步骤

1. 创建指定类型、限制的单题问卷并发布。
2. 以 reader 调用 progress，再绕过客户端直接以相同答案调用 submit。
3. 检查两次响应、提示和 Responses 数量；合法留空不保存空答案项。

#### 输入

```json
{
  "question": {
    "title": "验收题目",
    "type": "text",
    "validation": {}
  },
  "value": 123,
  "options": "选择题使用 A/B/C 三项，执行时替换为真实 ID",
  "progress": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": 123
      }
    ]
  },
  "submit": {
    "requestId": "<用例编号>",
    "answers": [
      {
        "question_id": "<q1>",
        "value": 123
      }
    ]
  }
}
```

#### 预期输出

- progress 和 submit 均 code=4001，HTTP 400。
- 提示包含“字符串”。
- 本次测试 Responses 数量为 0。

#### 实际结果

**通过**；阶段总耗时 1.014 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b0f962dcf769e33ea56/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b0f962dcf769e33ea56/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/2gGBqfADQDaW_3yifnSYnN_grlMvmDKQHEN0Mb7H6cY/progress` | 400 | {"code": 4001, "msg": "第 1 题：文本答案必须为字符串"} |
| 17 | 执行 | `POST /surveys/access/2gGBqfADQDaW_3yifnSYnN_grlMvmDKQHEN0Mb7H6cY/submit` | 400 | {"code": 4001, "msg": "第 1 题：文本答案必须为字符串"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 0 | 0 | 符合 |

### VAL-011 恰好选 2 项：实际 1 项

脚本节点：`tests/test_acceptance.py::test_acceptance[VAL-011]`

#### 步骤

1. 创建指定类型、限制的单题问卷并发布。
2. 以 reader 调用 progress，再绕过客户端直接以相同答案调用 submit。
3. 检查两次响应、提示和 Responses 数量；合法留空不保存空答案项。

#### 输入

```json
{
  "question": {
    "title": "验收题目",
    "type": "multiple",
    "validation": {
      "min_selected": 2,
      "max_selected": 2
    }
  },
  "value": [
    "A"
  ],
  "options": "选择题使用 A/B/C 三项，执行时替换为真实 ID",
  "progress": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": [
          "A"
        ]
      }
    ]
  },
  "submit": {
    "requestId": "<用例编号>",
    "answers": [
      {
        "question_id": "<q1>",
        "value": [
          "A"
        ]
      }
    ]
  }
}
```

#### 预期输出

- progress 和 submit 均 code=4001，HTTP 400。
- 提示包含“至少”。
- 本次测试 Responses 数量为 0。

#### 实际结果

**通过**；阶段总耗时 1.027 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b10962dcf769e33ea5c/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b10962dcf769e33ea5c/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/qclMUZqneW6NOLV1-FXTyGdSavomG5khs2NjYf3JEkM/progress` | 400 | {"code": 4001, "msg": "第 1 题：至少选择 2 项"} |
| 17 | 执行 | `POST /surveys/access/qclMUZqneW6NOLV1-FXTyGdSavomG5khs2NjYf3JEkM/submit` | 400 | {"code": 4001, "msg": "第 1 题：至少选择 2 项"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 0 | 0 | 符合 |

### VAL-012 恰好选 2 项：实际 2 项

脚本节点：`tests/test_acceptance.py::test_acceptance[VAL-012]`

#### 步骤

1. 创建指定类型、限制的单题问卷并发布。
2. 以 reader 调用 progress，再绕过客户端直接以相同答案调用 submit。
3. 检查两次响应、提示和 Responses 数量；合法留空不保存空答案项。

#### 输入

```json
{
  "question": {
    "title": "验收题目",
    "type": "multiple",
    "validation": {
      "min_selected": 2,
      "max_selected": 2
    }
  },
  "value": [
    "A",
    "B"
  ],
  "options": "选择题使用 A/B/C 三项，执行时替换为真实 ID",
  "progress": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": [
          "A",
          "B"
        ]
      }
    ]
  },
  "submit": {
    "requestId": "<用例编号>",
    "answers": [
      {
        "question_id": "<q1>",
        "value": [
          "A",
          "B"
        ]
      }
    ]
  }
}
```

#### 预期输出

- progress 和 submit 均 code=0，HTTP 200。
- progress 标记完成，提交返回 ID 和时间。
- 本次测试 Responses 数量为 1。

#### 实际结果

**通过**；阶段总耗时 1.001 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b11962dcf769e33ea65/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b11962dcf769e33ea65/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/o7jWgP8XNquVmD2wVrzxXxjPWMybi8-PmOydsQgf6L4/progress` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/o7jWgP8XNquVmD2wVrzxXxjPWMybi8-PmOydsQgf6L4/submit` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |
| 完整路径已结束 | true | true | 符合 |
| 提交返回字段 | ["response_id", "submitted_at"] | ["response_id", "submitted_at"] | 符合 |
| 非空答案项数量 | 1 | 1 | 符合 |

### VAL-013 恰好选 2 项：实际 3 项

脚本节点：`tests/test_acceptance.py::test_acceptance[VAL-013]`

#### 步骤

1. 创建指定类型、限制的单题问卷并发布。
2. 以 reader 调用 progress，再绕过客户端直接以相同答案调用 submit。
3. 检查两次响应、提示和 Responses 数量；合法留空不保存空答案项。

#### 输入

```json
{
  "question": {
    "title": "验收题目",
    "type": "multiple",
    "validation": {
      "min_selected": 2,
      "max_selected": 2
    }
  },
  "value": [
    "A",
    "B",
    "C"
  ],
  "options": "选择题使用 A/B/C 三项，执行时替换为真实 ID",
  "progress": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": [
          "A",
          "B",
          "C"
        ]
      }
    ]
  },
  "submit": {
    "requestId": "<用例编号>",
    "answers": [
      {
        "question_id": "<q1>",
        "value": [
          "A",
          "B",
          "C"
        ]
      }
    ]
  }
}
```

#### 预期输出

- progress 和 submit 均 code=4001，HTTP 400。
- 提示包含“最多”。
- 本次测试 Responses 数量为 0。

#### 实际结果

**通过**；阶段总耗时 1.039 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b12962dcf769e33ea6f/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b12962dcf769e33ea6f/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/fUhDyQt5m96cbHBci44cINjZbk5AoDU7xiUha9xRVWE/progress` | 400 | {"code": 4001, "msg": "第 1 题：最多选择 2 项"} |
| 17 | 执行 | `POST /surveys/access/fUhDyQt5m96cbHBci44cINjZbk5AoDU7xiUha9xRVWE/submit` | 400 | {"code": 4001, "msg": "第 1 题：最多选择 2 项"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 0 | 0 | 符合 |

### VAL-014 文本范围 2-10 字：实际 1 字

脚本节点：`tests/test_acceptance.py::test_acceptance[VAL-014]`

#### 步骤

1. 创建指定类型、限制的单题问卷并发布。
2. 以 reader 调用 progress，再绕过客户端直接以相同答案调用 submit。
3. 检查两次响应、提示和 Responses 数量；合法留空不保存空答案项。

#### 输入

```json
{
  "question": {
    "title": "验收题目",
    "type": "text",
    "validation": {
      "min_length": 2,
      "max_length": 10
    }
  },
  "value": "文",
  "options": "选择题使用 A/B/C 三项，执行时替换为真实 ID",
  "progress": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": "文"
      }
    ]
  },
  "submit": {
    "requestId": "<用例编号>",
    "answers": [
      {
        "question_id": "<q1>",
        "value": "文"
      }
    ]
  }
}
```

#### 预期输出

- progress 和 submit 均 code=4001，HTTP 400。
- 提示包含“至少”。
- 本次测试 Responses 数量为 0。

#### 实际结果

**通过**；阶段总耗时 1.000 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b13962dcf769e33ea78/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b13962dcf769e33ea78/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/NQiPrFUBJzcs5Lw7ygyjOhq_hgkHvyhGvzvvO8wlA3k/progress` | 400 | {"code": 4001, "msg": "第 1 题：至少填写 2 个字符"} |
| 17 | 执行 | `POST /surveys/access/NQiPrFUBJzcs5Lw7ygyjOhq_hgkHvyhGvzvvO8wlA3k/submit` | 400 | {"code": 4001, "msg": "第 1 题：至少填写 2 个字符"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 0 | 0 | 符合 |

### VAL-015 文本范围 2-10 字：实际 2 字

脚本节点：`tests/test_acceptance.py::test_acceptance[VAL-015]`

#### 步骤

1. 创建指定类型、限制的单题问卷并发布。
2. 以 reader 调用 progress，再绕过客户端直接以相同答案调用 submit。
3. 检查两次响应、提示和 Responses 数量；合法留空不保存空答案项。

#### 输入

```json
{
  "question": {
    "title": "验收题目",
    "type": "text",
    "validation": {
      "min_length": 2,
      "max_length": 10
    }
  },
  "value": "文文",
  "options": "选择题使用 A/B/C 三项，执行时替换为真实 ID",
  "progress": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": "文文"
      }
    ]
  },
  "submit": {
    "requestId": "<用例编号>",
    "answers": [
      {
        "question_id": "<q1>",
        "value": "文文"
      }
    ]
  }
}
```

#### 预期输出

- progress 和 submit 均 code=0，HTTP 200。
- progress 标记完成，提交返回 ID 和时间。
- 本次测试 Responses 数量为 1。

#### 实际结果

**通过**；阶段总耗时 1.043 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b14962dcf769e33ea7e/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b14962dcf769e33ea7e/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/SefNyeEBFJP0eTiWK-Tptg4k1illmrjal6jWsByzLXg/progress` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/SefNyeEBFJP0eTiWK-Tptg4k1illmrjal6jWsByzLXg/submit` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |
| 完整路径已结束 | true | true | 符合 |
| 提交返回字段 | ["response_id", "submitted_at"] | ["response_id", "submitted_at"] | 符合 |
| 非空答案项数量 | 1 | 1 | 符合 |

### VAL-016 文本范围 2-10 字：实际 9 字

脚本节点：`tests/test_acceptance.py::test_acceptance[VAL-016]`

#### 步骤

1. 创建指定类型、限制的单题问卷并发布。
2. 以 reader 调用 progress，再绕过客户端直接以相同答案调用 submit。
3. 检查两次响应、提示和 Responses 数量；合法留空不保存空答案项。

#### 输入

```json
{
  "question": {
    "title": "验收题目",
    "type": "text",
    "validation": {
      "min_length": 2,
      "max_length": 10
    }
  },
  "value": "文文文文文文文文文",
  "options": "选择题使用 A/B/C 三项，执行时替换为真实 ID",
  "progress": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": "文文文文文文文文文"
      }
    ]
  },
  "submit": {
    "requestId": "<用例编号>",
    "answers": [
      {
        "question_id": "<q1>",
        "value": "文文文文文文文文文"
      }
    ]
  }
}
```

#### 预期输出

- progress 和 submit 均 code=0，HTTP 200。
- progress 标记完成，提交返回 ID 和时间。
- 本次测试 Responses 数量为 1。

#### 实际结果

**通过**；阶段总耗时 0.985 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b15962dcf769e33ea85/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b15962dcf769e33ea85/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/9ExiLtWoHYPSB65raO_U222YW9hIvw2PvP2jyDrtScw/progress` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/9ExiLtWoHYPSB65raO_U222YW9hIvw2PvP2jyDrtScw/submit` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |
| 完整路径已结束 | true | true | 符合 |
| 提交返回字段 | ["response_id", "submitted_at"] | ["response_id", "submitted_at"] | 符合 |
| 非空答案项数量 | 1 | 1 | 符合 |

### VAL-017 文本范围 2-10 字：实际 10 字

脚本节点：`tests/test_acceptance.py::test_acceptance[VAL-017]`

#### 步骤

1. 创建指定类型、限制的单题问卷并发布。
2. 以 reader 调用 progress，再绕过客户端直接以相同答案调用 submit。
3. 检查两次响应、提示和 Responses 数量；合法留空不保存空答案项。

#### 输入

```json
{
  "question": {
    "title": "验收题目",
    "type": "text",
    "validation": {
      "min_length": 2,
      "max_length": 10
    }
  },
  "value": "文文文文文文文文文文",
  "options": "选择题使用 A/B/C 三项，执行时替换为真实 ID",
  "progress": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": "文文文文文文文文文文"
      }
    ]
  },
  "submit": {
    "requestId": "<用例编号>",
    "answers": [
      {
        "question_id": "<q1>",
        "value": "文文文文文文文文文文"
      }
    ]
  }
}
```

#### 预期输出

- progress 和 submit 均 code=0，HTTP 200。
- progress 标记完成，提交返回 ID 和时间。
- 本次测试 Responses 数量为 1。

#### 实际结果

**通过**；阶段总耗时 1.051 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b16962dcf769e33ea8c/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b16962dcf769e33ea8c/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/_IAw9Y86z02jqP3RXrJjaiUNhcCNj5k79DYXvdx94NI/progress` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/_IAw9Y86z02jqP3RXrJjaiUNhcCNj5k79DYXvdx94NI/submit` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |
| 完整路径已结束 | true | true | 符合 |
| 提交返回字段 | ["response_id", "submitted_at"] | ["response_id", "submitted_at"] | 符合 |
| 非空答案项数量 | 1 | 1 | 符合 |

### VAL-018 文本范围 2-10 字：实际 11 字

脚本节点：`tests/test_acceptance.py::test_acceptance[VAL-018]`

#### 步骤

1. 创建指定类型、限制的单题问卷并发布。
2. 以 reader 调用 progress，再绕过客户端直接以相同答案调用 submit。
3. 检查两次响应、提示和 Responses 数量；合法留空不保存空答案项。

#### 输入

```json
{
  "question": {
    "title": "验收题目",
    "type": "text",
    "validation": {
      "min_length": 2,
      "max_length": 10
    }
  },
  "value": "文文文文文文文文文文文",
  "options": "选择题使用 A/B/C 三项，执行时替换为真实 ID",
  "progress": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": "文文文文文文文文文文文"
      }
    ]
  },
  "submit": {
    "requestId": "<用例编号>",
    "answers": [
      {
        "question_id": "<q1>",
        "value": "文文文文文文文文文文文"
      }
    ]
  }
}
```

#### 预期输出

- progress 和 submit 均 code=4001，HTTP 400。
- 提示包含“最多”。
- 本次测试 Responses 数量为 0。

#### 实际结果

**通过**；阶段总耗时 1.005 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b17962dcf769e33ea93/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b17962dcf769e33ea93/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/Mg8w6UN_ggMU6-kLVVlROyiG99yMJqKwyNPwhkOWkfU/progress` | 400 | {"code": 4001, "msg": "第 1 题：最多填写 10 个字符"} |
| 17 | 执行 | `POST /surveys/access/Mg8w6UN_ggMU6-kLVVlROyiG99yMJqKwyNPwhkOWkfU/submit` | 400 | {"code": 4001, "msg": "第 1 题：最多填写 10 个字符"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 0 | 0 | 符合 |

### VAL-019 数字范围 [0,10]：实际 -1

脚本节点：`tests/test_acceptance.py::test_acceptance[VAL-019]`

#### 步骤

1. 创建指定类型、限制的单题问卷并发布。
2. 以 reader 调用 progress，再绕过客户端直接以相同答案调用 submit。
3. 检查两次响应、提示和 Responses 数量；合法留空不保存空答案项。

#### 输入

```json
{
  "question": {
    "title": "验收题目",
    "type": "number",
    "validation": {
      "min_value": 0,
      "max_value": 10
    }
  },
  "value": -1,
  "options": "选择题使用 A/B/C 三项，执行时替换为真实 ID",
  "progress": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": -1
      }
    ]
  },
  "submit": {
    "requestId": "<用例编号>",
    "answers": [
      {
        "question_id": "<q1>",
        "value": -1
      }
    ]
  }
}
```

#### 预期输出

- progress 和 submit 均 code=4001，HTTP 400。
- 提示包含“小于”。
- 本次测试 Responses 数量为 0。

#### 实际结果

**通过**；阶段总耗时 1.002 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b18962dcf769e33ea99/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b18962dcf769e33ea99/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/D5_ieJVZM1bBeG5entT_F8OpfoI4KKIz1LLkVPWSHnw/progress` | 400 | {"code": 4001, "msg": "第 1 题：数值不能小于 0"} |
| 17 | 执行 | `POST /surveys/access/D5_ieJVZM1bBeG5entT_F8OpfoI4KKIz1LLkVPWSHnw/submit` | 400 | {"code": 4001, "msg": "第 1 题：数值不能小于 0"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 0 | 0 | 符合 |

### VAL-020 数字范围 [0,10]：实际 0

脚本节点：`tests/test_acceptance.py::test_acceptance[VAL-020]`

#### 步骤

1. 创建指定类型、限制的单题问卷并发布。
2. 以 reader 调用 progress，再绕过客户端直接以相同答案调用 submit。
3. 检查两次响应、提示和 Responses 数量；合法留空不保存空答案项。

#### 输入

```json
{
  "question": {
    "title": "验收题目",
    "type": "number",
    "validation": {
      "min_value": 0,
      "max_value": 10
    }
  },
  "value": 0,
  "options": "选择题使用 A/B/C 三项，执行时替换为真实 ID",
  "progress": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": 0
      }
    ]
  },
  "submit": {
    "requestId": "<用例编号>",
    "answers": [
      {
        "question_id": "<q1>",
        "value": 0
      }
    ]
  }
}
```

#### 预期输出

- progress 和 submit 均 code=0，HTTP 200。
- progress 标记完成，提交返回 ID 和时间。
- 本次测试 Responses 数量为 1。

#### 实际结果

**通过**；阶段总耗时 1.045 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b19962dcf769e33ea9f/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b19962dcf769e33ea9f/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/nrcrEV-kYYArgwQYh1sc0XGM8MyPSt2_ovWasByzFkg/progress` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/nrcrEV-kYYArgwQYh1sc0XGM8MyPSt2_ovWasByzFkg/submit` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |
| 完整路径已结束 | true | true | 符合 |
| 提交返回字段 | ["response_id", "submitted_at"] | ["response_id", "submitted_at"] | 符合 |
| 非空答案项数量 | 1 | 1 | 符合 |

### VAL-021 数字范围 [0,10]：实际 10

脚本节点：`tests/test_acceptance.py::test_acceptance[VAL-021]`

#### 步骤

1. 创建指定类型、限制的单题问卷并发布。
2. 以 reader 调用 progress，再绕过客户端直接以相同答案调用 submit。
3. 检查两次响应、提示和 Responses 数量；合法留空不保存空答案项。

#### 输入

```json
{
  "question": {
    "title": "验收题目",
    "type": "number",
    "validation": {
      "min_value": 0,
      "max_value": 10
    }
  },
  "value": 10,
  "options": "选择题使用 A/B/C 三项，执行时替换为真实 ID",
  "progress": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": 10
      }
    ]
  },
  "submit": {
    "requestId": "<用例编号>",
    "answers": [
      {
        "question_id": "<q1>",
        "value": 10
      }
    ]
  }
}
```

#### 预期输出

- progress 和 submit 均 code=0，HTTP 200。
- progress 标记完成，提交返回 ID 和时间。
- 本次测试 Responses 数量为 1。

#### 实际结果

**通过**；阶段总耗时 1.026 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b1a962dcf769e33eaa6/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b1a962dcf769e33eaa6/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/Oc3as2CyJnLfr9r6dsn-5PnmlOJzYJw8LQflYIDTQCY/progress` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/Oc3as2CyJnLfr9r6dsn-5PnmlOJzYJw8LQflYIDTQCY/submit` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |
| 完整路径已结束 | true | true | 符合 |
| 提交返回字段 | ["response_id", "submitted_at"] | ["response_id", "submitted_at"] | 符合 |
| 非空答案项数量 | 1 | 1 | 符合 |

### VAL-022 数字范围 [0,10]：实际 11

脚本节点：`tests/test_acceptance.py::test_acceptance[VAL-022]`

#### 步骤

1. 创建指定类型、限制的单题问卷并发布。
2. 以 reader 调用 progress，再绕过客户端直接以相同答案调用 submit。
3. 检查两次响应、提示和 Responses 数量；合法留空不保存空答案项。

#### 输入

```json
{
  "question": {
    "title": "验收题目",
    "type": "number",
    "validation": {
      "min_value": 0,
      "max_value": 10
    }
  },
  "value": 11,
  "options": "选择题使用 A/B/C 三项，执行时替换为真实 ID",
  "progress": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": 11
      }
    ]
  },
  "submit": {
    "requestId": "<用例编号>",
    "answers": [
      {
        "question_id": "<q1>",
        "value": 11
      }
    ]
  }
}
```

#### 预期输出

- progress 和 submit 均 code=4001，HTTP 400。
- 提示包含“大于”。
- 本次测试 Responses 数量为 0。

#### 实际结果

**通过**；阶段总耗时 1.019 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b1b962dcf769e33eaad/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b1b962dcf769e33eaad/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/y7WDGB3jC-BQ5gbI6gcstcjsjUJ2TJhBRE-LeTtJRVc/progress` | 400 | {"code": 4001, "msg": "第 1 题：数值不能大于 10"} |
| 17 | 执行 | `POST /surveys/access/y7WDGB3jC-BQ5gbI6gcstcjsjUJ2TJhBRE-LeTtJRVc/submit` | 400 | {"code": 4001, "msg": "第 1 题：数值不能大于 10"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 0 | 0 | 符合 |

### VAL-023 整数数字题输入 1.0 (float)

脚本节点：`tests/test_acceptance.py::test_acceptance[VAL-023]`

#### 步骤

1. 创建指定类型、限制的单题问卷并发布。
2. 以 reader 调用 progress，再绕过客户端直接以相同答案调用 submit。
3. 检查两次响应、提示和 Responses 数量；合法留空不保存空答案项。

#### 输入

```json
{
  "question": {
    "title": "验收题目",
    "type": "number",
    "validation": {
      "integer_only": true
    }
  },
  "value": 1.0,
  "options": "选择题使用 A/B/C 三项，执行时替换为真实 ID",
  "progress": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": 1.0
      }
    ]
  },
  "submit": {
    "requestId": "<用例编号>",
    "answers": [
      {
        "question_id": "<q1>",
        "value": 1.0
      }
    ]
  }
}
```

#### 预期输出

- progress 和 submit 均 code=0，HTTP 200。
- progress 标记完成，提交返回 ID 和时间。
- 本次测试 Responses 数量为 1。

#### 实际结果

**通过**；阶段总耗时 1.158 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b1c962dcf769e33eab3/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b1c962dcf769e33eab3/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/OlB-6b9JLMOJXRtIFEw_xAdWPDf2oQBRJgRkvBrms28/progress` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/OlB-6b9JLMOJXRtIFEw_xAdWPDf2oQBRJgRkvBrms28/submit` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |
| 完整路径已结束 | true | true | 符合 |
| 提交返回字段 | ["response_id", "submitted_at"] | ["response_id", "submitted_at"] | 符合 |
| 非空答案项数量 | 1 | 1 | 符合 |

### VAL-024 整数数字题输入 1.5 (float)

脚本节点：`tests/test_acceptance.py::test_acceptance[VAL-024]`

#### 步骤

1. 创建指定类型、限制的单题问卷并发布。
2. 以 reader 调用 progress，再绕过客户端直接以相同答案调用 submit。
3. 检查两次响应、提示和 Responses 数量；合法留空不保存空答案项。

#### 输入

```json
{
  "question": {
    "title": "验收题目",
    "type": "number",
    "validation": {
      "integer_only": true
    }
  },
  "value": 1.5,
  "options": "选择题使用 A/B/C 三项，执行时替换为真实 ID",
  "progress": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": 1.5
      }
    ]
  },
  "submit": {
    "requestId": "<用例编号>",
    "answers": [
      {
        "question_id": "<q1>",
        "value": 1.5
      }
    ]
  }
}
```

#### 预期输出

- progress 和 submit 均 code=4001，HTTP 400。
- 提示包含“整数”。
- 本次测试 Responses 数量为 0。

#### 实际结果

**通过**；阶段总耗时 1.098 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b1d962dcf769e33eaba/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b1d962dcf769e33eaba/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/gohQjwoFgoeCOln0qUHTEjI6WQptcRRVl51U3X9uJow/progress` | 400 | {"code": 4001, "msg": "第 1 题：必须填写整数"} |
| 17 | 执行 | `POST /surveys/access/gohQjwoFgoeCOln0qUHTEjI6WQptcRRVl51U3X9uJow/submit` | 400 | {"code": 4001, "msg": "第 1 题：必须填写整数"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 0 | 0 | 符合 |

### VAL-025 整数数字题输入 True (bool)

脚本节点：`tests/test_acceptance.py::test_acceptance[VAL-025]`

#### 步骤

1. 创建指定类型、限制的单题问卷并发布。
2. 以 reader 调用 progress，再绕过客户端直接以相同答案调用 submit。
3. 检查两次响应、提示和 Responses 数量；合法留空不保存空答案项。

#### 输入

```json
{
  "question": {
    "title": "验收题目",
    "type": "number",
    "validation": {
      "integer_only": true
    }
  },
  "value": true,
  "options": "选择题使用 A/B/C 三项，执行时替换为真实 ID",
  "progress": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": true
      }
    ]
  },
  "submit": {
    "requestId": "<用例编号>",
    "answers": [
      {
        "question_id": "<q1>",
        "value": true
      }
    ]
  }
}
```

#### 预期输出

- progress 和 submit 均 code=4001，HTTP 400。
- 提示包含“有限数字”。
- 本次测试 Responses 数量为 0。

#### 实际结果

**通过**；阶段总耗时 1.074 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b1f962dcf769e33eac0/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b1f962dcf769e33eac0/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/Zc2iGAKgSHpqO_yS5OEOL-XD2LoRvht-S6uz20EaOoA/progress` | 400 | {"code": 4001, "msg": "第 1 题：数字限制和跳转阈值必须是有限数字"} |
| 17 | 执行 | `POST /surveys/access/Zc2iGAKgSHpqO_yS5OEOL-XD2LoRvht-S6uz20EaOoA/submit` | 400 | {"code": 4001, "msg": "第 1 题：数字限制和跳转阈值必须是有限数字"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 0 | 0 | 符合 |

### VAL-026 整数数字题输入 '1' (str)

脚本节点：`tests/test_acceptance.py::test_acceptance[VAL-026]`

#### 步骤

1. 创建指定类型、限制的单题问卷并发布。
2. 以 reader 调用 progress，再绕过客户端直接以相同答案调用 submit。
3. 检查两次响应、提示和 Responses 数量；合法留空不保存空答案项。

#### 输入

```json
{
  "question": {
    "title": "验收题目",
    "type": "number",
    "validation": {
      "integer_only": true
    }
  },
  "value": "1",
  "options": "选择题使用 A/B/C 三项，执行时替换为真实 ID",
  "progress": {
    "answers": [
      {
        "question_id": "<q1>",
        "value": "1"
      }
    ]
  },
  "submit": {
    "requestId": "<用例编号>",
    "answers": [
      {
        "question_id": "<q1>",
        "value": "1"
      }
    ]
  }
}
```

#### 预期输出

- progress 和 submit 均 code=4001，HTTP 400。
- 提示包含“有限数字”。
- 本次测试 Responses 数量为 0。

#### 实际结果

**通过**；阶段总耗时 1.090 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b20962dcf769e33eac6/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b20962dcf769e33eac6/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/JzOmFyMztdJ9QYjYN6TO1CD-vvIOrhMS7-cbI6F-DrY/progress` | 400 | {"code": 4001, "msg": "第 1 题：数字限制和跳转阈值必须是有限数字"} |
| 17 | 执行 | `POST /surveys/access/JzOmFyMztdJ9QYjYN6TO1CD-vvIOrhMS7-cbI6F-DrY/submit` | 400 | {"code": 4001, "msg": "第 1 题：数字限制和跳转阈值必须是有限数字"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 0 | 0 | 符合 |


## 提交问卷测试

### SUB-001 完整提交保存，匿名=False

脚本节点：`tests/test_acceptance.py::test_acceptance[SUB-001]`

#### 步骤

1. 创建必答文本题并发布，按场景设置匿名或重复填写开关。
2. reader 提交“第一份”；normal 到此结束；repeat 换标识，idempotent 原样重试，changed 保持标识但改为“第二份”。
3. 核对 HTTP 响应和数据库记录；幂等重试还检查提交 ID、时间完全相同。

#### 输入

```json
{
  "method": "POST",
  "path": "/surveys/access/<token>/submit",
  "mode": "normal",
  "setting": false,
  "first": {
    "requestId": "submit-1",
    "answers": [
      {
        "question_id": "<q1>",
        "value": "第一份"
      }
    ]
  },
  "second": null
}
```

#### 预期输出

- 依次得到业务码 [0]；数据库总记录数为 1。
- 保存匿名标记来自问卷，内部身份绑定 reader；提交响应仅含 response_id、submitted_at。

#### 实际结果

**通过**；阶段总耗时 1.058 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b21962dcf769e33eacc/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b21962dcf769e33eacc/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/7APDazKuGCPlbxpkgQQzzoe0Tr4lMXEnIB3Y5qnCo_U/submit` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |
| 提交输出字段 | ["response_id", "submitted_at"] | ["response_id", "submitted_at"] | 符合 |
| Responses.answers | [{"question_id": "6ae15b21962dcf769e33eacd", "value": "第一份"}] | [{"question_id": "6ae15b21962dcf769e33eacd", "value": "第一份"}] | 符合 |
| Responses.is_anonymous | false | false | 符合 |
| Responses.respondent_id | "6ae15b21962dcf769e33eacb" | "6ae15b21962dcf769e33eacb" | 符合 |

### SUB-002 完整提交保存，匿名=True

脚本节点：`tests/test_acceptance.py::test_acceptance[SUB-002]`

#### 步骤

1. 创建必答文本题并发布，按场景设置匿名或重复填写开关。
2. reader 提交“第一份”；normal 到此结束；repeat 换标识，idempotent 原样重试，changed 保持标识但改为“第二份”。
3. 核对 HTTP 响应和数据库记录；幂等重试还检查提交 ID、时间完全相同。

#### 输入

```json
{
  "method": "POST",
  "path": "/surveys/access/<token>/submit",
  "mode": "normal",
  "setting": true,
  "first": {
    "requestId": "submit-1",
    "answers": [
      {
        "question_id": "<q1>",
        "value": "第一份"
      }
    ]
  },
  "second": null
}
```

#### 预期输出

- 依次得到业务码 [0]；数据库总记录数为 1。
- 保存匿名标记来自问卷，内部身份绑定 reader；提交响应仅含 response_id、submitted_at。

#### 实际结果

**通过**；阶段总耗时 1.378 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b22962dcf769e33ead3/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b22962dcf769e33ead3/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/N6808FUnInWr8hEiFm9k6sjcLGMl9mljG4x7fb2pve4/submit` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |
| 提交输出字段 | ["response_id", "submitted_at"] | ["response_id", "submitted_at"] | 符合 |
| Responses.answers | [{"question_id": "6ae15b22962dcf769e33ead4", "value": "第一份"}] | [{"question_id": "6ae15b22962dcf769e33ead4", "value": "第一份"}] | 符合 |
| Responses.is_anonymous | true | true | 符合 |
| Responses.respondent_id | "6ae15b22962dcf769e33ead2" | "6ae15b22962dcf769e33ead2" | 符合 |

### SUB-003 不同 requestId 再次填写，允许多次=False

脚本节点：`tests/test_acceptance.py::test_acceptance[SUB-003]`

#### 步骤

1. 创建必答文本题并发布，按场景设置匿名或重复填写开关。
2. reader 提交“第一份”；normal 到此结束；repeat 换标识，idempotent 原样重试，changed 保持标识但改为“第二份”。
3. 核对 HTTP 响应和数据库记录；幂等重试还检查提交 ID、时间完全相同。

#### 输入

```json
{
  "method": "POST",
  "path": "/surveys/access/<token>/submit",
  "mode": "repeat",
  "setting": false,
  "first": {
    "requestId": "submit-1",
    "answers": [
      {
        "question_id": "<q1>",
        "value": "第一份"
      }
    ]
  },
  "second": {
    "requestId": "submit-2",
    "answers": [
      {
        "question_id": "<q1>",
        "value": "第一份"
      }
    ]
  }
}
```

#### 预期输出

- 依次得到业务码 [0, 4090]；数据库总记录数为 1。
- 保存匿名标记来自问卷，内部身份绑定 reader；提交响应仅含 response_id、submitted_at。

#### 实际结果

**通过**；阶段总耗时 1.577 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b24962dcf769e33eada/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b24962dcf769e33eada/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/Q9pF0lRcWqleV1hPAytdD6T0cNJ-8XX8CJKqnL-hAio/submit` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/Q9pF0lRcWqleV1hPAytdD6T0cNJ-8XX8CJKqnL-hAio/submit` | 409 | {"code": 4090, "msg": "该问卷不允许重复提交"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |
| 提交输出字段 | ["response_id", "submitted_at"] | ["response_id", "submitted_at"] | 符合 |
| Responses.answers | [{"question_id": "6ae15b24962dcf769e33eadb", "value": "第一份"}] | [{"question_id": "6ae15b24962dcf769e33eadb", "value": "第一份"}] | 符合 |
| Responses.is_anonymous | false | false | 符合 |
| Responses.respondent_id | "6ae15b23962dcf769e33ead9" | "6ae15b23962dcf769e33ead9" | 符合 |

### SUB-004 不同 requestId 再次填写，允许多次=True

脚本节点：`tests/test_acceptance.py::test_acceptance[SUB-004]`

#### 步骤

1. 创建必答文本题并发布，按场景设置匿名或重复填写开关。
2. reader 提交“第一份”；normal 到此结束；repeat 换标识，idempotent 原样重试，changed 保持标识但改为“第二份”。
3. 核对 HTTP 响应和数据库记录；幂等重试还检查提交 ID、时间完全相同。

#### 输入

```json
{
  "method": "POST",
  "path": "/surveys/access/<token>/submit",
  "mode": "repeat",
  "setting": true,
  "first": {
    "requestId": "submit-1",
    "answers": [
      {
        "question_id": "<q1>",
        "value": "第一份"
      }
    ]
  },
  "second": {
    "requestId": "submit-2",
    "answers": [
      {
        "question_id": "<q1>",
        "value": "第一份"
      }
    ]
  }
}
```

#### 预期输出

- 依次得到业务码 [0, 0]；数据库总记录数为 2。
- 保存匿名标记来自问卷，内部身份绑定 reader；提交响应仅含 response_id、submitted_at。

#### 实际结果

**通过**；阶段总耗时 1.339 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b25962dcf769e33eae1/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b25962dcf769e33eae1/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/TetqCiwByTJNMYNAaeVoKxnTr--45Lpkb4dBHSDDQWY/submit` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/TetqCiwByTJNMYNAaeVoKxnTr--45Lpkb4dBHSDDQWY/submit` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 再次填写生成不同提交 ID | true | true | 符合 |
| Responses 记录数 | 2 | 2 | 符合 |
| 提交输出字段 | ["response_id", "submitted_at"] | ["response_id", "submitted_at"] | 符合 |
| Responses.answers | [{"question_id": "6ae15b25962dcf769e33eae2", "value": "第一份"}] | [{"question_id": "6ae15b25962dcf769e33eae2", "value": "第一份"}] | 符合 |
| Responses.is_anonymous | false | false | 符合 |
| Responses.respondent_id | "6ae15b25962dcf769e33eae0" | "6ae15b25962dcf769e33eae0" | 符合 |

### SUB-005 原样重试返回原记录，允许多次=False

脚本节点：`tests/test_acceptance.py::test_acceptance[SUB-005]`

#### 步骤

1. 创建必答文本题并发布，按场景设置匿名或重复填写开关。
2. reader 提交“第一份”；normal 到此结束；repeat 换标识，idempotent 原样重试，changed 保持标识但改为“第二份”。
3. 核对 HTTP 响应和数据库记录；幂等重试还检查提交 ID、时间完全相同。

#### 输入

```json
{
  "method": "POST",
  "path": "/surveys/access/<token>/submit",
  "mode": "idempotent",
  "setting": false,
  "first": {
    "requestId": "submit-1",
    "answers": [
      {
        "question_id": "<q1>",
        "value": "第一份"
      }
    ]
  },
  "second": {
    "requestId": "submit-1",
    "answers": [
      {
        "question_id": "<q1>",
        "value": "第一份"
      }
    ]
  }
}
```

#### 预期输出

- 依次得到业务码 [0, 0]；数据库总记录数为 1。
- 保存匿名标记来自问卷，内部身份绑定 reader；提交响应仅含 response_id、submitted_at。

#### 实际结果

**通过**；阶段总耗时 1.347 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b26962dcf769e33eae9/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b26962dcf769e33eae9/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/MD7qhd9VuBbZjU-naGqMFyxtbS_2nmwETBkBt__oNFs/submit` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/MD7qhd9VuBbZjU-naGqMFyxtbS_2nmwETBkBt__oNFs/submit` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 幂等响应完全相同 | {"response_id": "6ae15b26962dcf769e33eaeb", "submitted_at": "2100-01-01T00:00:00+00:00"} | {"response_id": "6ae15b26962dcf769e33eaeb", "submitted_at": "2100-01-01T00:00:00+00:00"} | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |
| 提交输出字段 | ["response_id", "submitted_at"] | ["response_id", "submitted_at"] | 符合 |
| Responses.answers | [{"question_id": "6ae15b26962dcf769e33eaea", "value": "第一份"}] | [{"question_id": "6ae15b26962dcf769e33eaea", "value": "第一份"}] | 符合 |
| Responses.is_anonymous | false | false | 符合 |
| Responses.respondent_id | "6ae15b26962dcf769e33eae8" | "6ae15b26962dcf769e33eae8" | 符合 |

### SUB-006 原样重试返回原记录，允许多次=True

脚本节点：`tests/test_acceptance.py::test_acceptance[SUB-006]`

#### 步骤

1. 创建必答文本题并发布，按场景设置匿名或重复填写开关。
2. reader 提交“第一份”；normal 到此结束；repeat 换标识，idempotent 原样重试，changed 保持标识但改为“第二份”。
3. 核对 HTTP 响应和数据库记录；幂等重试还检查提交 ID、时间完全相同。

#### 输入

```json
{
  "method": "POST",
  "path": "/surveys/access/<token>/submit",
  "mode": "idempotent",
  "setting": true,
  "first": {
    "requestId": "submit-1",
    "answers": [
      {
        "question_id": "<q1>",
        "value": "第一份"
      }
    ]
  },
  "second": {
    "requestId": "submit-1",
    "answers": [
      {
        "question_id": "<q1>",
        "value": "第一份"
      }
    ]
  }
}
```

#### 预期输出

- 依次得到业务码 [0, 0]；数据库总记录数为 1。
- 保存匿名标记来自问卷，内部身份绑定 reader；提交响应仅含 response_id、submitted_at。

#### 实际结果

**通过**；阶段总耗时 1.499 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b28962dcf769e33eaf0/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b28962dcf769e33eaf0/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/bf-U8PpjPV6KdujXm3ESssnOlkI6Lp2fJkF0VFPU-js/submit` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/bf-U8PpjPV6KdujXm3ESssnOlkI6Lp2fJkF0VFPU-js/submit` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 幂等响应完全相同 | {"response_id": "6ae15b28962dcf769e33eaf2", "submitted_at": "2100-01-01T00:00:00+00:00"} | {"response_id": "6ae15b28962dcf769e33eaf2", "submitted_at": "2100-01-01T00:00:00+00:00"} | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |
| 提交输出字段 | ["response_id", "submitted_at"] | ["response_id", "submitted_at"] | 符合 |
| Responses.answers | [{"question_id": "6ae15b28962dcf769e33eaf1", "value": "第一份"}] | [{"question_id": "6ae15b28962dcf769e33eaf1", "value": "第一份"}] | 符合 |
| Responses.is_anonymous | false | false | 符合 |
| Responses.respondent_id | "6ae15b28962dcf769e33eaef" | "6ae15b28962dcf769e33eaef" | 符合 |

### SUB-007 同标识改变内容冲突，允许多次=False

脚本节点：`tests/test_acceptance.py::test_acceptance[SUB-007]`

#### 步骤

1. 创建必答文本题并发布，按场景设置匿名或重复填写开关。
2. reader 提交“第一份”；normal 到此结束；repeat 换标识，idempotent 原样重试，changed 保持标识但改为“第二份”。
3. 核对 HTTP 响应和数据库记录；幂等重试还检查提交 ID、时间完全相同。

#### 输入

```json
{
  "method": "POST",
  "path": "/surveys/access/<token>/submit",
  "mode": "changed",
  "setting": false,
  "first": {
    "requestId": "submit-1",
    "answers": [
      {
        "question_id": "<q1>",
        "value": "第一份"
      }
    ]
  },
  "second": {
    "requestId": "submit-1",
    "answers": [
      {
        "question_id": "<q1>",
        "value": "第二份"
      }
    ]
  }
}
```

#### 预期输出

- 依次得到业务码 [0, 4090]；数据库总记录数为 1。
- 保存匿名标记来自问卷，内部身份绑定 reader；提交响应仅含 response_id、submitted_at。

#### 实际结果

**通过**；阶段总耗时 1.240 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b29962dcf769e33eaf7/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b29962dcf769e33eaf7/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/EYD9fG4vMRiIcvnDwA4fHsf2DkY9iU7egp3p02pt__c/submit` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/EYD9fG4vMRiIcvnDwA4fHsf2DkY9iU7egp3p02pt__c/submit` | 409 | {"code": 4090, "msg": "请求标识已用于其他提交内容"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |
| 提交输出字段 | ["response_id", "submitted_at"] | ["response_id", "submitted_at"] | 符合 |
| Responses.answers | [{"question_id": "6ae15b29962dcf769e33eaf8", "value": "第一份"}] | [{"question_id": "6ae15b29962dcf769e33eaf8", "value": "第一份"}] | 符合 |
| Responses.is_anonymous | false | false | 符合 |
| Responses.respondent_id | "6ae15b29962dcf769e33eaf6" | "6ae15b29962dcf769e33eaf6" | 符合 |

### SUB-008 同标识改变内容冲突，允许多次=True

脚本节点：`tests/test_acceptance.py::test_acceptance[SUB-008]`

#### 步骤

1. 创建必答文本题并发布，按场景设置匿名或重复填写开关。
2. reader 提交“第一份”；normal 到此结束；repeat 换标识，idempotent 原样重试，changed 保持标识但改为“第二份”。
3. 核对 HTTP 响应和数据库记录；幂等重试还检查提交 ID、时间完全相同。

#### 输入

```json
{
  "method": "POST",
  "path": "/surveys/access/<token>/submit",
  "mode": "changed",
  "setting": true,
  "first": {
    "requestId": "submit-1",
    "answers": [
      {
        "question_id": "<q1>",
        "value": "第一份"
      }
    ]
  },
  "second": {
    "requestId": "submit-1",
    "answers": [
      {
        "question_id": "<q1>",
        "value": "第二份"
      }
    ]
  }
}
```

#### 预期输出

- 依次得到业务码 [0, 4090]；数据库总记录数为 1。
- 保存匿名标记来自问卷，内部身份绑定 reader；提交响应仅含 response_id、submitted_at。

#### 实际结果

**通过**；阶段总耗时 1.196 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b2a962dcf769e33eafe/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b2a962dcf769e33eafe/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/_RL5RlKzmAMsrP7NPB6iGrJlhS_s7I23RWteL-DnbbA/submit` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/_RL5RlKzmAMsrP7NPB6iGrJlhS_s7I23RWteL-DnbbA/submit` | 409 | {"code": 4090, "msg": "请求标识已用于其他提交内容"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |
| 提交输出字段 | ["response_id", "submitted_at"] | ["response_id", "submitted_at"] | 符合 |
| Responses.answers | [{"question_id": "6ae15b2a962dcf769e33eaff", "value": "第一份"}] | [{"question_id": "6ae15b2a962dcf769e33eaff", "value": "第一份"}] | 符合 |
| Responses.is_anonymous | false | false | 符合 |
| Responses.respondent_id | "6ae15b2a962dcf769e33eafd" | "6ae15b2a962dcf769e33eafd" | 符合 |

### SUB-009 关闭后首次提交

脚本节点：`tests/test_acceptance.py::test_acceptance[SUB-009]`

#### 步骤

1. 准备已发布的必答文本问卷；截止场景预先设为测试时钟一小时后。
2. 重试场景先成功提交；然后手动关闭，或推进注入时钟恰好到 deadline。
3. 提交或原样重试，检查返回值和数据库份数。

#### 输入

```json
{
  "requestId": "closed-1",
  "answer": "第一份",
  "expired": false,
  "retry": false,
  "deadline_offset_seconds": 3600
}
```

#### 预期输出

- 最终 code=4090，记录数为 0。
- 重试成功时返回原提交 ID 和时间，不能再创建记录。

#### 实际结果

**通过**；阶段总耗时 1.284 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b2c962dcf769e33eb05/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b2c962dcf769e33eb05/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/6ae15b2c962dcf769e33eb05/close` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/xc9O1eCO9qpxBRCdMrtuZxjOEbFzYsr2zlq3zcq-Mfs/submit` | 409 | {"code": 4090, "msg": "问卷已关闭"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 0 | 0 | 符合 |

### SUB-010 截止后首次提交

脚本节点：`tests/test_acceptance.py::test_acceptance[SUB-010]`

#### 步骤

1. 准备已发布的必答文本问卷；截止场景预先设为测试时钟一小时后。
2. 重试场景先成功提交；然后手动关闭，或推进注入时钟恰好到 deadline。
3. 提交或原样重试，检查返回值和数据库份数。

#### 输入

```json
{
  "requestId": "closed-1",
  "answer": "第一份",
  "expired": true,
  "retry": false,
  "deadline_offset_seconds": 3600
}
```

#### 预期输出

- 最终 code=4090，记录数为 0。
- 重试成功时返回原提交 ID 和时间，不能再创建记录。

#### 实际结果

**通过**；阶段总耗时 1.173 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b2d962dcf769e33eb0b/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `PUT /surveys/6ae15b2d962dcf769e33eb0b/deadline` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ae15b2d962dcf769e33eb0b/publish` | 200 | {"code": 0, "msg": "ok"} |
| 16 | 执行 | `POST /surveys/access/hb9bI8N8YY5p45RMSoU9XrKnke82IinGYJwDV1QtQGk/submit` | 409 | {"code": 4090, "msg": "问卷已截止"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 0 | 0 | 符合 |

### SUB-011 关闭后重试已有成功请求

脚本节点：`tests/test_acceptance.py::test_acceptance[SUB-011]`

#### 步骤

1. 准备已发布的必答文本问卷；截止场景预先设为测试时钟一小时后。
2. 重试场景先成功提交；然后手动关闭，或推进注入时钟恰好到 deadline。
3. 提交或原样重试，检查返回值和数据库份数。

#### 输入

```json
{
  "requestId": "closed-1",
  "answer": "第一份",
  "expired": false,
  "retry": true,
  "deadline_offset_seconds": 3600
}
```

#### 预期输出

- 最终 code=0，记录数为 1。
- 重试成功时返回原提交 ID 和时间，不能再创建记录。

#### 实际结果

**通过**；阶段总耗时 1.034 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b2e962dcf769e33eb11/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b2e962dcf769e33eb11/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/u0OcH0uVIQAZ3dXSD6h_K0Wkj_I3yjzC9oXLrySfaKw/submit` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/6ae15b2e962dcf769e33eb11/close` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 执行 | `POST /surveys/access/u0OcH0uVIQAZ3dXSD6h_K0Wkj_I3yjzC9oXLrySfaKw/submit` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |
| 关闭或截止后重试返回原结果 | {"response_id": "6ae15b2e962dcf769e33eb13", "submitted_at": "2100-01-01T00:00:00+00:00"} | {"response_id": "6ae15b2e962dcf769e33eb13", "submitted_at": "2100-01-01T00:00:00+00:00"} | 符合 |

### SUB-012 截止后重试已有成功请求

脚本节点：`tests/test_acceptance.py::test_acceptance[SUB-012]`

#### 步骤

1. 准备已发布的必答文本问卷；截止场景预先设为测试时钟一小时后。
2. 重试场景先成功提交；然后手动关闭，或推进注入时钟恰好到 deadline。
3. 提交或原样重试，检查返回值和数据库份数。

#### 输入

```json
{
  "requestId": "closed-1",
  "answer": "第一份",
  "expired": true,
  "retry": true,
  "deadline_offset_seconds": 3600
}
```

#### 预期输出

- 最终 code=0，记录数为 1。
- 重试成功时返回原提交 ID 和时间，不能再创建记录。

#### 实际结果

**通过**；阶段总耗时 1.285 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b2f962dcf769e33eb18/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `PUT /surveys/6ae15b2f962dcf769e33eb18/deadline` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ae15b2f962dcf769e33eb18/publish` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/QEq2Za4gaQoqzn2QZuFmCxqUvCLA61oG69zd74fTyJM/submit` | 200 | {"code": 0, "msg": "ok"} |
| 19 | 执行 | `POST /surveys/access/QEq2Za4gaQoqzn2QZuFmCxqUvCLA61oG69zd74fTyJM/submit` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |
| 关闭或截止后重试返回原结果 | {"response_id": "6ae15b2f962dcf769e33eb1a", "submitted_at": "2100-01-01T00:00:00+00:00"} | {"response_id": "6ae15b2f962dcf769e33eb1a", "submitted_at": "2100-01-01T00:00:00+00:00"} | 符合 |

### SUB-013 多人同时填写

脚本节点：`tests/test_acceptance.py::test_acceptance[SUB-013]`

#### 步骤

1. 准备已发布且每人限一次的必答文本问卷；截止场景先设置 deadline。
2. owner 与 reader 并发提交，各使用独立身份。
3. 读取各响应和数据库记录数，验证没有重复或半份提交。

#### 输入

```json
{
  "path": "/surveys/access/<token>/submit",
  "answer": "并发答案",
  "mode": "people",
  "control": "同步事件或注入时钟，不依赖任意 sleep"
}
```

#### 预期输出

- 业务码排序后为 [0, 0]；数据库记录数为 2。
- 同请求并发成功时，所有成功响应的提交 ID 和时间必须相同。

#### 实际结果

**通过**；阶段总耗时 1.034 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b30962dcf769e33eb1f/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b30962dcf769e33eb1f/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/bO2G9kbi_cXnLiSGcm0Wde7UFfNH3rXxeCDSfNznKXw/submit` | 200 | {"code": 0, "msg": "ok"} |
| 13 | 执行 | `POST /surveys/access/bO2G9kbi_cXnLiSGcm0Wde7UFfNH3rXxeCDSfNznKXw/submit` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 并发结果业务码集合 | [0, 0] | [0, 0] | 符合 |
| Responses 记录数 | 2 | 2 | 符合 |

### SUB-014 同请求并发重试

脚本节点：`tests/test_acceptance.py::test_acceptance[SUB-014]`

#### 步骤

1. 准备已发布且每人限一次的必答文本问卷；截止场景先设置 deadline。
2. 同一 reader 并发发送三次相同 requestId 和内容。
3. 读取各响应和数据库记录数，验证没有重复或半份提交。

#### 输入

```json
{
  "path": "/surveys/access/<token>/submit",
  "answer": "并发答案",
  "mode": "same_request",
  "control": "同步事件或注入时钟，不依赖任意 sleep"
}
```

#### 预期输出

- 业务码排序后为 [0, 0, 0]；数据库记录数为 1。
- 同请求并发成功时，所有成功响应的提交 ID 和时间必须相同。

#### 实际结果

**通过**；阶段总耗时 1.064 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b31962dcf769e33eb28/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b31962dcf769e33eb28/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/8J_mf2WDAX67_6nGk_557VRXUzg0Pi7B0BEzWLhyTPg/submit` | 200 | {"code": 0, "msg": "ok"} |
| 13 | 执行 | `POST /surveys/access/8J_mf2WDAX67_6nGk_557VRXUzg0Pi7B0BEzWLhyTPg/submit` | 200 | {"code": 0, "msg": "ok"} |
| 14 | 执行 | `POST /surveys/access/8J_mf2WDAX67_6nGk_557VRXUzg0Pi7B0BEzWLhyTPg/submit` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 并发结果业务码集合 | [0, 0, 0] | [0, 0, 0] | 符合 |
| 并发重试返回同一提交 | {"response_id": "6ae15b31962dcf769e33eb2a", "submitted_at": "2100-01-01T00:00:00+00:00"} | {"response_id": "6ae15b31962dcf769e33eb2a", "submitted_at": "2100-01-01T00:00:00+00:00"} | 符合 |
| 并发重试返回同一提交 | {"response_id": "6ae15b31962dcf769e33eb2a", "submitted_at": "2100-01-01T00:00:00+00:00"} | {"response_id": "6ae15b31962dcf769e33eb2a", "submitted_at": "2100-01-01T00:00:00+00:00"} | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |

### SUB-015 限填一次的并发竞争

脚本节点：`tests/test_acceptance.py::test_acceptance[SUB-015]`

#### 步骤

1. 准备已发布且每人限一次的必答文本问卷；截止场景先设置 deadline。
2. 同一 reader 并发发送三个不同 requestId。
3. 读取各响应和数据库记录数，验证没有重复或半份提交。

#### 输入

```json
{
  "path": "/surveys/access/<token>/submit",
  "answer": "并发答案",
  "mode": "different_requests",
  "control": "同步事件或注入时钟，不依赖任意 sleep"
}
```

#### 预期输出

- 业务码排序后为 [0, 4090, 4090]；数据库记录数为 1。
- 同请求并发成功时，所有成功响应的提交 ID 和时间必须相同。

#### 实际结果

**通过**；阶段总耗时 0.984 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b32962dcf769e33eb31/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b32962dcf769e33eb31/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/5Py-acJ7o1aDdsxaBCkv4OwWSAtJk8g7lX7jRj_bDts/submit` | 409 | {"code": 4090, "msg": "该问卷不允许重复提交"} |
| 13 | 执行 | `POST /surveys/access/5Py-acJ7o1aDdsxaBCkv4OwWSAtJk8g7lX7jRj_bDts/submit` | 409 | {"code": 4090, "msg": "该问卷不允许重复提交"} |
| 14 | 执行 | `POST /surveys/access/5Py-acJ7o1aDdsxaBCkv4OwWSAtJk8g7lX7jRj_bDts/submit` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 竞争响应状态与业务码对应 | 200 | 200 | 符合 |
| 竞争响应状态与业务码对应 | 409 | 409 | 符合 |
| 竞争响应状态与业务码对应 | 409 | 409 | 符合 |
| 并发结果业务码集合 | [0, 4090, 4090] | [0, 4090, 4090] | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |

### SUB-016 提交中途被关闭时回滚

脚本节点：`tests/test_acceptance.py::test_acceptance[SUB-016]`

#### 步骤

1. 准备已发布且每人限一次的必答文本问卷；截止场景先设置 deadline。
2. 暂停服务端路径校验后的提交，用 owner 关闭，再继续提交。
3. 读取各响应和数据库记录数，验证没有重复或半份提交。

#### 输入

```json
{
  "path": "/surveys/access/<token>/submit",
  "answer": "并发答案",
  "mode": "close_race",
  "control": "同步事件或注入时钟，不依赖任意 sleep"
}
```

#### 预期输出

- 业务码排序后为 [4090]；数据库记录数为 0。
- 同请求并发成功时，所有成功响应的提交 ID 和时间必须相同。

#### 实际结果

**通过**；阶段总耗时 1.037 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b33962dcf769e33eb3a/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b33962dcf769e33eb3a/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/fXmJKcMOOMXB1AmkAkhR-nwiaM8VOeU9Wgskg368IG8/submit` | 409 | {"code": 4090, "msg": "问卷已关闭"} |
| 15 | 执行 | `POST /surveys/6ae15b33962dcf769e33eb3a/close` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 到达暂停点 | true | true | 符合 |
| Responses 记录数 | 0 | 0 | 符合 |

### SUB-017 提交中途截止时回滚

脚本节点：`tests/test_acceptance.py::test_acceptance[SUB-017]`

#### 步骤

1. 准备已发布且每人限一次的必答文本问卷；截止场景先设置 deadline。
2. 路径校验后推进测试时钟到 deadline，再继续写入事务。
3. 读取各响应和数据库记录数，验证没有重复或半份提交。

#### 输入

```json
{
  "path": "/surveys/access/<token>/submit",
  "answer": "并发答案",
  "mode": "expiry_race",
  "control": "同步事件或注入时钟，不依赖任意 sleep"
}
```

#### 预期输出

- 业务码排序后为 [4090]；数据库记录数为 0。
- 同请求并发成功时，所有成功响应的提交 ID 和时间必须相同。

#### 实际结果

**通过**；阶段总耗时 1.024 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b34962dcf769e33eb41/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `PUT /surveys/6ae15b34962dcf769e33eb41/deadline` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ae15b34962dcf769e33eb41/publish` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/FW-_2-6N6pt-8YTpPpDX2rlnxOzZlUdwsEIbW5jDD50/submit` | 409 | {"code": 4090, "msg": "问卷已截止"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 0 | 0 | 符合 |


## 统计测试

### STA-001 四类统计、回答分母及整卷单题一致

脚本节点：`tests/test_acceptance.py::test_acceptance[STA-001]`

#### 步骤

1. 创建四种题型并允许多次填写，发布后由同一 reader 提交三份固定答案；第一份额外原样重试一次。
2. 读取整卷统计，再分别读取四道题的统计。

#### 输入

```json
{
  "submissions": [
    [
      "A",
      [
        "A",
        "B"
      ],
      "重复内容",
      0
    ],
    [
      "A",
      [
        "B"
      ],
      "重复内容",
      10
    ],
    [
      "B",
      [],
      "",
      null
    ]
  ],
  "paths": [
    "GET /surveys/<id>/statistics",
    "GET /surveys/<id>/questions/<qid>/statistics"
  ]
}
```

#### 预期输出

- 总份数=3，单选回答数=3、选项计数=[2,1,0]；多选回答数=2、计数=[1,2,0]。
- 文本保留两条重复内容；数字有效回答数=2、平均值=5，不使用总份数 3 作分母。
- 整卷每题结果与单题第一页完全相同。

#### 实际结果

**通过**；阶段总耗时 1.378 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b35962dcf769e33eb48/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b35962dcf769e33eb48/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ae15b35962dcf769e33eb48/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `POST /surveys/6ae15b35962dcf769e33eb48/questions` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ae15b35962dcf769e33eb48/publish` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 准备 | `POST /surveys/access/BmPbUWjLRRwZDMBSwLOjEMZDQf3X1TL1tMj_E9Hq1kk/submit` | 200 | {"code": 0, "msg": "ok"} |
| 24 | 准备 | `POST /surveys/access/BmPbUWjLRRwZDMBSwLOjEMZDQf3X1TL1tMj_E9Hq1kk/submit` | 200 | {"code": 0, "msg": "ok"} |
| 27 | 准备 | `POST /surveys/access/BmPbUWjLRRwZDMBSwLOjEMZDQf3X1TL1tMj_E9Hq1kk/submit` | 200 | {"code": 0, "msg": "ok"} |
| 30 | 准备 | `POST /surveys/access/BmPbUWjLRRwZDMBSwLOjEMZDQf3X1TL1tMj_E9Hq1kk/submit` | 200 | {"code": 0, "msg": "ok"} |
| 33 | 执行 | `GET /surveys/6ae15b35962dcf769e33eb48/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 43 | 执行 | `GET /surveys/6ae15b35962dcf769e33eb48/questions/6ae15b35962dcf769e33eb49/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 47 | 执行 | `GET /surveys/6ae15b35962dcf769e33eb48/questions/6ae15b35962dcf769e33eb4d/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 51 | 执行 | `GET /surveys/6ae15b35962dcf769e33eb48/questions/6ae15b35962dcf769e33eb51/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 55 | 执行 | `GET /surveys/6ae15b35962dcf769e33eb48/questions/6ae15b35962dcf769e33eb52/statistics` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 整卷提交份数 | 3 | 3 | 符合 |
| 各题有效回答数 | [3, 2, 2, 2] | [3, 2, 2, 2] | 符合 |
| 单选按配置顺序计数 | [2, 1, 0] | [2, 1, 0] | 符合 |
| 多选选项计数 | [1, 2, 0] | [1, 2, 0] | 符合 |
| 文本重复内容保留 | ["重复内容", "重复内容"] | ["重复内容", "重复内容"] | 符合 |
| 数字原值 | [0, 10] | [0, 10] | 符合 |
| 数字平均值 | 5 | 5.0 | 符合 |
| 单题与整卷一致 | {"question_id": "6ae15b35962dcf769e33eb49", "order": 1, "type": "single", "title": "验收题目", "answer_count": 3, "options": [{"option_id": "6ae15b35962dcf769e33eb4a", "text": "A", "count": 2}, {"option_id": "6ae15b35962dcf7…（完整值见原始 JSON） | {"question_id": "6ae15b35962dcf769e33eb49", "order": 1, "type": "single", "title": "验收题目", "answer_count": 3, "options": [{"option_id": "6ae15b35962dcf769e33eb4a", "text": "A", "count": 2}, {"option_id": "6ae15b35962dcf7…（完整值见原始 JSON） | 符合 |
| 单题与整卷一致 | {"question_id": "6ae15b35962dcf769e33eb4d", "order": 2, "type": "multiple", "title": "验收题目", "answer_count": 2, "options": [{"option_id": "6ae15b35962dcf769e33eb4e", "text": "A", "count": 1}, {"option_id": "6ae15b35962dc…（完整值见原始 JSON） | {"question_id": "6ae15b35962dcf769e33eb4d", "order": 2, "type": "multiple", "title": "验收题目", "answer_count": 2, "options": [{"option_id": "6ae15b35962dcf769e33eb4e", "text": "A", "count": 1}, {"option_id": "6ae15b35962dc…（完整值见原始 JSON） | 符合 |
| 单题与整卷一致 | {"question_id": "6ae15b35962dcf769e33eb51", "order": 3, "type": "text", "title": "验收题目", "answer_count": 2, "contents": {"items": [{"value": "重复内容"}, {"value": "重复内容"}], "total": 2, "page": 1, "page_size": 20}} | {"question_id": "6ae15b35962dcf769e33eb51", "order": 3, "type": "text", "title": "验收题目", "answer_count": 2, "contents": {"items": [{"value": "重复内容"}, {"value": "重复内容"}], "total": 2, "page": 1, "page_size": 20}} | 符合 |
| 单题与整卷一致 | {"question_id": "6ae15b35962dcf769e33eb52", "order": 4, "type": "number", "title": "验收题目", "answer_count": 2, "contents": {"items": [{"value": 0}, {"value": 10}], "total": 2, "page": 1, "page_size": 20}, "average": 5.0} | {"question_id": "6ae15b35962dcf769e33eb52", "order": 4, "type": "number", "title": "验收题目", "answer_count": 2, "contents": {"items": [{"value": 0}, {"value": 10}], "total": 2, "page": 1, "page_size": 20}, "average": 5.0} | 符合 |
| Responses 记录数 | 3 | 3 | 符合 |

### STA-002 无提交时返回零值和空列表

脚本节点：`tests/test_acceptance.py::test_acceptance[STA-002]`

#### 步骤

1. 创建含四种题型的草稿问卷，不提交。
2. 读取整卷和每道单题统计。

#### 输入

```json
{
  "submission_count": 0,
  "status": "draft"
}
```

#### 预期输出

- 总份数、各题回答数、各选项计数为 0；填空列表为空；数字平均值为 null。

#### 实际结果

**通过**；阶段总耗时 1.058 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b37962dcf769e33eb5a/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b37962dcf769e33eb5a/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ae15b37962dcf769e33eb5a/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `POST /surveys/6ae15b37962dcf769e33eb5a/questions` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 执行 | `GET /surveys/6ae15b37962dcf769e33eb5a/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 24 | 执行 | `GET /surveys/6ae15b37962dcf769e33eb5a/questions/6ae15b37962dcf769e33eb5b/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 30 | 执行 | `GET /surveys/6ae15b37962dcf769e33eb5a/questions/6ae15b37962dcf769e33eb5f/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 36 | 执行 | `GET /surveys/6ae15b37962dcf769e33eb5a/questions/6ae15b37962dcf769e33eb63/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 42 | 执行 | `GET /surveys/6ae15b37962dcf769e33eb5a/questions/6ae15b37962dcf769e33eb64/statistics` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 无提交时总数 | 0 | 0 | 符合 |
| 空问卷题目回答数 | 0 | 0 | 符合 |
| 全部选项零计数 | [0, 0, 0] | [0, 0, 0] | 符合 |
| 空问卷单题统计一致 | {"question_id": "6ae15b37962dcf769e33eb5b", "order": 1, "type": "single", "title": "验收题目", "answer_count": 0, "options": [{"option_id": "6ae15b37962dcf769e33eb5c", "text": "A", "count": 0}, {"option_id": "6ae15b37962dcf7…（完整值见原始 JSON） | {"question_id": "6ae15b37962dcf769e33eb5b", "order": 1, "type": "single", "title": "验收题目", "answer_count": 0, "options": [{"option_id": "6ae15b37962dcf769e33eb5c", "text": "A", "count": 0}, {"option_id": "6ae15b37962dcf7…（完整值见原始 JSON） | 符合 |
| 空问卷题目回答数 | 0 | 0 | 符合 |
| 全部选项零计数 | [0, 0, 0] | [0, 0, 0] | 符合 |
| 空问卷单题统计一致 | {"question_id": "6ae15b37962dcf769e33eb5f", "order": 2, "type": "multiple", "title": "验收题目", "answer_count": 0, "options": [{"option_id": "6ae15b37962dcf769e33eb60", "text": "A", "count": 0}, {"option_id": "6ae15b37962dc…（完整值见原始 JSON） | {"question_id": "6ae15b37962dcf769e33eb5f", "order": 2, "type": "multiple", "title": "验收题目", "answer_count": 0, "options": [{"option_id": "6ae15b37962dcf769e33eb60", "text": "A", "count": 0}, {"option_id": "6ae15b37962dc…（完整值见原始 JSON） | 符合 |
| 空问卷题目回答数 | 0 | 0 | 符合 |
| 空内容列表 | [] | [] | 符合 |
| 空问卷单题统计一致 | {"question_id": "6ae15b37962dcf769e33eb63", "order": 3, "type": "text", "title": "验收题目", "answer_count": 0, "contents": {"items": [], "total": 0, "page": 1, "page_size": 20}} | {"question_id": "6ae15b37962dcf769e33eb63", "order": 3, "type": "text", "title": "验收题目", "answer_count": 0, "contents": {"items": [], "total": 0, "page": 1, "page_size": 20}} | 符合 |
| 空问卷题目回答数 | 0 | 0 | 符合 |
| 空内容列表 | [] | [] | 符合 |
| 空问卷单题统计一致 | {"question_id": "6ae15b37962dcf769e33eb64", "order": 4, "type": "number", "title": "验收题目", "answer_count": 0, "contents": {"items": [], "total": 0, "page": 1, "page_size": 20}, "average": null} | {"question_id": "6ae15b37962dcf769e33eb64", "order": 4, "type": "number", "title": "验收题目", "answer_count": 0, "contents": {"items": [], "total": 0, "page": 1, "page_size": 20}, "average": null} | 符合 |
| 空平均值不能为 0 | null | null | 符合 |

### STA-003 text 内容稳定分页与全量汇总

脚本节点：`tests/test_acceptance.py::test_acceptance[STA-003]`

#### 步骤

1. 创建单题问卷并发布。本排序专项直接在测试库插入 27 条符合字段约定的旧格式答卷。
2. 数值为 0..26，文本为“内容0”..“内容26”；每三条时间相同，组内 ID 递增，但较晚时间组的 ID 更小；实际逆序插入。
3. 读取整卷，再用 page_size=10 读取第 1、2、3、4 页。

#### 输入

```json
{
  "values": "内容0..内容26",
  "page_size": 10,
  "pages": [
    1,
    2,
    3,
    4
  ],
  "insertion_order": "逆序；时间升序、同时间 ID 升序为预期",
  "id_rule": "同时间组内递增，较晚时间组 ID 更小"
}
```

#### 预期输出

- 整卷仅返回最早 20 条；各页分别有 10、10、7、0 条且顺序稳定，total=27。
- 数字平均值在所有页都为 13，不能只取当前页计算；旧记录缺少幂等字段仍计入。

#### 实际结果

**通过**；阶段总耗时 0.987 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b38962dcf769e33eb69/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b38962dcf769e33eb69/publish` | 200 | {"code": 0, "msg": "ok"} |
| 14 | 执行 | `GET /surveys/6ae15b38962dcf769e33eb69/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 执行 | `GET /surveys/6ae15b38962dcf769e33eb69/questions/6ae15b38962dcf769e33eb6a/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 23 | 执行 | `GET /surveys/6ae15b38962dcf769e33eb69/questions/6ae15b38962dcf769e33eb6a/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 28 | 执行 | `GET /surveys/6ae15b38962dcf769e33eb69/questions/6ae15b38962dcf769e33eb6a/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 33 | 执行 | `GET /surveys/6ae15b38962dcf769e33eb69/questions/6ae15b38962dcf769e33eb6a/statistics` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 27 | 27 | 符合 |
| 整卷返回前 20 条 | ["内容0", "内容1", "内容2", "内容3", "内容4", "内容5", "内容6", "内容7", "内容8", "内容9", "内容10", "内容11", "内容12", "内容13", "内容14", "内容15", "内容16", "内容17", "内容18", "内容19"] | ["内容0", "内容1", "内容2", "内容3", "内容4", "内容5", "内容6", "内容7", "内容8", "内容9", "内容10", "内容11", "内容12", "内容13", "内容14", "内容15", "内容16", "内容17", "内容18", "内容19"] | 符合 |
| 第 1 页内容 | ["内容0", "内容1", "内容2", "内容3", "内容4", "内容5", "内容6", "内容7", "内容8", "内容9"] | ["内容0", "内容1", "内容2", "内容3", "内容4", "内容5", "内容6", "内容7", "内容8", "内容9"] | 符合 |
| 第 1 页完整总数 | 27 | 27 | 符合 |
| 第 2 页内容 | ["内容10", "内容11", "内容12", "内容13", "内容14", "内容15", "内容16", "内容17", "内容18", "内容19"] | ["内容10", "内容11", "内容12", "内容13", "内容14", "内容15", "内容16", "内容17", "内容18", "内容19"] | 符合 |
| 第 2 页完整总数 | 27 | 27 | 符合 |
| 第 3 页内容 | ["内容20", "内容21", "内容22", "内容23", "内容24", "内容25", "内容26"] | ["内容20", "内容21", "内容22", "内容23", "内容24", "内容25", "内容26"] | 符合 |
| 第 3 页完整总数 | 27 | 27 | 符合 |
| 第 4 页内容 | [] | [] | 符合 |
| 第 4 页完整总数 | 27 | 27 | 符合 |

### STA-004 number 内容稳定分页与全量汇总

脚本节点：`tests/test_acceptance.py::test_acceptance[STA-004]`

#### 步骤

1. 创建单题问卷并发布。本排序专项直接在测试库插入 27 条符合字段约定的旧格式答卷。
2. 数值为 0..26，文本为“内容0”..“内容26”；每三条时间相同，组内 ID 递增，但较晚时间组的 ID 更小；实际逆序插入。
3. 读取整卷，再用 page_size=10 读取第 1、2、3、4 页。

#### 输入

```json
{
  "values": "0..26",
  "page_size": 10,
  "pages": [
    1,
    2,
    3,
    4
  ],
  "insertion_order": "逆序；时间升序、同时间 ID 升序为预期",
  "id_rule": "同时间组内递增，较晚时间组 ID 更小"
}
```

#### 预期输出

- 整卷仅返回最早 20 条；各页分别有 10、10、7、0 条且顺序稳定，total=27。
- 数字平均值在所有页都为 13，不能只取当前页计算；旧记录缺少幂等字段仍计入。

#### 实际结果

**通过**；阶段总耗时 0.999 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b39962dcf769e33eb6f/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b39962dcf769e33eb6f/publish` | 200 | {"code": 0, "msg": "ok"} |
| 14 | 执行 | `GET /surveys/6ae15b39962dcf769e33eb6f/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 执行 | `GET /surveys/6ae15b39962dcf769e33eb6f/questions/6ae15b39962dcf769e33eb70/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 24 | 执行 | `GET /surveys/6ae15b39962dcf769e33eb6f/questions/6ae15b39962dcf769e33eb70/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 30 | 执行 | `GET /surveys/6ae15b39962dcf769e33eb6f/questions/6ae15b39962dcf769e33eb70/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 36 | 执行 | `GET /surveys/6ae15b39962dcf769e33eb6f/questions/6ae15b39962dcf769e33eb70/statistics` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 27 | 27 | 符合 |
| 整卷返回前 20 条 | [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19] | [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19] | 符合 |
| 第 1 页内容 | [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] | [0, 1, 2, 3, 4, 5, 6, 7, 8, 9] | 符合 |
| 第 1 页完整总数 | 27 | 27 | 符合 |
| 第 1 页平均值基于全部 27 条 | 13 | 13.0 | 符合 |
| 第 2 页内容 | [10, 11, 12, 13, 14, 15, 16, 17, 18, 19] | [10, 11, 12, 13, 14, 15, 16, 17, 18, 19] | 符合 |
| 第 2 页完整总数 | 27 | 27 | 符合 |
| 第 2 页平均值基于全部 27 条 | 13 | 13.0 | 符合 |
| 第 3 页内容 | [20, 21, 22, 23, 24, 25, 26] | [20, 21, 22, 23, 24, 25, 26] | 符合 |
| 第 3 页完整总数 | 27 | 27 | 符合 |
| 第 3 页平均值基于全部 27 条 | 13 | 13.0 | 符合 |
| 第 4 页内容 | [] | [] | 符合 |
| 第 4 页完整总数 | 27 | 27 | 符合 |
| 第 4 页平均值基于全部 27 条 | 13 | 13.0 | 符合 |

### STA-005 权限和身份不泄露，匿名=False

脚本节点：`tests/test_acceptance.py::test_acceptance[STA-005]`

#### 步骤

1. 创建问卷并提交“测试内容”。
2. 以未登录、reader、owner 分别读取整卷及单题统计。
3. 递归检查 owner 响应的字段名，不允许出现填写者身份或内部提交元数据。

#### 输入

```json
{
  "allow_anonymous": false,
  "answer": "测试内容",
  "roles": [
    null,
    "reader",
    "owner"
  ]
}
```

#### 预期输出

- 未登录为 4010，非所有者为 4030，owner 成功。
- 内容项仅含 value；不返回用户名、用户 ID、提交 ID、提交时间、幂等标识或哈希。

#### 实际结果

**通过**；阶段总耗时 1.005 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b3a962dcf769e33eb75/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b3a962dcf769e33eb75/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/access/trLlUsgiF9UhpCqo654FkfB5FsV9XVeFC65tZhQkguo/submit` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `GET /surveys/6ae15b3a962dcf769e33eb75/statistics` | 401 | {"code": 4010, "msg": "请先登录"} |
| 19 | 执行 | `GET /surveys/6ae15b3a962dcf769e33eb75/statistics` | 403 | {"code": 4030, "msg": "无权限"} |
| 23 | 执行 | `GET /surveys/6ae15b3a962dcf769e33eb75/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 28 | 执行 | `GET /surveys/6ae15b3a962dcf769e33eb75/questions/6ae15b3a962dcf769e33eb76/statistics` | 401 | {"code": 4010, "msg": "请先登录"} |
| 32 | 执行 | `GET /surveys/6ae15b3a962dcf769e33eb75/questions/6ae15b3a962dcf769e33eb76/statistics` | 403 | {"code": 4030, "msg": "无权限"} |
| 36 | 执行 | `GET /surveys/6ae15b3a962dcf769e33eb75/questions/6ae15b3a962dcf769e33eb76/statistics` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 统计中不存在禁止的身份字段 | [] | [] | 符合 |
| 内容项只有 value | [{"value": "测试内容"}] | [{"value": "测试内容"}] | 符合 |
| 统计中不存在禁止的身份字段 | [] | [] | 符合 |
| 内容项只有 value | [{"value": "测试内容"}] | [{"value": "测试内容"}] | 符合 |

### STA-006 权限和身份不泄露，匿名=True

脚本节点：`tests/test_acceptance.py::test_acceptance[STA-006]`

#### 步骤

1. 创建问卷并提交“测试内容”。
2. 以未登录、reader、owner 分别读取整卷及单题统计。
3. 递归检查 owner 响应的字段名，不允许出现填写者身份或内部提交元数据。

#### 输入

```json
{
  "allow_anonymous": true,
  "answer": "测试内容",
  "roles": [
    null,
    "reader",
    "owner"
  ]
}
```

#### 预期输出

- 未登录为 4010，非所有者为 4030，owner 成功。
- 内容项仅含 value；不返回用户名、用户 ID、提交 ID、提交时间、幂等标识或哈希。

#### 实际结果

**通过**；阶段总耗时 1.082 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b3b962dcf769e33eb7c/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b3b962dcf769e33eb7c/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/access/ltS0GNdqapUrxmJ91ph0IeTwRI3yv2ZI_-lmEuY7Q8Q/submit` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `GET /surveys/6ae15b3b962dcf769e33eb7c/statistics` | 401 | {"code": 4010, "msg": "请先登录"} |
| 19 | 执行 | `GET /surveys/6ae15b3b962dcf769e33eb7c/statistics` | 403 | {"code": 4030, "msg": "无权限"} |
| 23 | 执行 | `GET /surveys/6ae15b3b962dcf769e33eb7c/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 28 | 执行 | `GET /surveys/6ae15b3b962dcf769e33eb7c/questions/6ae15b3b962dcf769e33eb7d/statistics` | 401 | {"code": 4010, "msg": "请先登录"} |
| 32 | 执行 | `GET /surveys/6ae15b3b962dcf769e33eb7c/questions/6ae15b3b962dcf769e33eb7d/statistics` | 403 | {"code": 4030, "msg": "无权限"} |
| 36 | 执行 | `GET /surveys/6ae15b3b962dcf769e33eb7c/questions/6ae15b3b962dcf769e33eb7d/statistics` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 统计中不存在禁止的身份字段 | [] | [] | 符合 |
| 内容项只有 value | [{"value": "测试内容"}] | [{"value": "测试内容"}] | 符合 |
| 统计中不存在禁止的身份字段 | [] | [] | 符合 |
| 内容项只有 value | [{"value": "测试内容"}] | [{"value": "测试内容"}] | 符合 |

### STA-007 whole 并发读取共享快照

脚本节点：`tests/test_acceptance.py::test_acceptance[STA-007]`

#### 步骤

1. 发布可多次填写的数字问卷，提交数值 10。
2. 整卷在总数读取后暂停；单题在汇总与明细之间暂停，随后通过真实提交接口写入 20。
3. 恢复统计，检查当前响应；再查询一次检查新提交已可见。

#### 输入

```json
{
  "initial_values": [
    10
  ],
  "concurrent_value": 20,
  "scope": "whole",
  "control": "threading.Event 控制查询交错"
}
```

#### 预期输出

- 当前响应仍为总数=1、回答数=1、内容=[10]、平均值=10。
- 下次查询为总数=2、回答数=2、内容=[10,20]、平均值=15。

#### 实际结果

**通过**；阶段总耗时 1.047 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b3c962dcf769e33eb83/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b3c962dcf769e33eb83/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/access/FucTTQlR5lt7fXDeJ2fozpeII1WMFWtky831zd8nSbQ/submit` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `GET /surveys/6ae15b3c962dcf769e33eb83/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 执行 | `POST /surveys/access/FucTTQlR5lt7fXDeJ2fozpeII1WMFWtky831zd8nSbQ/submit` | 200 | {"code": 0, "msg": "ok"} |
| 24 | 执行 | `GET /surveys/6ae15b3c962dcf769e33eb83/statistics` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 统计已到达暂停点 | true | true | 符合 |
| Responses 记录数 | 2 | 2 | 符合 |
| 当前快照 总份数 | 1 | 1 | 符合 |
| 当前快照 题目回答数 | 1 | 1 | 符合 |
| 当前快照 内容列表 | [10] | [10] | 符合 |
| 当前快照 平均值 | 10 | 10.0 | 符合 |
| 后续请求 总份数 | 2 | 2 | 符合 |
| 后续请求 题目回答数 | 2 | 2 | 符合 |
| 后续请求 内容列表 | [10, 20] | [10, 20] | 符合 |
| 后续请求 平均值 | 15 | 15.0 | 符合 |

### STA-008 single 并发读取共享快照

脚本节点：`tests/test_acceptance.py::test_acceptance[STA-008]`

#### 步骤

1. 发布可多次填写的数字问卷，提交数值 10。
2. 整卷在总数读取后暂停；单题在汇总与明细之间暂停，随后通过真实提交接口写入 20。
3. 恢复统计，检查当前响应；再查询一次检查新提交已可见。

#### 输入

```json
{
  "initial_values": [
    10
  ],
  "concurrent_value": 20,
  "scope": "single",
  "control": "threading.Event 控制查询交错"
}
```

#### 预期输出

- 当前响应仍为总数=1、回答数=1、内容=[10]、平均值=10。
- 下次查询为总数=2、回答数=2、内容=[10,20]、平均值=15。

#### 实际结果

**通过**；阶段总耗时 1.158 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ae15b3d962dcf769e33eb8b/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ae15b3d962dcf769e33eb8b/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/access/6t8vdFKLS1xkdKyzvf1-KkyVfRbYjhtWx5s4XwjbrK8/submit` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `GET /surveys/6ae15b3d962dcf769e33eb8b/questions/6ae15b3d962dcf769e33eb8c/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 执行 | `POST /surveys/access/6t8vdFKLS1xkdKyzvf1-KkyVfRbYjhtWx5s4XwjbrK8/submit` | 200 | {"code": 0, "msg": "ok"} |
| 24 | 执行 | `GET /surveys/6ae15b3d962dcf769e33eb8b/questions/6ae15b3d962dcf769e33eb8c/statistics` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 统计已到达暂停点 | true | true | 符合 |
| Responses 记录数 | 2 | 2 | 符合 |
| 当前快照 总份数 | 1 | 1 | 符合 |
| 当前快照 题目回答数 | 1 | 1 | 符合 |
| 当前快照 内容列表 | [10] | [10] | 符合 |
| 当前快照 平均值 | 10 | 10.0 | 符合 |
| 后续请求 总份数 | 2 | 2 | 符合 |
| 后续请求 题目回答数 | 2 | 2 | 符合 |
| 后续请求 内容列表 | [10, 20] | [10, 20] | 符合 |
| 后续请求 平均值 | 15 | 15.0 | 符合 |

## 原有回归与可追溯性

原有账号、问卷、填写和统计测试保留，不把历史通过结果当成本次结果。每个节点的本次结果列在 JSON 的 tests 中。
每次运行输出到独立时间戳目录，不覆盖旧轮次的失败证据。项目根目录的同名报告仅是最近一次运行的副本。
业务数据使用临时测试库，teardown 阶段记录其清理是否成功。跳过或未执行的测试没有实际成功响应，报告不会自动补写通过。
