(function () {
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

  function buildExpenseOptions(select, despesas) {
    if (!select) return;
    select.innerHTML = '<option value="">Aplicar automaticamente na divida mais antiga</option>';
    despesas.forEach((despesa) => {
      const option = document.createElement("option");
      option.value = despesa.id;
      option.textContent = `${despesa.titulo} - pago por ${despesa.paga_por_nome}`;
      select.appendChild(option);
    });
  }

  function buildReferenciaOptions(select, despesas, divisoes, pagadorId, recebedorId, formatDate) {
    if (!select) return;
    const divisoesEmAberto = divisoes.filter(
      (divisao) =>
        Number(divisao.morador) === Number(pagadorId) &&
        Number(divisao.saldo_aberto) > 0
    );
    const despesasPermitidas = despesas.filter((despesa) => {
      if (recebedorId && Number(despesa.paga_por) !== Number(recebedorId)) {
        return false;
      }
      return divisoesEmAberto.some((divisao) => Number(divisao.despesa) === Number(despesa.id));
    });

    const valorAtual = select.value;
    select.innerHTML = '<option value="">Aplicar automaticamente na divida mais antiga</option>';

    despesasPermitidas.forEach((despesa) => {
      const option = document.createElement("option");
      option.value = despesa.id;
      option.textContent = `${despesa.titulo} - ${formatDate(despesa.data_despesa)}`;
      select.appendChild(option);
    });

    if (valorAtual && despesasPermitidas.some((despesa) => Number(despesa.id) === Number(valorAtual))) {
      select.value = valorAtual;
    }
  }

  async function renderFinancas(ctx) {
    const {
      state,
      apiFetch,
      renderList,
      fillSelect,
      formatMoney,
      formatDate,
      getMeuSaldo,
      getSaldoDescriptor,
    } = ctx;

    const [despesasResponse, pagamentosResponse, divisoesResponse] = await Promise.all([
      apiFetch("/api/despesas/"),
      apiFetch("/api/pagamentos/"),
      apiFetch("/api/divisoes/"),
    ]);
    const despesas = await despesasResponse.json();
    const pagamentos = await pagamentosResponse.json();
    const divisoes = await divisoesResponse.json();
    const minhasDivisoes = divisoes.filter(
      (divisao) =>
        Number(divisao.morador) === Number(state.currentUser.morador_id) &&
        Number(divisao.saldo_aberto) > 0
    );
    const meuSaldo = getMeuSaldo();
    const saldoInfo = getSaldoDescriptor(meuSaldo ? meuSaldo.saldo : 0);

    document.getElementById("financas-total-despesas").textContent = formatMoney(state.currentResumo.total_despesas);
    document.getElementById("financas-total-quitado").textContent = formatMoney(state.currentResumo.total_quitado);
    document.getElementById("financas-total-pendente").textContent = formatMoney(state.currentResumo.total_pendente);
    document.getElementById("financas-meu-saldo").textContent = formatMoney(meuSaldo ? meuSaldo.saldo : 0);

    const meuStatus = document.getElementById("financas-meu-status");
    meuStatus.className = `badge ${saldoInfo.className}`;
    meuStatus.textContent = saldoInfo.label;

    renderList(
      "financas-saldos-list",
      state.currentResumo.moradores,
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
              <span class="helper-text">Pendente</span>
              <strong>${formatMoney(morador.total_pendente)}</strong>
            </div>
            <div>
              <span class="helper-text">Quitado</span>
              <strong>${formatMoney(morador.total_quitado)}</strong>
            </div>
            <div>
              <span class="helper-text">A receber</span>
              <strong>${formatMoney(morador.total_credito_aberto)}</strong>
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
              <span class="helper-text">
                Pago por ${despesa.paga_por_nome} - ${despesa.participantes_count} participante(s)
              </span>
              <span class="helper-text">
                Quitado: ${formatMoney(despesa.valor_quitado)} - Em aberto: ${formatMoney(despesa.valor_em_aberto)}
              </span>
            </div>
          </div>
          <strong>${formatMoney(despesa.valor_total)}</strong>
        `;
        return div;
      },
      "Nenhuma despesa cadastrada."
    );

    renderList(
      "financas-divisoes-list",
      minhasDivisoes,
      (divisao) => {
        const div = document.createElement("div");
        div.className = "expense-item";
        div.innerHTML = `
          <div style="display:flex; align-items:center; gap:15px;">
            <div class="exp-icon" style="background: #fff3f0; color: var(--danger);">
              <i class="fa-solid fa-file-circle-exclamation"></i>
            </div>
            <div>
              <strong style="display:block;">${divisao.despesa_titulo}</strong>
              <span style="font-size:0.8em; color:var(--text-muted); display:block;">
                ${formatDate(divisao.despesa_data)} - ${divisao.despesa_categoria}
              </span>
              <span class="helper-text">Credor: ${divisao.credor_nome}</span>
              <span class="helper-text">
                Devido: ${formatMoney(divisao.valor_devido)} - Pago: ${formatMoney(divisao.valor_pago)}
              </span>
            </div>
          </div>
          <span class="badge badge-danger">${formatMoney(divisao.saldo_aberto)}</span>
        `;
        return div;
      },
      "Voce nao possui dividas em aberto no momento."
    );

    renderList(
      "financas-pagamentos-list",
      pagamentos,
      (pagamento) => {
        const resumoItens = (pagamento.itens || [])
          .map((item) => `${item.despesa_titulo}: ${formatMoney(item.valor_aplicado)}`)
          .join(" | ");

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
              <span class="helper-text">${resumoItens || "Pagamento sem aplicacoes listadas"}</span>
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
    buildExpenseOptions(document.getElementById("pagamento-referencia-despesa"), despesas);

    Array.from(document.getElementById("despesa-moradores").options).forEach((option) => {
      option.selected = true;
    });

    const pagadorSelect = document.getElementById("pagamento-pagador");
    const recebedorSelect = document.getElementById("pagamento-recebedor");
    const referenciaSelect = document.getElementById("pagamento-referencia-despesa");
    const refreshReferencia = () =>
      buildReferenciaOptions(
        referenciaSelect,
        despesas,
        divisoes,
        pagadorSelect.value,
        recebedorSelect.value,
        formatDate
      );

    pagadorSelect.onchange = refreshReferencia;
    recebedorSelect.onchange = refreshReferencia;
    refreshReferencia();
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
      data_despesa: form.data_despesa.value,
      morador_ids: Array.from(document.getElementById("despesa-moradores").selectedOptions).map((option) =>
        Number(option.value)
      ),
    };
    const response = await apiFetch("/api/despesas/", { method: "POST", body: JSON.stringify(payload) });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      showToast(getErrorMessage(data, "Nao foi possivel salvar a despesa."), "danger");
      return;
    }
    form.reset();
    closeModal("modal-despesa");
    await reloadFinancialSources();
    await renderFinancas(ctx);
    showToast("Despesa cadastrada com sucesso!", "success");
  }

  async function submitPagamento(ctx, event) {
    event.preventDefault();
    const { state, apiFetch, closeModal, reloadFinancialSources, showToast } = ctx;
    const form = event.currentTarget;
    const referenciaDespesa = form.referencia_despesa.value ? Number(form.referencia_despesa.value) : null;
    const payload = {
      republica: state.currentUser.republica_id,
      pagador: Number(form.pagador.value),
      recebedor: Number(form.recebedor.value),
      valor: form.valor.value,
      referencia_despesa: referenciaDespesa,
      observacao: form.observacao.value,
      data_pagamento: form.data_pagamento.value,
    };
    const response = await apiFetch("/api/pagamentos/", { method: "POST", body: JSON.stringify(payload) });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      showToast(getErrorMessage(data, "Nao foi possivel registrar o pagamento."), "danger");
      return;
    }
    form.reset();
    closeModal("modal-pagamento");
    await reloadFinancialSources();
    await renderFinancas(ctx);
    showToast("Pagamento registrado e aplicado com sucesso!", "success");
  }

  window.RABBU_APP.initPage(async (ctx) => {
    document.getElementById("despesa-form").addEventListener("submit", (event) => submitDespesa(ctx, event));
    document.getElementById("pagamento-form").addEventListener("submit", (event) => submitPagamento(ctx, event));
    await renderFinancas(ctx);
  });
})();
