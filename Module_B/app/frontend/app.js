const authStatus = document.getElementById("authStatus");
const crudOutput = document.getElementById("crudOutput");
const portfolioOutput = document.getElementById("portfolioOutput");
const adminOutput = document.getElementById("adminOutput");
const roleBadge = document.getElementById("roleBadge");

let sessionToken = "";
let isAdminUser = false;
let currentRole = "guest";
let currentInternalRole = "staff";

const SQL_TABLES_EXTRACTED = [
  "members",
  "customers",
  "staff",
  "categories",
  "products",
  "suppliers",
  "purchase_orders",
  "purchase_order_items",
  "sales",
  "sale_items",
  "payments",
  "attendance",
  "projects",
];

const TABLES_BY_ROLE = {
  member: SQL_TABLES_EXTRACTED,
  staff: ["products", "attendance", "categories", "customers", "sales", "sale_items", "payments"],
  customer: ["products", "categories", "sales", "payments"],
};

const TABLE_ID_FIELD_MAP = {
  projects: "project_id",
  members: "member_id",
  products: "product_id",
  categories: "category_id",
  customers: "customer_id",
  staff: "staff_id",
  suppliers: "supplier_id",
  purchase_orders: "poid",
  purchase_order_items: "po_item_id",
  sales: "sale_id",
  sale_items: "sale_item_id",
  payments: "payment_id",
  attendance: "attendance_id",
};

const TABLE_PAYLOAD_TEMPLATES = {
  projects: {
    project_name: "Warehouse Automation",
    description: "RFID-based inventory tracking",
    status: "active",
  },
  members: {
    username: "newmember",
    email: "newmember@example.com",
    full_name: "New Member",
    department: "Operations",
    status: "active",
    created_at: "2026-03-22T10:30:48.371299",
    updated_at: "2026-03-22T10:30:48.371299",
  },
  staff: {
    name: "Store Staff",
    role: "Cashier",
    salary: 35000,
    contact_number: "9999999999",
    join_date: "2026-03-22",
    member_id: 1,
  },
  products: {
    name: "Barcode Scanner",
    price: 2499.0,
    stock_quantity: 30,
    reorder_level: 5,
    category_id: 1,
  },
  categories: {
    category_name: "Automation",
    description: "Automation tools and devices",
    created_at: "2026-03-22T10:30:48.371299",
  },
  customers: {
    name: "Customer Name",
    email: "customer@example.com",
    contact_number: "8888888888",
    loyalty_points: 0,
    created_at: "2026-03-22T10:30:48.371299",
  },
  suppliers: {
    name: "Supply Co",
    contact_number: "7777777777",
    email: "supply@example.com",
    address: "Main Road, City",
  },
  purchase_orders: {
    supplier_id: 1,
    order_date: "2026-03-22",
    total_amount: 12000.0,
    status: "pending",
  },
  purchase_order_items: {
    poid: 1,
    product_id: 1,
    quantity: 10,
    cost_price: 900.0,
  },
  sales: {
    customer_id: 1,
    staff_id: 1,
    sale_date: "2026-03-22",
    total_amount: 1500.0,
  },
  sale_items: {
    sale_id: 1,
    product_id: 1,
    quantity: 2,
    unit_price: 750.0,
  },
  payments: {
    sale_id: 1,
    payment_method: "UPI",
    amount: 1500.0,
    payment_date: "2026-03-22",
  },
  attendance: {
    staff_id: 1,
    entry_time: "09:00:00",
    exit_time: "18:00:00",
    work_date: "2026-03-22",
  },
};

function roleSelectEl() {
  return document.getElementById("portalRole");
}

function tableSelectEl() {
  return document.getElementById("tableSelect");
}

