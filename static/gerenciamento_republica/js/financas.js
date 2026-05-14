(function () {
  const CATEGORY_LABELS = {
    ALUGUEL: "Moradia",
    ENERGIA: "Energia",
    AGUA: "Água",
    INTERNET: "Internet",
    MERCADO: "Mercado",
    LIMPEZA: "Limpeza",
    OUTROS: "Outros",
  };

  function getErrorMessage(data, fallbackMessage) {
    if (!data || typeof data !== "object") return fallbackMessage;
    if (data.detail) return data.detail;

    const firstKey = Object.keys(data)[0];
    if (!firstKey) return fallbackMessage;

    const firstValue = data[firstKey];
    if (Array.isArray(firstValue) && firstValue.length) {
      return firstValue[0];
    }
    if (typeof firstValue === "string") {
      return firstValue;
    }
    return fallbackMessage;
  }

  function toNumber(value) {
    return Number(value || 0);
  }

  function isPaid(expense) {
    return expense.status_pagamento === "PAGA";
  }

  function formatCategoryLabel(category) {
    return CATEGORY_LABELS[category] || category || "Outros";
  }

  function pluralize(count, singular, plural) {
    return count === 1 ? singular : plural;
  }

  function compareByDate(a, b, key, direction = "asc") {
    const valueA = a[key] || "";
    const valueB = b[key] || "";
    if (valueA === valueB) return 0;
    if (!valueA) return 1;
    if (!valueB) return -1;
    return direction === "asc"
      ? valueA.localeCompare(valueB)
      : valueB.localeCompare(valueA);
  }

  function canConfirmPayment(state, expense) {
    return Boolean(state.currentUser.morador_id) || state.currentUser.morador_eh_admin;
  }

  function buildExpenseCard(ctx, expense, variant) {
    const { state, formatMoney, formatDate, openModal } = ctx;
    const card = document.createElement("article");
    card.className = `financas-card financas-card-${variant}`;

    const vencimento = expense.data_vencimento
      ? `Vence em ${formatDate(expense.data_vencimento)}`
      : "Sem vencimento informado";
    const descricao = expense.descricao || "Sem observações adicionais.";
    const categoria = formatCategoryLabel(expense.categoria);
    const pagamentoInfo = isPaid(expense)
      ? `Pago por ${expense.quitada_por_nome || expense.paga_por_nome}`
      : `Responsável: ${expense.paga_por_nome}`;
    const dataStatus = isPaid(expense)
      ? `Quitada em ${formatDate(expense.data_pagamento)}`
      : vencimento;

    card.innerHTML = `
      <div class="financas-card-top">
        <div>
          <span class="status-chip ${isPaid(expense) ? "status-concluida" : "status-pendente"}">
            ${isPaid(expense) ? "Pago" : "Pendente"}
          </span>
          <h4>${expense.titulo}</h4>
        </div>
        <strong>${formatMoney(expense.valor_total)}</strong>
      </div>
      <p class="financas-card-description">${descricao}</p>
      <div class="financas-card-metadata">
          <span><i class="fa-solid fa-tag"></i> ${categoria}</span>
          <span><i class="fa-solid fa-calendar-days"></i> ${dataStatus}</span>
          <span><i class="fa-solid fa-user"></i> ${pagamentoInfo}</span>
          <span><i class="fa-solid fa-users"></i> ${expense.participantes_count} ${pluralize(expense.participantes_count, "participante", "participantes")}</span>
      </div>
    `;

    const actions = document.createElement("div");
    actions.className = "financas-card-actions";

    if (!isPaid(expense) && canConfirmPayment(state, expense)) {
      const button = document.createElement("button");
      button.className = "btn btn-sm";
      button.innerHTML = '<i class="fa-solid fa-file-circle-check"></i> Registrar pagamento';
      button.addEventListener("click", () => {
        document.getElementById("comprovante-despesa-id").value = expense.id;
        document.getElementById("comprovante-despesa-titulo").value = expense.titulo;
        document.querySelector("#comprovante-form input[name='data_pagamento']").value =
          new Date().toISOString().slice(0, 10);
        openModal("modal-comprovante");
      });
      actions.appendChild(button);
    }

    if (isPaid(expense) && expense.comprovante_url) {
      const link = document.createElement("a");
      link.className = "btn btn-outline btn-sm";
      link.href = expense.comprovante_url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.innerHTML = '<i class="fa-solid fa-paperclip"></i> Ver comprovante';
      actions.appendChild(link);
    }

    if (actions.children.length) {
      card.appendChild(actions);
    }

    return card;
  }

  async function renderFinancas(ctx) {
    const {
      state,
      apiFetch,
      renderList,
      fillSelect,
      formatMoney,
      formatDate,
    } = ctx;

    const [despesasResponse, divisoesResponse] = await Promise.all([
      apiFetch("/api/despesas/"),
      apiFetch("/api/divisoes/"),
    ]);

    const despesas = await despesasResponse.json();
    const divisoes = await divisoesResponse.json();

    const pendentes = despesas
      .filter((expense) => !isPaid(expense))
      .sort((a, b) => compareByDate(a, b, "data_vencimento", "asc"));
    const pagas = despesas
      .filter((expense) => isPaid(expense))
      .sort((a, b) => compareByDate(a, b, "data_pagamento", "desc"));
    const minhasCotas = divisoes
      .filter(
      (divisao) => Number(divisao.morador) === Number(state.currentUser.morador_id)
      )
      .sort((a, b) => compareByDate(a, b, "despesa_data", "desc"));

    const totalGastos = despesas.reduce((acc, expense) => acc + toNumber(expense.valor_total), 0);
    const valorPendente = pendentes.reduce((acc, expense) => acc + toNumber(expense.valor_total), 0);
    const valorPago = pagas.reduce((acc, expense) => acc + toNumber(expense.valor_total), 0);
    const minhaParticipacao = minhasCotas.reduce(
      (acc, divisao) => acc + toNumber(divisao.valor_devido),
      0
    );

    document.getElementById("financas-total-gastos").textContent = formatMoney(totalGastos);
    document.getElementById("financas-total-pendentes").textContent = String(pendentes.length);
    document.getElementById("financas-total-pagas").textContent = String(pagas.length);
    document.getElementById("financas-minha-participacao").textContent = formatMoney(minhaParticipacao);
    document.getElementById("financas-valor-pendente").textContent = `${formatMoney(valorPendente)} em aberto`;
    document.getElementById("financas-valor-pago").textContent = `${formatMoney(valorPago)} comprovados`;
    document.getElementById("financas-meu-status").textContent =
      minhasCotas.length > 0
        ? `${minhasCotas.length} ${pluralize(minhasCotas.length, "conta entra", "contas entram")} na sua parcela atual.`
        : "Você ainda não participa de contas cadastradas.";
    document.getElementById("financas-pendentes-resumo").textContent =
      pendentes.length > 0
        ? `${pendentes.length} ${pluralize(pendentes.length, "conta aguardando pagamento", "contas aguardando pagamento")}`
        : "Nenhuma conta em aberto no momento.";
    document.getElementById("financas-pagas-resumo").textContent =
      pagas.length > 0
        ? `${pagas.length} ${pluralize(pagas.length, "conta já foi quitada", "contas já foram quitadas")}`
        : "Sem contas pagas ainda.";

    renderList(
      "financas-pendentes-list",
      pendentes,
      (expense) => buildExpenseCard(ctx, expense, "pendente"),
      "Nenhuma conta pendente no momento."
    );

    renderList(
      "financas-pagas-list",
      pagas,
      (expense) => buildExpenseCard(ctx, expense, "paga"),
      "Nenhuma conta paga ainda."
    );

    renderList(
      "financas-minhas-cotas-list",
      minhasCotas,
      (divisao) => {
        const item = document.createElement("div");
        item.className = "expense-item";
        item.innerHTML = `
          <div class="expense-item-main">
            <div class="exp-icon"><i class="fa-solid fa-receipt"></i></div>
            <div class="expense-item-details">
              <strong style="display:block;">${divisao.despesa_titulo}</strong>
              <span class="helper-text">${formatDate(divisao.despesa_data)} • ${formatCategoryLabel(divisao.despesa_categoria)}</span>
              <span class="helper-text">Lançada por: ${divisao.credor_nome}</span>
            </div>
          </div>
          <strong>${formatMoney(divisao.valor_devido)}</strong>
        `;
        return item;
      },
      "Você ainda não participa de nenhuma despesa cadastrada."
    );

    renderList(
      "financas-saldos-list",
      [...state.currentResumo.moradores].sort(
        (a, b) => toNumber(b.total_devido) - toNumber(a.total_devido)
      ),
      (morador) => {
        const card = document.createElement("div");
        const destaque = Number(morador.id) === Number(state.currentUser.morador_id) ? " (você)" : "";
        card.className = "saldo-card";
        card.innerHTML = `
          <div class="saldo-card-top">
            <div>
              <strong style="display:block;">${morador.nome}${destaque}</strong>
              <span class="helper-text">Participação acumulada nos gastos</span>
            </div>
            <span class="badge badge-warning">Cota ${formatMoney(morador.total_devido)}</span>
          </div>
          <div class="saldo-card-metrics">
            <div>
              <span class="helper-text">Quitado</span>
              <strong>${formatMoney(morador.total_quitado)}</strong>
            </div>
            <div>
              <span class="helper-text">Pendente</span>
              <strong>${formatMoney(morador.total_pendente)}</strong>
            </div>
            <div>
              <span class="helper-text">Saldo estimado</span>
              <strong>${formatMoney(morador.saldo)}</strong>
            </div>
          </div>
        `;
        return card;
      },
      "Nenhum morador encontrado."
    );

    fillSelect(document.getElementById("despesa-paga-por"), false);
    fillSelect(document.getElementById("despesa-moradores"), false);
    Array.from(document.getElementById("despesa-moradores").options).forEach((option) => {
      option.selected = true;
    });
  }

  async function submitDespesa(ctx, event) {
    event.preventDefault();
    const { state, apiFetch, closeModal, reloadFinancialSources, showToast } = ctx;
    const form = event.currentTarget;

    const payload = {
      republica: state.currentUser.republica_id,
      titulo: form.titulo.value,
      descricao: form.descricao.value,
      categoria: form.categoria.value,
      valor_total: form.valor_total.value,
      paga_por: Number(form.paga_por.value),
      data_vencimento: form.data_vencimento.value || null,
      data_despesa: form.data_despesa.value,
      morador_ids: Array.from(document.getElementById("despesa-moradores").selectedOptions).map(
        (option) => Number(option.value)
      ),
    };

    const response = await apiFetch("/api/despesas/", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      showToast(getErrorMessage(data, "Não foi possível salvar a despesa."), "danger");
      return;
    }

    form.reset();
    closeModal("modal-despesa");
    await reloadFinancialSources();
    await renderFinancas(ctx);
    showToast("Despesa cadastrada com sucesso!", "success");
  }

  async function submitComprovante(ctx, event) {
    event.preventDefault();
    const { apiFetch, closeModal, reloadFinancialSources, showToast } = ctx;
    const form = event.currentTarget;
    const despesaId = document.getElementById("comprovante-despesa-id").value;
    const comprovante = form.comprovante_pagamento.files[0];

    const payload = new FormData();
    payload.append("status_pagamento", "PAGA");
    payload.append("data_pagamento", form.data_pagamento.value);
    if (comprovante) {
      payload.append("comprovante_pagamento", comprovante);
    }

    const response = await apiFetch(`/api/despesas/${despesaId}/`, {
      method: "PATCH",
      body: payload,
    });
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      showToast(getErrorMessage(data, "Não foi possível registrar o pagamento."), "danger");
      return;
    }

    form.reset();
    closeModal("modal-comprovante");
    await reloadFinancialSources();
    await renderFinancas(ctx);
    showToast("Pagamento registrado com comprovante!", "success");
  }

  window.RABBU_APP.initPage(async (ctx) => {
    const despesaForm = document.getElementById("despesa-form");
    const comprovanteForm = document.getElementById("comprovante-form");
    const hoje = new Date().toISOString().slice(0, 10);

    despesaForm.querySelector("input[name='data_despesa']").value = hoje;
    comprovanteForm.querySelector("input[name='data_pagamento']").value = hoje;

    despesaForm.addEventListener("submit", (event) => submitDespesa(ctx, event));
    comprovanteForm.addEventListener("submit", (event) => submitComprovante(ctx, event));

    await renderFinancas(ctx);
  });
})();
