# 测试用例与执行报告

- 运行编号：`20261018T014451579457Z-66d436`
- 开始时间（UTC）：2026-10-18T01:44:51.579457+00:00
- 结束时间（UTC）：2026-10-18T01:47:29.948651+00:00
- pytest/运行器退出码：`0`
- 六类验收：共 88 条；通过 88。
- 原有回归：通过 273。
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
  "replica_set": "acceptanceTest",
  "hosts": [
    "127.0.0.1:27132"
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
输入中的 <form_id>/<q1>/<token>/<A> 等为准备接口实际返回的 ID、问卷链接标识或选项 ID，不是登录凭证。完整实际输入及响应见逐次请求证据。
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

**通过**；阶段总耗时 0.722 秒。

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
| Question_forms.owner_id | "6ad424952930a45aebbe6f06" | "6ad424952930a45aebbe6f06" | 符合 |

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

**通过**；阶段总耗时 0.525 秒。

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

**通过**；阶段总耗时 0.543 秒。

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

**通过**；阶段总耗时 0.547 秒。

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
| Question_forms.owner_id | "6ad424972930a45aebbe6f13" | "6ad424972930a45aebbe6f13" | 符合 |

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

**通过**；阶段总耗时 0.544 秒。

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
| Question_forms.owner_id | "6ad424972930a45aebbe6f18" | "6ad424972930a45aebbe6f18" | 符合 |

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

**通过**；阶段总耗时 0.530 秒。

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

**通过**；阶段总耗时 0.569 秒。

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

**通过**；阶段总耗时 0.529 秒。

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

**通过**；阶段总耗时 0.558 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 执行 | `POST /surveys/6ad4249a2930a45aebbe6f2b/questions` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Questions 记录数 | 1 | 1 | 符合 |
| 题型 | "single" | "single" | 符合 |
| 题目顺序 | 1 | 1 | 符合 |
| 默认非必答 | false | false | 符合 |
| 选项数量 | 3 | 3 | 符合 |
| 新选项 ID 有效 | true | true | 符合 |
| Questions.form_id | "6ad4249a2930a45aebbe6f2b" | "6ad4249a2930a45aebbe6f2b" | 符合 |

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

**通过**；阶段总耗时 0.540 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 执行 | `POST /surveys/6ad4249a2930a45aebbe6f34/questions` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Questions 记录数 | 1 | 1 | 符合 |
| 题型 | "multiple" | "multiple" | 符合 |
| 题目顺序 | 1 | 1 | 符合 |
| 默认非必答 | false | false | 符合 |
| 选项数量 | 3 | 3 | 符合 |
| 新选项 ID 有效 | true | true | 符合 |
| Questions.form_id | "6ad4249a2930a45aebbe6f34" | "6ad4249a2930a45aebbe6f34" | 符合 |

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

**通过**；阶段总耗时 0.555 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 执行 | `POST /surveys/6ad4249b2930a45aebbe6f3d/questions` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Questions 记录数 | 1 | 1 | 符合 |
| 题型 | "text" | "text" | 符合 |
| 题目顺序 | 1 | 1 | 符合 |
| 默认非必答 | false | false | 符合 |
| 填空题没有选项 | [] | [] | 符合 |
| Questions.form_id | "6ad4249b2930a45aebbe6f3d" | "6ad4249b2930a45aebbe6f3d" | 符合 |

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

**通过**；阶段总耗时 0.557 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 执行 | `POST /surveys/6ad4249b2930a45aebbe6f43/questions` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Questions 记录数 | 1 | 1 | 符合 |
| 题型 | "number" | "number" | 符合 |
| 题目顺序 | 1 | 1 | 符合 |
| 默认非必答 | false | false | 符合 |
| 填空题没有选项 | [] | [] | 符合 |
| Questions.form_id | "6ad4249b2930a45aebbe6f43" | "6ad4249b2930a45aebbe6f43" | 符合 |

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

**通过**；阶段总耗时 0.544 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 执行 | `POST /surveys/6ad4249c2930a45aebbe6f49/questions` | 400 | {"code": 4001, "msg": "标题必须是非空字符串"} |

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

**通过**；阶段总耗时 0.536 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 执行 | `POST /surveys/6ad4249c2930a45aebbe6f4e/questions` | 400 | {"code": 4001, "msg": "type：缺少必填字段"} |

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

**通过**；阶段总耗时 0.523 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 执行 | `POST /surveys/6ad4249d2930a45aebbe6f53/questions` | 400 | {"code": 4001, "msg": "type：不支持的取值"} |

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

**通过**；阶段总耗时 0.554 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 执行 | `POST /surveys/6ad4249d2930a45aebbe6f58/questions` | 400 | {"code": 4001, "msg": "选择题至少需要两个选项"} |

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

**通过**；阶段总耗时 0.540 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 执行 | `POST /surveys/6ad4249e2930a45aebbe6f5e/questions` | 400 | {"code": 4001, "msg": "选择题至少需要两个选项"} |

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

**通过**；阶段总耗时 0.590 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 执行 | `POST /surveys/6ad4249f2930a45aebbe6f65/questions` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Questions 记录数 | 1 | 1 | 符合 |
| 题型 | "single" | "single" | 符合 |
| 题目顺序 | 1 | 1 | 符合 |
| 默认非必答 | false | false | 符合 |
| 选项数量 | 2 | 2 | 符合 |
| 新选项 ID 有效 | true | true | 符合 |
| Questions.form_id | "6ad4249f2930a45aebbe6f65" | "6ad4249f2930a45aebbe6f65" | 符合 |

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

**通过**；阶段总耗时 0.528 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 执行 | `POST /surveys/6ad4249f2930a45aebbe6f6d/questions` | 400 | {"code": 4001, "msg": "最小限制不能大于最大限制"} |

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

**通过**；阶段总耗时 0.558 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 执行 | `POST /surveys/6ad424a02930a45aebbe6f73/questions` | 400 | {"code": 4001, "msg": "数字范围内不存在符合整数限制的答案"} |

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

**通过**；阶段总耗时 0.536 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 执行 | `POST /surveys/6ad424a02930a45aebbe6f79/questions` | 403 | {"code": 4030, "msg": "无权限"} |

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

**通过**；阶段总耗时 0.548 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424a12930a45aebbe6f7e/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424a12930a45aebbe6f7e/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/6ad424a12930a45aebbe6f7e/questions` | 409 | {"code": 4090, "msg": "发布后不能修改问卷"} |

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

**通过**；阶段总耗时 0.568 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424a12930a45aebbe6f84/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424a12930a45aebbe6f84/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ad424a12930a45aebbe6f84/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `PATCH /surveys/6ad424a12930a45aebbe6f84/questions/6ad424a12930a45aebbe6f85` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ad424a12930a45aebbe6f84/publish` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 执行 | `POST /surveys/access/HUfkir8NHFX2UD3rkMmfqsHZwifiAsuRwbatLADklug/progress` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 下一题 | "6ad424a12930a45aebbe6f8a" | "6ad424a12930a45aebbe6f8a" | 符合 |
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

**通过**；阶段总耗时 0.601 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424a22930a45aebbe6f8f/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424a22930a45aebbe6f8f/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ad424a22930a45aebbe6f8f/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `PATCH /surveys/6ad424a22930a45aebbe6f8f/questions/6ad424a22930a45aebbe6f90` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ad424a22930a45aebbe6f8f/publish` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 执行 | `POST /surveys/access/TRhrV6KIGj4-FiLIsjVAWFzzQSMOfO9KuX-1Nsof3wE/progress` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 下一题 | "6ad424a22930a45aebbe6f94" | "6ad424a22930a45aebbe6f94" | 符合 |
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

**通过**；阶段总耗时 0.584 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424a22930a45aebbe6f9a/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424a22930a45aebbe6f9a/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ad424a22930a45aebbe6f9a/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `PATCH /surveys/6ad424a22930a45aebbe6f9a/questions/6ad424a22930a45aebbe6f9b` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ad424a22930a45aebbe6f9a/publish` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 执行 | `POST /surveys/access/05dF04m-ZAfotIx3n7Fm6ChQGIRJUdmoJT-Bl9suHKk/progress` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 下一题 | "6ad424a22930a45aebbe6fa0" | "6ad424a22930a45aebbe6fa0" | 符合 |
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

**通过**；阶段总耗时 0.591 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424a32930a45aebbe6fa5/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424a32930a45aebbe6fa5/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ad424a32930a45aebbe6fa5/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `PATCH /surveys/6ad424a32930a45aebbe6fa5/questions/6ad424a32930a45aebbe6fa6` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ad424a32930a45aebbe6fa5/publish` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 执行 | `POST /surveys/access/sEtsrUmDd6aZhegYIwA7T7yLsa3ktXKt7_2bcfwL6Ts/progress` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 下一题 | "6ad424a32930a45aebbe6faa" | "6ad424a32930a45aebbe6faa" | 符合 |
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

**通过**；阶段总耗时 0.608 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424a42930a45aebbe6fb0/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424a42930a45aebbe6fb0/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ad424a42930a45aebbe6fb0/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `PATCH /surveys/6ad424a42930a45aebbe6fb0/questions/6ad424a42930a45aebbe6fb1` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ad424a42930a45aebbe6fb0/publish` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 执行 | `POST /surveys/access/KFNUNlFXXvrj5UG-8jd6tXBz-tJJID9VXW0GaRNi4IQ/progress` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 下一题 | "6ad424a42930a45aebbe6fb5" | "6ad424a42930a45aebbe6fb5" | 符合 |
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

**通过**；阶段总耗时 0.588 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424a42930a45aebbe6fbb/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424a42930a45aebbe6fbb/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ad424a42930a45aebbe6fbb/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `PATCH /surveys/6ad424a42930a45aebbe6fbb/questions/6ad424a42930a45aebbe6fbc` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ad424a42930a45aebbe6fbb/publish` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 执行 | `POST /surveys/access/0eKYZhppp0rXPmbjD8HETNM8XrxrutM21VsLq_5emek/progress` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 下一题 | "6ad424a42930a45aebbe6fbe" | "6ad424a42930a45aebbe6fbe" | 符合 |
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

**通过**；阶段总耗时 0.573 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424a52930a45aebbe6fc3/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424a52930a45aebbe6fc3/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ad424a52930a45aebbe6fc3/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `PATCH /surveys/6ad424a52930a45aebbe6fc3/questions/6ad424a52930a45aebbe6fc4` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ad424a52930a45aebbe6fc3/publish` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 执行 | `POST /surveys/access/qIdf2ehIAsTQ0MGJqxhwwFAQI7gitPhUe3xdza0UsjM/progress` | 200 | {"code": 0, "msg": "ok"} |

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

**通过**；阶段总耗时 0.574 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424a52930a45aebbe6fcb/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424a52930a45aebbe6fcb/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ad424a52930a45aebbe6fcb/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `PATCH /surveys/6ad424a52930a45aebbe6fcb/questions/6ad424a52930a45aebbe6fcc` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ad424a52930a45aebbe6fcb/publish` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 执行 | `POST /surveys/access/XY_3-L7XqFXDmxb5HcNBpghUl1VVrcVAsOz2y781YFU/progress` | 200 | {"code": 0, "msg": "ok"} |

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

**通过**；阶段总耗时 0.641 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424a62930a45aebbe6fd3/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424a62930a45aebbe6fd3/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ad424a62930a45aebbe6fd3/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ad424a62930a45aebbe6fd7/questions` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 执行 | `PATCH /surveys/6ad424a62930a45aebbe6fd3/questions/6ad424a62930a45aebbe6fd4` | 400 | {"code": 4001, "msg": "只能跳转到后续题目或 end"} |

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

**通过**；阶段总耗时 0.609 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424a72930a45aebbe6fde/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424a72930a45aebbe6fde/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ad424a72930a45aebbe6fde/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ad424a72930a45aebbe6fe2/questions` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 执行 | `PATCH /surveys/6ad424a72930a45aebbe6fde/questions/6ad424a72930a45aebbe6fe0` | 400 | {"code": 4001, "msg": "只能跳转到后续题目或 end"} |

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

**通过**；阶段总耗时 0.571 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424a72930a45aebbe6fe9/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424a72930a45aebbe6fe9/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ad424a72930a45aebbe6fe9/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ad424a72930a45aebbe6fed/questions` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 执行 | `PATCH /surveys/6ad424a72930a45aebbe6fe9/questions/6ad424a72930a45aebbe6fea` | 400 | {"code": 4001, "msg": "跳转目标不存在或不属于当前问卷"} |

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

**通过**；阶段总耗时 0.565 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424a82930a45aebbe6ff4/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424a82930a45aebbe6ff4/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ad424a82930a45aebbe6ff4/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ad424a82930a45aebbe6ff8/questions` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 执行 | `PATCH /surveys/6ad424a82930a45aebbe6ff4/questions/6ad424a82930a45aebbe6ff5` | 400 | {"code": 4001, "msg": "跳转目标不存在或不属于当前问卷"} |

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

**通过**；阶段总耗时 0.573 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424a82930a45aebbe6fff/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424a82930a45aebbe6fff/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ad424a82930a45aebbe6fff/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ad424a82930a45aebbe7003/questions` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 执行 | `PATCH /surveys/6ad424a82930a45aebbe6fff/questions/6ad424a82930a45aebbe7000` | 400 | {"code": 4001, "msg": "同一题的跳转规则必须互斥"} |

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

**通过**；阶段总耗时 0.616 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424a92930a45aebbe700a/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424a92930a45aebbe700a/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ad424a92930a45aebbe700a/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `PATCH /surveys/6ad424a92930a45aebbe700a/questions/6ad424a92930a45aebbe700b` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ad424a92930a45aebbe700a/publish` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 执行 | `POST /surveys/access/Uespl1ti72tYlvBIR7_BlfmSY3oKVWkwNKvbI7Lxp8E/progress` | 200 | {"code": 0, "msg": "ok"} |
| 26 | 执行 | `POST /surveys/access/Uespl1ti72tYlvBIR7_BlfmSY3oKVWkwNKvbI7Lxp8E/submit` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 清除跳过题目 | ["6ad424a92930a45aebbe700f"] | ["6ad424a92930a45aebbe700f"] | 符合 |
| 实际路径答案 | [{"question_id": "6ad424a92930a45aebbe700b", "value": "6ad424a92930a45aebbe700c"}, {"question_id": "6ad424a92930a45aebbe7010", "value": "末题答案"}] | [{"question_id": "6ad424a92930a45aebbe700b", "value": "6ad424a92930a45aebbe700c"}, {"question_id": "6ad424a92930a45aebbe7010", "value": "末题答案"}] | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |
| Responses.answers | [{"question_id": "6ad424a92930a45aebbe700b", "value": "6ad424a92930a45aebbe700c"}, {"question_id": "6ad424a92930a45aebbe7010", "value": "末题答案"}] | [{"question_id": "6ad424a92930a45aebbe700b", "value": "6ad424a92930a45aebbe700c"}, {"question_id": "6ad424a92930a45aebbe7010", "value": "末题答案"}] | 符合 |

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

**通过**；阶段总耗时 0.610 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424aa2930a45aebbe7016/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424aa2930a45aebbe7016/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ad424aa2930a45aebbe7016/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `PATCH /surveys/6ad424aa2930a45aebbe7016/questions/6ad424aa2930a45aebbe7017` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ad424aa2930a45aebbe7016/publish` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 执行 | `POST /surveys/access/DRVkow8e3lFhCvcMbyKUbAcGoB2YVhtMV03k3rD-fgE/progress` | 200 | {"code": 0, "msg": "ok"} |
| 25 | 执行 | `POST /surveys/access/DRVkow8e3lFhCvcMbyKUbAcGoB2YVhtMV03k3rD-fgE/progress` | 200 | {"code": 0, "msg": "ok"} |
| 30 | 执行 | `POST /surveys/access/DRVkow8e3lFhCvcMbyKUbAcGoB2YVhtMV03k3rD-fgE/submit` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 修改前经过三题 | 3 | 3 | 符合 |
| 清除跳过题目 | ["6ad424aa2930a45aebbe701b"] | ["6ad424aa2930a45aebbe701b"] | 符合 |
| 实际路径答案 | [{"question_id": "6ad424aa2930a45aebbe7017", "value": "6ad424aa2930a45aebbe7018"}, {"question_id": "6ad424aa2930a45aebbe701c", "value": "末题答案"}] | [{"question_id": "6ad424aa2930a45aebbe7017", "value": "6ad424aa2930a45aebbe7018"}, {"question_id": "6ad424aa2930a45aebbe701c", "value": "末题答案"}] | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |
| Responses.answers | [{"question_id": "6ad424aa2930a45aebbe7017", "value": "6ad424aa2930a45aebbe7018"}, {"question_id": "6ad424aa2930a45aebbe701c", "value": "末题答案"}] | [{"question_id": "6ad424aa2930a45aebbe7017", "value": "6ad424aa2930a45aebbe7018"}, {"question_id": "6ad424aa2930a45aebbe701c", "value": "末题答案"}] | 符合 |


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

**通过**；阶段总耗时 0.578 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424aa2930a45aebbe7022/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424aa2930a45aebbe7022/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/Zdk-abF_e3TkX8YsPbxuz4gJd3R9I_KrulvZQgdojWo/progress` | 400 | {"code": 4001, "msg": "第 1 题：该题为必答题"} |
| 17 | 执行 | `POST /surveys/access/Zdk-abF_e3TkX8YsPbxuz4gJd3R9I_KrulvZQgdojWo/submit` | 400 | {"code": 4001, "msg": "第 1 题：该题为必答题"} |

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

**通过**；阶段总耗时 0.585 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424ab2930a45aebbe7028/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424ab2930a45aebbe7028/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/xA4rXUBdQ1ZSSSHoKh1pQ14WTxQvlmWHGvc6BhCjp9k/progress` | 400 | {"code": 4001, "msg": "第 1 题：该题为必答题"} |
| 17 | 执行 | `POST /surveys/access/xA4rXUBdQ1ZSSSHoKh1pQ14WTxQvlmWHGvc6BhCjp9k/submit` | 400 | {"code": 4001, "msg": "第 1 题：该题为必答题"} |

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

**通过**；阶段总耗时 0.604 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424ab2930a45aebbe702e/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424ab2930a45aebbe702e/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/FTlkaDcw2vdBl0pnPmLHPyNe5HfIOClPHd1rd-KXkEg/progress` | 400 | {"code": 4001, "msg": "第 1 题：该题为必答题"} |
| 17 | 执行 | `POST /surveys/access/FTlkaDcw2vdBl0pnPmLHPyNe5HfIOClPHd1rd-KXkEg/submit` | 400 | {"code": 4001, "msg": "第 1 题：该题为必答题"} |

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

**通过**；阶段总耗时 0.584 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424ac2930a45aebbe7034/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424ac2930a45aebbe7034/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/f8uSA51ZYt8bUJ4RrDIXSNoHPZvuI1SwFGC_N6Eeow4/progress` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/f8uSA51ZYt8bUJ4RrDIXSNoHPZvuI1SwFGC_N6Eeow4/submit` | 200 | {"code": 0, "msg": "ok"} |

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

**通过**；阶段总耗时 0.546 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424ac2930a45aebbe703b/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424ac2930a45aebbe703b/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/i4U7jYhwlog4zXd8zbDSQTBezvnT9a9dSnGtwyHuT3o/progress` | 400 | {"code": 4001, "msg": "第 1 题：该题为必答题"} |
| 17 | 执行 | `POST /surveys/access/i4U7jYhwlog4zXd8zbDSQTBezvnT9a9dSnGtwyHuT3o/submit` | 400 | {"code": 4001, "msg": "第 1 题：该题为必答题"} |

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

**通过**；阶段总耗时 0.577 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424ad2930a45aebbe7044/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424ad2930a45aebbe7044/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/twjBpUmdaNq00WDXlAhZLOucBMwAP5pFEsQePnAIlZA/progress` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/twjBpUmdaNq00WDXlAhZLOucBMwAP5pFEsQePnAIlZA/submit` | 200 | {"code": 0, "msg": "ok"} |

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

**通过**；阶段总耗时 0.570 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424ae2930a45aebbe704e/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424ae2930a45aebbe704e/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/nh2omL863zj7vLHgOvza5yWf_3o4_UFXFUFHchtc7_w/progress` | 400 | {"code": 4001, "msg": "第 1 题：不能重复选择同一选项"} |
| 17 | 执行 | `POST /surveys/access/nh2omL863zj7vLHgOvza5yWf_3o4_UFXFUFHchtc7_w/submit` | 400 | {"code": 4001, "msg": "第 1 题：不能重复选择同一选项"} |

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

**通过**；阶段总耗时 0.566 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424ae2930a45aebbe7057/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424ae2930a45aebbe7057/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/03wkUQJ-O9kLKdurvkg2R7kCOr9kf02qPWLgQgWQNZw/progress` | 400 | {"code": 4001, "msg": "第 1 题：选项不存在"} |
| 17 | 执行 | `POST /surveys/access/03wkUQJ-O9kLKdurvkg2R7kCOr9kf02qPWLgQgWQNZw/submit` | 400 | {"code": 4001, "msg": "第 1 题：选项不存在"} |

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

**通过**；阶段总耗时 0.551 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424af2930a45aebbe7060/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424af2930a45aebbe7060/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/mLWyaj6KsQqy8QU_IefEKTHeQ3xGVHwhFr7yamt2iHM/progress` | 400 | {"code": 4001, "msg": "第 1 题：选项不存在"} |
| 17 | 执行 | `POST /surveys/access/mLWyaj6KsQqy8QU_IefEKTHeQ3xGVHwhFr7yamt2iHM/submit` | 400 | {"code": 4001, "msg": "第 1 题：选项不存在"} |

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

**通过**；阶段总耗时 0.545 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424af2930a45aebbe7069/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424af2930a45aebbe7069/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/M9_HerZ7zProKAj6IggZUC_OtXihgf45LiGlGgtsJpY/progress` | 400 | {"code": 4001, "msg": "第 1 题：文本答案必须为字符串"} |
| 17 | 执行 | `POST /surveys/access/M9_HerZ7zProKAj6IggZUC_OtXihgf45LiGlGgtsJpY/submit` | 400 | {"code": 4001, "msg": "第 1 题：文本答案必须为字符串"} |

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

**通过**；阶段总耗时 0.555 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424b02930a45aebbe706f/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424b02930a45aebbe706f/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/SIlTPy28a9Fd6X0YY0ZVHQSksAOeiJlMGaSkNppAgr4/progress` | 400 | {"code": 4001, "msg": "第 1 题：至少选择 2 项"} |
| 17 | 执行 | `POST /surveys/access/SIlTPy28a9Fd6X0YY0ZVHQSksAOeiJlMGaSkNppAgr4/submit` | 400 | {"code": 4001, "msg": "第 1 题：至少选择 2 项"} |

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

**通过**；阶段总耗时 0.597 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424b02930a45aebbe7078/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424b02930a45aebbe7078/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/4tSt9G7yZXcq-1U9qhVwJvE9LjRe6nPajDve22rbqK8/progress` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/4tSt9G7yZXcq-1U9qhVwJvE9LjRe6nPajDve22rbqK8/submit` | 200 | {"code": 0, "msg": "ok"} |

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

**通过**；阶段总耗时 0.584 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424b12930a45aebbe7082/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424b12930a45aebbe7082/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/X2PdkfoBKIMPDbJ1Os85BvYuvhUduiJ2SiEjJovfYrU/progress` | 400 | {"code": 4001, "msg": "第 1 题：最多选择 2 项"} |
| 17 | 执行 | `POST /surveys/access/X2PdkfoBKIMPDbJ1Os85BvYuvhUduiJ2SiEjJovfYrU/submit` | 400 | {"code": 4001, "msg": "第 1 题：最多选择 2 项"} |

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

**通过**；阶段总耗时 0.556 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424b22930a45aebbe708b/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424b22930a45aebbe708b/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/fQbNTQC9YDYxVO7UiQZ_X2B2Pp_3-bmlpqgUVIDr6xw/progress` | 400 | {"code": 4001, "msg": "第 1 题：至少填写 2 个字符"} |
| 17 | 执行 | `POST /surveys/access/fQbNTQC9YDYxVO7UiQZ_X2B2Pp_3-bmlpqgUVIDr6xw/submit` | 400 | {"code": 4001, "msg": "第 1 题：至少填写 2 个字符"} |

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

**通过**；阶段总耗时 0.595 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424b22930a45aebbe7091/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424b22930a45aebbe7091/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/9m4T1BTj1KZ7XQ9cVvWBNo8nxdKfcjhgJnXIOvjJ-s4/progress` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/9m4T1BTj1KZ7XQ9cVvWBNo8nxdKfcjhgJnXIOvjJ-s4/submit` | 200 | {"code": 0, "msg": "ok"} |

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

**通过**；阶段总耗时 0.560 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424b32930a45aebbe7098/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424b32930a45aebbe7098/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/-UE3RyFAXvouhh-TOf7-PDSrEuJMT3c9ELWAuaaenZQ/progress` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/-UE3RyFAXvouhh-TOf7-PDSrEuJMT3c9ELWAuaaenZQ/submit` | 200 | {"code": 0, "msg": "ok"} |

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

**通过**；阶段总耗时 0.554 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424b32930a45aebbe709f/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424b32930a45aebbe709f/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/QavwRrpaCNxDRVW7wl5IZ_pqImqc65ALtRr4sVy3-zE/progress` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/QavwRrpaCNxDRVW7wl5IZ_pqImqc65ALtRr4sVy3-zE/submit` | 200 | {"code": 0, "msg": "ok"} |

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

**通过**；阶段总耗时 0.583 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424b42930a45aebbe70a6/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424b42930a45aebbe70a6/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/ern6G-FQOc6h7ZlwtIaXVky3WB4g_Ajqho0oGe7uJ-g/progress` | 400 | {"code": 4001, "msg": "第 1 题：最多填写 10 个字符"} |
| 17 | 执行 | `POST /surveys/access/ern6G-FQOc6h7ZlwtIaXVky3WB4g_Ajqho0oGe7uJ-g/submit` | 400 | {"code": 4001, "msg": "第 1 题：最多填写 10 个字符"} |

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

**通过**；阶段总耗时 0.583 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424b42930a45aebbe70ac/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424b42930a45aebbe70ac/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/NJikGFdLQltrPICpFSbhM9_wStPQX2x5BhtJW5ZA2YM/progress` | 400 | {"code": 4001, "msg": "第 1 题：数值不能小于 0"} |
| 17 | 执行 | `POST /surveys/access/NJikGFdLQltrPICpFSbhM9_wStPQX2x5BhtJW5ZA2YM/submit` | 400 | {"code": 4001, "msg": "第 1 题：数值不能小于 0"} |

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

**通过**；阶段总耗时 0.599 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424b52930a45aebbe70b2/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424b52930a45aebbe70b2/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/MYqjSQ1iFfzTyF-k7wgQD8ZRsVGqe8Mi4V1OdvinRaI/progress` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/MYqjSQ1iFfzTyF-k7wgQD8ZRsVGqe8Mi4V1OdvinRaI/submit` | 200 | {"code": 0, "msg": "ok"} |

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

**通过**；阶段总耗时 0.563 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424b62930a45aebbe70b9/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424b62930a45aebbe70b9/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/CzWxJ9ch4E8weD6ksaChhQCmsk54Gfznc80HL1UmB7g/progress` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/CzWxJ9ch4E8weD6ksaChhQCmsk54Gfznc80HL1UmB7g/submit` | 200 | {"code": 0, "msg": "ok"} |

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

**通过**；阶段总耗时 0.546 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424b62930a45aebbe70c0/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424b62930a45aebbe70c0/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/xVTJlQT0eX0BwwH94zXkFh0-KYLi_oMon-wYkg0AauA/progress` | 400 | {"code": 4001, "msg": "第 1 题：数值不能大于 10"} |
| 17 | 执行 | `POST /surveys/access/xVTJlQT0eX0BwwH94zXkFh0-KYLi_oMon-wYkg0AauA/submit` | 400 | {"code": 4001, "msg": "第 1 题：数值不能大于 10"} |

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

**通过**；阶段总耗时 0.622 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424b72930a45aebbe70c6/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424b72930a45aebbe70c6/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/Hoxp-G2iP5Tc-bWHZLwLWg7dGwcHmwXKC_NHySF2f6I/progress` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/Hoxp-G2iP5Tc-bWHZLwLWg7dGwcHmwXKC_NHySF2f6I/submit` | 200 | {"code": 0, "msg": "ok"} |

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

**通过**；阶段总耗时 0.585 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424b72930a45aebbe70cd/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424b72930a45aebbe70cd/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/AVioCuu4ep79u1RC9BoWEprTM9zqA7TMLFqTZJbMY6s/progress` | 400 | {"code": 4001, "msg": "第 1 题：必须填写整数"} |
| 17 | 执行 | `POST /surveys/access/AVioCuu4ep79u1RC9BoWEprTM9zqA7TMLFqTZJbMY6s/submit` | 400 | {"code": 4001, "msg": "第 1 题：必须填写整数"} |

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

**通过**；阶段总耗时 0.546 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424b82930a45aebbe70d3/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424b82930a45aebbe70d3/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/IRzkeJkFRzXo9Y7KwAhH8rl-jQoA7OvhEycQukc3k9U/progress` | 400 | {"code": 4001, "msg": "第 1 题：数字限制和跳转阈值必须是有限数字"} |
| 17 | 执行 | `POST /surveys/access/IRzkeJkFRzXo9Y7KwAhH8rl-jQoA7OvhEycQukc3k9U/submit` | 400 | {"code": 4001, "msg": "第 1 题：数字限制和跳转阈值必须是有限数字"} |

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

**通过**；阶段总耗时 0.564 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424b82930a45aebbe70d9/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424b82930a45aebbe70d9/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/8kBDfhSrrYzz3jkwBD6am19JMHNtJ0GThblkPBdBktE/progress` | 400 | {"code": 4001, "msg": "第 1 题：数字限制和跳转阈值必须是有限数字"} |
| 17 | 执行 | `POST /surveys/access/8kBDfhSrrYzz3jkwBD6am19JMHNtJ0GThblkPBdBktE/submit` | 400 | {"code": 4001, "msg": "第 1 题：数字限制和跳转阈值必须是有限数字"} |

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

**通过**；阶段总耗时 0.591 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424b92930a45aebbe70df/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424b92930a45aebbe70df/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/xO-6jo5P2KkwmzKfEYKqHk1enkQ9Avz-eswinf4xaDs/submit` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |
| 提交输出字段 | ["response_id", "submitted_at"] | ["response_id", "submitted_at"] | 符合 |
| Responses.answers | [{"question_id": "6ad424b92930a45aebbe70e0", "value": "第一份"}] | [{"question_id": "6ad424b92930a45aebbe70e0", "value": "第一份"}] | 符合 |
| Responses.is_anonymous | false | false | 符合 |
| Responses.respondent_id | "6ad424b92930a45aebbe70de" | "6ad424b92930a45aebbe70de" | 符合 |

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

**通过**；阶段总耗时 0.554 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424ba2930a45aebbe70e6/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424ba2930a45aebbe70e6/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/GYeGDchBRwh6PDwY89OrBDKq_Re8j7gVekjviPKyn2c/submit` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |
| 提交输出字段 | ["response_id", "submitted_at"] | ["response_id", "submitted_at"] | 符合 |
| Responses.answers | [{"question_id": "6ad424ba2930a45aebbe70e7", "value": "第一份"}] | [{"question_id": "6ad424ba2930a45aebbe70e7", "value": "第一份"}] | 符合 |
| Responses.is_anonymous | true | true | 符合 |
| Responses.respondent_id | "6ad424ba2930a45aebbe70e5" | "6ad424ba2930a45aebbe70e5" | 符合 |

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

**通过**；阶段总耗时 0.598 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424ba2930a45aebbe70ed/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424ba2930a45aebbe70ed/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/CJrjdjcZzukenAbPpNVaFRFDsv9fZbAAr3ymJ9Bl1ws/submit` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/CJrjdjcZzukenAbPpNVaFRFDsv9fZbAAr3ymJ9Bl1ws/submit` | 409 | {"code": 4090, "msg": "该问卷不允许重复提交"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |
| 提交输出字段 | ["response_id", "submitted_at"] | ["response_id", "submitted_at"] | 符合 |
| Responses.answers | [{"question_id": "6ad424ba2930a45aebbe70ee", "value": "第一份"}] | [{"question_id": "6ad424ba2930a45aebbe70ee", "value": "第一份"}] | 符合 |
| Responses.is_anonymous | false | false | 符合 |
| Responses.respondent_id | "6ad424ba2930a45aebbe70ec" | "6ad424ba2930a45aebbe70ec" | 符合 |

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

**通过**；阶段总耗时 0.581 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424bb2930a45aebbe70f4/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424bb2930a45aebbe70f4/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/X0cRFR9QBWpL3kf9CBlQ9fLCFciAE9nCOMDQiHHcgwU/submit` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/X0cRFR9QBWpL3kf9CBlQ9fLCFciAE9nCOMDQiHHcgwU/submit` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 再次填写生成不同提交 ID | true | true | 符合 |
| Responses 记录数 | 2 | 2 | 符合 |
| 提交输出字段 | ["response_id", "submitted_at"] | ["response_id", "submitted_at"] | 符合 |
| Responses.answers | [{"question_id": "6ad424bb2930a45aebbe70f5", "value": "第一份"}] | [{"question_id": "6ad424bb2930a45aebbe70f5", "value": "第一份"}] | 符合 |
| Responses.is_anonymous | false | false | 符合 |
| Responses.respondent_id | "6ad424bb2930a45aebbe70f3" | "6ad424bb2930a45aebbe70f3" | 符合 |

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

**通过**；阶段总耗时 0.592 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424bb2930a45aebbe70fc/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424bb2930a45aebbe70fc/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/3vm2pTlImKYc7xDF3LVptz6iDEB5REgyGflTHxL977A/submit` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/3vm2pTlImKYc7xDF3LVptz6iDEB5REgyGflTHxL977A/submit` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 幂等响应完全相同 | {"response_id": "6ad424bb2930a45aebbe70fe", "submitted_at": "2100-01-01T00:00:00+00:00"} | {"response_id": "6ad424bb2930a45aebbe70fe", "submitted_at": "2100-01-01T00:00:00+00:00"} | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |
| 提交输出字段 | ["response_id", "submitted_at"] | ["response_id", "submitted_at"] | 符合 |
| Responses.answers | [{"question_id": "6ad424bb2930a45aebbe70fd", "value": "第一份"}] | [{"question_id": "6ad424bb2930a45aebbe70fd", "value": "第一份"}] | 符合 |
| Responses.is_anonymous | false | false | 符合 |
| Responses.respondent_id | "6ad424bb2930a45aebbe70fb" | "6ad424bb2930a45aebbe70fb" | 符合 |

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

**通过**；阶段总耗时 0.556 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424bc2930a45aebbe7103/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424bc2930a45aebbe7103/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/qTiAhtZWrvaBIhu-UJYW4vfotWLSCIod3AJJHAHQC9s/submit` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/qTiAhtZWrvaBIhu-UJYW4vfotWLSCIod3AJJHAHQC9s/submit` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 幂等响应完全相同 | {"response_id": "6ad424bc2930a45aebbe7105", "submitted_at": "2100-01-01T00:00:00+00:00"} | {"response_id": "6ad424bc2930a45aebbe7105", "submitted_at": "2100-01-01T00:00:00+00:00"} | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |
| 提交输出字段 | ["response_id", "submitted_at"] | ["response_id", "submitted_at"] | 符合 |
| Responses.answers | [{"question_id": "6ad424bc2930a45aebbe7104", "value": "第一份"}] | [{"question_id": "6ad424bc2930a45aebbe7104", "value": "第一份"}] | 符合 |
| Responses.is_anonymous | false | false | 符合 |
| Responses.respondent_id | "6ad424bc2930a45aebbe7102" | "6ad424bc2930a45aebbe7102" | 符合 |

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

**通过**；阶段总耗时 0.554 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424bd2930a45aebbe710a/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424bd2930a45aebbe710a/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/qSzRLxdkCOW7Hs8kUOijAeva7nEqP4yChrArWi47dEU/submit` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/qSzRLxdkCOW7Hs8kUOijAeva7nEqP4yChrArWi47dEU/submit` | 409 | {"code": 4090, "msg": "请求标识已用于其他提交内容"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |
| 提交输出字段 | ["response_id", "submitted_at"] | ["response_id", "submitted_at"] | 符合 |
| Responses.answers | [{"question_id": "6ad424bd2930a45aebbe710b", "value": "第一份"}] | [{"question_id": "6ad424bd2930a45aebbe710b", "value": "第一份"}] | 符合 |
| Responses.is_anonymous | false | false | 符合 |
| Responses.respondent_id | "6ad424bc2930a45aebbe7109" | "6ad424bc2930a45aebbe7109" | 符合 |

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

**通过**；阶段总耗时 0.590 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424bd2930a45aebbe7111/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424bd2930a45aebbe7111/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/NoHTd3fUB-SPmUEzrqTCLrNrtTljcH0bdPtf0cygdAU/submit` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/NoHTd3fUB-SPmUEzrqTCLrNrtTljcH0bdPtf0cygdAU/submit` | 409 | {"code": 4090, "msg": "请求标识已用于其他提交内容"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |
| 提交输出字段 | ["response_id", "submitted_at"] | ["response_id", "submitted_at"] | 符合 |
| Responses.answers | [{"question_id": "6ad424bd2930a45aebbe7112", "value": "第一份"}] | [{"question_id": "6ad424bd2930a45aebbe7112", "value": "第一份"}] | 符合 |
| Responses.is_anonymous | false | false | 符合 |
| Responses.respondent_id | "6ad424bd2930a45aebbe7110" | "6ad424bd2930a45aebbe7110" | 符合 |

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

**通过**；阶段总耗时 0.603 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424be2930a45aebbe7118/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424be2930a45aebbe7118/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/6ad424be2930a45aebbe7118/close` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/RxZ30vbWosUHYv_z9CMzO-kDnQIKyVXeYZbZNNwO17s/submit` | 409 | {"code": 4090, "msg": "问卷已关闭"} |

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

**通过**；阶段总耗时 0.548 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424be2930a45aebbe711e/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `PUT /surveys/6ad424be2930a45aebbe711e/deadline` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ad424be2930a45aebbe711e/publish` | 200 | {"code": 0, "msg": "ok"} |
| 16 | 执行 | `POST /surveys/access/366A1ybybyYfPTUhEbwl-W3Eiq3T334Q9J1XFH2ZE5k/submit` | 409 | {"code": 4090, "msg": "问卷已截止"} |

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

**通过**；阶段总耗时 0.577 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424bf2930a45aebbe7124/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424bf2930a45aebbe7124/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/ihGz0q0dXX_hS6jw1hObMDSPb92RdGcp2CjouvUeS4E/submit` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/6ad424bf2930a45aebbe7124/close` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 执行 | `POST /surveys/access/ihGz0q0dXX_hS6jw1hObMDSPb92RdGcp2CjouvUeS4E/submit` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |
| 关闭或截止后重试返回原结果 | {"response_id": "6ad424bf2930a45aebbe7126", "submitted_at": "2100-01-01T00:00:00+00:00"} | {"response_id": "6ad424bf2930a45aebbe7126", "submitted_at": "2100-01-01T00:00:00+00:00"} | 符合 |

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

**通过**；阶段总耗时 0.565 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424bf2930a45aebbe712b/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `PUT /surveys/6ad424bf2930a45aebbe712b/deadline` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ad424bf2930a45aebbe712b/publish` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/xCeMWmL5K-WGcVucggNTrcXIQBz4HtLe1J-HnvHoUkE/submit` | 200 | {"code": 0, "msg": "ok"} |
| 19 | 执行 | `POST /surveys/access/xCeMWmL5K-WGcVucggNTrcXIQBz4HtLe1J-HnvHoUkE/submit` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| Responses 记录数 | 1 | 1 | 符合 |
| 关闭或截止后重试返回原结果 | {"response_id": "6ad424bf2930a45aebbe712d", "submitted_at": "2100-01-01T00:00:00+00:00"} | {"response_id": "6ad424bf2930a45aebbe712d", "submitted_at": "2100-01-01T00:00:00+00:00"} | 符合 |

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

**通过**；阶段总耗时 0.567 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424c02930a45aebbe7132/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424c02930a45aebbe7132/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/LtigsOLQRwlYVAz0J0tGpePdWFb81fTy-anWcOAi--U/submit` | 200 | {"code": 0, "msg": "ok"} |
| 13 | 执行 | `POST /surveys/access/LtigsOLQRwlYVAz0J0tGpePdWFb81fTy-anWcOAi--U/submit` | 200 | {"code": 0, "msg": "ok"} |

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

**通过**；阶段总耗时 0.629 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424c12930a45aebbe713b/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424c12930a45aebbe713b/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/D0YKtN_0P4UK30awjF2wWxPlsnCi-xv1vkj7FEksMus/submit` | 200 | {"code": 0, "msg": "ok"} |
| 13 | 执行 | `POST /surveys/access/D0YKtN_0P4UK30awjF2wWxPlsnCi-xv1vkj7FEksMus/submit` | 200 | {"code": 0, "msg": "ok"} |
| 14 | 执行 | `POST /surveys/access/D0YKtN_0P4UK30awjF2wWxPlsnCi-xv1vkj7FEksMus/submit` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 并发结果业务码集合 | [0, 0, 0] | [0, 0, 0] | 符合 |
| 并发重试返回同一提交 | {"response_id": "6ad424c12930a45aebbe713d", "submitted_at": "2100-01-01T00:00:00+00:00"} | {"response_id": "6ad424c12930a45aebbe713d", "submitted_at": "2100-01-01T00:00:00+00:00"} | 符合 |
| 并发重试返回同一提交 | {"response_id": "6ad424c12930a45aebbe713d", "submitted_at": "2100-01-01T00:00:00+00:00"} | {"response_id": "6ad424c12930a45aebbe713d", "submitted_at": "2100-01-01T00:00:00+00:00"} | 符合 |
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

**通过**；阶段总耗时 0.583 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424c12930a45aebbe7144/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424c12930a45aebbe7144/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/HXkhf10giWl5NSmtTrzO-laXnLwbGSR9IVx1Lmjy4Mo/submit` | 409 | {"code": 4090, "msg": "该问卷不允许重复提交"} |
| 13 | 执行 | `POST /surveys/access/HXkhf10giWl5NSmtTrzO-laXnLwbGSR9IVx1Lmjy4Mo/submit` | 409 | {"code": 4090, "msg": "该问卷不允许重复提交"} |
| 14 | 执行 | `POST /surveys/access/HXkhf10giWl5NSmtTrzO-laXnLwbGSR9IVx1Lmjy4Mo/submit` | 200 | {"code": 0, "msg": "ok"} |

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

**通过**；阶段总耗时 0.591 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424c22930a45aebbe714d/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424c22930a45aebbe714d/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 执行 | `POST /surveys/access/chuWNeIuVwPOsKf7Xv4wfY98mltvxadRM-mHibtoyJY/submit` | 409 | {"code": 4090, "msg": "问卷已关闭"} |
| 15 | 执行 | `POST /surveys/6ad424c22930a45aebbe714d/close` | 200 | {"code": 0, "msg": "ok"} |

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

**通过**；阶段总耗时 0.600 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424c22930a45aebbe7154/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `PUT /surveys/6ad424c22930a45aebbe7154/deadline` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ad424c22930a45aebbe7154/publish` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `POST /surveys/access/ERneDV9YqR8JTAo4Kseot40RZuoV3MPa1jmWQd3jeUk/submit` | 409 | {"code": 4090, "msg": "问卷已截止"} |

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

**通过**；阶段总耗时 0.633 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424c32930a45aebbe715b/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424c32930a45aebbe715b/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ad424c32930a45aebbe715b/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `POST /surveys/6ad424c32930a45aebbe715b/questions` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 准备 | `POST /surveys/6ad424c32930a45aebbe715b/publish` | 200 | {"code": 0, "msg": "ok"} |
| 21 | 准备 | `POST /surveys/access/5w1i9V5YgrglHgKaNK0e7YHkKbrsYAK4xPORXnti0lM/submit` | 200 | {"code": 0, "msg": "ok"} |
| 24 | 准备 | `POST /surveys/access/5w1i9V5YgrglHgKaNK0e7YHkKbrsYAK4xPORXnti0lM/submit` | 200 | {"code": 0, "msg": "ok"} |
| 27 | 准备 | `POST /surveys/access/5w1i9V5YgrglHgKaNK0e7YHkKbrsYAK4xPORXnti0lM/submit` | 200 | {"code": 0, "msg": "ok"} |
| 30 | 准备 | `POST /surveys/access/5w1i9V5YgrglHgKaNK0e7YHkKbrsYAK4xPORXnti0lM/submit` | 200 | {"code": 0, "msg": "ok"} |
| 33 | 执行 | `GET /surveys/6ad424c32930a45aebbe715b/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 43 | 执行 | `GET /surveys/6ad424c32930a45aebbe715b/questions/6ad424c32930a45aebbe715c/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 47 | 执行 | `GET /surveys/6ad424c32930a45aebbe715b/questions/6ad424c32930a45aebbe7160/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 51 | 执行 | `GET /surveys/6ad424c32930a45aebbe715b/questions/6ad424c32930a45aebbe7164/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 55 | 执行 | `GET /surveys/6ad424c32930a45aebbe715b/questions/6ad424c32930a45aebbe7165/statistics` | 200 | {"code": 0, "msg": "ok"} |

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
| 单题与整卷一致 | {"question_id": "6ad424c32930a45aebbe715c", "order": 1, "type": "single", "title": "验收题目", "answer_count": 3, "options": [{"option_id": "6ad424c32930a45aebbe715d", "text": "A", "count": 2}, {"option_id": "6ad424c32930a45…（完整值见原始 JSON） | {"question_id": "6ad424c32930a45aebbe715c", "order": 1, "type": "single", "title": "验收题目", "answer_count": 3, "options": [{"option_id": "6ad424c32930a45aebbe715d", "text": "A", "count": 2}, {"option_id": "6ad424c32930a45…（完整值见原始 JSON） | 符合 |
| 单题与整卷一致 | {"question_id": "6ad424c32930a45aebbe7160", "order": 2, "type": "multiple", "title": "验收题目", "answer_count": 2, "options": [{"option_id": "6ad424c32930a45aebbe7161", "text": "A", "count": 1}, {"option_id": "6ad424c32930a…（完整值见原始 JSON） | {"question_id": "6ad424c32930a45aebbe7160", "order": 2, "type": "multiple", "title": "验收题目", "answer_count": 2, "options": [{"option_id": "6ad424c32930a45aebbe7161", "text": "A", "count": 1}, {"option_id": "6ad424c32930a…（完整值见原始 JSON） | 符合 |
| 单题与整卷一致 | {"question_id": "6ad424c32930a45aebbe7164", "order": 3, "type": "text", "title": "验收题目", "answer_count": 2, "contents": {"items": [{"value": "重复内容"}, {"value": "重复内容"}], "total": 2, "page": 1, "page_size": 20}} | {"question_id": "6ad424c32930a45aebbe7164", "order": 3, "type": "text", "title": "验收题目", "answer_count": 2, "contents": {"items": [{"value": "重复内容"}, {"value": "重复内容"}], "total": 2, "page": 1, "page_size": 20}} | 符合 |
| 单题与整卷一致 | {"question_id": "6ad424c32930a45aebbe7165", "order": 4, "type": "number", "title": "验收题目", "answer_count": 2, "contents": {"items": [{"value": 0}, {"value": 10}], "total": 2, "page": 1, "page_size": 20}, "average": 5.0} | {"question_id": "6ad424c32930a45aebbe7165", "order": 4, "type": "number", "title": "验收题目", "answer_count": 2, "contents": {"items": [{"value": 0}, {"value": 10}], "total": 2, "page": 1, "page_size": 20}, "average": 5.0} | 符合 |
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

**通过**；阶段总耗时 0.644 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424c42930a45aebbe716d/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424c42930a45aebbe716d/questions` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/6ad424c42930a45aebbe716d/questions` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 准备 | `POST /surveys/6ad424c42930a45aebbe716d/questions` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 执行 | `GET /surveys/6ad424c42930a45aebbe716d/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 24 | 执行 | `GET /surveys/6ad424c42930a45aebbe716d/questions/6ad424c42930a45aebbe716e/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 30 | 执行 | `GET /surveys/6ad424c42930a45aebbe716d/questions/6ad424c42930a45aebbe7172/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 36 | 执行 | `GET /surveys/6ad424c42930a45aebbe716d/questions/6ad424c42930a45aebbe7176/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 42 | 执行 | `GET /surveys/6ad424c42930a45aebbe716d/questions/6ad424c42930a45aebbe7177/statistics` | 200 | {"code": 0, "msg": "ok"} |

| 检查项 | 预期值 | 实际值 | 结果 |
| --- | --- | --- | --- |
| 前置注册登录用户已保存 | ["owner", "reader"] | ["owner", "reader"] | 符合 |
| 无提交时总数 | 0 | 0 | 符合 |
| 空问卷题目回答数 | 0 | 0 | 符合 |
| 全部选项零计数 | [0, 0, 0] | [0, 0, 0] | 符合 |
| 空问卷单题统计一致 | {"question_id": "6ad424c42930a45aebbe716e", "order": 1, "type": "single", "title": "验收题目", "answer_count": 0, "options": [{"option_id": "6ad424c42930a45aebbe716f", "text": "A", "count": 0}, {"option_id": "6ad424c42930a45…（完整值见原始 JSON） | {"question_id": "6ad424c42930a45aebbe716e", "order": 1, "type": "single", "title": "验收题目", "answer_count": 0, "options": [{"option_id": "6ad424c42930a45aebbe716f", "text": "A", "count": 0}, {"option_id": "6ad424c42930a45…（完整值见原始 JSON） | 符合 |
| 空问卷题目回答数 | 0 | 0 | 符合 |
| 全部选项零计数 | [0, 0, 0] | [0, 0, 0] | 符合 |
| 空问卷单题统计一致 | {"question_id": "6ad424c42930a45aebbe7172", "order": 2, "type": "multiple", "title": "验收题目", "answer_count": 0, "options": [{"option_id": "6ad424c42930a45aebbe7173", "text": "A", "count": 0}, {"option_id": "6ad424c42930a…（完整值见原始 JSON） | {"question_id": "6ad424c42930a45aebbe7172", "order": 2, "type": "multiple", "title": "验收题目", "answer_count": 0, "options": [{"option_id": "6ad424c42930a45aebbe7173", "text": "A", "count": 0}, {"option_id": "6ad424c42930a…（完整值见原始 JSON） | 符合 |
| 空问卷题目回答数 | 0 | 0 | 符合 |
| 空内容列表 | [] | [] | 符合 |
| 空问卷单题统计一致 | {"question_id": "6ad424c42930a45aebbe7176", "order": 3, "type": "text", "title": "验收题目", "answer_count": 0, "contents": {"items": [], "total": 0, "page": 1, "page_size": 20}} | {"question_id": "6ad424c42930a45aebbe7176", "order": 3, "type": "text", "title": "验收题目", "answer_count": 0, "contents": {"items": [], "total": 0, "page": 1, "page_size": 20}} | 符合 |
| 空问卷题目回答数 | 0 | 0 | 符合 |
| 空内容列表 | [] | [] | 符合 |
| 空问卷单题统计一致 | {"question_id": "6ad424c42930a45aebbe7177", "order": 4, "type": "number", "title": "验收题目", "answer_count": 0, "contents": {"items": [], "total": 0, "page": 1, "page_size": 20}, "average": null} | {"question_id": "6ad424c42930a45aebbe7177", "order": 4, "type": "number", "title": "验收题目", "answer_count": 0, "contents": {"items": [], "total": 0, "page": 1, "page_size": 20}, "average": null} | 符合 |
| 空平均值不能为 0 | null | null | 符合 |

### STA-003 text 内容稳定分页与全量汇总

脚本节点：`tests/test_acceptance.py::test_acceptance[STA-003]`

#### 步骤

1. 创建单题问卷并发布。本排序专项直接在测试库插入 27 条符合字段约定的旧格式答卷。
2. 数值为 0..26，文本为“内容0”..“内容26”；每三条时间相同，ID 固定升序，实际逆序插入。
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
  "insertion_order": "逆序；时间升序、ID 升序为预期"
}
```

#### 预期输出

- 整卷仅返回最早 20 条；各页分别有 10、10、7、0 条且顺序稳定，total=27。
- 数字平均值在所有页都为 13，不能只取当前页计算；旧记录缺少幂等字段仍计入。

#### 实际结果

**通过**；阶段总耗时 0.599 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424c42930a45aebbe717c/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424c42930a45aebbe717c/publish` | 200 | {"code": 0, "msg": "ok"} |
| 14 | 执行 | `GET /surveys/6ad424c42930a45aebbe717c/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 执行 | `GET /surveys/6ad424c42930a45aebbe717c/questions/6ad424c42930a45aebbe717d/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 23 | 执行 | `GET /surveys/6ad424c42930a45aebbe717c/questions/6ad424c42930a45aebbe717d/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 28 | 执行 | `GET /surveys/6ad424c42930a45aebbe717c/questions/6ad424c42930a45aebbe717d/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 33 | 执行 | `GET /surveys/6ad424c42930a45aebbe717c/questions/6ad424c42930a45aebbe717d/statistics` | 200 | {"code": 0, "msg": "ok"} |

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
2. 数值为 0..26，文本为“内容0”..“内容26”；每三条时间相同，ID 固定升序，实际逆序插入。
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
  "insertion_order": "逆序；时间升序、ID 升序为预期"
}
```

#### 预期输出

- 整卷仅返回最早 20 条；各页分别有 10、10、7、0 条且顺序稳定，total=27。
- 数字平均值在所有页都为 13，不能只取当前页计算；旧记录缺少幂等字段仍计入。

#### 实际结果

**通过**；阶段总耗时 0.618 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424c52930a45aebbe7182/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424c52930a45aebbe7182/publish` | 200 | {"code": 0, "msg": "ok"} |
| 14 | 执行 | `GET /surveys/6ad424c52930a45aebbe7182/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 执行 | `GET /surveys/6ad424c52930a45aebbe7182/questions/6ad424c52930a45aebbe7183/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 24 | 执行 | `GET /surveys/6ad424c52930a45aebbe7182/questions/6ad424c52930a45aebbe7183/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 30 | 执行 | `GET /surveys/6ad424c52930a45aebbe7182/questions/6ad424c52930a45aebbe7183/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 36 | 执行 | `GET /surveys/6ad424c52930a45aebbe7182/questions/6ad424c52930a45aebbe7183/statistics` | 200 | {"code": 0, "msg": "ok"} |

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

**通过**；阶段总耗时 0.642 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424c62930a45aebbe7188/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424c62930a45aebbe7188/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/access/aW7yL2iGPqzn8o_mJjEYrjlcypAa_NSF1JrjsYIZUb8/submit` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `GET /surveys/6ad424c62930a45aebbe7188/statistics` | 401 | {"code": 4010, "msg": "请先登录"} |
| 19 | 执行 | `GET /surveys/6ad424c62930a45aebbe7188/statistics` | 403 | {"code": 4030, "msg": "无权限"} |
| 23 | 执行 | `GET /surveys/6ad424c62930a45aebbe7188/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 28 | 执行 | `GET /surveys/6ad424c62930a45aebbe7188/questions/6ad424c62930a45aebbe7189/statistics` | 401 | {"code": 4010, "msg": "请先登录"} |
| 32 | 执行 | `GET /surveys/6ad424c62930a45aebbe7188/questions/6ad424c62930a45aebbe7189/statistics` | 403 | {"code": 4030, "msg": "无权限"} |
| 36 | 执行 | `GET /surveys/6ad424c62930a45aebbe7188/questions/6ad424c62930a45aebbe7189/statistics` | 200 | {"code": 0, "msg": "ok"} |

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

**通过**；阶段总耗时 0.609 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424c62930a45aebbe718f/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424c62930a45aebbe718f/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/access/jeWhqq-ZjV_R0AxqjC7l0DZNDx-YpGXu7MCm8-zMA3Y/submit` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `GET /surveys/6ad424c62930a45aebbe718f/statistics` | 401 | {"code": 4010, "msg": "请先登录"} |
| 19 | 执行 | `GET /surveys/6ad424c62930a45aebbe718f/statistics` | 403 | {"code": 4030, "msg": "无权限"} |
| 23 | 执行 | `GET /surveys/6ad424c62930a45aebbe718f/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 28 | 执行 | `GET /surveys/6ad424c62930a45aebbe718f/questions/6ad424c62930a45aebbe7190/statistics` | 401 | {"code": 4010, "msg": "请先登录"} |
| 32 | 执行 | `GET /surveys/6ad424c62930a45aebbe718f/questions/6ad424c62930a45aebbe7190/statistics` | 403 | {"code": 4030, "msg": "无权限"} |
| 36 | 执行 | `GET /surveys/6ad424c62930a45aebbe718f/questions/6ad424c62930a45aebbe7190/statistics` | 200 | {"code": 0, "msg": "ok"} |

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

**通过**；阶段总耗时 0.619 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424c72930a45aebbe7196/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424c72930a45aebbe7196/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/access/t8sdpLeLDm8kt9Yc1socCx0CWWCJ63mj6R9PvphHcKA/submit` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `GET /surveys/6ad424c72930a45aebbe7196/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 执行 | `POST /surveys/access/t8sdpLeLDm8kt9Yc1socCx0CWWCJ63mj6R9PvphHcKA/submit` | 200 | {"code": 0, "msg": "ok"} |
| 24 | 执行 | `GET /surveys/6ad424c72930a45aebbe7196/statistics` | 200 | {"code": 0, "msg": "ok"} |

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

**通过**；阶段总耗时 0.612 秒。

| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |
| ---: | --- | --- | --- | --- |
| 3 | 准备 | `POST /surveys` | 200 | {"code": 0, "msg": "ok"} |
| 6 | 准备 | `POST /surveys/6ad424c72930a45aebbe719e/questions` | 200 | {"code": 0, "msg": "ok"} |
| 9 | 准备 | `POST /surveys/6ad424c72930a45aebbe719e/publish` | 200 | {"code": 0, "msg": "ok"} |
| 12 | 准备 | `POST /surveys/access/__IGbKL9Ys6ckdDWO7AgBjZchFS8z23WpsmSs4kAD0w/submit` | 200 | {"code": 0, "msg": "ok"} |
| 15 | 执行 | `GET /surveys/6ad424c72930a45aebbe719e/questions/6ad424c72930a45aebbe719f/statistics` | 200 | {"code": 0, "msg": "ok"} |
| 18 | 执行 | `POST /surveys/access/__IGbKL9Ys6ckdDWO7AgBjZchFS8z23WpsmSs4kAD0w/submit` | 200 | {"code": 0, "msg": "ok"} |
| 24 | 执行 | `GET /surveys/6ad424c72930a45aebbe719e/questions/6ad424c72930a45aebbe719f/statistics` | 200 | {"code": 0, "msg": "ok"} |

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
