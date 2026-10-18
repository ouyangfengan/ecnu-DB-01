from dataclasses import asdict, dataclass


CATEGORIES = {
    "CRE": "创建问卷测试", "ADD": "添加题目测试", "JMP": "跳转逻辑测试",
    "VAL": "校验测试", "SUB": "提交问卷测试", "STA": "统计测试",
}


@dataclass(frozen=True)
class Case:
    id: str
    category: str
    title: str
    scenario: str
    steps: tuple
    inputs: dict
    expected: tuple
    parameters: dict

    def metadata(self):
        return asdict(self)


CASES = []


def define(prefix, title, scenario, parameters, steps, inputs, expected):
    number = 1 + sum(case.id.startswith(prefix + "-") for case in CASES)
    CASES.append(Case(
        f"{prefix}-{number:03}", CATEGORIES[prefix], title, scenario,
        tuple(steps), inputs, tuple(expected), parameters,
    ))


for title, body, role, code, message in [
    ("正常创建及默认字段", {"title": "  验收问卷  "}, "owner", 0, None),
    ("标题未提供", {}, "owner", 4001, "必填"),
    ("标题为空白", {"title": " \t "}, "owner", 4001, "非空"),
    ("标题长度 199 字", {"title": "问" * 199}, "owner", 0, None),
    ("标题长度 200 字", {"title": "问" * 200}, "owner", 0, None),
    ("标题长度 201 字", {"title": "问" * 201}, "owner", 4001, "长度"),
    ("未登录创建", {"title": "验收问卷"}, None, 4010, "请先登录"),
    ("匿名字段不能用字符串代替布尔值", {"title": "问卷", "allow_anonymous": "true"}, "owner", 4001, "布尔"),
]:
    define("CRE", title, "create",
           {"body": body, "role": role, "code": code, "message": message},
           ["准备 owner、reader 两个账号并登录；未登录场景不携带凭证。",
            "调用 POST /surveys，随后查询本测试库中的 Question_forms。",
            "成功场景核对默认字段、所有者和返回链接；失败场景检查未写入问卷。"],
           {"method": "POST", "path": "/surveys", "role": role, "json": body},
           [f"HTTP {200 if code == 0 else 401 if code == 4010 else 400}，code={code}。",
            "成功时返回合法 form_id 和链接，保存为 draft、默认非匿名且不允许多次填写；失败时问卷数为 0。"])


for kind in ("single", "multiple", "text", "number"):
    body = {"title": "验收题目", "type": kind}
    if kind in ("single", "multiple"):
        body["options"] = [{"text": "A"}, {"text": "B"}, {"text": "C"}]
    define("ADD", f"添加 {kind} 题型", "add", {"body": body, "code": 0},
           ["创建一份草稿问卷。", "调用添加题目接口，再读取题目数据库记录。",
            "检查题型、默认非必答、题目顺序及选择题的服务端选项 ID。"],
           {"method": "POST", "path": "/surveys/<form_id>/questions", "json": body},
           ["HTTP 200、code=0；题目数为 1、order=1、required=false，选项 ID 由服务端生成。"])