function renderTableOptions(tableNames) {
  const select = tableSelectEl();
  const current = select.value;
  select.innerHTML = "";

  tableNames.forEach((name) => {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    select.appendChild(option);
  });

  if (tableNames.includes(current)) {
    select.value = current;
    return;
  }

  if (tableNames.includes("projects")) {
    select.value = "projects";
  }

  applyPayloadTemplateForSelectedTable();
}

function applyTableVisibility() {
  const allowedTables = TABLES_BY_ROLE[currentRole] || [];
  renderTableOptions(allowedTables);
}

const controlsToToggle = [
  "meButton",
  "logoutButton",
  "listBtn",
  "getBtn",
  "portfolioListBtn",
  "portfolioOneBtn",
  "updateSelfPortfolioBtn",
];

const adminOnlyControls = [
  "createBtn",
  "updateBtn",
  "deleteBtn",
  "adminListGroupsBtn",
  "adminAddToGroupBtn",
  "adminRemoveFromGroupBtn",
  "adminUnauthorizedCheckBtn",
];

function setAuthenticated(enabled) {
  document.body.classList.toggle("logged-in", enabled);
  document.body.classList.toggle("logged-out", !enabled);

  controlsToToggle.forEach((id) => {
    document.getElementById(id).disabled = !enabled;
  });

  if (!enabled) {
    adminOnlyControls.forEach((id) => {
      document.getElementById(id).disabled = true;
    });
    renderTableOptions([]);
  }
}

function applyRolePermissions() {
  adminOnlyControls.forEach((id) => {
    document.getElementById(id).disabled = !isAdminUser;
  });
  const canUpdateSelfPortfolio = Boolean(sessionToken) && currentRole !== "customer";
  document.getElementById("updateSelfPortfolioBtn").disabled = !canUpdateSelfPortfolio;
  applyTableVisibility();
  roleBadge.textContent = `Role: ${currentRole}`;
}

function setOutput(el, data) {
  el.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

function formatWhoAmI(me, token = "") {
  const member = me.member || {};
  const groups = Array.isArray(me.groups) ? me.groups : [];
  const allowedTables = Array.isArray(me.allowed_tables) ? me.allowed_tables : [];
  const groupSummary = groups.length
    ? groups.map((g) => `${g.group_name} (${g.role_in_group})`).join(", ")
    : "None";

  const lines = [
    "Authenticated User",
    "------------------",
    `Username: ${member.username || "N/A"}`,
    `Member ID: ${member.member_id ?? "N/A"}`,
    `Full Name: ${member.full_name || "N/A"}`,
    `Email: ${member.email || "N/A"}`,
    `Department: ${member.department || "N/A"}`,
    `Status: ${member.status || "N/A"}`,
    `Portal Role: ${me.portal_role || currentRole}`,
    `Internal Role: ${me.role || currentInternalRole}`,
    `Admin: ${Boolean(me.is_admin)}`,
    `Groups: ${groupSummary}`,
    `Allowed Tables: ${allowedTables.join(", ") || "None"}`,
  ];

  if (token) {
    lines.push(`Session Token: ${token}`);
  }

  return lines.join("\n");
}

async function apiCall(path, options = {}) {
  return window.ApiService.call(path, options);
}

async function authenticate(username, password, selectedPortalRole) {
  const result = await apiCall("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password, portal_role: selectedPortalRole }),
  });

  sessionToken = result.session_token;
  window.ApiService.setToken(sessionToken);
  setAuthenticated(true);

  const me = await apiCall("/api/auth/me");
  currentRole = me.portal_role || result.portal_role || selectedPortalRole;
  currentInternalRole = me.role || result.role || "staff";
  isAdminUser = Boolean(me.is_admin);
  applyRolePermissions();
  setOutput(authStatus, formatWhoAmI(me, sessionToken));
  return { login: result, me };
}

function resetAuthState(messageText) {
  setAuthenticated(false);
  sessionToken = "";
  window.ApiService.setToken("");
  isAdminUser = false;
  currentRole = "guest";
  currentInternalRole = "staff";
  roleBadge.textContent = "";
  if (messageText) {
    setOutput(authStatus, messageText);
  } else {
    authStatus.textContent = "";
  }
}

