"use strict";

const $ = (id) => document.getElementById(id);
const views = ["view-login", "view-list", "view-customer"];

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function money(value) {
  return "₹" + Number(value).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function todayLocal() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
}

function say(text, ok) {
  const m = $("msg");
  m.textContent = text || "";
  m.className = ok ? "msg ok" : "msg";
}

function show(viewId) {
  views.forEach((v) => $(v).classList.toggle("hidden", v !== viewId));
  const loggedIn = viewId !== "view-login";
  $("who").classList.toggle("hidden", !loggedIn);
  say("");
}

// ---------- talking to the API ----------
async function api(path, method, body) {
  const headers = { "Content-Type": "application/json" };
  const token = localStorage.getItem("token");
  if (token) headers["Authorization"] = "Bearer " + token;
  let res;
  try {
    res = await fetch(path, {
      method: method || "GET",
      headers: headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (e) {
    return { ok: false, status: 0, data: { error: "Cannot reach the server." } };
  }
  let data = {};
  try { data = await res.json(); } catch (e) { /* no JSON body */ }
  if (res.status === 401 && token) {
    logout("Your session ended. Please log in again.");
  }
  return { ok: res.ok, status: res.status, data: data };
}

// ---------- login / signup / logout ----------
async function auth(kind) {
  const email = $("email").value.trim();
  const password = $("password").value;
  const r = await api("/api/" + kind, "POST", { email: email, password: password });
  if (!r.ok) { say(r.data.error || "Something went wrong."); return; }
  if (kind === "signup") {
    say("Account created. Now click Log in.", true);
    return;
  }
  localStorage.setItem("token", r.data.token);
  localStorage.setItem("email", email);
  $("password").value = "";
  route();
}

function logout(message) {
  localStorage.removeItem("token");
  localStorage.removeItem("email");
  location.hash = "#/";
  show("view-login");
  if (message) say(message);
}

// ---------- customer list ----------
async function showList() {
  show("view-list");
  const r = await api("/api/summary");
  if (!r.ok) { say(r.data.error || "Could not load customers."); return; }

  const list = $("list");
  list.textContent = "";
  let total = 0;

  if (r.data.length === 0) {
    list.appendChild(el("p", "muted", "No customers yet. Add your first one below."));
  }

  r.data.forEach((c) => {
    const bal = Number(c.balance);
    if (bal > 0) total += bal;

    const row = el("a", "row");
    row.href = "#/customer/" + c.id;

    const left = el("div");
    left.appendChild(el("div", "", c.name));
    left.appendChild(el("div", "muted", c.phone || ""));

    let right;
    if (bal > 0) right = el("div", "owes", money(bal) + " owes you");
    else if (bal < 0) right = el("div", "advance", money(-bal) + " advance");
    else right = el("div", "settled", "settled");

    row.appendChild(left);
    row.appendChild(right);
    list.appendChild(row);
  });

  $("total").textContent = money(total);
}

async function addCustomer() {
  const name = $("cname").value.trim();
  const phone = $("cphone").value.trim();
  if (!name) { say("Please enter a name."); return; }
  const r = await api("/api/customers", "POST", { name: name, phone: phone });
  if (!r.ok) { say(r.data.error || "Could not add customer."); return; }
  $("cname").value = "";
  $("cphone").value = "";
  await showList();
  say("Customer added.", true);
}

// ---------- one customer ----------
async function showCustomer(id) {
  show("view-customer");
  $("edate").value = todayLocal();

  const [sum, ent] = await Promise.all([
    api("/api/summary"),
    api("/api/customers/" + id + "/entries"),
  ]);
  if (!ent.ok) { say(ent.data.error || "Customer not found."); return; }

  const me = (sum.data || []).find((c) => String(c.id) === String(id));
  $("c-name").textContent = me ? me.name : "Customer";
  $("c-phone").textContent = me && me.phone ? me.phone : "";

  const bal = Number(ent.data.balance);
  const balEl = $("c-balance");
  if (bal > 0) {
    $("c-balance-label").textContent = "Owes you";
    balEl.textContent = money(bal);
    balEl.className = "big owes";
  } else if (bal < 0) {
    $("c-balance-label").textContent = "Paid in advance";
    balEl.textContent = money(-bal);
    balEl.className = "big advance";
  } else {
    $("c-balance-label").textContent = "Balance";
    balEl.textContent = "Settled";
    balEl.className = "big settled";
  }

  const box = $("entries");
  box.textContent = "";
  if (ent.data.entries.length === 0) {
    box.appendChild(el("p", "muted", "No entries yet."));
  }
  ent.data.entries.forEach((e) => {
    const row = el("div", "row");
    const left = el("div");
    left.appendChild(el("div", "", e.type === "credit" ? "Credit given" : "Payment received"));
    left.appendChild(el("div", "entry-note", e.entry_date + (e.note ? " · " + e.note : "")));
    row.appendChild(left);
    row.appendChild(el("div", e.type, (e.type === "credit" ? "+" : "−") + money(e.amount)));
    box.appendChild(row);
  });
}

async function addEntry(id) {
  const amount = $("eamount").value.trim();
  if (!amount || isNaN(Number(amount)) || Number(amount) <= 0) {
    say("Enter an amount above zero.");
    return;
  }
  const r = await api("/api/customers/" + id + "/entries", "POST", {
    type: $("etype").value,
    amount: amount,
    note: $("enote").value.trim(),
    entry_date: $("edate").value,
  });
  if (!r.ok) { say(r.data.error || "Could not save entry."); return; }
  $("eamount").value = "";
  $("enote").value = "";
  await showCustomer(id);
  say("Entry saved.", true);
}

// ---------- which page to show ----------
function route() {
  const token = localStorage.getItem("token");
  if (!token) { show("view-login"); return; }
  $("who-email").textContent = localStorage.getItem("email") || "";
  const m = location.hash.match(/^#\/customer\/(\d+)$/);
  if (m) showCustomer(m[1]); else showList();
}

$("btn-login").addEventListener("click", () => auth("login"));
$("btn-signup").addEventListener("click", () => auth("signup"));
$("logout").addEventListener("click", () => logout());
$("btn-add-customer").addEventListener("click", addCustomer);
$("btn-add-entry").addEventListener("click", () => {
  const m = location.hash.match(/^#\/customer\/(\d+)$/);
  if (m) addEntry(m[1]);
});
$("password").addEventListener("keydown", (e) => { if (e.key === "Enter") auth("login"); });
window.addEventListener("hashchange", route);

route();
