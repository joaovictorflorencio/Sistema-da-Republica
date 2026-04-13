(function () {
  const tokenKey = "gerenciamento_republica_token";
  const token = localStorage.getItem(tokenKey);
  const page = document.body.dataset.page;
  const urls = window.RABBU_CONFIG.urls;
  let currentUser = null;
  let currentOverview = null;
  let currentResumo = null;
  let currentMoradores = [];
  let draggedTaskId = null;

  if (!token) {
    window.location.href = urls.login;
    return;
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
        Authorization: `Token ${token}`,
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
    currentMoradores.forEach((morador) => {
      const option = document.createElement("option");
      option.value = morador.id;
      option.textContent = morador.nome;
      select.appendChild(option);
    });
  }

  function applyUserUI() {
    document.getElementById("header-user-name").textContent = currentUser.first_name || currentUser.username;
    document.getElementById("header-user-role").textContent = currentUser.republica_nome || "Sem republica";
    document.getElementById("header-avatar-circle").textContent =
      (currentUser.first_name || currentUser.username || "R")[0].toUpperCase();
    document.getElementById("sidebar-republica-nome").textContent = currentUser.republica_nome || "Sem republica";
    document.getElementById("sidebar-republica-id").textContent = currentUser.republica_id
      ? `ID ${currentUser.republica_id}`
      : "Sem vinculo";
  }

  function getMeuSaldo() {
    if (!currentUser || !currentResumo || !currentUser.morador_id) return null;
    return currentResumo.moradores.find((item) => item.id === currentUser.morador_id) || null;
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
    currentUser = await meResponse.json();
    applyUserUI();

    if (!currentUser.republica_id) {
      throw new Error("Usuario sem republica");
    }

    const [overviewResponse, moradoresResponse, resumoResponse] = await Promise.all([
      apiFetch(urls.dashboardOverview),
      apiFetch("/api/moradores/"),
      apiFetch(`/api/republicas/${currentUser.republica_id}/resumo-financeiro/`),
    ]);

    currentOverview = await overviewResponse.json();
    currentMoradores = await moradoresResponse.json();
    currentResumo = await resumoResponse.json();
  }

  function renderList(containerId, items, renderItem, emptyText) {
    const container = document.getElementById(containerId);
    container.innerHTML = "";
    if (!items.length) {
      container.innerHTML = `<div class="empty-state">${emptyText}</div>`;
      return;
    }
    items.forEach((item) => container.appendChild(renderItem(item)));
  }

  function renderDashboard() {
    const saldo = getMeuSaldo();
    document.getElementById("dashboard-user-saldo").textContent = formatMoney(saldo ? saldo.saldo : 0);
    const badge = document.getElementById("dashboard-saldo-badge");
    if (saldo && Number(saldo.saldo) >= 0) {
      badge.className = "badge badge-success";
      badge.textContent = "A receber";
    } else {
      badge.className = "badge badge-danger";
      badge.textContent = "A pagar";
    }

    document.getElementById("dashboard-total-casa").textContent = formatMoney(currentOverview.total_despesas);
    document.getElementById("dashboard-total-contas").textContent =
      `${currentOverview.ultimas_despesas.length} despesas recentes`;
    document.getElementById("dashboard-moradores-count").textContent = currentOverview.total_moradores;
    document.getElementById("dashboard-tarefas-count").textContent = currentOverview.total_tarefas_pendentes;

    const minhaTarefa = currentOverview.tarefas_pendentes.find(
      (item) => currentUser.morador_id && item.responsavel === currentUser.morador_id
    );
    document.getElementById("dashboard-user-task").textContent = minhaTarefa ? minhaTarefa.titulo : "Sem tarefa";
    document.getElementById("dashboard-user-task-status").textContent = minhaTarefa ? minhaTarefa.status : "Livre";

    renderList(
      "dashboard-resumo-list",
      currentResumo.moradores,
      (morador) => {
        const div = document.createElement("div");
        div.className = "expense-item";
        div.innerHTML = `
          <div>
            <strong style="display:block;">${morador.nome}</strong>
            <span class="helper-text">Devido: ${formatMoney(morador.total_devido)} - Pago: ${formatMoney(morador.total_pago_em_despesas)}</span>
          </div>
          <span class="badge ${Number(morador.saldo) >= 0 ? "badge-success" : "badge-danger"}">${formatMoney(morador.saldo)}</span>
        `;
        return div;
      },
      "Nenhum saldo para exibir."
    );

    renderList(
      "dashboard-despesas-list",
      currentOverview.ultimas_despesas,
      (despesa) => {
        const div = document.createElement("div");
        div.className = "expense-item";
        div.innerHTML = `
          <div>
            <strong style="display:block;">${despesa.titulo}</strong>
            <span class="helper-text">${despesa.categoria} - pago por ${despesa.paga_por_nome}</span>
          </div>
          <strong>${formatMoney(despesa.valor_total)}</strong>
        `;
        return div;
      },
      "Nenhuma despesa cadastrada."
    );

    renderList(
      "dashboard-tarefas-list",
      currentOverview.tarefas_pendentes,
      (tarefa) => {
        const div = document.createElement("div");
        div.className = "expense-item";
        div.innerHTML = `
          <div>
            <strong style="display:block;">${tarefa.titulo}</strong>
            <span class="helper-text">${tarefa.responsavel_nome || "Sem responsavel"} - ${tarefa.prioridade}</span>
          </div>
          <span class="status-chip status-${tarefa.status.toLowerCase()}">${tarefa.status}</span>
        `;
        return div;
      },
      "Nenhuma tarefa pendente."
    );
  }

  async function reloadFinancialSources() {
    const [overviewResponse, resumoResponse] = await Promise.all([
      apiFetch(urls.dashboardOverview),
      apiFetch(`/api/republicas/${currentUser.republica_id}/resumo-financeiro/`),
    ]);
    currentOverview = await overviewResponse.json();
    currentResumo = await resumoResponse.json();
  }

  async function renderFinancas() {
    const [despesasResponse, pagamentosResponse] = await Promise.all([
      apiFetch("/api/despesas/"),
      apiFetch("/api/pagamentos/"),
    ]);
    const despesas = await despesasResponse.json();
    const pagamentos = await pagamentosResponse.json();
    const meuSaldo = getMeuSaldo();
    const saldoInfo = getSaldoDescriptor(meuSaldo ? meuSaldo.saldo : 0);

    document.getElementById("financas-total-despesas").textContent = formatMoney(currentOverview.total_despesas);
    document.getElementById("financas-total-pagamentos").textContent = formatMoney(
      pagamentos.reduce((acc, item) => acc + Number(item.valor), 0)
    );
    document.getElementById("financas-meu-saldo").textContent = formatMoney(meuSaldo ? meuSaldo.saldo : 0);

    const meuStatus = document.getElementById("financas-meu-status");
    meuStatus.className = `badge ${saldoInfo.className}`;
    meuStatus.textContent = saldoInfo.label;

    renderList(
      "financas-saldos-list",
      currentResumo.moradores,
      (morador) => {
        const div = document.createElement("div");
        const saldoDescriptor = getSaldoDescriptor(morador.saldo);
        div.className = "saldo-card";
        div.innerHTML = `
          <div class="saldo-card-top">
            <div>
              <strong style="display:block;">${morador.nome}</strong>
              <span class="helper-text">${saldoDescriptor.label}</span>
            </div>
            <span class="badge ${saldoDescriptor.className}">${formatMoney(morador.saldo)}</span>
          </div>
          <div class="saldo-card-metrics">
            <div>
              <span class="helper-text">Devido</span>
              <strong>${formatMoney(morador.total_devido)}</strong>
            </div>
            <div>
              <span class="helper-text">Pagou em despesas</span>
              <strong>${formatMoney(morador.total_pago_em_despesas)}</strong>
            </div>
            <div>
              <span class="helper-text">Recebeu em acertos</span>
              <strong>${formatMoney(morador.total_recebido_em_acertos)}</strong>
            </div>
          </div>
        `;
        return div;
      },
      "Nenhum saldo encontrado."
    );

    renderList(
      "financas-despesas-list",
      despesas,
      (despesa) => {
        const div = document.createElement("div");
        div.className = "expense-item";
        div.innerHTML = `
          <div style="display:flex; align-items:center; gap:15px;">
            <div class="exp-icon"><i class="fa-solid fa-file-invoice-dollar"></i></div>
            <div>
              <strong style="display:block;">${despesa.titulo}</strong>
              <span style="font-size:0.8em; color:var(--text-muted); display:block;">
                ${formatDate(despesa.data_despesa)} - ${despesa.categoria}
              </span>
              <span class="helper-text">Pago por ${despesa.paga_por_nome}</span>
            </div>
          </div>
          <strong>${formatMoney(despesa.valor_total)}</strong>
        `;
        return div;
      },
      "Nenhuma despesa cadastrada."
    );

    renderList(
      "financas-pagamentos-list",
      pagamentos,
      (pagamento) => {
        const div = document.createElement("div");
        div.className = "expense-item";
        div.innerHTML = `
          <div style="display:flex; align-items:center; gap:15px;">
            <div class="exp-icon" style="background: var(--success); color: white">
              <i class="fa-brands fa-pix"></i>
            </div>
            <div>
              <strong style="display:block;">${pagamento.pagador_nome} pagou ${pagamento.recebedor_nome}</strong>
              <span style="font-size:0.8em; color:var(--text-muted); display:block;">
                ${formatDate(pagamento.data_pagamento)}
              </span>
              <span class="helper-text">${pagamento.observacao || "Sem observacao"}</span>
            </div>
          </div>
          <strong>${formatMoney(pagamento.valor)}</strong>
        `;
        return div;
      },
      "Nenhum pagamento registrado."
    );

    fillSelect(document.getElementById("despesa-paga-por"), false);
    fillSelect(document.getElementById("despesa-moradores"), false);
    fillSelect(document.getElementById("pagamento-pagador"), false);
    fillSelect(document.getElementById("pagamento-recebedor"), false);
    Array.from(document.getElementById("despesa-moradores").options).forEach((option) => {
      option.selected = true;
    });
  }

  async function renderTarefas() {
    const response = await apiFetch("/api/tarefas/");
    const tarefas = await response.json();
    ["pendente", "andamento", "concluida"].forEach((column) => {
      document.getElementById(`tarefas-${column}-list`).innerHTML = "";
    });
    if (!tarefas.length) {
      document.getElementById("tarefas-pendente-list").innerHTML = '<div class="empty-state">Nenhuma tarefa cadastrada.</div>';
    }

    const statusMap = {
      PENDENTE: "pendente",
      EM_ANDAMENTO: "andamento",
      CONCLUIDA: "concluida",
    };

    tarefas.forEach((tarefa) => {
      const div = document.createElement("div");
      div.className = "task-card color-primary";
      div.id = `task-${tarefa.id}`;
      div.dataset.taskId = tarefa.id;
      div.draggable = true;
      div.ondragstart = dragStart;
      div.innerHTML = `
        <div style="display:flex; gap:10px; align-items:flex-start;">
          <div style="flex:1;">
            <div class="task-title">${tarefa.titulo}</div>
            <div class="task-meta">
              <span><i class="fa-regular fa-user"></i> ${tarefa.responsavel_nome || "Sem responsavel"}</span>
              <span><i class="fa-regular fa-calendar"></i> ${formatDate(tarefa.data_limite)}</span>
            </div>
            <div class="task-actions">
              <span class="status-chip status-${tarefa.status.toLowerCase()}">${tarefa.status}</span>
              <span class="status-chip status-pendente">${tarefa.prioridade}</span>
            </div>
            ${
              tarefa.status !== "CONCLUIDA"
                ? `
                  <div class="task-card-footer">
                    <button
                      type="button"
                      class="btn btn-sm task-complete-btn"
                      data-action="complete-task"
                      data-task-id="${tarefa.id}"
                    >
                      <i class="fa-solid fa-check"></i>
                      Concluir
                    </button>
                  </div>
                `
                : ""
            }
          </div>
        </div>
      `;
      document.getElementById(`tarefas-${statusMap[tarefa.status]}-list`).appendChild(div);
    });

    fillSelect(document.getElementById("tarefa-responsavel"), true);
  }

  async function submitDespesa(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = {
      republica: currentUser.republica_id,
      titulo: form.titulo.value,
      descricao: form.descricao.value,
      categoria: form.categoria.value,
      valor_total: form.valor_total.value,
      paga_por: Number(form.paga_por.value),
      data_despesa: form.data_despesa.value,
      morador_ids: Array.from(document.getElementById("despesa-moradores").selectedOptions).map((option) => Number(option.value)),
    };
    const response = await apiFetch("/api/despesas/", { method: "POST", body: JSON.stringify(payload) });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      showToast(data.detail || "Nao foi possivel salvar a despesa.", "danger");
      return;
    }
    form.reset();
    closeModal("modal-despesa");
    await reloadFinancialSources();
    await renderFinancas();
    showToast("Despesa cadastrada com sucesso!", "success");
  }

  async function submitPagamento(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = {
      republica: currentUser.republica_id,
      pagador: Number(form.pagador.value),
      recebedor: Number(form.recebedor.value),
      valor: form.valor.value,
      observacao: form.observacao.value,
      data_pagamento: form.data_pagamento.value,
    };
    const response = await apiFetch("/api/pagamentos/", { method: "POST", body: JSON.stringify(payload) });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      showToast(data.detail || "Nao foi possivel registrar o pagamento.", "danger");
      return;
    }
    form.reset();
    closeModal("modal-pagamento");
    await reloadFinancialSources();
    await renderFinancas();
    showToast("Pagamento registrado com sucesso!", "success");
  }

  async function submitTarefa(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = {
      republica: currentUser.republica_id,
      titulo: form.titulo.value,
      descricao: form.descricao.value,
      responsavel: form.responsavel.value ? Number(form.responsavel.value) : null,
      prioridade: form.prioridade.value,
      status: form.status.value,
      data_limite: form.data_limite.value || null,
    };
    const response = await apiFetch("/api/tarefas/", { method: "POST", body: JSON.stringify(payload) });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      showToast(data.detail || "Nao foi possivel salvar a tarefa.", "danger");
      return;
    }
    form.reset();
    closeModal("modal-nova-tarefa");
    await renderTarefas();
    showToast("Tarefa criada com sucesso!", "success");
  }

  async function updateTaskStatus(taskId, status) {
    const response = await apiFetch(`/api/tarefas/${taskId}/`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
    if (!response.ok) {
      showToast("Nao foi possivel atualizar a tarefa.", "danger");
      return false;
    }
    await renderTarefas();
    return true;
  }

  document.addEventListener("click", (event) => {
    const completeButton = event.target.closest('[data-action="complete-task"]');
    if (completeButton) {
      updateTaskStatus(completeButton.dataset.taskId, "CONCLUIDA").then((success) => {
        if (success) {
          showToast("Tarefa concluida com sucesso!", "success");
        }
      });
      return;
    }
  });

  window.dragStart = function (event) {
    draggedTaskId = event.currentTarget.dataset.taskId;
    event.dataTransfer.setData("text/plain", draggedTaskId);
  };

  window.allowDrop = function (event) {
    event.preventDefault();
    event.currentTarget.classList.add("drag-over");
  };

  window.dragLeave = function (event) {
    event.currentTarget.classList.remove("drag-over");
  };

  window.dropTask = async function (event) {
    event.preventDefault();
    event.currentTarget.classList.remove("drag-over");
    const taskId = draggedTaskId || event.dataTransfer.getData("text/plain");
    const status = event.currentTarget.dataset.status;
    if (!taskId || !status) return;
    const success = await updateTaskStatus(taskId, status);
    if (success) {
      showToast("Tarefa atualizada com sucesso!", "success");
    }
  };

  async function init() {
    bindModalEvents();
    document.getElementById("logout-button").addEventListener("click", async () => {
      await apiFetch(urls.authLogout, { method: "POST" });
      localStorage.removeItem(tokenKey);
      window.location.href = urls.login;
    });

    await loadCommonData();

    if (page === "dashboard") {
      renderDashboard();
      return;
    }

    if (page === "financas") {
      document.getElementById("despesa-form").addEventListener("submit", submitDespesa);
      document.getElementById("pagamento-form").addEventListener("submit", submitPagamento);
      await renderFinancas();
      return;
    }

    if (page === "tarefas") {
      document.getElementById("tarefa-form").addEventListener("submit", submitTarefa);
      await renderTarefas();
    }
  }

  init().catch((error) => {
    if (error && error.message === "Usuario sem republica") {
      showToast("Seu usuario ainda nao esta vinculado a uma republica. Vamos para o cadastro.", "warning");
      setTimeout(() => {
        window.location.href = urls.cadastro;
      }, 1000);
      return;
    }
    showToast("Nao foi possivel carregar os dados da pagina.", "danger");
  });
})();
