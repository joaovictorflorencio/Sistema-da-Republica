(function () {
  function escapeHtml(value) {
    return String(value || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function renderTaskDescription(tarefa) {
    const descricao = String(tarefa.descricao || "").trim();
    if (!descricao) {
      return "";
    }

    return `
      <p class="task-description">
        <i class="fa-regular fa-note-sticky"></i>
        <span>${escapeHtml(descricao)}</span>
      </p>
    `;
  }

  async function renderTarefas(ctx) {
    const { apiFetch, renderList, fillSelect, formatDate, formatDateTime } = ctx;
    const response = await apiFetch("/api/tarefas/");
    const tarefas = await response.json();
    const tarefasConcluidas = tarefas
      .filter((tarefa) => tarefa.status === "CONCLUIDA")
      .sort((a, b) => {
        const dateA = a.concluida_em ? new Date(a.concluida_em).getTime() : 0;
        const dateB = b.concluida_em ? new Date(b.concluida_em).getTime() : 0;
        return dateB - dateA;
      });

    ["pendente", "andamento"].forEach((column) => {
      document.getElementById(`tarefas-${column}-list`).innerHTML = "";
    });

    if (!tarefas.length) {
      document.getElementById("tarefas-pendente-list").innerHTML = '<div class="empty-state">Nenhuma tarefa cadastrada.</div>';
    }

    const statusMap = {
      PENDENTE: "pendente",
      EM_ANDAMENTO: "andamento",
    };

    tarefas
      .filter((tarefa) => tarefa.status !== "CONCLUIDA")
      .forEach((tarefa) => {
        const div = document.createElement("div");
        div.className = "task-card color-primary";
        div.id = `task-${tarefa.id}`;
        div.dataset.taskId = tarefa.id;
        div.draggable = true;
        div.addEventListener("dragstart", (event) => {
          ctx.state.draggedTaskId = event.currentTarget.dataset.taskId;
          event.dataTransfer.setData("text/plain", ctx.state.draggedTaskId);
        });
        div.innerHTML = `
          <div style="display:flex; gap:10px; align-items:flex-start;">
            <div style="flex:1;">
              <div class="task-title">${escapeHtml(tarefa.titulo)}</div>
              ${renderTaskDescription(tarefa)}
              <div class="task-meta">
                <span><i class="fa-regular fa-user"></i> ${escapeHtml(tarefa.responsavel_nome || "Sem responsavel")}</span>
                <span><i class="fa-regular fa-calendar"></i> ${formatDate(tarefa.data_limite)}</span>
              </div>
              <div class="task-actions">
                <span class="status-chip status-${tarefa.status.toLowerCase()}">${tarefa.status}</span>
                <span class="status-chip status-pendente">${tarefa.prioridade}</span>
              </div>
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
            </div>
          </div>
        `;
        document.getElementById(`tarefas-${statusMap[tarefa.status]}-list`).appendChild(div);
      });

    renderList(
      "tarefas-history-list",
      tarefasConcluidas,
      (tarefa) => {
        const div = document.createElement("div");
        div.className = "expense-item";
        div.innerHTML = `
          <div class="task-history-details">
            <strong style="display:block;">${escapeHtml(tarefa.titulo)}</strong>
            ${renderTaskDescription(tarefa)}
            <span class="helper-text">
              ${escapeHtml(tarefa.responsavel_nome || "Sem responsavel")} - concluida em ${formatDateTime(tarefa.concluida_em)}
            </span>
          </div>
          <span class="badge badge-success">Concluida</span>
        `;
        return div;
      },
      "Nenhuma tarefa concluida ainda."
    );

    fillSelect(document.getElementById("tarefa-responsavel"), true);
  }

  async function updateTaskStatus(ctx, taskId, status) {
    const { apiFetch, showToast } = ctx;
    const response = await apiFetch(`/api/tarefas/${taskId}/`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
    if (!response.ok) {
      showToast("Nao foi possivel atualizar a tarefa.", "danger");
      return false;
    }
    await renderTarefas(ctx);
    return true;
  }

  async function submitTarefa(ctx, event) {
    event.preventDefault();
    const { state, apiFetch, closeModal, showToast } = ctx;
    const form = event.currentTarget;
    const payload = {
      republica: state.currentUser.republica_id,
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
    await renderTarefas(ctx);
    showToast("Tarefa criada com sucesso!", "success");
  }

  window.RABBU_APP.initPage(async (ctx) => {
    document.getElementById("tarefa-form").addEventListener("submit", (event) => submitTarefa(ctx, event));

    document.addEventListener("click", (event) => {
      const completeButton = event.target.closest('[data-action="complete-task"]');
      if (completeButton) {
        updateTaskStatus(ctx, completeButton.dataset.taskId, "CONCLUIDA").then((success) => {
          if (success) {
            ctx.showToast("Tarefa concluida com sucesso!", "success");
          }
        });
      }
    });

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
      const taskId = ctx.state.draggedTaskId || event.dataTransfer.getData("text/plain");
      const status = event.currentTarget.dataset.status;
      if (!taskId || !status) return;
      const success = await updateTaskStatus(ctx, taskId, status);
      if (success) {
        ctx.showToast("Tarefa atualizada com sucesso!", "success");
      }
    };

    await renderTarefas(ctx);
  });
})();
