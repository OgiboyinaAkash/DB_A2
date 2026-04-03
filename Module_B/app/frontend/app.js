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
];

const TABLES_BY_ROLE = {
  member: SQL_TABLES_EXTRACTED,
  staff: ["products", "attendance", "categories", "customers", "sales", "sale_items", "payments"],
  customer: ["products", "categories", "sales", "payments"],
};

const TABLE_ID_FIELD_MAP = {
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
  members: {
    name: "John Doe",
    age: 32,
    email: "john.doe@outlet.com",
    contact_number: "9876543210",
    role: "Manager",
    image: "john.jpg",
    created_at: "2026-03-22T10:30:48",
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

  if (tableNames.length > 0) {
    select.value = tableNames[0];
  }

  generateFormForSelectedTable();
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

function showPage(pageName) {
  // Hide all pages
  document.querySelectorAll(".content-page").forEach((page) => {
    page.classList.remove("active");
  });
  
  // Remove active from all nav buttons
  document.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.classList.remove("active");
  });
  
  // Show selected page
  const page = document.getElementById(`${pageName}-page`);
  if (page) {
    page.classList.add("active");
  }
  
  // Mark nav button as active
  const navBtn = document.querySelector(`[data-page="${pageName}"]`);
  if (navBtn) {
    navBtn.classList.add("active");
  }
}

function showUserInfo() {
  const modal = document.getElementById("userInfoPanel");
  if (modal) {
    modal.style.display = "flex";
  }
}

function hideUserInfo() {
  const modal = document.getElementById("userInfoPanel");
  if (modal) {
    modal.style.display = "none";
  }
}