for title, body, role, published, code, message in [
    ("题目标题为空", {"title": "", "type": "text"}, "owner", False, 4001, "非空"),
    ("题目缺少题型", {"title": "题目"}, "owner", False, 4001, "必填"),
    ("不支持的题型", {"title": "题目", "type": "matrix"}, "owner", False, 4001, "不支持"),
    ("单选题缺少选项", {"title": "题目", "type": "single"}, "owner", False, 4001, "至少"),
    ("多选题只有一个选项", {"title": "题目", "type": "multiple", "options": [{"text": "A"}]}, "owner", False, 4001, "至少"),
    ("单选题恰好两个选项", {"title": "题目", "type": "single", "options": [{"text": "A"}, {"text": "B"}]}, "owner", False, 0, None),
    ("文本最少长度大于最多长度", {"title": "题目", "type": "text", "validation": {"min_length": 3, "max_length": 1}}, "owner", False, 4001, "最小"),
    ("数字区间内没有合法整数", {"title": "题目", "type": "number", "validation": {"min_value": 0.1, "max_value": 0.9, "integer_only": True}}, "owner", False, 4001, "整数"),
    ("非所有者添加", {"title": "题目", "type": "text"}, "reader", False, 4030, "无权限"),
    ("已发布问卷禁止添加", {"title": "题目", "type": "text"}, "owner", True, 4090, "发布后"),
]:
    define("ADD", title, "add",
           {"body": body, "role": role, "published": published, "code": code, "message": message},
           ["owner 创建草稿；已发布场景先添加一题并发布。", "以指定身份调用添加接口。",
            "读取 Questions 数量和问卷 revision，检查成功写入或失败回滚。"],
           {"method": "POST", "path": "/surveys/<form_id>/questions", "role": role,
            "initial_status": "published" if published else "draft", "json": body},
           [f"code={code}" + (f"，提示包含“{message}”。" if message else "，返回新题目。"),
            "成功新增 1 题；失败不新增题目且 revision 不改变。"])


for kind, value, destination in [
    ("single", "A", "q3"), ("single", "B", "q2"),
    ("multiple", ["B", "A"], "q3"), ("multiple", ["A"], "q2"),
    ("multiple", ["A", "B", "C"], "q2"),
    ("number", 4.9, "q3"), ("number", 5, "end"), ("number", 5.1, "end"),
]:
    condition = (
        [{"condition": {"op": "lt", "value": 5}, "target": "<q3>"},
         {"condition": {"op": "gte", "value": 5}, "target": "end"}]
        if kind == "number" else
        [{"condition": {"op": "eq" if kind == "single" else "exact",
                        "value": "<A>" if kind == "single" else ["<A>", "<B>"]},
          "target": "<q3>"}]
    )
    define("JMP", f"{kind} 输入 {value!r} 跳转至 {destination}", "jump",
           {"kind": kind, "value": value, "destination": destination},
           ["依次创建 q1、必答文本 q2、必答文本 q3；q1 使用指定题型。",
            "PATCH q1 配置输入中列出的跳转规则，然后发布。",
            "POST progress，仅提供 q1 答案，检查下一题或结束标记。"],
           {"configuration": condition, "value": value, "options": "A/B/C 对应 q1 返回的选项 ID",
            "method": "POST", "path": "/surveys/access/<token>/progress",
            "json": {"answers": [{"question_id": "<q1>", "value": value}]}},
           ["HTTP 200、code=0。", f"next_question={destination}；end 时为 null 且 complete=true，否则 complete=false。"])

for invalid in ("self", "backward", "foreign", "missing", "overlap"):
    titles = {"self": "禁止跳向自身", "backward": "禁止向前题跳转", "foreign": "禁止跨问卷目标",
              "missing": "禁止不存在的目标", "overlap": "拒绝在边界 5 重叠的规则"}
    define("JMP", titles[invalid], "invalid_jump", {"invalid": invalid},
           ["创建数字 q1、数字 q2、文本 q3，另建问卷中的一题用于跨问卷场景。",
            "自跳配置 q1→q1；逆向配置 q2→q1；跨卷/不存在使用对应 ID；重叠使用 lte 5 和 gte 5。",
            "PATCH 保存规则并读取原题和 revision，确认失败未修改配置。"],
           {"method": "PATCH", "path": "/surveys/<form_id>/questions/<source_id>",
            "case": invalid, "ordinary_condition": {"op": "eq", "value": 1},
            "overlap_conditions": [{"op": "lte", "value": 5}, {"op": "gte", "value": 5}]},
           ["HTTP 400、code=4001；规则列表仍为空，revision 不变。"])

