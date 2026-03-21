const ApiService = (() => {
  let sessionToken = "";

  function setToken(token) {
    sessionToken = token || "";
  }

  function getToken() {
    return sessionToken;
  }

  async function call(path, options = {}) {
    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    };

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

  return {
    setToken,
    getToken,
    call,
  };
})();

window.ApiService = ApiService;