function setAuthenticated(enabled) {
  const loginScreen = document.querySelector(".login-screen");
  const appScreen = document.querySelector(".app-screen");
  
  if (enabled) {
    // Hide login, show app
    if (loginScreen) loginScreen.style.display = "none";
    if (appScreen) appScreen.style.display = "flex";
    document.body.classList.add("logged-in");
    document.body.classList.remove("logged-out");
    
    // Don't show any page by default - user must click a nav tab
  } else {
    // Show login, hide app
    if (loginScreen) loginScreen.style.display = "flex";
    if (appScreen) appScreen.style.display = "none";
    document.body.classList.remove("logged-in");
    document.body.classList.add("logged-out");
    
    // Hide user info modal
    hideUserInfo();
    
    // Clear form
    document.getElementById("username").value = "";
    document.getElementById("password").value = "";
  }

  controlsToToggle.forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.disabled = !enabled;
  });

  if (!enabled) {
    adminOnlyControls.forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.disabled = true;
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

function setProfileOutput(content) {
  const el = document.getElementById("portfolioOutput");
  if (typeof content === "string") {
    if (content.includes("failed") || content.includes("error")) {
      el.innerHTML = `<div class="empty-state"><p>❌ ${content}</p></div>`;
    } else {
      el.innerHTML = `<div class="profile-card"><p style="color: var(--success);">✅ ${content}</p></div>`;
    }
  } else {
    el.innerHTML = typeof content === "string" ? content : JSON.stringify(content, null, 2);
  }
}

function createProfileCard(member, groups = []) {
  if (!member) return "";
  
  const memberData = member.member || member;
  const memberGroups = groups || member.groups || [];
  
  let html = '<div class="profile-card">';
  html += `<h3>👤 ${memberData.full_name || "Member Profile"}</h3>`;
  html += '<div class="profile-fields">';
  
  // Display key fields
  const fields = {
    "ID": memberData.member_id || "N/A",
    "Username": memberData.username || "N/A",
    "Full Name": memberData.full_name || "N/A",
    "Email": memberData.email || "N/A",
    "Contact": memberData.contact_number || "N/A",
    "Department": memberData.department || "N/A",
    "Age": memberData.age || "N/A",
    "Status": memberData.status || "N/A"
  };
  
  Object.entries(fields).forEach(([label, value]) => {
    if (value !== "N/A" || memberData[label.toLowerCase()]) {
      html += `<div class="profile-field">
        <div class="profile-field-label">${label}</div>
        <div class="profile-field-value">${value || "—"}</div>
      </div>`;
    }
  });
  
  html += '</div>';
  
  // Display groups if any
  if (memberGroups && memberGroups.length > 0) {
    html += '<div class="groups-list"><strong>📊 Groups Assigned:</strong>';
    memberGroups.forEach(group => {
      const groupName = group.group_name || "Unknown";
      const role = group.role_in_group || group.role_in_group || "member";
      html += `<div class="group-item">${groupName} <span class="group-role">(${role})</span></div>`;
    });
    html += '</div>';
  }
  
  html += '</div>';
  return html;
}

function displayProfileList(data) {
  const el = document.getElementById("portfolioOutput");
  if (!data || !data.records || data.records.length === 0) {
    el.innerHTML = '<div class="empty-state"><p>No profiles found</p></div>';
    return;
  }
  
  let html = '<div class="profiles-grid">';
  data.records.forEach(record => {
    const member = record.data || record;
    const groups = member.groups || [];
    html += createProfileCard(member, groups);
  });
  html += '</div>';
  el.innerHTML = html;
}

function displayProfileDetail(data) {
  const el = document.getElementById("portfolioOutput");
  if (!data) {
    el.innerHTML = '<div class="empty-state"><p>Member not found</p></div>';
    return;
  }
  
  const member = data.member || data;
  const groups = data.groups || [];
  const html = createProfileCard(member, groups);
  el.innerHTML = html;
}

function formatRecordsTable(data, tableName) {
  if (!data || !data.records || data.records.length === 0) {
    return '<div class="empty-state"><p>No records found</p></div>';
  }

  let html = '<div class="table-display"><table class="data-table"><thead><tr>';
  
  // Get column headers from first record
  const firstRecord = data.records[0]?.data || data.records[0];
  const columns = Object.keys(firstRecord || {});
  
  if (columns.length === 0) {
    return '<div class="empty-state"><p>No data to display</p></div>';
  }
  
  // Create headers
  columns.forEach(col => {
    html += `<th>${col}</th>`;
  });
  html += '</tr></thead><tbody>';
  
  // Create rows
  data.records.forEach(record => {
    const rowData = record.data || record;
    html += '<tr>';
    columns.forEach(col => {
      let value = rowData[col];
      
      // Format value
      if (value === null || value === undefined) {
        value = '—';
      } else if (typeof value === 'object') {
        value = JSON.stringify(value).substring(0, 50);
      } else if (typeof value === 'string' && value.length > 50) {
        value = value.substring(0, 50) + '...';
      }
      
      html += `<td>${value}</td>`;
    });
    html += '</tr>';
  });
  
  html += '</tbody></table></div>';
  return html;
}

function formatGroupsList(data) {
  // Handle both "groups" and "records" keys from API
  const groups = data?.groups || data?.records || [];
  
  if (!groups || groups.length === 0) {
    return '<div class="empty-state"><p>No groups found</p></div>';
  }

  let html = '<div class="groups-display">';
  
  groups.forEach(group => {
    const members = group.members || [];
    
    html += `<div class="group-card">
      <h4>👥 ${group.group_name || 'Unknown Group'}</h4>
      <div class="group-details">
        <div class="detail-row"><span class="label">ID:</span> <span class="value">${group.group_id || 'N/A'}</span></div>
        <div class="detail-row"><span class="label">Created:</span> <span class="value">${group.created_at || 'N/A'}</span></div>`;
    
    if (group.description) {
      html += `<div class="detail-row"><span class="label">Description:</span> <span class="value">${group.description}</span></div>`;
    }
    
    // Display members in this group
    html += `<div class="detail-row"><span class="label">Members:</span> <span class="value">`;
    if (members && members.length > 0) {
      html += `<div class="members-list">`;
      members.forEach(member => {
        const memberId = member.member_id || 'N/A';
        const memberName = member.full_name || member.username || 'Unknown';
        html += `<div class="member-item">
          <span class="member-id">#${memberId}</span> 
          <span class="member-name">${memberName}</span>
        </div>`;
      });
      html += `</div>`;
    } else {
      html += `<em>No members</em>`;
    }
    html += `</span></div>`;
    
    html += `</div></div>`;
  });
  
  html += '</div>';
  return html;
}

function formatWhoAmI(me, token = "") {
  const member = me.member || {};
  const groups = Array.isArray(me.groups) ? me.groups : [];
  const allowedTables = Array.isArray(me.allowed_tables) ? me.allowed_tables : [];
  const groupSummary = groups.length
    ? groups.map((g) => `${g.group_name} (${g.role_in_group})`).join(", ")
    : "None";

  const lines = [
    "🔐 Authenticated User Session",
    "─────────────────────────────",
    `👤 Username: ${member.username || "N/A"}`,
    `🆔 Member ID: ${member.member_id ?? "N/A"}`,
    `📧 Email: ${member.email || "N/A"}`,
    `📱 Contact: ${member.contact_number || "N/A"}`,
    `👔 Role: ${member.role || "N/A"}`,
    `📅 Age: ${member.age || "N/A"}`,
    `✅ Account Status: ${member.status || "N/A"}`,
    `🎯 Portal Role: ${me.portal_role || currentRole}`,
    `🔑 Internal Role: ${me.role || currentInternalRole}`,
    `⚙️ Admin Access: ${Boolean(me.is_admin) ? "Yes" : "No"}`,
    `👥 Groups: ${groupSummary}`,
    `📊 Allowed Tables: ${allowedTables.join(", ") || "None"}`,
  ];

  if (token) {
    lines.push(`🔐 Session Token: ${token.substring(0, 30)}...`);
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
    console.log("Logout result:", result);
  } catch (error) {
    console.log("Logout error:", error.message);
  } finally {
    resetAuthState("");
    setAuthenticated(false);
  }
});

