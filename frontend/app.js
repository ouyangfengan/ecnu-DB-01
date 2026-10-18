const app = document.querySelector("#app");
const topActions = document.querySelector("#top-actions");
const toastElement = document.querySelector("#toast");

const state = {
  token: sessionStorage.getItem("survey-token") || "",
  username: sessionStorage.getItem("survey-username") || "",
  view: "home",
  surveyToken: new URL(location.href).searchParams.get("survey") || "",
  toastTimer: null,
};

const TYPES = {
  single: "单选题",
  multiple: "多选题",
  text: "文本填空",
  number: "数字填空",
};
const STATUSES = { draft: "草稿", published: "已发布", closed: "已关闭" };

function node(tag, { className, text, attrs = {}, on = {} } = {}, children = []) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  for (const [name, value] of Object.entries(attrs)) {
    if (value !== null && value !== undefined) element.setAttribute(name, String(value));
  }
  for (const [name, handler] of Object.entries(on)) element.addEventListener(name, handler);
  for (const child of Array.isArray(children) ? children : [children]) {
    if (child instanceof Node) element.append(child);
    else if (child !== null && child !== undefined) element.append(document.createTextNode(String(child)));
  }
  return element;
}

function inputField(label, input, hint = "") {
  const children = [node("span", { text: label }), input];
  if (hint) children.push(node("small", { text: hint }));
  return node("label", { className: "field" }, children);
}

function textInput({ value = "", placeholder = "", type = "text", required = false, min = null, max = null, step = null } = {}) {
  return node("input", {
    attrs: { type, value, placeholder, required: required ? "" : null, min, max, step },
  });
}

function textArea(value = "", placeholder = "", rows = 3) {
  const element = node("textarea", { attrs: { placeholder, rows } });
  element.value = value;
  return element;
}

function selectInput(options, selected, attributes = {}) {
  const select = node("select", { attrs: attributes });
  for (const item of options) {
    const option = node("option", {
      text: item.label,
      attrs: { value: item.value, selected: String(item.value) === String(selected) ? "" : null },
    });
    select.append(option);
  }
  return select;
}

function checkInput(label, checked = false) {
  const box = node("input", { attrs: { type: "checkbox" } });
  box.checked = checked;
  return node("label", { className: "check-row" }, [box, node("span", { text: label })]);
}

function showToast(message, error = false) {
  toastElement.textContent = message;
  toastElement.classList.toggle("error-box", error);
  toastElement.classList.add("show");
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => {
    toastElement.classList.remove("show");
    toastElement.classList.remove("error-box");
  }, 3200);
}

class ApiFailure extends Error {
  constructor(message, code = 0, status = 0, data = {}) {
    super(message);
    this.code = code;
    this.status = status;
    this.data = data;
  }
}

async function api(path, { method = "GET", body, auth = true } = {}) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth && state.token) headers.Authorization = `Bearer ${state.token}`;
  let response;
  try {
    response = await fetch(path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiFailure("无法连接服务，请检查后端是否启动以及浏览器网络。");
  }
  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new ApiFailure(`服务器返回了无法识别的响应（HTTP ${response.status}）。`, 0, response.status);
  }
  if (!response.ok || payload.code !== 0) {
    if (payload.code === 4010 && state.token) {
      clearLogin();
      renderLogin("登录凭证已失效，请重新登录。");
    }
    throw new ApiFailure(payload.msg || `请求失败（HTTP ${response.status}）`, payload.code, response.status, payload.data);
  }
  return payload.data || {};
}

async function safe(action) {
  try {
    await action();
  } catch (error) {
    if (error instanceof ApiFailure) showToast(error.message, true);
    else {
      console.error(error);
      showToast(error?.message || "操作失败，请重试。", true);
    }
  }
}

function clearLogin() {
  state.token = "";
  state.username = "";
  sessionStorage.removeItem("survey-token");
  sessionStorage.removeItem("survey-username");
  updateHeader();
}

function updateHeader() {
  topActions.replaceChildren();
  if (!state.token) {
    topActions.append(node("span", { text: state.surveyToken ? "请登录后填写问卷" : "登录后管理与填写问卷" }));
    return;
  }
  topActions.append(node("span", { text: state.username || "已登录" }));
  topActions.append(button("退出", () => safe(async () => {
    try {
      await api("/auth/logout", { method: "POST", body: {} });
    } finally {
      clearLogin();
      navigateHome();
    }
  }), "small"));
}

function sectionTitle(title, right = null) {
  return node("div", { className: "section-title" }, [
    node("h2", { text: title }),
    right,
  ]);
}

function pageHeader(label, title, description, action = null) {
  return node("div", { className: "page-head" }, [
    node("div", {}, [
      node("p", { className: "eyebrow", text: label }),
      node("h1", { text: title }),
      node("p", { className: "subtitle", text: description }),
    ]),
    action,
  ]);
}

function statusBadge(status) {
  return node("span", { className: `badge ${status}`, text: STATUSES[status] || status || "未知状态" });
}

function navigateHome() {
  state.surveyToken = "";
  const url = new URL(location.href);
  url.searchParams.delete("survey");
  history.pushState({}, "", url.pathname + url.search + url.hash);
  if (state.token) showDashboard();
  else renderLogin();
}

