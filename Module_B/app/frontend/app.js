const authStatus = document.getElementById("authStatus");
const crudOutput = document.getElementById("crudOutput");
const portfolioOutput = document.getElementById("portfolioOutput");
const adminOutput = document.getElementById("adminOutput");
const roleBadge = document.getElementById("roleBadge");

let sessionToken = "";
let isAdminUser = false;

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
  controlsToToggle.forEach((id) => {
    document.getElementById(id).disabled = !enabled;
  });

  if (!enabled) {
    adminOnlyControls.forEach((id) => {
      document.getElementById(id).disabled = true;
    });
  }
}

function applyRolePermissions() {
  adminOnlyControls.forEach((id) => {
    document.getElementById(id).disabled = !isAdminUser;
  });
  roleBadge.textContent = isAdminUser
    ? "Role: Admin (full CRUD + group management)"
    : "Role: Regular User (read-only project data + update own portfolio)";
}

function setOutput(el, data) {
  el.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

async function apiCall(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (sessionToken) {
    headers.Authorization = `Bearer ${sessionToken}`;
  }
  const response = await fetch(path, { ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || `HTTP ${response.status}`);
  }
  return data;
}

document.getElementById("loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;

  try {
    const result = await apiCall("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    sessionToken = result.session_token;
    setAuthenticated(true);
    isAdminUser = false;
    try {
      const me = await apiCall("/api/auth/me");
      isAdminUser = Boolean(me.is_admin);
      applyRolePermissions();
    } catch (_) {
      isAdminUser = false;
      applyRolePermissions();
    }
    setOutput(authStatus, result);
  } catch (error) {
    setAuthenticated(false);
    sessionToken = "";
    isAdminUser = false;
    roleBadge.textContent = "Role: Not authenticated";
    setOutput(authStatus, `Login failed: ${error.message}`);
  }
});

document.getElementById("logoutButton").addEventListener("click", async () => {
  try {
    const result = await apiCall("/api/auth/logout", { method: "POST" });
    setOutput(authStatus, result);
  } catch (error) {
    setOutput(authStatus, `Logout failed: ${error.message}`);
  } finally {
    sessionToken = "";
    isAdminUser = false;
    setAuthenticated(false);
    roleBadge.textContent = "Role: Not authenticated";
  }
});

document.getElementById("meButton").addEventListener("click", async () => {
  try {
    const result = await apiCall("/api/auth/me");
    isAdminUser = Boolean(result.is_admin);
    applyRolePermissions();
    setOutput(authStatus, result);
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
    const result = await apiCall(`/api/project/${tableName()}`, {
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
    const result = await apiCall(`/api/project/${tableName()}/${encodeURIComponent(id)}`, {
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
setOutput(authStatus, "Not authenticated");
setOutput(crudOutput, "Login first to use CRUD endpoints.");
setOutput(portfolioOutput, "Login first to view member portfolio.");
setOutput(adminOutput, "Admin actions require admin role.");