document.getElementById("meButton").addEventListener("click", async () => {
  try {
    const result = await apiCall("/api/auth/me");
    currentRole = result.portal_role || currentRole;
    currentInternalRole = result.role || currentInternalRole;
    isAdminUser = Boolean(result.is_admin);
    applyRolePermissions();
    
    // Show the modal with user info
    const authStatusEl = document.getElementById("authStatus");
    setOutput(authStatusEl, formatWhoAmI(result, sessionToken));
    showUserInfo();
  } catch (error) {
    alert(`Failed to load user info: ${error.message}`);
  }
});

// Close user info modal when clicking close button
const closeBtn = document.querySelector(".close-btn");
if (closeBtn) {
  closeBtn.addEventListener("click", hideUserInfo);
}

// Close modal when clicking outside content
const userInfoModal = document.getElementById("userInfoPanel");
if (userInfoModal) {
  userInfoModal.addEventListener("click", (e) => {
    if (e.target === userInfoModal) {
      hideUserInfo();
    }
  });
}

// Navigation menu handlers
document.querySelectorAll(".nav-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const page = btn.getAttribute("data-page");
    if (page) {
      showPage(page);
    }
  });
});

function tableName() {
  return document.getElementById("tableSelect").value;
}

function recordId() {
  return document.getElementById("recordIdInput").value.trim();
}