window.addEventListener("popstate", () => {
  state.surveyToken = new URL(location.href).searchParams.get("survey") || "";
  if (state.surveyToken && state.token) safe(() => startFilling(state.surveyToken));
  else if (!state.token) renderLogin();
  else showDashboard();
});

function renderLogin(message = "") {
  state.view = "auth";
  updateHeader();
  app.replaceChildren();

  let registering = false;
  const card = node("section", { className: "card" });
  const draw = () => {
    card.replaceChildren();
    card.append(
      node("p", { className: "eyebrow", text: state.surveyToken ? "问卷填写" : "欢迎使用" }),
      node("h1", { text: registering ? "创建账号" : "登录简问" }),
      node("p", { className: "subtitle", text: state.surveyToken
        ? "登录后即可查看问卷并提交答案。匿名问卷同样需要登录。"
        : "登录后创建问卷、填写问卷或查看统计。" }),
    );
    if (message) card.append(node("div", { className: "notice", text: message }));
    const form = node("form", { className: "stack" });
    const username = textInput({ placeholder: "请输入用户名", required: true, max: 50 });
    username.autocomplete = "username";
    const password = textInput({ type: "password", placeholder: "请输入密码", required: true });
    password.autocomplete = registering ? "new-password" : "current-password";
    form.append(inputField("用户名", username));
    form.append(inputField("密码", password, registering ? "注册密码长度为 6-12 个字符。" : ""));
    form.append(node("button", { className: "btn primary", attrs: { type: "submit" }, text: registering ? "注册并登录" : "登录" }));
    form.addEventListener("submit", async event => {
      event.preventDefault();
      const credentials = { username: username.value, password: password.value };
      await safe(async () => {
        if (registering) await api("/auth/register", { method: "POST", body: credentials, auth: false });
        const result = await api("/auth/login", { method: "POST", body: credentials, auth: false });
        state.token = result.token;
        state.username = result.username;
        sessionStorage.setItem("survey-token", result.token);
        sessionStorage.setItem("survey-username", result.username);
        updateHeader();
        if (state.surveyToken) await startFilling(state.surveyToken);
        else await showDashboard();
      });
    });
    card.append(form);
    card.append(node("div", { className: "section-divider" }));
    card.append(node("div", { className: "actions between" }, [
      node("span", { className: "muted", text: registering ? "已有账号？" : "第一次使用？" }),
      button(registering ? "返回登录" : "注册账号", () => { registering = !registering; draw(); }, "ghost"),
    ]));
  };
  draw();
  app.append(card);
}

function surveyBrowserLink(apiLink) {
  const url = new URL(apiLink, location.origin);
  const marker = "/surveys/access/";
  const index = url.pathname.indexOf(marker);
  if (index < 0) throw new Error("服务端返回的访问链接格式无效。");
  const access = url.pathname.slice(index + marker.length);
  return `${location.origin}/ui/?survey=${encodeURIComponent(access)}`;
}

function surveyCard(form) {
  const content = node("div", {}, [
    node("div", { className: "actions" }, [
      node("h3", { text: form.title }),
      statusBadge(form.status),
    ]),
    node("div", { className: "survey-meta" }, [
      node("span", { text: form.description || "暂无说明" }),
      node("span", { text: form.allow_anonymous ? "允许匿名显示" : "实名问卷" }),
      node("span", { text: form.allow_multiple_submissions ? "允许重复填写" : "每人限填一次" }),
      node("span", { text: `创建于 ${formatDate(form.created_at)}` }),
    ]),
  ]);
  const actions = node("div", { className: "actions" }, [
    button("管理", () => safe(() => openSurvey(form.form_id)), "small"),
    button("统计", () => safe(() => showStatistics(form.form_id)), "small"),
  ]);
  if (form.status === "published") {
    const share = surveyBrowserLink(form.access_link);
    actions.append(button("复制填写链接", () => copyText(share), "small"));
  }
  return node("article", { className: "survey-card" }, [content, actions]);
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
}

async function showDashboard(page = 1) {
  state.view = "home";
  state.surveyToken = "";
  updateHeader();
  app.replaceChildren(node("div", { className: "loading", text: "正在读取问卷…" }));
  const result = await api(`/surveys?page=${page}&page_size=20`);
  const createButton = button("＋ 创建问卷", () => renderCreateForm(), "primary");
  app.replaceChildren(
    pageHeader("工作台", "我的问卷", `共 ${result.total} 份问卷。草稿可继续编辑，发布后可复制填写链接并查看统计。`, createButton),
  );

  if (!result.items.length) {
    app.append(node("div", { className: "empty" }, [
      node("strong", { text: "还没有问卷" }),
      node("span", { text: "创建一份问卷，添加题目后即可发布。" }),
    ]));
  } else {
    app.append(node("div", { className: "survey-list" }, result.items.map(surveyCard)));
  }
  if (result.total > result.page_size) {
    const pages = Math.ceil(result.total / result.page_size);
    app.append(node("div", { className: "pagination" }, [
      button("上一页", () => safe(() => showDashboard(Math.max(1, page - 1))), "small"),
      node("span", { text: `第 ${page} / ${pages} 页` }),
      button("下一页", () => safe(() => showDashboard(Math.min(pages, page + 1))), "small"),
    ]));
  }
}