document.getElementById("loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const selectedPortalRole = roleSelectEl().value;
  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;

  try {
    await authenticate(username, password, selectedPortalRole);
  } catch (error) {
    resetAuthState(`Login failed: ${error.message}`);
  }
});

document.getElementById("logoutButton").addEventListener("click", async () => {
  try {
    const result = await apiCall("/api/auth/logout", { method: "POST" });
    setOutput(authStatus, result);
  } catch (error) {
    setOutput(authStatus, `Logout failed: ${error.message}`);
  } finally {
    resetAuthState("");
  }
});

document.getElementById("meButton").addEventListener("click", async () => {
  try {
    const result = await apiCall("/api/auth/me");
    currentRole = result.portal_role || currentRole;
    currentInternalRole = result.role || currentInternalRole;
    isAdminUser = Boolean(result.is_admin);
    applyRolePermissions();
    setOutput(authStatus, formatWhoAmI(result, sessionToken));
  } catch (error) {
    setOutput(authStatus, `Request failed: ${error.message}`);
  }
});

function tableName() {
  return document.getElementById("tableSelect").value;
}

function recordId() {
  return document.getElementById("recordIdInput").value.trim();
}

function parsePayload() {
  const raw = document.getElementById("payloadInput").value;
  return JSON.parse(raw);
}

function applyPayloadTemplateForSelectedTable() {
  const selectedTable = tableName();
  const template = TABLE_PAYLOAD_TEMPLATES[selectedTable];
  if (!template) {
    return;
  }

  document.getElementById("payloadInput").value = JSON.stringify(template, null, 2);
}

document.getElementById("listBtn").addEventListener("click", async () => {
  try {
    const result = await apiCall(`/api/project/${tableName()}`);
    setOutput(crudOutput, result);
  } catch (error) {
    setOutput(crudOutput, `List failed: ${error.message}`);
  }
});

document.getElementById("getBtn").addEventListener("click", async () => {
  const id = recordId();
  if (!id) {
    setOutput(crudOutput, "Record ID is required");
    return;
  }

  try {
    const result = await apiCall(`/api/project/${tableName()}/${encodeURIComponent(id)}`);
    setOutput(crudOutput, result);
  } catch (error) {
    setOutput(crudOutput, `Read failed: ${error.message}`);
  }
});