function parsePayload() {
  const form = document.getElementById("payloadForm");
  const payload = {};
  const fields = form.querySelectorAll("[data-field-name]");
  
  fields.forEach((field) => {
    const fieldName = field.getAttribute("data-field-name");
    const fieldType = field.getAttribute("data-field-type") || "text";
    let value = field.value.trim();
    
    if (!value) return; // Skip empty fields
    
    // Type conversion
    if (fieldType === "number" || fieldType === "float") {
      value = isNaN(value) ? value : parseFloat(value);
    } else if (fieldType === "int") {
      value = isNaN(value) ? value : parseInt(value);
    }
    
    payload[fieldName] = value;
  });
  
  // Auto-add created_at if not already set
  if (!payload.created_at) {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    payload.created_at = `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
  }
  
  return payload;
}

function generateFormForSelectedTable() {
  const selectedTable = tableName();
  const template = TABLE_PAYLOAD_TEMPLATES[selectedTable];
  const form = document.getElementById("payloadForm");
  
  if (!template) {
    form.innerHTML = "<p style='color: var(--text-tertiary);'>No template available</p>";
    return;
  }
  
  form.innerHTML = "";
  
  const fieldTypes = {
    // Numeric fields
    age: "int", poid: "int", po_item_id: "int", quantity: "int",
    stock_quantity: "int", reorder_level: "int", member_id: "int",
    category_id: "int", product_id: "int", staff_id: "int",
    customer_id: "int", supplier_id: "int", sale_id: "int",
    attendance_id: "int", payment_id: "int", sale_item_id: "int",
    
    price: "float", salary: "float", unit_price: "float",
    total_amount: "float", cost_price: "float", amount: "float",
    loyalty_points: "int",
  };
  
  const autoGeneratedFields = ["created_at", "updated_at", "id"];
  
  Object.entries(template).forEach(([key, value]) => {
    // Skip auto-generated fields
    if (autoGeneratedFields.includes(key)) {
      return;
    }
    
    const formGroup = document.createElement("div");
    formGroup.className = "form-group";
    
    const label = document.createElement("label");
    label.innerHTML = `<span>${key}</span>`;
    
    const input = document.createElement("input");
    input.type = "text";
    input.setAttribute("data-field-name", key);
    input.setAttribute("data-field-type", fieldTypes[key] || "text");
    input.placeholder = typeof value === "string" ? value : JSON.stringify(value);
    input.value = "";
    
    const typeHint = document.createElement("span");
    typeHint.className = "field-type";
    typeHint.textContent = fieldTypes[key] || "text";
    label.appendChild(typeHint);
    
    formGroup.appendChild(label);
    formGroup.appendChild(input);
    form.appendChild(formGroup);
  });
}

document.getElementById("listBtn").addEventListener("click", async () => {
  try {
    const result = await apiCall(`/api/project/${tableName()}`);
    const table = tableName();
    const html = formatRecordsTable(result, table);
    crudOutput.innerHTML = html;
  } catch (error) {
    crudOutput.innerHTML = `<div class="empty-state"><p>❌ List failed: ${error.message}</p></div>`;
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
    displayProfileList(result);
  } catch (error) {
    setProfileOutput(`Portfolio fetch failed: ${error.message}`);
  }
});

document.getElementById("portfolioOneBtn").addEventListener("click", async () => {
  const memberId = document.getElementById("portfolioMemberId").value.trim();
  if (!memberId) {
    setProfileOutput("Member ID is required");
    return;
  }

  try {
    const result = await apiCall(`/api/member-portfolio/${encodeURIComponent(memberId)}`);
    displayProfileDetail(result);
  } catch (error) {
    setProfileOutput(`Member fetch failed: ${error.message}`);
  }
});

document.getElementById("updateSelfPortfolioBtn").addEventListener("click", async () => {
  try {
    const form = document.getElementById("profileUpdateForm");
    const payload = {};
    const fields = form.querySelectorAll("[data-field-name]");
    
    fields.forEach((field) => {
      const fieldName = field.getAttribute("data-field-name");
      const value = field.value.trim();
      if (value) {
        payload[fieldName] = value;
      }
    });
    
    if (Object.keys(payload).length === 0) {
      setProfileOutput("Please fill in at least one field");
      return;
    }

    const result = await apiCall("/api/member-portfolio/me", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    setProfileOutput(result.message || "Profile updated successfully");
    // Clear form after successful update
    form.querySelectorAll("input").forEach(input => input.value = "");
  } catch (error) {
    setProfileOutput(`Update self profile failed: ${error.message}`);
  }
});

function adminValues() {
  return {
    groupId: document.getElementById("adminGroupId").value.trim(),
    memberId: document.getElementById("adminMemberId").value.trim(),
  };
}

document.getElementById("adminListGroupsBtn").addEventListener("click", async () => {
  try {
    const result = await apiCall("/api/admin/groups");
    const html = formatGroupsList(result);
    adminOutput.innerHTML = html;
  } catch (error) {
    adminOutput.innerHTML = `<div class="empty-state"><p>❌ List groups failed: ${error.message}</p></div>`;
  }
});

document.getElementById("adminAddToGroupBtn").addEventListener("click", async () => {
  const { groupId, memberId } = adminValues();
  if (!groupId || !memberId) {
    setOutput(adminOutput, "Group ID and Member ID are required");
    return;
  }

  try {
    const result = await apiCall(`/api/admin/groups/${encodeURIComponent(groupId)}/members`, {
      method: "POST",
      body: JSON.stringify({ member_id: Number(memberId), role: "member" }),
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
  generateFormForSelectedTable();
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