function renderCreateForm() {
  state.view = "create";
  app.replaceChildren(
    pageHeader("新问卷", "创建问卷", "先填写基本信息。题目添加完成后，可以设置跳转并发布。"),
  );
  const form = node("form", { className: "panel stack" });
  const title = textInput({ placeholder: "例如：课程学习反馈", required: true, max: 200 });
  const description = textArea("", "介绍问卷目的或填写说明");
  const anonymous = checkInput("匿名问卷：提交数据不向创建者展示填写者身份。");
  const multiple = checkInput("允许同一账号多次填写。");
  form.append(node("div", { className: "form-grid" }, [
    inputField("问卷标题", title),
    inputField("问卷说明", description),
    anonymous, multiple,
  ]));
  form.append(node("div", { className: "actions end" }, [
    button("取消", () => showDashboard()),
    node("button", { className: "btn primary", attrs: { type: "submit" }, text: "创建问卷" }),
  ]));
  form.addEventListener("submit", event => {
    event.preventDefault();
    safe(async () => {
      const created = await api("/surveys", {
        method: "POST",
        body: {
          title: title.value,
          description: description.value,
          allow_anonymous: anonymous.querySelector("input").checked,
          allow_multiple_submissions: multiple.querySelector("input").checked,
        },
      });
      await openSurvey(created.form_id);
      showToast("问卷已创建。");
    });
  });
  app.append(form);
}

function ruleRow(question, questions, initial = null, onRemove = () => {}) {
  const card = node("div", { className: "rule-card stack" });
  const type = question.type;
  const condition = initial?.condition || {};
  const target = initial?.target || "end";
  const fields = node("div", { className: "rule-grid" });

  let operation = null;
  if (type === "number") {
    operation = selectInput([
      { value: "eq", label: "等于" }, { value: "lt", label: "小于" },
      { value: "lte", label: "小于等于" }, { value: "gt", label: "大于" },
      { value: "gte", label: "大于等于" }, { value: "between", label: "位于区间" },
    ], condition.op || "eq");
    fields.append(inputField("匹配条件", operation));
  } else {
    const fixed = type === "single" ? "eq" : "exact";
    fields.append(inputField("匹配方式", node("input", { attrs: { value: type === "single" ? "选中该选项" : "选中集合完全相同", disabled: "" } })));
    operation = node("input", { attrs: { type: "hidden", value: fixed } });
  }

  let valueControl;
  const makeValueControl = () => {
    if (type === "single") {
      valueControl = selectInput(question.options.map(option => ({
        value: option.option_id, label: option.text,
      })), condition.value || question.options[0]?.option_id || "");
      fields.append(inputField("选项", valueControl));
    } else if (type === "multiple") {
      valueControl = selectInput(question.options.map(option => ({
        value: option.option_id, label: option.text,
      })), "", { multiple: "" });
      const selected = new Set(Array.isArray(condition.value) ? condition.value : []);
      for (const option of valueControl.options) option.selected = selected.has(option.value);
      valueControl.size = Math.min(4, Math.max(2, question.options.length));
      fields.append(inputField("精确匹配的选项集合（可多选）", valueControl));
    } else {
      const op = operation.value;
      if (op === "between") {
        const lower = textInput({ type: "number", step: "any", value: condition.lower ?? 0, required: true });
        const upper = textInput({ type: "number", step: "any", value: condition.upper ?? 10, required: true });
        const includeLower = checkInput("包含下边界", condition.include_lower !== false);
        const includeUpper = checkInput("包含上边界", condition.include_upper !== false);
        valueControl = { lower, upper, includeLower, includeUpper };
        fields.append(inputField("下边界", lower), inputField("上边界", upper), includeLower, includeUpper);
      } else {
        valueControl = textInput({ type: "number", step: "any", value: condition.value ?? 0, required: true });
        fields.append(inputField("比较数值", valueControl));
      }
    }
  };
  makeValueControl();

  const targetOptions = questions
    .filter(item => item.order > question.order)
    .map(item => ({ value: item.question_id, label: `第 ${item.order} 题：${item.title}` }));
  targetOptions.push({ value: "end", label: "结束问卷" });
  const targetControl = selectInput(targetOptions, target);
  fields.append(node("label", { className: "field wide" }, [
    node("span", { text: "跳转到" }),
    targetControl,
  ]));
  if (operation && type === "number") {
    operation.addEventListener("change", () => {
      const previous = operation.value;
      if (previous === "between") {
        condition.lower = valueControl?.lower?.value ?? 0;
        condition.upper = valueControl?.upper?.value ?? 10;
      } else if (valueControl instanceof HTMLInputElement) {
        condition.value = valueControl.value;
      }
      condition.op = previous;
      fields.replaceChildren();
      fields.append(inputField("匹配条件", operation));
      makeValueControl();
      fields.append(node("label", { className: "field wide" }, [
        node("span", { text: "跳转到" }), targetControl,
      ]));
    });
  }
  const read = () => {
    const op = operation.value;
    let ruleCondition;
    if (type === "single") ruleCondition = { op, value: valueControl.value };
    else if (type === "multiple") {
      ruleCondition = { op, value: Array.from(valueControl.selectedOptions, option => option.value) };
    } else if (op === "between") {
      ruleCondition = {
        op, lower: Number(valueControl.lower.value), upper: Number(valueControl.upper.value),
        include_lower: valueControl.includeLower.querySelector("input").checked,
        include_upper: valueControl.includeUpper.querySelector("input").checked,
      };
    } else ruleCondition = { op, value: Number(valueControl.value) };
    return { condition: ruleCondition, target: targetControl.value };
  };
  card.append(fields);
  card.append(node("div", { className: "actions end" }, [
    button("移除此规则", onRemove, "small danger"),
  ]));
  return { element: card, read };
}