document.getElementById("createBtn").addEventListener("click", async () => {
  try {
    const payload = parsePayload();
    const currentTable = tableName();
    const idValue = recordId();

    if (idValue) {
      const numericId = Number(idValue);
      if (!Number.isInteger(numericId)) {
        setOutput(crudOutput, "Record ID must be an integer when provided");
        return;
      }

      const idField = TABLE_ID_FIELD_MAP[currentTable];
      if (idField && payload[idField] == null) {
        payload[idField] = numericId;
      }

      if (payload.record_id == null) {
        payload.record_id = numericId;
      }
    }

    const result = await apiCall(`/api/project/${currentTable}`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    setOutput(crudOutput, result);
  } catch (error) {
    setOutput(crudOutput, `Create failed: ${error.message}`);
  }
});

document.getElementById("updateBtn").addEventListener("click", async () => {
  const id = recordId();
  if (!id) {
    setOutput(crudOutput, "Record ID is required");
    return;
  }

  try {
    const payload = parsePayload();
    const currentTable = tableName();
    const result = await apiCall(`/api/project/${currentTable}/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    setOutput(crudOutput, result);
  } catch (error) {
    setOutput(crudOutput, `Update failed: ${error.message}`);
  }
});

document.getElementById("deleteBtn").addEventListener("click", async () => {
  const id = recordId();
  if (!id) {
    setOutput(crudOutput, "Record ID is required");
    return;
  }

  try {
    const result = await apiCall(`/api/project/${tableName()}/${encodeURIComponent(id)}`, {
      method: "DELETE",
    });
    setOutput(crudOutput, result);
  } catch (error) {
    setOutput(crudOutput, `Delete failed: ${error.message}`);
  }
});

document.getElementById("portfolioListBtn").addEventListener("click", async () => {
  try {
    const result = await apiCall("/api/member-portfolio");
    setOutput(portfolioOutput, result);
  } catch (error) {
    setOutput(portfolioOutput, `Portfolio fetch failed: ${error.message}`);
  }
});

document.getElementById("portfolioOneBtn").addEventListener("click", async () => {
  const memberId = document.getElementById("portfolioMemberId").value.trim();
  if (!memberId) {
    setOutput(portfolioOutput, "Member ID is required");
    return;
  }

  try {
    const result = await apiCall(`/api/member-portfolio/${encodeURIComponent(memberId)}`);
    setOutput(portfolioOutput, result);
  } catch (error) {
    setOutput(portfolioOutput, `Member fetch failed: ${error.message}`);
  }
});

document.getElementById("updateSelfPortfolioBtn").addEventListener("click", async () => {
  try {
    const payload = JSON.parse(document.getElementById("selfPortfolioPayload").value);
    const result = await apiCall("/api/member-portfolio/me", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    setOutput(portfolioOutput, result);
  } catch (error) {
    setOutput(portfolioOutput, `Update self profile failed: ${error.message}`);
  }
});

function adminValues() {
  return {
    groupId: document.getElementById("adminGroupId").value.trim(),
    memberId: document.getElementById("adminMemberId").value.trim(),
    role: document.getElementById("adminRole").value,
  };
}

document.getElementById("adminListGroupsBtn").addEventListener("click", async () => {
  try {
    const result = await apiCall("/api/admin/groups");
    setOutput(adminOutput, result);
  } catch (error) {
    setOutput(adminOutput, `Admin list groups failed: ${error.message}`);
  }
});

document.getElementById("adminAddToGroupBtn").addEventListener("click", async () => {
  const { groupId, memberId, role } = adminValues();
  if (!groupId || !memberId) {
    setOutput(adminOutput, "Group ID and Member ID are required");
    return;
  }

  try {
    const result = await apiCall(`/api/admin/groups/${encodeURIComponent(groupId)}/members`, {
      method: "POST",
      body: JSON.stringify({ member_id: Number(memberId), role }),
    });
    setOutput(adminOutput, result);
  } catch (error) {
    setOutput(adminOutput, `Admin add member failed: ${error.message}`);
  }
});

document.getElementById("adminRemoveFromGroupBtn").addEventListener("click", async () => {
  const { groupId, memberId } = adminValues();
  if (!groupId || !memberId) {
    setOutput(adminOutput, "Group ID and Member ID are required");
    return;
  }

  try {
    const result = await apiCall(
      `/api/admin/groups/${encodeURIComponent(groupId)}/members/${encodeURIComponent(memberId)}`,
      { method: "DELETE" }
    );
    setOutput(adminOutput, result);
  } catch (error) {
    setOutput(adminOutput, `Admin remove member failed: ${error.message}`);
  }
});

tableSelectEl().addEventListener("change", () => {
  applyPayloadTemplateForSelectedTable();
});

document.getElementById("adminUnauthorizedCheckBtn").addEventListener("click", async () => {
  try {
    const result = await apiCall("/api/admin/audit/unauthorized-check");
    setOutput(adminOutput, result);
  } catch (error) {
    setOutput(adminOutput, `Unauthorized check failed: ${error.message}`);
  }
});

setAuthenticated(false);
applyRolePermissions();
roleBadge.textContent = "";
authStatus.textContent = "";
setOutput(crudOutput, "Login first to use CRUD endpoints.");
setOutput(portfolioOutput, "Login first to view member portfolio.");
setOutput(adminOutput, "Admin actions require admin role.");