for change in (False, True):
    define("JMP", "修改答案后清理旧路径" if change else "跳过必答题不误报", "skip_path",
           {"change": change},
           ["建立必答单选 q1、必答文本 q2/q3，配置 q1 选 A 跳到 q3，再发布。",
            "修改场景先用 B、旧答案、末题答案调用 progress，确认经过三题。",
            "发送 q1=A、q2=旧答案、q3=末题答案，检查 progress 后提交并读取保存答案。"],
           {"initial": ["B", "旧答案", "末题答案"] if change else None,
            "updated": ["A", "旧答案", "末题答案"],
            "paths": ["/surveys/access/<token>/progress", "/surveys/access/<token>/submit"]},
           ["两接口均 code=0；discarded_question_ids 仅包含 q2。",
            "保存答案只含 q1、q3，不要求被跳过的必答 q2，也不保存其旧值。"])


validation_rows = [
    ("必答文本空字符串", "text", {"required": True}, "", 4001, "必答"),
    ("必答文本 null", "text", {"required": True}, None, 4001, "必答"),
    ("必答文本纯空白", "text", {"required": True}, " \t ", 4001, "必答"),
    ("选答文本可留空", "text", {}, "", 0, None),
    ("必答多选无最少数仍不能空", "multiple", {"required": True}, [], 4001, "必答"),
    ("必答多选默认选一项有效", "multiple", {"required": True}, ["A"], 0, None),
    ("多选重复选项", "multiple", {}, ["A", "A"], 4001, "重复"),
    ("多选不存在选项", "multiple", {}, ["missing"], 4001, "不存在"),
    ("单选不存在选项", "single", {}, "missing", 4001, "不存在"),
    ("文本不能提交数字", "text", {}, 123, 4001, "字符串"),
]
for count in (1, 2, 3):
    validation_rows.append((
        f"恰好选 2 项：实际 {count} 项", "multiple", {"min_selected": 2, "max_selected": 2},
        ["A", "B", "C"][:count], 0 if count == 2 else 4001, None if count == 2 else ("至少" if count < 2 else "最多"),
    ))
for length in (1, 2, 9, 10, 11):
    validation_rows.append((
        f"文本范围 2-10 字：实际 {length} 字", "text", {"min_length": 2, "max_length": 10},
        "文" * length, 0 if 2 <= length <= 10 else 4001,
        None if 2 <= length <= 10 else ("至少" if length < 2 else "最多"),
    ))
for value in (-1, 0, 10, 11):
    validation_rows.append((
        f"数字范围 [0,10]：实际 {value}", "number", {"min_value": 0, "max_value": 10},
        value, 0 if 0 <= value <= 10 else 4001,
        None if 0 <= value <= 10 else ("小于" if value < 0 else "大于"),
    ))
for value, code in ((1.0, 0), (1.5, 4001), (True, 4001), ("1", 4001)):
    validation_rows.append((
        f"整数数字题输入 {value!r} ({type(value).__name__})", "number", {"integer_only": True},
        value, code, None if not code else ("整数" if value == 1.5 else "有限数字"),
    ))
for title, kind, limits, value, code, message in validation_rows:
    define("VAL", title, "validation",
           {"kind": kind, "limits": limits, "value": value, "code": code, "message": message},
           ["创建指定类型、限制的单题问卷并发布。",
            "以 reader 调用 progress，再绕过客户端直接以相同答案调用 submit。",
            "检查两次响应、提示和 Responses 数量；合法留空不保存空答案项。"],
           {"question": {"title": "验收题目", "type": kind, "validation": limits},
            "value": value, "options": "选择题使用 A/B/C 三项，执行时替换为真实 ID",
            "progress": {"answers": [{"question_id": "<q1>", "value": value}]},
            "submit": {"requestId": "<用例编号>", "answers": [{"question_id": "<q1>", "value": value}]}},
           [f"progress 和 submit 均 code={code}，HTTP {200 if code == 0 else 400}。",
            f"提示包含“{message}”。" if message else "progress 标记完成，提交返回 ID 和时间。",
            f"本次测试 Responses 数量为 {1 if code == 0 else 0}。"])