function optionEditor(question, initialType, valueHolder) {
  const wrap = node("div", { className: "field full" });
  const list = node("div", { className: "stack" });
  const help = node("small", { className: "hint", text: "至少两个选项。编辑已有选项时会保留选项 ID。" });
  const appendOption = (text = "", optionId = null) => {
    const row = node("div", { className: "actions" });
    const value = textInput({ value: text, placeholder: "选项内容", required: true });
    value.classList.add("option-text");
    if (optionId) value.dataset.optionId = optionId;
    row.append(value);
    row.append(button("删除", () => {
      row.remove();
      if (list.children.length < 2) help.textContent = "选择题至少需要两个选项。";
    }, "small danger"));
    list.append(row);
  };
  const existing = question?.type === initialType ? question.options || [] : [];
  if (existing.length) existing.forEach(option => appendOption(option.text, option.option_id));
  else {
    const entries = valueHolder?.options || ["选项一", "选项二"];
    entries.forEach(option => {
      if (typeof option === "string") appendOption(option);
      else appendOption(option.text, option.option_id || null);
    });
  }
  wrap.append(node("span", { text: "选项" }), list, help,
    button("＋ 添加选项", () => appendOption(), "small"));
  return {
    element: wrap,
    read: () => Array.from(list.querySelectorAll(".option-text")).map(element => ({
      ...(element.dataset.optionId ? { option_id: element.dataset.optionId } : {}),
      text: element.value,
    })),
  };
}

function questionEditor(form, questions, question = null) {
  const initial = {
    title: question?.title || "",
    type: question?.type || "single",
    validation: { ...(question?.validation || {}) },
    options: question?.options?.map(option => option.text) || ["选项一", "选项二"],
  };
  const panel = node("section", { className: "panel stack" });
  panel.append(sectionTitle(question ? `编辑第 ${question.order} 题` : "添加题目"));
  const formElement = node("form", { className: "stack" });
  const title = textInput({ value: initial.title, placeholder: "请输入题目内容", required: true });
  const type = selectInput(Object.entries(TYPES).map(([value, label]) => ({ value, label })), initial.type);
  const required = checkInput("必答题", initial.validation.required === true);
  formElement.append(node("div", { className: "form-grid" }, [
    inputField("题目标题", title),
    inputField("题型", type),
    required,
  ]));

  const config = node("div", { className: "form-grid" });
  let options = null;
  let validationInputs = {};
  const drawTypeFields = (selectedType, currentValidation, currentOptions) => {
    config.replaceChildren();
    if (selectedType === "single" || selectedType === "multiple") {
      options = optionEditor(question, selectedType, { options: currentOptions });
      config.append(options.element);
    } else options = null;
    validationInputs = {};
    const limits = selectedType === "multiple"
      ? [["min_selected", "最少选择"], ["max_selected", "最多选择"]]
      : selectedType === "text"
        ? [["min_length", "最少字数"], ["max_length", "最多字数"]]
        : selectedType === "number"
          ? [["min_value", "最小值"], ["max_value", "最大值"]]
          : [];
    for (const [key, label] of limits) {
      const isNumeric = selectedType === "number";
      const control = textInput({
        type: "number", step: isNumeric ? "any" : "1",
        value: currentValidation[key] ?? "", placeholder: "不限制",
      });
      validationInputs[key] = control;
      config.append(inputField(label, control));
    }
    if (selectedType === "number") {
      const integer = checkInput("只允许整数", currentValidation.integer_only === true);
      validationInputs.integer_only = integer.querySelector("input");
      config.append(integer);
    }
  };
  drawTypeFields(initial.type, initial.validation, initial.options);
  formElement.append(config);

  const rulesSection = node("div", { className: "stack" });
  let rows = [];
  const drawRules = ruleValues => {
    rulesSection.replaceChildren();
    rows = [];
    rulesSection.append(node("div", { className: "section-title" }, [
      node("h3", { text: "跳转规则" }),
      question
        ? button("＋ 添加规则", () => { ruleValues.push(null); drawRules(ruleValues); }, "small")
        : node("span", { className: "muted", text: "添加后可编辑跳转目标。" }),
    ]));
    if (!question) {
      rulesSection.append(node("p", { className: "hint", text: "先创建目标题，再编辑前面的题目配置跳转。规则在保存时校验互斥。" }));
      return;
    }
    const editedQuestion = {
      ...question,
      type: type.value,
      options: options?.read() || [],
    };
    if (editedQuestion.type === "text") {
      rulesSection.append(node("p", { className: "hint", text: "文本题不支持跳转规则。" }));
      return;
    }
    if (!ruleValues.length) {
      rulesSection.append(node("p", { className: "hint", text: "无匹配规则时按顺序进入下一题；数字题支持 between 区间。" }));
    }
    ruleValues.forEach((rule, index) => {
      const row = ruleRow(editedQuestion, questions, rule, () => {
        ruleValues.splice(index, 1);
        drawRules(ruleValues);
      });
      rows.push(row);
      rulesSection.append(row.element);
    });
  };
  const ruleValues = question ? structuredClone(question.jump_rules || []) : [];
  drawRules(ruleValues);
  formElement.append(rulesSection);

  type.addEventListener("change", () => {
    const next = type.value;
    const currentOptions = options?.read().filter(option => option.text.trim()) || initial.options;
    if (next !== initial.type) {
      initial.type = next;
      initial.validation = {};
      initial.options = currentOptions;
      drawTypeFields(next, initial.validation, currentOptions);
      drawRules([]);
    }
  });

  function readValidation(selectedType) {
    const result = { required: required.querySelector("input").checked };
    for (const [key, control] of Object.entries(validationInputs)) {
      if (key === "integer_only") result[key] = control.checked;
      else if (control.value !== "") {
        result[key] = selectedType === "number" ? Number(control.value) : Number.parseInt(control.value, 10);
      }
    }
    return result;
  }

  formElement.append(node("div", { className: "actions end" }, [
    button("取消", () => openSurvey(form.form_id)),
    node("button", {
      className: "btn primary", attrs: { type: "submit" },
      text: question ? "保存题目" : "添加题目",
    }),
  ]));
  formElement.addEventListener("submit", event => {
    event.preventDefault();
    safe(async () => {
      const kind = type.value;
      const payload = {
        title: title.value,
        type: kind,
        options: options ? options.read() : [],
        validation: readValidation(kind),
        jump_rules: rows.map(row => row.read()),
      };
      const path = question
        ? `/surveys/${form.form_id}/questions/${question.question_id}`
        : `/surveys/${form.form_id}/questions`;
      const saved = await api(path, { method: question ? "PATCH" : "POST", body: payload });
      await openSurvey(form.form_id);
      showToast(question ? "题目已保存。" : `第 ${saved.order} 题已添加。`);
    });
  });
  panel.append(formElement);
  return panel;
}

