(function () {
  const tokenKey = "gerenciamento_republica_token";
  const urls = window.RABBU_CONFIG.urls;
  const state = {
    currentUser: null,
    currentOverview: null,
    currentResumo: null,
    currentMoradores: [],
    draggedTaskId: null,
  };

  function getToken() {
    return localStorage.getItem(tokenKey);
  }

  function ensureAuthenticated() {
    if (!getToken()) {
      window.location.href = urls.login;
      return false;
    }
    return true;
  }

  function formatMoney(value) {
    return Number(value || 0).toLocaleString("pt-BR", {
      style: "currency",
      currency: "BRL",
    });
  }

  function formatDate(value) {
    if (!value) return "-";
    return new Date(`${value}T00:00:00`).toLocaleDateString("pt-BR");
  }

  function formatDateTime(value) {
    if (!value) return "-";
    return new Date(value).toLocaleString("pt-BR");
  }

  function showToast(msg, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    let icon = "fa-info";
    if (type === "success") icon = "fa-check";
    if (type === "danger") icon = "fa-xmark";
    if (type === "warning") icon = "fa-triangle-exclamation";
    toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${msg}</span>`;
    container.appendChild(toast);
    setTimeout(() => toast.classList.add("show"), 10);
    setTimeout(() => {
      toast.classList.remove("show");
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  async function apiFetch(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Token ${getToken()}`,
        ...(options.headers || {}),
      },
    });
    if (response.status === 401) {
      localStorage.removeItem(tokenKey);
      window.location.href = urls.login;
      throw new Error("Sessao expirada");
    }
    return response;
  }

  function openModal(id) {
    const element = document.getElementById(id);
    if (element) element.classList.add("active");
  }

  function closeModal(id) {
    const element = document.getElementById(id);
    if (element) element.classList.remove("active");
  }

  function bindModalEvents() {
    document.querySelectorAll("[data-open-modal]").forEach((button) => {
      button.addEventListener("click", () => openModal(button.dataset.openModal));
    });
    document.querySelectorAll("[data-close-modal]").forEach((button) => {
      button.addEventListener("click", () => closeModal(button.dataset.closeModal));
    });
    document.querySelectorAll(".modal-overlay").forEach((overlay) => {
      overlay.addEventListener("click", (event) => {
        if (event.target === overlay) {
          overlay.classList.remove("active");
        }
      });
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        document.querySelectorAll(".modal-overlay.active").forEach((overlay) => {
          overlay.classList.remove("active");
        });
      }
    });
  }

  function fillSelect(select, allowBlank) {
    if (!select) return;
    select.innerHTML = allowBlank ? '<option value="">Sem responsavel</option>' : "";
    state.currentMoradores.forEach((morador) => {
      const option = document.createElement("option");
      option.value = morador.id;
      option.textContent = morador.nome;
      select.appendChild(option);
    });
  }

  function applyUserUI() {
    const currentUser = state.currentUser;
    document.getElementById("header-user-name").textContent = currentUser.first_name || currentUser.username;
    const roleLabel = currentUser.morador_eh_admin ? "Admin da republica" : "Morador da republica";
    document.getElementById("header-user-role").textContent = currentUser.republica_nome
      ? `${roleLabel} - ${currentUser.republica_nome}`
      : "Sem republica";
    const avatar = document.getElementById("header-avatar-circle");
    const fallbackInitial = (currentUser.first_name || currentUser.username || "R")[0].toUpperCase();
    avatar.textContent = fallbackInitial;
    document.getElementById("sidebar-republica-nome").textContent = currentUser.republica_nome || "Sem republica";
    document.getElementById("sidebar-republica-id").textContent = currentUser.republica_id
      ? `ID ${currentUser.republica_id}`
      : "Sem vinculo";
  }

  function getMeuSaldo() {
    if (!state.currentUser || !state.currentResumo || !state.currentUser.morador_id) return null;
    return state.currentResumo.moradores.find((item) => item.id === state.currentUser.morador_id) || null;
  }

  function getSaldoDescriptor(valor) {
    if (Number(valor) > 0) {
      return { label: "Voce tem a receber", className: "badge-success" };
    }
    if (Number(valor) < 0) {
      return { label: "Voce precisa pagar", className: "badge-danger" };
    }
    return { label: "Tudo em dia", className: "badge-warning" };
  }

  async function loadCommonData() {
    const meResponse = await apiFetch(urls.authMe);
    state.currentUser = await meResponse.json();
    applyUserUI();

    if (!state.currentUser.republica_id) {
      throw new Error("Usuario sem republica");
    }

    const [overviewResponse, moradoresResponse, resumoResponse] = await Promise.all([
      apiFetch(urls.dashboardOverview),
      apiFetch("/api/moradores/"),
      apiFetch(`/api/republicas/${state.currentUser.republica_id}/resumo-financeiro/`),
    ]);

    state.currentOverview = await overviewResponse.json();
    state.currentMoradores = (await moradoresResponse.json()).filter((morador) => morador.ativo);
    state.currentResumo = await resumoResponse.json();
  }

  async function reloadFinancialSources() {
    const [overviewResponse, resumoResponse] = await Promise.all([
      apiFetch(urls.dashboardOverview),
      apiFetch(`/api/republicas/${state.currentUser.republica_id}/resumo-financeiro/`),
    ]);
    state.currentOverview = await overviewResponse.json();
    state.currentResumo = await resumoResponse.json();
  }

  function renderList(containerId, items, renderItem, emptyText) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = "";
    if (!items.length) {
      container.innerHTML = `<div class="empty-state">${emptyText}</div>`;
      return;
    }
    items.forEach((item) => container.appendChild(renderItem(item)));
  }

  async function bindLogout() {
    const logoutButton = document.getElementById("logout-button");
    if (!logoutButton) return;
    logoutButton.addEventListener("click", async () => {
      await apiFetch(urls.authLogout, { method: "POST" });
      localStorage.removeItem(tokenKey);
      window.location.href = urls.login;
    });
  }

  async function initPage(pageInitializer) {
    if (!ensureAuthenticated()) return;

    try {
      bindModalEvents();
      await bindLogout();
      await loadCommonData();
      await pageInitializer({
        state,
        urls,
        apiFetch,
        renderList,
        fillSelect,
        showToast,
        formatMoney,
        formatDate,
        formatDateTime,
        getMeuSaldo,
        getSaldoDescriptor,
        openModal,
        closeModal,
        reloadFinancialSources,
      });
    } catch (error) {
      if (error && error.message === "Usuario sem republica") {
        showToast("Seu usuario ainda nao esta vinculado a uma republica. Vamos para o cadastro.", "warning");
        setTimeout(() => {
          window.location.href = urls.cadastro;
        }, 1000);
        return;
      }
      showToast("Nao foi possivel carregar os dados da pagina.", "danger");
    }
  }

  window.RABBU_APP = {
    state,
    urls,
    initPage,
    apiFetch,
    renderList,
    fillSelect,
    showToast,
    formatMoney,
    formatDate,
    formatDateTime,
    getMeuSaldo,
    getSaldoDescriptor,
    openModal,
    closeModal,
    reloadFinancialSources,
  };
})();