for mode in ("normal", "repeat", "idempotent", "changed"):
    variants = (False, True) if mode != "normal" else (False, True)
    for flag in variants:
        title = {
            "normal": f"完整提交保存，匿名={flag}",
            "repeat": f"不同 requestId 再次填写，允许多次={flag}",
            "idempotent": f"原样重试返回原记录，允许多次={flag}",
            "changed": f"同标识改变内容冲突，允许多次={flag}",
        }[mode]
        codes = [0] if mode == "normal" else [0, 4090 if mode == "changed" or (mode == "repeat" and not flag) else 0]
        count = 2 if mode == "repeat" and flag else 1
        define("SUB", title, "submission", {"mode": mode, "flag": flag},
               ["创建必答文本题并发布，按场景设置匿名或重复填写开关。",
                "reader 提交“第一份”；normal 到此结束；repeat 换标识，idempotent 原样重试，changed 保持标识但改为“第二份”。",
                "核对 HTTP 响应和数据库记录；幂等重试还检查提交 ID、时间完全相同。"],
               {"method": "POST", "path": "/surveys/access/<token>/submit",
                "mode": mode, "setting": flag,
                "first": {"requestId": "submit-1", "answers": [{"question_id": "<q1>", "value": "第一份"}]},
                "second": None if mode == "normal" else {
                    "requestId": "submit-2" if mode == "repeat" else "submit-1",
                    "answers": [{"question_id": "<q1>", "value": "第二份" if mode == "changed" else "第一份"}]}},
               [f"依次得到业务码 {codes}；数据库总记录数为 {count}。",
                "保存匿名标记来自问卷，内部身份绑定 reader；提交响应仅含 response_id、submitted_at。"])

for expired, retry in ((False, False), (True, False), (False, True), (True, True)):
    define("SUB", f"{'截止' if expired else '关闭'}后{'重试已有成功请求' if retry else '首次提交'}",
           "closed_submission", {"expired": expired, "retry": retry},
           ["准备已发布的必答文本问卷；截止场景预先设为测试时钟一小时后。",
            "重试场景先成功提交；然后手动关闭，或推进注入时钟恰好到 deadline。",
            "提交或原样重试，检查返回值和数据库份数。"],
           {"requestId": "closed-1", "answer": "第一份", "expired": expired,
            "retry": retry, "deadline_offset_seconds": 3600},
           [f"最终 code={0 if retry else 4090}，记录数为 {1 if retry else 0}。",
            "重试成功时返回原提交 ID 和时间，不能再创建记录。"])

for mode in ("people", "same_request", "different_requests", "close_race", "expiry_race"):
    descriptions = {
        "people": ("多人同时填写", "owner 与 reader 并发提交，各使用独立身份。", [0, 0], 2),
        "same_request": ("同请求并发重试", "同一 reader 并发发送三次相同 requestId 和内容。", [0, 0, 0], 1),
        "different_requests": ("限填一次的并发竞争", "同一 reader 并发发送三个不同 requestId。", [0, 4090, 4090], 1),
        "close_race": ("提交中途被关闭时回滚", "暂停服务端路径校验后的提交，用 owner 关闭，再继续提交。", [4090], 0),
        "expiry_race": ("提交中途截止时回滚", "路径校验后推进测试时钟到 deadline，再继续写入事务。", [4090], 0),
    }
    title, action, codes, count = descriptions[mode]
    define("SUB", title, "concurrent_submission", {"mode": mode, "codes": codes, "count": count},
           ["准备已发布且每人限一次的必答文本问卷；截止场景先设置 deadline。",
            action, "读取各响应和数据库记录数，验证没有重复或半份提交。"],
           {"path": "/surveys/access/<token>/submit", "answer": "并发答案",
            "mode": mode, "control": "同步事件或注入时钟，不依赖任意 sleep"},
           [f"业务码排序后为 {codes}；数据库记录数为 {count}。",
            "同请求并发成功时，所有成功响应的提交 ID 和时间必须相同。"])


