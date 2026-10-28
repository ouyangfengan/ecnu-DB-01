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

function navButton(label, view, action) {
  return button(label, action, `small ${state.view === view ? "primary" : "ghost"}`);
}

function updateHeader() {
  topActions.replaceChildren();
  if (!state.token) {
    topActions.append(node("span", { text: state.surveyToken ? "请登录后填写问卷" : "登录后管理与填写问卷" }));
    return;
  }
  topActions.append(node("nav", { className: "nav" }, [
    navButton("我的问卷", "home", () => safe(showDashboard)),
    navButton("填写问卷", "fill", () => safe(openFillingLink)),
    navButton("资源库", "resources", () => safe(showResources)),
    navButton("收到的共享", "received", () => safe(showReceived)),
    navButton("题库", "banks", () => safe(showBanks)),
  ]));
  topActions.append(node("span", { className: "top-user", text: state.username || "已登录" }));
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

function accessTokenFromInput(value) {
  const text = String(value || "").trim();
  if (!text) return "";
  const marker = "/surveys/access/";
  const index = text.indexOf(marker);
  if (index >= 0) return decodeURIComponent(text.slice(index + marker.length).split(/[?#]/)[0]);
  const match = text.match(/[?&]survey=([^&#]+)/);
  return match ? decodeURIComponent(match[1]) : text;
}

async function openFillingLink() {
  const input = prompt("粘贴问卷填写链接或访问标识：");
  if (input === null) return;
  const token = accessTokenFromInput(input);
  if (!token) {
    showToast("未能识别填写链接，请检查后重试。", true);
    return;
  }
  await startFilling(token);
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

function formatDeadline(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  const pad = part => String(part).padStart(2, "0");
  return `${date.getFullYear()}年${pad(date.getMonth() + 1)}月${pad(date.getDate())}日 ${pad(date.getHours())}:${pad(date.getMinutes())}`;
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
  const appendOption = (text = "", optionId = null, fromSource = false) => {
    const row = node("div", { className: "actions" });
    const value = textInput({ value: text, placeholder: "选项内容", required: true });
    value.classList.add("option-text");
    if (optionId) value.dataset.optionId = optionId;
    if (fromSource) {
      // 沿用来源版本的选项 ID 不能直接改文字，否则服务端按 4001 拒绝。
      value.title = "该选项沿用来源版本的选项 ID，改名请删除后重新添加。";
      row.append(node("small", { className: "hint", text: "来源选项：改名请删除后重新添加" }));
    }
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
      else appendOption(option.text, option.option_id || null, Boolean(option.option_id));
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
  control.lang = "zh-CN";
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
    node("span", { className: "badge", text: form.deadline ? `截止 ${formatDeadline(form.deadline)}` : "不限截止时间" }),
  ]);
  summary.append(meta);
  if (form.status !== "draft") {
    const responsesHolder = node("div", { className: "section" });
    summary.append(node("div", { className: "toolbar" }, [
      button("答卷明细", () => safe(() => renderResponsesSection(form, responsesHolder))),
    ]));
    summary.append(responsesHolder);
  }
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
      importVersionPanel(form),
      importBankPanel(form),
      questionEditor(form, form.questions),
      deadlineInput(form),
      node("div", { className: "actions end" }, [
        button("发布问卷", () => safe(() => publishSurvey(form)), "primary"),
      ]),
    ]));
  }
}

async function renderResponsesSection(form, container, page = 1) {
  container.replaceChildren(node("div", { className: "loading", text: "正在读取答卷…" }));
  const data = await api(`/surveys/${form.form_id}/responses?page=${page}&page_size=20`);
  const box = node("div", { className: "panel stack" });
  box.append(sectionTitle(`答卷明细（${data.total}）`));
  box.append(node("p", { className: "hint", text: data.allow_anonymous
    ? "匿名问卷：仅显示提交时间与答案，不显示填写者身份。"
    : "实名问卷：显示填写者用户名。" }));
  if (!data.items.length) {
    box.append(node("p", { className: "muted", text: "暂无答卷。" }));
    container.replaceChildren(box);
    return;
  }
  const list = node("div", { className: "stack" });
  for (const item of data.items) {
    list.append(node("div", { className: "rule-card stack" }, [
      node("div", { className: "actions" }, [
        node("strong", { text: item.is_anonymous
          ? "匿名填写者"
          : item.respondent_username || shortId(item.respondent_id) }),
        node("span", { className: "badge", text: item.is_anonymous ? "匿名" : "实名" }),
      ]),
      node("p", { className: "hint", text: `提交于 ${formatDate(item.submitted_at)}　有效答案 ${item.answers.length} 项` }),
    ]));
  }
  box.append(list);
  if (data.total > data.page_size) {
    box.append(paginationBar(
      data,
      () => renderResponsesSection(form, container, data.page - 1),
      () => renderResponsesSection(form, container, data.page + 1),
    ));
  }
  container.replaceChildren(box);
}

function questionCard(form, question) {
  const body = node("article", { className: "question-card" });
  const versionHolder = node("div", { className: "section" });
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
      form.status === "draft" ? button("版本关联", () => safe(() => openQuestionVersionPanel(form, question, versionHolder)), "small") : null,
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
  if (form.status === "draft") body.append(versionHolder);
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

const CHANGE_TYPES = { create: "创建", derive: "派生", restore: "恢复", save: "保存", fork: "复用" };
const SHARE_STATUSES = { active: "有效", revoked: "已撤销" };

function uniqueId() {
  return crypto.randomUUID();
}

function shortId(value) {
  if (!value) return "—";
  const text = String(value);
  return text.length <= 10 ? text : `${text.slice(0, 8)}…`;
}

function emptyBox(title, text) {
  return node("div", { className: "empty" }, [
    node("strong", { text: title }),
    node("span", { text: text }),
  ]);
}

function appendPagination(container, result, loader) {
  if (result.total <= result.page_size) return;
  const pages = Math.ceil(result.total / result.page_size);
  const page = result.page;
  container.append(node("div", { className: "pagination" }, [
    button("上一页", () => safe(() => loader(Math.max(1, page - 1))), "small", page <= 1),
    node("span", { text: `第 ${page} / ${pages} 页` }),
    button("下一页", () => safe(() => loader(Math.min(pages, page + 1))), "small", page >= pages),
  ]));
}

function paginationBar(pageData, previous, next) {
  const page = pageData.page || 1;
  const size = pageData.page_size || 20;
  const total = pageData.total || 0;
  const pages = Math.max(1, Math.ceil(total / size));
  return node("div", { className: "pagination" }, [
    button("上一页", () => safe(previous), "small", page <= 1),
    node("span", { text: `第 ${page} / ${pages} 页，共 ${total} 条` }),
    button("下一页", () => safe(next), "small", page >= pages),
  ]);
}

function contentFields(initial = {}) {
  const title = textInput({ value: initial.title || "", placeholder: "请输入题目内容", required: true });
  const typeSelect = selectInput(
    Object.entries(TYPES).map(([value, label]) => ({ value, label })),
    initial.type || "single",
  );
  const config = node("div", { className: "form-grid" });
  let type = initial.type || "single";
  let options = (initial.options || []).map(option => ({ ...option }));
  let validation = { ...(initial.validation || {}) };
  let optionEditorRef = null;
  let validationInputs = {};

  const draw = () => {
    config.replaceChildren();
    if (type === "single" || type === "multiple") {
      optionEditorRef = optionEditor(null, type, { options });
      config.append(optionEditorRef.element);
    } else optionEditorRef = null;
    validationInputs = {};
    const limits = type === "multiple"
      ? [["min_selected", "最少选择"], ["max_selected", "最多选择"]]
      : type === "text"
        ? [["min_length", "最少字数"], ["max_length", "最多字数"]]
        : type === "number"
          ? [["min_value", "最小值"], ["max_value", "最大值"]]
          : [];
    for (const [key, label] of limits) {
      const numeric = type === "number";
      const control = textInput({
        type: "number", step: numeric ? "any" : "1",
        value: validation[key] ?? "", placeholder: "不限制",
      });
      validationInputs[key] = control;
      config.append(inputField(label, control));
    }
    if (type === "number") {
      const integer = checkInput("只允许整数", validation.integer_only === true);
      validationInputs.integer_only = integer.querySelector("input");
      config.append(integer);
    }
  };
  typeSelect.addEventListener("change", () => {
    const next = typeSelect.value;
    if (next === type) return;
    if (optionEditorRef) options = optionEditorRef.read().filter(option => option.text.trim());
    validation = {};
    type = next;
    draw();
  });
  draw();

  const read = () => {
    const content = {
      title: title.value, type,
      options: optionEditorRef ? optionEditorRef.read() : [],
      validation: {},
    };
    for (const [key, control] of Object.entries(validationInputs)) {
      if (key === "integer_only") content.validation[key] = control.checked;
      else if (control.value !== "") {
        content.validation[key] = type === "number"
          ? Number(control.value) : Number.parseInt(control.value, 10);
      }
    }
    return content;
  };
  return {
    elements: [inputField("题目标题", title), inputField("题型", typeSelect), config],
    read,
  };
}

function contentSummary(content) {
  const box = node("div", { className: "panel stack" });
  box.append(node("h3", { text: content.title }));
  box.append(node("div", { className: "question-config" }, [
    node("span", { className: "badge", text: TYPES[content.type] || content.type }),
    ...(content.options || []).map(option => node("span", { className: "badge", text: option.text })),
  ]));
  const limits = Object.entries(content.validation || {});
  if (limits.length) {
    box.append(node("p", { className: "hint", text: `校验：${limits.map(([key, value]) => `${key}=${value}`).join("，")}` }));
  }
  return box;
}

async function allVersionOptions({ resourceId = null } = {}) {
  const groups = [];
  const own = await api("/question-resources?page=1&page_size=100");
  const ownOptions = [];
  for (const resource of own.items) {
    if (resourceId && resource.resource_id !== resourceId) continue;
    const detail = await api(`/question-resources/${resource.resource_id}`);
    for (const version of detail.versions) {
      ownOptions.push({
        value: version.version_id,
        label: `${resource.title} · v${version.version_number}`,
      });
    }
  }
  if (ownOptions.length) groups.push({ label: "我的资源", options: ownOptions });
  const received = await api("/question-shares/received?page=1&page_size=100");
  const sharedOptions = received.items
    .filter(share => !resourceId || share.resource_id === resourceId)
    .map(share => ({
      value: share.version_id,
      label: `${share.title} · v${share.version_number}（来自 ${share.owner_username}）`,
    }));
  if (sharedOptions.length) groups.push({ label: "收到的共享", options: sharedOptions });
  return groups;
}

function versionPicker({ resourceId = null, placeholder = "请选择版本" } = {}) {
  const field = node("label", { className: "field full" });
  const select = selectInput([{ value: "", label: "正在加载版本…" }], "");
  field.append(node("span", { text: "题目版本" }), select);
  safe(async () => {
    const groups = await allVersionOptions({ resourceId });
    select.replaceChildren(node("option", { text: placeholder, attrs: { value: "" } }));
    for (const group of groups) {
      const optgroup = node("optgroup", { attrs: { label: group.label } });
      for (const option of group.options) {
        optgroup.append(node("option", { text: option.label, attrs: { value: option.value } }));
      }
      select.append(optgroup);
    }
    if (!groups.length) select.replaceChildren(node("option", { text: "没有可用版本", attrs: { value: "" } }));
  });
  return { element: field, read: () => select.value };
}

function bankPicker() {
  const container = node("div", { className: "form-grid" });
  const bankSelect = selectInput([{ value: "", label: "正在加载题库…" }], "");
  const memberSelect = selectInput([{ value: "", label: "请先选择题库" }], "");
  const members = new Map();
  container.append(inputField("题库", bankSelect), inputField("成员", memberSelect));

  const loadMembers = async () => {
    memberSelect.replaceChildren(node("option", { text: "正在加载成员…", attrs: { value: "" } }));
    members.clear();
    if (!bankSelect.value) return;
    const result = await api(`/question-banks/${bankSelect.value}/members?page=1&page_size=100`);
    memberSelect.replaceChildren(node("option", {
      text: result.items.length ? "请选择成员" : "该题库暂无成员", attrs: { value: "" },
    }));
    for (const member of result.items) {
      members.set(member.member_id, member);
      memberSelect.append(node("option", {
        text: `${member.available ? (member.title || "（无标题）") : "不可用成员"} · v${shortId(member.version_id)}`,
        attrs: { value: member.member_id },
      }));
    }
  };
  bankSelect.addEventListener("change", () => safe(loadMembers));
  safe(async () => {
    const result = await api("/question-banks?page=1&page_size=100");
    bankSelect.replaceChildren(node("option", {
      text: result.items.length ? "请选择题库" : "暂无题库", attrs: { value: "" },
    }));
    for (const bank of result.items) {
      bankSelect.append(node("option", { text: bank.name, attrs: { value: bank.bank_id } }));
    }
    if (result.items.length === 1) {
      bankSelect.value = result.items[0].bank_id;
      await loadMembers();
    }
  });
  return {
    element: container,
    read: () => ({
      bank_id: bankSelect.value,
      member_id: memberSelect.value,
      member: members.get(memberSelect.value) || null,
    }),
  };
}

async function showResources(page = 1) {
  state.view = "resources";
  updateHeader();
  app.replaceChildren(node("div", { className: "loading", text: "正在读取资源…" }));
  const result = await api(`/question-resources?page=${page}&page_size=20`);
  app.replaceChildren(pageHeader(
    "题目资源库", "我的题目资源",
    `共 ${result.total} 个资源。资源包含不可变版本，可分享、入卷与统计。`,
    button("＋ 新建资源", () => renderResourceCreate(), "primary"),
  ));
  if (!result.items.length) {
    app.append(emptyBox("还没有题目资源", "新建资源后即可保存版本、分享给他人或入卷到问卷。"));
  } else {
    app.append(node("div", { className: "survey-list" }, result.items.map(resource => node("article", { className: "survey-card" }, [
      node("div", {}, [
        node("h3", { text: resource.title }),
        node("div", { className: "survey-meta" }, [
          node("span", { text: `最新版本 v${resource.last_version_number}` }),
          node("span", { text: `创建于 ${formatDate(resource.created_at)}` }),
          node("span", { className: "mono", text: resource.resource_id }),
        ]),
      ]),
      node("div", { className: "actions" }, [
        button("详情", () => safe(() => showResourceDetail(resource.resource_id)), "small primary"),
      ]),
    ]))));
  }
  appendPagination(app, result, showResources);
}

function renderResourceCreate() {
  state.view = "resource-create";
  updateHeader();
  app.replaceChildren(pageHeader("新建资源", "创建题目资源", "资源会自动产生版本 v1，可继续派生、分享或入卷。"));
  const editor = contentFields({});
  const form = node("form", { className: "panel stack" });
  form.append(...editor.elements);
  form.append(node("div", { className: "actions end" }, [
    button("取消", () => safe(showResources)),
    node("button", { className: "btn primary", attrs: { type: "submit" }, text: "创建资源" }),
  ]));
  form.addEventListener("submit", event => {
    event.preventDefault();
    safe(async () => {
      const created = await api("/question-resources", {
        method: "POST", body: { requestId: uniqueId(), ...editor.read() },
      });
      showToast("资源已创建。");
      await showResourceDetail(created.resource_id);
    });
  });
  app.append(form);
}

async function showResourceDetail(resourceId) {
  state.view = "resource-detail";
  updateHeader();
  app.replaceChildren(node("div", { className: "loading", text: "正在读取资源…" }));
  const detail = await api(`/question-resources/${resourceId}`);
  app.replaceChildren(pageHeader(
    "资源详情", "题目资源",
    `资源 ${detail.resource_id}，共 ${detail.versions.length} 个版本。`,
    button("返回资源库", () => safe(showResources)),
  ));
  const usageHolder = node("div", { className: "section" });
  app.append(node("div", { className: "toolbar" }, [
    button("资源级使用情况", () => safe(() => renderUsageSection(resourceId, null, usageHolder))),
  ]));
  app.append(usageHolder);
  for (const version of detail.versions) app.append(versionCard(resourceId, version));
}

function versionCard(resourceId, version) {
  const card = node("article", { className: "question-card" });
  const detail = node("div", { className: "stack section" });
  card.append(node("div", { className: "question-head" }, [
    node("div", {}, [
      node("h3", { text: `v${version.version_number} · ${CHANGE_TYPES[version.change_type] || version.change_type}` }),
      node("div", { className: "question-config" }, [
        node("span", { className: "badge", text: `版本号 ${version.version_number}` }),
        version.parent_version_id ? node("span", { className: "badge", text: `父版本 ${shortId(version.parent_version_id)}` }) : null,
      ]),
      node("p", { className: "hint", text: `版本 ID：${version.version_id}　创建于 ${formatDate(version.created_at)}` }),
    ]),
    node("div", { className: "actions" }, [
      button("查看内容", () => safe(async () => {
        const data = await api(`/question-resources/${resourceId}/versions/${version.version_id}`);
        detail.replaceChildren(contentSummary(data.content));
      }), "small"),
      button("使用情况", () => safe(() => renderUsageSection(resourceId, version.version_id, detail)), "small"),
      button("跨问卷统计", () => safe(() => renderVersionStatistics(resourceId, version.version_id, detail)), "small"),
      button("分享管理", () => safe(() => renderShareSection(resourceId, version.version_id, detail)), "small"),
      button("恢复为最新版本", () => safe(async () => {
        await api(`/question-resources/${resourceId}/versions/${version.version_id}/restore`, {
          method: "POST", body: { requestId: uniqueId() },
        });
        showToast("已恢复为新版本。");
        await showResourceDetail(resourceId);
      }), "small"),
      button("派生新版本", () => safe(() => renderDeriveForm(resourceId, version.version_id, detail)), "small"),
    ]),
  ]));
  card.append(detail);
  return card;
}

async function renderUsageSection(resourceId, versionId, container, page = 1) {
  container.replaceChildren(node("div", { className: "loading", text: "正在统计使用情况…" }));
  const scopePath = versionId
    ? `/question-resources/${resourceId}/versions/${versionId}/usage`
    : `/question-resources/${resourceId}/usage`;
  const data = await api(`${scopePath}?page=${page}&page_size=20`);
  const box = node("div", { className: "panel stack" });
  box.append(sectionTitle(`使用情况（${data.scope === "owner" ? "所有者视图" : "本人引用"}）`));
  if (data.scope === "owner") {
    box.append(node("div", { className: "survey-meta" }, [
      node("span", { text: `问卷总数 ${data.survey_count}` }),
      node("span", { text: `本人问卷 ${data.own_survey_count}` }),
      node("span", { text: `他人问卷 ${data.other_survey_count}` }),
    ]));
  }
  box.append(usageList(data.own_surveys));
  if (data.own_surveys.total > data.own_surveys.page_size) {
    box.append(paginationBar(
      data.own_surveys,
      () => renderUsageSection(resourceId, versionId, container, data.own_surveys.page - 1),
      () => renderUsageSection(resourceId, versionId, container, data.own_surveys.page + 1),
    ));
  }
  container.replaceChildren(box);
}

function usageList(pageData) {
  const list = node("div", { className: "stack" });
  list.append(node("p", { className: "hint", text: `本人引用问卷 ${pageData.total} 份（第 ${pageData.page} 页，每页 ${pageData.page_size}）。` }));
  if (!pageData.items.length) {
    list.append(node("p", { className: "muted", text: "暂无本人引用。" }));
    return list;
  }
  for (const form of pageData.items) {
    list.append(node("div", { className: "rule-card stack" }, [
      node("div", { className: "actions" }, [node("strong", { text: form.title }), statusBadge(form.status)]),
      node("p", { className: "hint", text: `卷内题：${form.questions.map(question => shortId(question.question_id)).join("，")}` }),
    ]));
  }
  return list;
}

async function renderVersionStatistics(resourceId, versionId, container, page = 1) {
  container.replaceChildren(node("div", { className: "loading", text: "正在计算统计…" }));
  const data = await api(`/question-resources/${resourceId}/versions/${versionId}/statistics?page=${page}&page_size=20`);
  const box = node("div", { className: "panel stack" });
  box.append(node("div", { className: "actions" }, [
    node("h3", { text: `v${data.version_number} 跨问卷统计` }),
    node("span", { className: "badge", text: TYPES[data.type] || data.type }),
  ]));
  box.append(node("p", { className: "hint", text: `${data.title}　有效问卷 ${data.survey_count} 份，有效回答 ${data.answer_count} 条` }));
  box.append(crossStatBody(resourceId, versionId, data, container));
  container.replaceChildren(box);
}

function crossStatBody(resourceId, versionId, data, container) {
  const body = node("div", { className: "stack" });
  const reload = page => () => renderVersionStatistics(resourceId, versionId, container, page);
  if (data.options) {
    const max = Math.max(1, ...data.options.map(option => option.count));
    for (const option of data.options) {
      body.append(node("div", { className: "stat-option" }, [
        node("span", { text: option.text }),
        node("div", { className: "bar-track" }, [
          node("div", { className: "bar-fill", attrs: { style: `width:${option.count / max * 100}%` } }),
        ]),
        node("span", { className: "stat-count", text: `${option.count}（${(option.ratio * 100).toFixed(1)}%）` }),
      ]));
    }
    return body;
  }
  if (data.type === "number") {
    const average = data.average === null || data.average === undefined
      ? "暂无" : new Intl.NumberFormat(undefined, { maximumFractionDigits: 4 }).format(data.average);
    body.append(node("div", { className: "metric", text: average }, [node("small", { text: "平均值" })]));
    body.append(node("p", { className: "hint", text: `最小值 ${data.min_value ?? "—"}，最大值 ${data.max_value ?? "—"}` }));
    const list = node("ul", { className: "content-list" });
    for (const item of data.values.items) list.append(node("li", { text: `${item.value}　出现 ${item.count} 次` }));
    if (!list.children.length) list.append(node("li", { className: "muted", text: "暂无有效回答" }));
    body.append(list);
    body.append(paginationBar(data.values, reload(data.values.page - 1), reload(data.values.page + 1)));
    return body;
  }
  const list = node("ul", { className: "content-list" });
  for (const item of data.contents.items) list.append(node("li", { text: String(item.value) }));
  if (!list.children.length) list.append(node("li", { className: "muted", text: "暂无有效回答" }));
  body.append(list);
  body.append(paginationBar(data.contents, reload(data.contents.page - 1), reload(data.contents.page + 1)));
  return body;
}

async function renderShareSection(resourceId, versionId, container, page = 1) {
  container.replaceChildren(node("div", { className: "loading", text: "正在读取共享授权…" }));
  const data = await api(`/question-resources/${resourceId}/versions/${versionId}/shares?page=${page}&page_size=20`);
  const box = node("div", { className: "panel stack" });
  box.append(sectionTitle("分享管理"));
  const recipient = textInput({ placeholder: "接收者完整用户名", required: true, max: 50 });
  const grantForm = node("form", { className: "form-grid" });
  grantForm.append(inputField("授予给", recipient));
  grantForm.append(node("div", { className: "actions end" }, [
    node("button", { className: "btn primary", attrs: { type: "submit" }, text: "授予访问" }),
  ]));
  grantForm.addEventListener("submit", event => {
    event.preventDefault();
    safe(async () => {
      const result = await api(`/question-resources/${resourceId}/versions/${versionId}/shares`, {
        method: "POST", body: { requestId: uniqueId(), recipient_username: recipient.value },
      });
      showToast(result.changed ? "已授予访问。" : "该用户已有有效授权。");
      await renderShareSection(resourceId, versionId, container, page);
    });
  });
  box.append(grantForm);
  box.append(node("p", { className: "hint", text: `已发出授权 ${data.total} 条（第 ${data.page} 页，每页 ${data.page_size}）。` }));
  const list = node("div", { className: "stack" });
  if (!data.items.length) list.append(node("p", { className: "muted", text: "暂无授权记录。" }));
  for (const share of data.items) {
    list.append(node("div", { className: "rule-card actions between" }, [
      node("div", {}, [
        node("div", { className: "actions" }, [
          node("strong", { text: share.recipient_username }),
          node("span", {
            className: `badge ${share.status === "active" ? "published" : "closed"}`,
            text: SHARE_STATUSES[share.status] || share.status,
          }),
        ]),
        node("p", {
          className: "hint",
          text: `授权修订号 ${share.authorization_revision}　启用 ${formatDate(share.authorized_at)}`
            + (share.revoked_at ? `　撤销 ${formatDate(share.revoked_at)}` : ""),
        }),
      ]),
      share.status === "active" ? button("撤销", () => safe(async () => {
        await api(`/question-resources/${resourceId}/versions/${versionId}/shares/${share.share_id}/revoke`, {
          method: "POST", body: { requestId: uniqueId() },
        });
        showToast("已撤销授权。");
        await renderShareSection(resourceId, versionId, container, page);
      }), "small danger") : null,
    ]));
  }
  box.append(list);
  if (data.total > data.page_size) {
    box.append(paginationBar(
      data,
      () => renderShareSection(resourceId, versionId, container, data.page - 1),
      () => renderShareSection(resourceId, versionId, container, data.page + 1),
    ));
  }
  container.replaceChildren(box);
}

async function renderDeriveForm(resourceId, versionId, container) {
  container.replaceChildren(node("div", { className: "loading", text: "正在读取版本内容…" }));
  const detail = await api(`/question-resources/${resourceId}/versions/${versionId}`);
  const editor = contentFields(detail.content || {});
  const form = node("form", { className: "panel stack" });
  form.append(sectionTitle(`从 v${detail.version_number} 派生新版本`));
  form.append(...editor.elements);
  form.append(node("div", { className: "actions end" }, [
    button("取消", () => container.replaceChildren()),
    node("button", { className: "btn primary", attrs: { type: "submit" }, text: "创建派生版本" }),
  ]));
  form.addEventListener("submit", event => {
    event.preventDefault();
    safe(async () => {
      await api(`/question-resources/${resourceId}/versions`, {
        method: "POST",
        body: { requestId: uniqueId(), parent_version_id: versionId, ...editor.read() },
      });
      showToast("已创建派生版本。");
      await showResourceDetail(resourceId);
    });
  });
  container.replaceChildren(form);
}

async function showReceived(page = 1) {
  state.view = "received";
  updateHeader();
  app.replaceChildren(node("div", { className: "loading", text: "正在读取收到的共享…" }));
  const result = await api(`/question-shares/received?page=${page}&page_size=20`);
  app.replaceChildren(pageHeader(
    "收到的共享", "共享给我的题目版本",
    `共 ${result.total} 条有效授权。可查看内容并 fork 为本人独立资源。`,
  ));
  if (!result.items.length) {
    app.append(emptyBox("暂无共享", "当他人把具体版本共享给你时，会显示在这里。"));
  } else {
    app.append(node("div", { className: "survey-list" }, result.items.map(share => node("article", { className: "survey-card" }, [
      node("div", {}, [
        node("h3", { text: share.title }),
        node("div", { className: "survey-meta" }, [
          node("span", { text: TYPES[share.type] || share.type }),
          node("span", { text: `来自 ${share.owner_username}` }),
          node("span", { text: `版本 v${share.version_number}` }),
          node("span", { text: `授权于 ${formatDate(share.authorized_at)}` }),
        ]),
      ]),
      node("div", { className: "actions" }, [
        button("查看内容", () => safe(() => showSharedVersion(share)), "small primary"),
      ]),
    ]))));
  }
  appendPagination(app, result, showReceived);
}

async function showSharedVersion(share) {
  state.view = "shared-version";
  updateHeader();
  app.replaceChildren(node("div", { className: "loading", text: "正在读取版本内容…" }));
  const detail = await api(`/question-resources/${share.resource_id}/versions/${share.version_id}`);
  app.replaceChildren(pageHeader(
    "共享版本", detail.content.title,
    `来自 ${share.owner_username} 的授权版本 v${detail.version_number}。`,
    button("返回", () => safe(showReceived)),
  ));
  app.append(contentSummary(detail.content));
  app.append(node("div", { className: "toolbar" }, [
    button("fork 为我的资源", () => safe(() => renderForkForm(share, detail, app)), "primary"),
  ]));
}

async function renderForkForm(share, detail, container) {
  const editor = contentFields(detail.content || {});
  const form = node("form", { className: "panel stack section" });
  form.append(sectionTitle(`fork 自 ${share.owner_username} 的版本 v${detail.version_number}`));
  form.append(...editor.elements);
  form.append(node("div", { className: "actions end" }, [
    button("取消", () => form.remove()),
    node("button", { className: "btn primary", attrs: { type: "submit" }, text: "创建独立资源" }),
  ]));
  form.addEventListener("submit", event => {
    event.preventDefault();
    safe(async () => {
      const created = await api(`/question-resources/${share.resource_id}/versions/${share.version_id}/fork`, {
        method: "POST", body: { requestId: uniqueId(), ...editor.read() },
      });
      showToast("已创建独立资源。");
      await showResourceDetail(created.resource_id);
    });
  });
  container.append(form);
}

async function showBanks(page = 1) {
  state.view = "banks";
  updateHeader();
  app.replaceChildren(node("div", { className: "loading", text: "正在读取题库…" }));
  const result = await api(`/question-banks?page=${page}&page_size=20`);
  app.replaceChildren(pageHeader(
    "题库", "我的题库",
    `共 ${result.total} 个题库。题库用于固定收录资源的具体版本。`,
    button("＋ 新建题库", () => renderBankCreate(), "primary"),
  ));
  if (!result.items.length) {
    app.append(emptyBox("还没有题库", "创建题库后可收录资源的具体版本。"));
  } else {
    app.append(node("div", { className: "survey-list" }, result.items.map(bank => node("article", { className: "survey-card" }, [
      node("div", {}, [
        node("h3", { text: bank.name }),
        node("div", { className: "survey-meta" }, [
          node("span", { text: bank.description || "暂无说明" }),
          node("span", { text: `创建于 ${formatDate(bank.created_at)}` }),
        ]),
      ]),
      node("div", { className: "actions" }, [
        button("管理", () => safe(() => showBankDetail(bank.bank_id)), "small primary"),
      ]),
    ]))));
  }
  appendPagination(app, result, showBanks);
}

function renderBankCreate() {
  state.view = "bank-create";
  updateHeader();
  app.replaceChildren(pageHeader("新建题库", "创建题库", "名称去掉首尾空白后需为 1-100 个字符。"));
  const name = textInput({ placeholder: "题库名称", required: true, max: 100 });
  const description = textArea("", "题库说明（可选，最多 1000 字符）", 3);
  const form = node("form", { className: "panel stack" });
  form.append(node("div", { className: "form-grid" }, [
    inputField("题库名称", name),
    inputField("题库说明", description),
  ]));
  form.append(node("div", { className: "actions end" }, [
    button("取消", () => safe(showBanks)),
    node("button", { className: "btn primary", attrs: { type: "submit" }, text: "创建题库" }),
  ]));
  form.addEventListener("submit", event => {
    event.preventDefault();
    safe(async () => {
      const created = await api("/question-banks", {
        method: "POST", body: { requestId: uniqueId(), name: name.value, description: description.value },
      });
      showToast("题库已创建。");
      await showBankDetail(created.bank_id);
    });
  });
  app.append(form);
}

async function showBankDetail(bankId, page = 1) {
  state.view = "bank-detail";
  updateHeader();
  app.replaceChildren(node("div", { className: "loading", text: "正在读取题库…" }));
  const bank = await api(`/question-banks/${bankId}`);
  const members = await api(`/question-banks/${bankId}/members?page=${page}&page_size=20`);
  app.replaceChildren(pageHeader("题库管理", bank.name, bank.description || "暂无题库说明。", button("返回题库", () => safe(showBanks))));
  app.append(bankEditPanel(bank));
  app.append(bankAddMemberPanel(bankId));
  app.append(node("section", { className: "section" }, [sectionTitle(`成员（${members.total}）`)]));
  if (!members.items.length) app.append(emptyBox("还没有成员", "从资源的具体版本收录进题库。"));
  else app.append(node("div", { className: "stack" }, members.items.map(member => bankMemberCard(bankId, member))));
  appendPagination(app, members, nextPage => showBankDetail(bankId, nextPage));
}

function bankEditPanel(bank) {
  const panel = node("section", { className: "panel stack" });
  panel.append(sectionTitle("修改题库信息"));
  const name = textInput({ value: bank.name, required: true, max: 100 });
  const description = textArea(bank.description || "", "题库说明", 3);
  panel.append(node("div", { className: "form-grid" }, [
    inputField("题库名称", name),
    inputField("题库说明", description),
  ]));
  panel.append(node("div", { className: "actions end" }, [
    button("保存修改", () => safe(async () => {
      await api(`/question-banks/${bank.bank_id}`, {
        method: "PATCH", body: { requestId: uniqueId(), name: name.value, description: description.value },
      });
      showToast("已保存修改。");
      await showBankDetail(bank.bank_id);
    }), "primary"),
    button("删除题库", () => safe(async () => {
      if (!confirm(`确定删除题库“${bank.name}”吗？仅清理题库关系，不删除资源、版本、授权或答卷。`)) return;
      const result = await api(`/question-banks/${bank.bank_id}/delete`, {
        method: "POST", body: { requestId: uniqueId() },
      });
      showToast(`题库已删除，移除成员 ${result.removed_member_count} 条。`);
      await showBanks();
    }), "danger"),
  ]));
  return panel;
}

function bankAddMemberPanel(bankId) {
  const panel = node("section", { className: "panel stack" });
  panel.append(sectionTitle("收录版本到题库"));
  const picker = versionPicker();
  panel.append(picker.element);
  panel.append(node("div", { className: "actions end" }, [
    button("收录为成员", () => safe(async () => {
      const versionId = picker.read();
      if (!versionId) throw new Error("请先选择资源与版本。");
      const result = await api(`/question-banks/${bankId}/members`, {
        method: "POST", body: { requestId: uniqueId(), version_id: versionId },
      });
      showToast(result.changed ? "已收录版本。" : "该资源同版本已收录，返回已有成员。");
      await showBankDetail(bankId);
    }), "primary"),
  ]));
  return panel;
}

function bankMemberCard(bankId, member) {
  const card = node("article", { className: "question-card" });
  card.append(node("div", { className: "question-head" }, [
    node("div", {}, [
      node("h3", { text: member.available ? (member.title || "（无标题）") : "不可用成员" }),
      node("div", { className: "question-config" }, [
        node("span", {
          className: `badge ${member.available ? "published" : "closed"}`,
          text: member.available ? (TYPES[member.type] || member.type) : "不可用",
        }),
        node("span", { className: "badge", text: `固定版本 ${shortId(member.version_id)}` }),
      ]),
      node("p", { className: "hint", text: `资源 ${shortId(member.resource_id)}　收录于 ${formatDate(member.added_at)}` }),
    ]),
    node("div", { className: "actions" }, [
      button("更新版本", () => safe(() => renderMemberSwitchForm(bankId, member, card)), "small"),
      button("移出", () => safe(async () => {
        await api(`/question-banks/${bankId}/members/${member.member_id}/remove`, {
          method: "POST", body: { requestId: uniqueId() },
        });
        showToast("已移出成员。");
        await showBankDetail(bankId);
      }), "small danger"),
    ]),
  ]));
  return card;
}

function renderMemberSwitchForm(bankId, member, card) {
  const panel = node("form", { className: "panel stack section" });
  panel.append(sectionTitle("更新成员版本"));
  const picker = versionPicker({ resourceId: member.resource_id });
  panel.append(picker.element);
  panel.append(node("p", { className: "hint", text: `当前版本：${member.version_id}。仅允许同一资源内更新。` }));
  panel.append(node("div", { className: "actions end" }, [
    button("取消", () => panel.remove()),
    node("button", { className: "btn primary", attrs: { type: "submit" }, text: "更新版本" }),
  ]));
  panel.addEventListener("submit", event => {
    event.preventDefault();
    safe(async () => {
      const versionId = picker.read();
      if (!versionId) throw new Error("请先选择目标版本。");
      const result = await api(`/question-banks/${bankId}/members/${member.member_id}/switch-version`, {
        method: "POST",
        body: { requestId: uniqueId(), expected_version_id: member.version_id, version_id: versionId },
      });
      showToast(result.changed ? "成员版本已更新。" : "版本未变化。");
      await showBankDetail(bankId);
    });
  });
  card.after(panel);
}

function importVersionPanel(form) {
  const panel = node("section", { className: "panel stack" });
  panel.append(sectionTitle("从资源版本入卷"));
  const picker = versionPicker();
  const required = checkInput("设为必答", false);
  panel.append(picker.element, required);
  panel.append(node("div", { className: "actions end" }, [
    button("入卷", () => safe(async () => {
      const versionId = picker.read();
      if (!versionId) throw new Error("请先选择版本。");
      const result = await api(`/surveys/${form.form_id}/questions/from-version`, {
        method: "POST",
        body: { requestId: uniqueId(), version_id: versionId, required: required.querySelector("input").checked },
      });
      showToast(`已入卷为第 ${result.order} 题。`);
      await openSurvey(form.form_id);
    }), "primary"),
  ]));
  return panel;
}

function importBankPanel(form) {
  const panel = node("section", { className: "panel stack" });
  panel.append(sectionTitle("从题库入卷"));
  const picker = bankPicker();
  const required = checkInput("设为必答", false);
  panel.append(picker.element, required);
  panel.append(node("div", { className: "actions end" }, [
    button("入卷", () => safe(async () => {
      const { bank_id, member_id, member } = picker.read();
      if (!member) throw new Error("请先选择题库与成员。");
      const result = await api(`/surveys/${form.form_id}/questions/from-bank`, {
        method: "POST",
        body: {
          requestId: uniqueId(), bank_id, member_id,
          expected_member_version_id: member.version_id,
          required: required.querySelector("input").checked,
        },
      });
      showToast(`已入卷为第 ${result.order} 题。`);
      await openSurvey(form.form_id);
    }), "primary"),
  ]));
  return panel;
}

async function openQuestionVersionPanel(form, question, container) {
  container.replaceChildren(node("div", { className: "loading", text: "正在读取关联…" }));
  let link = null;
  try {
    const result = await api(`/surveys/${form.form_id}/questions/${question.question_id}/source`);
    link = result && result.resource_id ? result : null;
  } catch {
    link = null;
  }
  const panel = node("div", { className: "panel stack" });
  panel.append(sectionTitle("版本关联"));
  panel.append(node("p", {
    className: "hint",
    text: link
      ? `当前关联资源 ${link.resource_id}，版本 ${link.version_id}，关联于 ${formatDate(link.linked_at)}。`
      : "当前尚未关联任何题目版本。",
  }));
  if (!link) panel.append(linkForm(form, question));
  panel.append(node("div", { className: "actions" }, [
    button("仅保存为独立资源", () => safe(async () => {
      const result = await api(`/surveys/${form.form_id}/questions/${question.question_id}/save`, {
        method: "POST", body: { requestId: uniqueId() },
      });
      showToast("已保存为独立资源。");
      await showResourceDetail(result.resource_id);
    }), "small"),
    !link ? button("保存并关联", () => safe(async () => {
      await api(`/surveys/${form.form_id}/questions/${question.question_id}/save-and-link`, {
        method: "POST", body: { requestId: uniqueId(), includeHistoricalAnswers: true },
      });
      showToast("已保存并关联。");
      await openSurvey(form.form_id);
    }), "small") : null,
  ]));
  if (link) {
    panel.append(switchForm(form, question, link));
    panel.append(deriveSwitchForm(form, question, link));
  }
  panel.append(node("div", { className: "actions" }, [
    button(question.validation.required ? "设为选答" : "设为必答", () => safe(async () => {
      await api(`/surveys/${form.form_id}/questions/${question.question_id}/required`, {
        method: "PATCH", body: { required: !question.validation.required },
      });
      showToast("必答设置已更新。");
      await openSurvey(form.form_id);
    }), "small"),
  ]));
  container.replaceChildren(panel);
}

function linkForm(form, question) {
  const wrap = node("div", { className: "stack" });
  const picker = versionPicker();
  const include = checkInput("包含历史答案（关联必须勾选）", true);
  wrap.append(sectionTitle("关联现有版本"), picker.element, include);
  wrap.append(node("div", { className: "actions end" }, [
    button("关联该版本", () => safe(async () => {
      const versionId = picker.read();
      if (!versionId) throw new Error("请先选择版本。");
      if (!include.querySelector("input").checked) throw new Error("关联现有版本需勾选包含历史答案。");
      await api(`/surveys/${form.form_id}/questions/${question.question_id}/link`, {
        method: "POST", body: { version_id: versionId, includeHistoricalAnswers: true },
      });
      showToast("已关联版本。");
      await openSurvey(form.form_id);
    }), "primary"),
  ]));
  return wrap;
}

function switchForm(form, question, link) {
  const wrap = node("div", { className: "stack" });
  const picker = versionPicker({ resourceId: link.resource_id });
  wrap.append(sectionTitle("换版（同一资源）"), picker.element);
  wrap.append(node("div", { className: "actions end" }, [
    button("切换到所选版本", () => safe(async () => {
      const versionId = picker.read();
      if (!versionId) throw new Error("请先选择目标版本。");
      await api(`/surveys/${form.form_id}/questions/${question.question_id}/switch-version`, {
        method: "POST",
        body: { requestId: uniqueId(), expected_version_id: link.version_id, version_id: versionId },
      });
      showToast("已切换版本。");
      await openSurvey(form.form_id);
    }), "primary"),
  ]));
  return wrap;
}

function deriveSwitchForm(form, question, link) {
  const wrap = node("div", { className: "stack" });
  wrap.append(sectionTitle("派生并换版（仅原资源所有者）"));
  const holder = node("div", { className: "stack" });
  const editor = contentFields({});
  const include = checkInput("确认按此内容创建新版本并切换关联", false);
  const formElement = node("form", { className: "stack" });
  formElement.append(...editor.elements, include);
  formElement.append(node("div", { className: "actions end" }, [
    node("button", { className: "btn primary", attrs: { type: "submit" }, text: "派生并换版" }),
  ]));
  formElement.addEventListener("submit", event => {
    event.preventDefault();
    safe(async () => {
      if (!include.querySelector("input").checked) throw new Error("请先确认派生并换版。");
      await api(`/surveys/${form.form_id}/questions/${question.question_id}/derive-and-switch`, {
        method: "POST",
        body: {
          requestId: uniqueId(), expected_version_id: link.version_id,
          parent_version_id: link.version_id, ...editor.read(),
        },
      });
      showToast("已派生新版本并切换关联。");
      await openSurvey(form.form_id);
    });
  });
  holder.append(formElement);
  wrap.append(holder);
  return wrap;
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
