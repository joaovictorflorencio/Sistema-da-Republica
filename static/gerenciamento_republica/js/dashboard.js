(function () {
  function renderDashboard(ctx) {
    // O dashboard e uma visao rapida: mostra os principais indicadores para o
    // morador entender a situacao da casa sem entrar em cada tela.
    const { state, formatMoney, renderList, getMeuSaldo } = ctx;
    const saldo = getMeuSaldo();
    const adminMorador = state.currentMoradores.find((morador) => morador.eh_admin);

    document.getElementById("dashboard-user-saldo").textContent = formatMoney(saldo ? saldo.total_pendente : 0);
    const badge = document.getElementById("dashboard-saldo-badge");
    if (saldo && Number(saldo.total_pendente) > 0) {
      badge.className = "badge badge-warning";
      badge.textContent = "Sob sua responsabilidade";
    } else {
      badge.className = "badge badge-success";
      badge.textContent = "Tudo em dia";
    }

    document.getElementById("dashboard-total-casa").textContent = formatMoney(state.currentOverview.total_despesas);
    document.getElementById("dashboard-total-contas").textContent =
      `${state.currentOverview.ultimas_despesas.length} despesas recentes`;
    document.getElementById("dashboard-moradores-count").textContent = state.currentOverview.total_moradores;
    document.getElementById("dashboard-tarefas-count").textContent = state.currentOverview.total_tarefas_pendentes;
    document.getElementById("dashboard-admin-name").textContent = adminMorador
      ? adminMorador.id === state.currentUser.morador_id
        ? `${adminMorador.nome} (voce)`
        : adminMorador.nome
      : "Nao definido";

    const minhaTarefa = state.currentOverview.tarefas_pendentes.find(
      (item) => state.currentUser.morador_id && item.responsavel === state.currentUser.morador_id
    );
    document.getElementById("dashboard-user-task").textContent = minhaTarefa ? minhaTarefa.titulo : "Sem tarefa";
    document.getElementById("dashboard-user-task-status").textContent = minhaTarefa ? minhaTarefa.status : "Livre";

    renderList(
      "dashboard-resumo-list",
      state.currentResumo.moradores,
      (morador) => {
        const div = document.createElement("div");
        div.className = "expense-item";
        div.innerHTML = `
          <div>
            <strong style="display:block;">${morador.nome}</strong>
            <span class="helper-text">Atribuído: ${formatMoney(morador.total_devido)} - Pago: ${formatMoney(morador.total_quitado)}</span>
          </div>
          <span class="badge ${Number(morador.total_pendente) > 0 ? "badge-warning" : "badge-success"}">${formatMoney(morador.total_pendente)}</span>
        `;
        return div;
      },
      "Nenhum saldo para exibir."
    );

    renderList(
      "dashboard-despesas-list",
      state.currentOverview.ultimas_despesas,
      (despesa) => {
        const div = document.createElement("div");
        div.className = "expense-item";
        div.innerHTML = `
          <div>
            <strong style="display:block;">${despesa.titulo}</strong>
            <span class="helper-text">${despesa.categoria} - responsável: ${despesa.paga_por_nome}</span>
          </div>
          <strong>${formatMoney(despesa.valor_total)}</strong>
        `;
        return div;
      },
      "Nenhuma despesa cadastrada."
    );

    renderList(
      "dashboard-tarefas-list",
      state.currentOverview.tarefas_pendentes,
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

  window.RABBU_APP.initPage(async (ctx) => {
    renderDashboard(ctx);
  });
})();