define("STA", "四类统计、回答分母及整卷单题一致", "statistics", {"mode": "totals"},
       ["创建四种题型并允许多次填写，发布后由同一 reader 提交三份固定答案；第一份额外原样重试一次。",
        "读取整卷统计，再分别读取四道题的统计。"],
       {"submissions": [["A", ["A", "B"], "重复内容", 0], ["A", ["B"], "重复内容", 10], ["B", [], "", None]],
        "paths": ["GET /surveys/<id>/statistics", "GET /surveys/<id>/questions/<qid>/statistics"]},
       ["总份数=3，单选回答数=3、选项计数=[2,1,0]；多选回答数=2、计数=[1,2,0]。",
        "文本保留两条重复内容；数字有效回答数=2、平均值=5，不使用总份数 3 作分母。",
        "整卷每题结果与单题第一页完全相同。"])
define("STA", "无提交时返回零值和空列表", "statistics", {"mode": "empty"},
       ["创建含四种题型的草稿问卷，不提交。", "读取整卷和每道单题统计。"],
       {"submission_count": 0, "status": "draft"},
       ["总份数、各题回答数、各选项计数为 0；填空列表为空；数字平均值为 null。"])
for kind in ("text", "number"):
    define("STA", f"{kind} 内容稳定分页与全量汇总", "statistics", {"mode": "pagination", "kind": kind},
           ["创建单题问卷并发布。本排序专项直接在测试库插入 27 条符合字段约定的旧格式答卷。",
            "数值为 0..26，文本为“内容0”..“内容26”；每三条时间相同，组内 ID 递增，但较晚时间组的 ID 更小；实际逆序插入。",
            "读取整卷，再用 page_size=10 读取第 1、2、3、4 页。"],
           {"values": "0..26" if kind == "number" else "内容0..内容26",
            "page_size": 10, "pages": [1, 2, 3, 4], "insertion_order": "逆序；时间升序、同时间 ID 升序为预期",
            "id_rule": "同时间组内递增，较晚时间组 ID 更小"},
           ["整卷仅返回最早 20 条；各页分别有 10、10、7、0 条且顺序稳定，total=27。",
            "数字平均值在所有页都为 13，不能只取当前页计算；旧记录缺少幂等字段仍计入。"])
for anonymous in (False, True):
    define("STA", f"权限和身份不泄露，匿名={anonymous}", "statistics", {"mode": "privacy", "anonymous": anonymous},
           ["创建问卷并提交“测试内容”。", "以未登录、reader、owner 分别读取整卷及单题统计。",
            "递归检查 owner 响应的字段名，不允许出现填写者身份或内部提交元数据。"],
           {"allow_anonymous": anonymous, "answer": "测试内容", "roles": [None, "reader", "owner"]},
           ["未登录为 4010，非所有者为 4030，owner 成功。",
            "内容项仅含 value；不返回用户名、用户 ID、提交 ID、提交时间、幂等标识或哈希。"])
for scope in ("whole", "single"):
    define("STA", f"{scope} 并发读取共享快照", "statistics", {"mode": "snapshot", "scope": scope},
           ["发布可多次填写的数字问卷，提交数值 10。",
            "整卷在总数读取后暂停；单题在汇总与明细之间暂停，随后通过真实提交接口写入 20。",
            "恢复统计，检查当前响应；再查询一次检查新提交已可见。"],
           {"initial_values": [10], "concurrent_value": 20, "scope": scope,
            "control": "threading.Event 控制查询交错"},
           ["当前响应仍为总数=1、回答数=1、内容=[10]、平均值=10。",
            "下次查询为总数=2、回答数=2、内容=[10,20]、平均值=15。"])