function deadlineInput(form) {
  const section = node("section", { className: "panel stack" });
  section.append(sectionTitle("截止时间"));
  const current = form.deadline ? new Date(form.deadline) : null;
  const localValue = current && !Number.isNaN(current.getTime())
    ? new Date(current.getTime() - current.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
    : "";
  const control = textInput({ type: "datetime-local", value: localValue });
  section.append(inputField("停止收集时间", control, "留空并点击“清除”表示不限时。发布后不能修改。"));
  section.append(node("div", { className: "actions" }, [
    button("保存截止时间", () => safe(async () => {
      if (!control.value) throw new Error("请选择时间；清除请使用旁边按钮。");
      const value = new Date(control.value).toISOString();
      await api(`/surveys/${form.form_id}/deadline`, { method: "PUT", body: { deadline: value } });
      await openSurvey(form.form_id);
      showToast("截止时间已更新。");
    }), "primary"),
    button("清除", () => safe(async () => {
      await api(`/surveys/${form.form_id}/deadline`, { method: "PUT", body: { deadline: null } });
      await openSurvey(form.form_id);
      showToast("已清除截止时间。");
    }), "small"),
  ]));
  return section;
}

async function openSurvey(formId) {
  state.view = "detail";
  app.replaceChildren(node("div", { className: "loading", text: "正在读取问卷…" }));
  const form = await api(`/surveys/${formId}`);
  renderSurvey(form);
}

function renderSurvey(form) {
  const isDraft = form.status === "draft";
  app.replaceChildren(
    pageHeader("问卷管理", form.title, form.description || "暂无问卷说明。", button("返回列表", () => safe(showDashboard))),
  );

  const summary = node("section", { className: "panel" });
  const meta = node("div", { className: "actions" }, [
    statusBadge(form.status),
    node("span", { className: "badge", text: form.allow_anonymous ? "匿名问卷" : "实名问卷" }),
    node("span", { className: "badge", text: form.allow_multiple_submissions ? "允许重复填写" : "每人限填一次" }),
    node("span", { className: "badge", text: form.deadline ? `截止 ${formatDate(form.deadline)}` : "不限截止时间" }),
  ]);
  summary.append(meta);
  if (form.status === "published") {
    const link = surveyBrowserLink(form.access_link);
    summary.append(node("div", { className: "section" }, [
      node("p", { className: "field-label", text: "浏览器填写链接（登录后可填写）" }),
      node("div", { className: "share-box mono", text: link }),
      node("div", { className: "toolbar" }, [
        button("复制填写链接", () => copyText(link), "primary"),
        button("查看统计", () => safe(() => showStatistics(form.form_id))),
        button("关闭问卷", () => safe(() => closeSurvey(form)), "danger"),
      ]),
    ]));
  }
  app.append(summary);

  const questionHeading = node("div", { className: "section-title" }, [
    node("h2", { text: `题目（${form.questions.length}）` }),
    !isDraft ? statusBadge(form.status) : null,
  ]);
  app.append(node("section", { className: "section" }, [questionHeading]));
  for (const question of form.questions) app.append(questionCard(form, question));
  if (isDraft) {
    app.append(node("section", { className: "section stack" }, [
      questionEditor(form, form.questions),
      deadlineInput(form),
      node("div", { className: "actions end" }, [
        button("发布问卷", () => safe(() => publishSurvey(form)), "primary"),
      ]),
    ]));
  }
}

function questionCard(form, question) {
  const body = node("article", { className: "question-card" });
  const heading = node("div", { className: "question-head" }, [
    node("div", {}, [
      node("h3", { text: `${question.order}. ${question.title}` }),
      node("div", { className: "question-config" }, [
        node("span", { className: "badge", text: TYPES[question.type] || question.type }),
        node("span", { className: "badge", text: question.validation.required ? "必答" : "选答" }),
      ]),
    ]),
    node("div", { className: "actions" }, [
      form.status === "draft" ? button("编辑", () => {
        body.replaceWith(questionEditor(form, form.questions, question));
      }, "small") : null,
      form.status !== "draft" ? button("单题统计", () => safe(() => showStatistics(form.form_id, question)), "small") : null,
    ]),
  ]);
  body.append(heading);
  if (question.options?.length) {
    body.append(node("p", {
      className: "hint",
      text: `选项：${question.options.map(option => option.text).join(" / ")}`,
    }));
  }
  const settings = Object.entries(question.validation || {})
    .filter(([key, value]) => key !== "required" && value !== null)
    .map(([key, value]) => `${key}=${value}`);
  if (settings.length) body.append(node("p", { className: "hint", text: `限制：${settings.join("，")}` }));
  if (question.jump_rules?.length) {
    body.append(node("p", { className: "hint", text: `已配置 ${question.jump_rules.length} 条跳转规则` }));
  }
  return body;
}

async function publishSurvey(form) {
  await api(`/surveys/${form.form_id}/publish`, { method: "POST" });
  await openSurvey(form.form_id);
  showToast("问卷已发布。");
}

async function closeSurvey(form) {
  if (!confirm(`确定关闭“${form.title}”吗？关闭后填写者无法继续提交。`)) return;
  await api(`/surveys/${form.form_id}/close`, { method: "POST" });
  await openSurvey(form.form_id);
  showToast("问卷已关闭。");
}

async function copyText(value) {
  try {
    await navigator.clipboard.writeText(value);
    showToast("链接已复制。");
  } catch {
    const area = textArea(value, "", 2);
    area.readOnly = true;
    app.append(area);
    area.select();
    showToast("浏览器未授权剪贴板，请手动复制选中的链接。");
  }
}

function answerControl(question, previousValue) {
  if (question.type === "single" || question.type === "multiple") {
    const options = node("div", { className: "choice-list" });
    const inputType = question.type === "single" ? "radio" : "checkbox";
    const name = `answer-${question.question_id}`;
    for (const option of question.options || []) {
      const control = node("input", { attrs: { type: inputType, name, value: option.option_id } });
      control.checked = question.type === "single"
        ? previousValue === option.option_id
        : Array.isArray(previousValue) && previousValue.includes(option.option_id);
      options.append(node("label", { className: "choice-row" }, [
        control,
        node("span", { text: option.text }),
      ]));
    }
    return {
      element: options,
      read: () => question.type === "single"
        ? options.querySelector("input:checked")?.value ?? null
        : Array.from(options.querySelectorAll("input:checked"), item => item.value),
    };
  }
  if (question.type === "text") {
    const control = textArea(previousValue ?? "", "请输入答案", 5);
    return { element: control, read: () => control.value.trim() ? control.value : null };
  }
  const control = textInput({ type: "number", step: question.validation?.integer_only ? "1" : "any",
    value: previousValue ?? "", placeholder: "请输入数字" });
  if (question.validation?.min_value !== undefined) control.min = question.validation.min_value;
  if (question.validation?.max_value !== undefined) control.max = question.validation.max_value;
  return { element: control, read: () => control.value === "" ? null : Number(control.value) };
}

function pendingKey(accessToken) {
  return `survey-pending-${accessToken}`;
}

function dropPending(accessToken) {
  sessionStorage.removeItem(pendingKey(accessToken));
  if (state.filling) state.filling.pending = null;
}

async function startFilling(accessToken) {
  state.view = "fill";
  state.surveyToken = accessToken;
  updateHeader();
  let pending = null;
  try {
    pending = JSON.parse(sessionStorage.getItem(pendingKey(accessToken)) || "null");
    if (!pending || typeof pending.requestId !== "string" || !Array.isArray(pending.answers)) {
      pending = null;
      sessionStorage.removeItem(pendingKey(accessToken));
    }
  } catch {
    sessionStorage.removeItem(pendingKey(accessToken));
  }
  if (pending) {
    state.filling = {
      accessToken,
      form: { title: "提交结果待确认", description: "" },
      answers: pending.answers,
      current: null,
      complete: true,
      pending,
      error: "",
    };
    renderFilling();
    return;
  }
  app.replaceChildren(node("div", { className: "loading", text: "正在打开问卷…" }));
  const form = await api(`/surveys/access/${encodeURIComponent(accessToken)}`);
  const progress = await api(`/surveys/access/${encodeURIComponent(accessToken)}/progress`, {
    method: "POST", body: { answers: [] },
  });
  state.filling = {
    accessToken, form, answers: progress.answers || [],
    current: progress.next_question, complete: progress.complete,
    pending, error: "",
  };
  renderFilling();
}

function renderFilling() {
  const filling = state.filling;
  if (!filling) return;
  const { form, current } = filling;
  app.replaceChildren(pageHeader("填写问卷", form.title, form.description || "请按题目顺序填写。"));
  if (!current) {
    renderFillComplete(filling);
    return;
  }
  const answered = filling.answers.length;
  const progressValue = Math.min(100, answered / Math.max(form.questions.length, 1) * 100);
  const panel = node("section", { className: "panel" });
  panel.append(node("div", { className: "progress-head" }, [
    node("span", { className: "badge", text: `第 ${current.order} 题` }),
    node("span", { className: "muted", text: current.validation.required ? "必答" : "选答" }),
  ]));
  panel.append(node("div", { className: "progress-track" }, [
    node("div", { className: "progress-fill", attrs: { style: `width:${progressValue}%` } }),
  ]));
  panel.append(node("h2", { className: "section", text: current.title }));
  panel.append(node("p", { className: "muted", text: TYPES[current.type] }));
  const previous = filling.answers.find(answer => answer.question_id === current.question_id)?.value;
  const answer = answerControl(current, previous);
  panel.append(node("div", { className: "answer-box" }, [answer.element]));
  panel.append(node("div", { className: "section-divider" }));
  panel.append(node("div", { className: "actions between" }, [
    button("上一步", () => goPrevious(), "", filling.answers.length === 0),
    node("div", { className: "actions" }, [
      !current.validation.required ? button("跳过", () => safe(() => answerAndContinue(current, null)), "small") : null,
      button("继续", () => safe(() => answerAndContinue(current, answer.read())), "primary"),
    ]),
  ]));
  if (current.type === "multiple" && current.validation.min_selected !== undefined) {
    panel.append(node("p", { className: "hint", text: `至少选择 ${current.validation.min_selected} 项。` }));
  }
  app.append(panel);
}

function button(text, action, kind = "", disabled = false) {
  return node("button", {
    className: `btn ${kind}`.trim(),
    attrs: { type: "button", disabled: disabled ? "" : null },
    on: { click: action },
  }, text);
}

async function answerAndContinue(question, value) {
  const filling = state.filling;
  const nextAnswers = filling.answers.filter(answer => answer.question_id !== question.question_id);
  nextAnswers.push({ question_id: question.question_id, value });
  const progress = await api(`/surveys/access/${encodeURIComponent(filling.accessToken)}/progress`, {
    method: "POST", body: { answers: nextAnswers },
  });
  filling.answers = progress.answers || [];
  filling.current = progress.next_question;
  filling.complete = progress.complete;
  filling.error = "";
  dropPending(filling.accessToken);
  renderFilling();
}

function goPrevious() {
  const filling = state.filling;
  if (!filling || !filling.answers.length) return;
  const previous = filling.answers[filling.answers.length - 1];
  const question = filling.form.questions.find(item => item.question_id === previous.question_id);
  if (!question) return;
  filling.answers = filling.answers.slice(0, -1);
  filling.current = question;
  filling.complete = false;
  filling.error = "";
  dropPending(filling.accessToken);
  renderFilling();
}

function renderFillComplete(filling) {
  const panel = node("section", { className: "panel stack" }, [
    node("div", {
      className: filling.pending ? "notice" : "success-box",
      text: filling.pending
        ? "存在一条尚未确认的提交。重试会使用原 requestId 和答案，不会创建新的提交。"
        : "已完成当前作答路径，可以提交问卷。",
    }),
    node("p", { className: "muted", text: filling.pending
      ? "结果确认前不能修改答案；如果服务器已经保存，原样重试会返回那条提交记录。"
      : "提交后不能修改本次记录。如需调整答案，请返回修改。" }),
  ]);
  if (filling.error) panel.append(node("div", { className: "error-box", text: filling.error }));
  const actions = filling.pending
    ? [
      button("原样重试提交", () => safe(() => submitFilling()), "primary"),
      button("返回首页", () => navigateHome(), "ghost"),
    ]
    : [
      button("返回修改", () => goPrevious()),
      button("提交问卷", () => safe(() => submitFilling()), "primary"),
      button("返回首页", () => navigateHome(), "ghost"),
    ];
  panel.append(node("div", { className: "actions" }, actions));
  app.append(panel);
}

async function submitFilling() {
  const filling = state.filling;
  const key = pendingKey(filling.accessToken);
  let pending = filling.pending;
  if (!pending) {
    pending = {
      requestId: crypto.randomUUID(),
      answers: structuredClone(filling.answers),
    };
    filling.pending = pending;
    sessionStorage.setItem(key, JSON.stringify(pending));
  }
  try {
    const result = await api(`/surveys/access/${encodeURIComponent(filling.accessToken)}/submit`, {
      method: "POST", body: pending,
    });
    sessionStorage.removeItem(key);
    filling.pending = null;
    const successPanel = node("section", { className: "panel stack" }, [
      node("div", { className: "success-box", text: "提交成功，感谢填写。" }),
      node("p", { className: "muted", text: `提交时间：${formatDate(result.submitted_at)}` }),
      button("返回首页", () => navigateHome(), "primary"),
    ]);
    app.replaceChildren(pageHeader("已提交", filling.form.title, "你的答案已保存。"), successPanel);
  } catch (error) {
    filling.error = `${error.message}。如为网络中断，可使用“原样重试提交”查询并返回同一次提交结果。`;
    renderFilling();
    throw error;
  }
}

async function showStatistics(formId, singleQuestion = null) {
  state.view = "statistics";
  app.replaceChildren(node("div", { className: "loading", text: "正在计算统计结果…" }));
  const result = singleQuestion
    ? await api(`/surveys/${formId}/questions/${singleQuestion.question_id}/statistics?page=1&page_size=20`)
    : await api(`/surveys/${formId}/statistics`);
  const form = singleQuestion
    ? { form_id: formId, title: (await api(`/surveys/${formId}`)).title }
    : result;
  app.replaceChildren(
    pageHeader("统计结果", form.title, `已保存提交 ${singleQuestion ? result.submission_count : result.submission_count} 份。统计按每次成功提交计数，不按填写者去重。`,
      button("返回问卷", () => safe(() => openSurvey(formId)))),
  );
  if (singleQuestion) {
    app.append(statCard(singleQuestion, result.question, formId));
  } else {
    app.append(node("div", { className: "stat-grid" }, result.questions.map(question => statCard(question, question, formId))));
  }
}

function statCard(question, stats, formId) {
  const card = node("section", { className: "stat-card" });
  card.append(node("div", { className: "actions" }, [
    node("span", { className: "badge", text: `第 ${question.order} 题` }),
    node("span", { className: "badge", text: TYPES[question.type] || question.type }),
  ]));
  card.append(node("h3", { className: "section", text: question.title }));
  card.append(node("p", { className: "stat-subtitle", text: `有效回答 ${stats.answer_count} 份` }));
  if (stats.options) {
    const max = Math.max(1, ...stats.options.map(option => option.count));
    for (const option of stats.options) {
      card.append(node("div", { className: "stat-option" }, [
        node("span", { text: option.text }),
        node("div", { className: "bar-track" }, [
          node("div", { className: "bar-fill", attrs: { style: `width:${option.count / max * 100}%` } }),
        ]),
        node("span", { className: "stat-count", text: `${option.count}` }),
      ]));
    }
    return card;
  }

  if (question.type === "number") {
    const average = stats.average === null ? "暂无" : new Intl.NumberFormat(undefined, { maximumFractionDigits: 4 }).format(stats.average);
    card.append(node("div", { className: "metric", text: average }, [
      node("small", { text: "平均值" }),
    ]));
  }
  const list = node("ul", { className: "content-list" });
  for (const item of stats.contents?.items || []) {
    list.append(node("li", { text: String(item.value) }));
  }
  if (!list.children.length) list.append(node("li", { className: "muted", text: "暂无有效回答" }));
  card.append(list);
  const total = stats.contents?.total || 0;
  const page = stats.contents?.page || 1;
  const pageSize = stats.contents?.page_size || 20;
  card.append(node("div", { className: "pagination" }, [
    button("上一页", () => safe(() => loadQuestionPage(formId, question, Math.max(1, page - 1))), "small", page <= 1),
    node("span", { text: `第 ${page} 页，共 ${total} 条` }),
    button("下一页", () => safe(() => loadQuestionPage(formId, question, page + 1)), "small", page * pageSize >= total),
  ]));
  return card;
}

async function loadQuestionPage(formId, question, page) {
  const result = await api(`/surveys/${formId}/questions/${question.question_id}/statistics?page=${page}&page_size=20`);
  const current = state.view === "statistics"
    ? { form_id: formId, title: app.querySelector("h1")?.textContent || "统计结果" }
    : { title: "统计结果" };
  app.replaceChildren(
    pageHeader("统计结果", current.title, `已保存提交 ${result.submission_count} 份。统计按每次成功提交计数。`,
      button("返回问卷", () => safe(() => openSurvey(formId)))),
    statCard(question, result.question, formId),
  );
}

async function boot() {
  updateHeader();
  if (!state.token) {
    renderLogin();
    return;
  }
  if (state.surveyToken) await safe(() => startFilling(state.surveyToken));
  else await safe(showDashboard);
}

boot();
