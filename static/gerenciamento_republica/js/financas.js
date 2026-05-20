(function () {
  const CATEGORY_LABELS = {
    ALUGUEL: "Moradia",
    ENERGIA: "Energia",
    AGUA: "Agua",
    INTERNET: "Internet",
    MERCADO: "Mercado",
    LIMPEZA: "Limpeza",
    OUTROS: "Outros",
  };

  const ALLOWED_PROOF_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg", ".webp"];
  const MAX_PROOF_SIZE = 5 * 1024 * 1024;

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

  function getTodayISO() {
    return new Date().toISOString().slice(0, 10);
  }

  function isOverdue(expense) {
    // Conta vencida continua pendente; apenas recebe destaque visual.
    return !isPaid(expense) && Boolean(expense.data_vencimento) && expense.data_vencimento < getTodayISO();
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
    // O admin pode acompanhar tudo, mas o morador comum so quita a conta
    // atribuida diretamente a ele.
    return (
      state.currentUser.is_staff ||
      state.currentUser.morador_eh_admin ||
      Number(state.currentUser.morador_id) === Number(expense.paga_por)
    );
  }

  function validateProofFile(file) {
    // O frontend antecipa a mesma regra de comprovante aplicada pelo backend.
    if (!file) {
      return "Selecione um comprovante para registrar o pagamento.";
    }

    const lowerName = String(file.name || "").toLowerCase();
    const hasAllowedExtension = ALLOWED_PROOF_EXTENSIONS.some((extension) => lowerName.endsWith(extension));
    if (!hasAllowedExtension) {
      return "Use um comprovante em PDF, PNG, JPG ou WEBP.";
    }

    if (file.size > MAX_PROOF_SIZE) {
      return "O comprovante precisa ter no maximo 5 MB.";
    }

    return null;
  }

  function setPaymentFieldError(form, fieldName, message) {
    const field = form.elements[fieldName];
    const error = form.querySelector(`[data-field-error="${fieldName}"]`);
    const hasError = Boolean(message);

    if (field) {
      field.classList.toggle("input-error", hasError);
      field.setAttribute("aria-invalid", hasError ? "true" : "false");
    }

    if (error) {
      error.textContent = message || "";
      error.classList.toggle("active", hasError);
    }
  }

  function clearPaymentFieldErrors(form) {
    setPaymentFieldError(form, "data_pagamento", "");
    setPaymentFieldError(form, "comprovante_pagamento", "");
  }

  function validatePaymentForm(form) {
    // Registrar pagamento exige data e comprovante; sem ambos a conta continua
    // como pendente.
    clearPaymentFieldErrors(form);

    const dataPagamento = form.data_pagamento.value;
    const comprovante = form.comprovante_pagamento.files[0];
    let firstError = null;

    if (!dataPagamento) {
      firstError = "Informe a data em que a conta foi paga.";
      setPaymentFieldError(form, "data_pagamento", firstError);
    }

    const proofMessage = validateProofFile(comprovante);
    if (proofMessage) {
      if (!firstError) firstError = proofMessage;
      setPaymentFieldError(form, "comprovante_pagamento", proofMessage);
    }

    if (firstError) {
      const invalidField = form.querySelector(".input-error");
      if (invalidField) invalidField.focus();
    }

    return firstError;
  }

  function buildExpenseCard(ctx, expense, variant) {
    // Cada card reflete o estado real da conta: pendente, vencida ou paga.
    const { state, formatMoney, formatDate, openModal } = ctx;
    const card = document.createElement("article");
    card.className = `financas-card financas-card-${variant}`;
    if (isOverdue(expense)) {
      card.classList.add("financas-card-vencida");
    }

    const overdue = isOverdue(expense);
    const vencimento = expense.data_vencimento
      ? `${overdue ? "Venceu em" : "Vence em"} ${formatDate(expense.data_vencimento)}`
      : "Sem vencimento informado";
    const descricao = expense.descricao || "Sem observacoes adicionais.";
    const categoria = formatCategoryLabel(expense.categoria);
    const pagamentoInfo = isPaid(expense)
      ? `Pago por ${expense.quitada_por_nome || expense.paga_por_nome}`
      : `Responsavel cadastrado: ${expense.paga_por_nome}`;
    const dataStatus = isPaid(expense)
      ? `Quitada em ${formatDate(expense.data_pagamento)}`
      : vencimento;
    const cadastroInfo = `Lancada em ${formatDate(expense.data_despesa)}`;

    card.innerHTML = `
      <div class="financas-card-top">
        <div>
          <span class="status-chip ${isPaid(expense) ? "status-concluida" : "status-pendente"}">
            ${isPaid(expense) ? "Pago" : "Pendente"}
          </span>
          ${overdue ? '<span class="status-chip status-vencida">Vencida</span>' : ""}
          <h4>${expense.titulo}</h4>
        </div>
        <strong>${formatMoney(expense.valor_total)}</strong>
      </div>
      <p class="financas-card-description">${descricao}</p>
      <div class="financas-card-metadata">
          <span><i class="fa-solid fa-tag"></i> ${categoria}</span>
          <span><i class="fa-solid fa-calendar-days"></i> ${dataStatus}</span>
          <span><i class="fa-solid fa-user"></i> ${pagamentoInfo}</span>
          <span><i class="fa-solid fa-clock"></i> ${cadastroInfo}</span>
      </div>
    `;

    const actions = document.createElement("div");
    actions.className = "financas-card-actions";

    if (!isPaid(expense) && canConfirmPayment(state, expense)) {
      const button = document.createElement("button");
      button.className = "btn btn-sm";
      button.innerHTML = '<i class="fa-solid fa-file-circle-check"></i> Registrar pagamento';
      button.addEventListener("click", () => {
        const comprovanteForm = document.getElementById("comprovante-form");
        if (comprovanteForm) {
          clearPaymentFieldErrors(comprovanteForm);
        }
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
    const { state, apiFetch, renderList, fillSelect, formatMoney, formatDate } = ctx;

    const despesasResponse = await apiFetch("/api/despesas/");
    const despesas = await despesasResponse.json();

    // O quadro separa o que ainda precisa de acao do que ja foi comprovado.
    const pendentes = despesas
      .filter((expense) => !isPaid(expense))
      .sort((a, b) => compareByDate(a, b, "data_vencimento", "asc"));
    const pagas = despesas
      .filter((expense) => isPaid(expense))
      .sort((a, b) => compareByDate(a, b, "data_pagamento", "desc"));
    const minhasContas = despesas
      .filter((expense) => Number(expense.paga_por) === Number(state.currentUser.morador_id))
      .sort((a, b) => compareByDate(a, b, "data_vencimento", "asc"));
    const minhasPendentes = minhasContas.filter((expense) => !isPaid(expense));

    // O resumo por morador considera quem e responsavel pela conta cadastrada.
    const resumoResponsaveis = state.currentMoradores.map((morador) => {
      const contas = despesas.filter((expense) => Number(expense.paga_por) === Number(morador.id));
      const contasPendentes = contas.filter((expense) => !isPaid(expense));
      const contasPagas = contas.filter((expense) => isPaid(expense));
      return {
        id: morador.id,
        nome: morador.nome,
        totalContas: contas.length,
        valorTotal: contas.reduce((acc, expense) => acc + toNumber(expense.valor_total), 0),
        valorPendente: contasPendentes.reduce((acc, expense) => acc + toNumber(expense.valor_total), 0),
        contasPendentes: contasPendentes.length,
        contasPagas: contasPagas.length,
      };
    });

    const totalGastos = despesas.reduce((acc, expense) => acc + toNumber(expense.valor_total), 0);
    const valorPendente = pendentes.reduce((acc, expense) => acc + toNumber(expense.valor_total), 0);
    const valorPago = pagas.reduce((acc, expense) => acc + toNumber(expense.valor_total), 0);
    const meuValorPendente = minhasPendentes.reduce((acc, expense) => acc + toNumber(expense.valor_total), 0);

    document.getElementById("financas-total-gastos").textContent = formatMoney(totalGastos);
    document.getElementById("financas-total-pendentes").textContent = String(pendentes.length);
    document.getElementById("financas-total-pagas").textContent = String(pagas.length);
    document.getElementById("financas-minha-participacao").textContent = formatMoney(meuValorPendente);
    document.getElementById("financas-valor-pendente").textContent = `${formatMoney(valorPendente)} em aberto`;
    document.getElementById("financas-valor-pago").textContent = `${formatMoney(valorPago)} comprovados`;
    document.getElementById("financas-meu-status").textContent =
      minhasContas.length > 0
        ? `${minhasPendentes.length} ${pluralize(minhasPendentes.length, "conta pendente", "contas pendentes")} atribuidas a voce.`
        : "Voce ainda nao tem contas atribuidas.";
    document.getElementById("financas-pendentes-resumo").textContent =
      pendentes.length > 0
        ? `${pendentes.length} ${pluralize(pendentes.length, "conta aguardando pagamento", "contas aguardando pagamento")}`
        : "Nenhuma conta em aberto no momento.";
    document.getElementById("financas-pagas-resumo").textContent =
      pagas.length > 0
        ? `${pagas.length} ${pluralize(pagas.length, "conta ja foi quitada", "contas ja foram quitadas")}`
        : "Sem contas pagas ainda.";

    const toolbarNote = document.getElementById("financas-toolbar-note");
    if (toolbarNote) {
      if (state.currentUser.is_staff || state.currentUser.morador_eh_admin) {
        toolbarNote.textContent =
          "Voce pode cadastrar novas despesas, escolher o responsavel e acompanhar o status de cada conta.";
      } else {
        toolbarNote.textContent =
          "Apenas o admin cadastra despesas. Voce pode registrar pagamento somente das contas atribuidas a voce.";
      }
    }

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
      "financas-minhas-contas-list",
      minhasContas,
      (expense) => {
        const item = document.createElement("div");
        item.className = "expense-item";
        item.innerHTML = `
          <div class="expense-item-main">
            <div class="exp-icon"><i class="fa-solid fa-receipt"></i></div>
            <div class="expense-item-details">
              <strong style="display:block;">${expense.titulo}</strong>
              <span class="helper-text">${formatDate(expense.data_despesa)} - ${formatCategoryLabel(expense.categoria)}</span>
              <span class="helper-text">${isPaid(expense) ? "Conta ja paga" : "Aguardando pagamento"}</span>
            </div>
          </div>
          <strong>${formatMoney(expense.valor_total)}</strong>
        `;
        return item;
      },
      "Voce ainda nao tem despesas sob sua responsabilidade."
    );

    renderList(
      "financas-responsaveis-list",
      resumoResponsaveis.sort((a, b) => b.valorPendente - a.valorPendente),
      (morador) => {
        const card = document.createElement("div");
        const destaque = Number(morador.id) === Number(state.currentUser.morador_id) ? " (voce)" : "";
        card.className = "saldo-card";
        card.innerHTML = `
          <div class="saldo-card-top">
            <div>
              <strong style="display:block;">${morador.nome}${destaque}</strong>
              <span class="helper-text">${morador.totalContas} ${pluralize(morador.totalContas, "conta atribuida", "contas atribuidas")}</span>
            </div>
            <span class="badge badge-warning">${formatMoney(morador.valorTotal)}</span>
          </div>
          <div class="saldo-card-metrics">
            <div>
              <span class="helper-text">Pagas</span>
              <strong>${morador.contasPagas}</strong>
            </div>
            <div>
              <span class="helper-text">Pendentes</span>
              <strong>${morador.contasPendentes}</strong>
            </div>
            <div>
              <span class="helper-text">Valor em aberto</span>
              <strong>${formatMoney(morador.valorPendente)}</strong>
            </div>
          </div>
        `;
        return card;
      },
      "Nenhum morador encontrado."
    );

    fillSelect(document.getElementById("despesa-paga-por"), false);
    const botaoNovaDespesa = document.getElementById("financas-nova-despesa-btn");
    if (botaoNovaDespesa) {
      botaoNovaDespesa.classList.toggle(
        "hidden",
        !(state.currentUser.is_staff || state.currentUser.morador_eh_admin)
      );
    }
  }

  async function submitDespesa(ctx, event) {
    event.preventDefault();
    const { state, apiFetch, closeModal, reloadFinancialSources, showToast } = ctx;
    const form = event.currentTarget;

    // A republica vem do usuario logado para evitar cadastro em republica errada.
    const payload = {
      republica: state.currentUser.republica_id,
      titulo: form.titulo.value,
      descricao: form.descricao.value,
      categoria: form.categoria.value,
      valor_total: form.valor_total.value,
      paga_por: Number(form.paga_por.value),
      data_vencimento: form.data_vencimento.value || null,
      data_despesa: form.data_despesa.value,
    };

    const response = await apiFetch("/api/despesas/", {
      method: "POST",
      body: JSON.stringify(payload),
    });
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

  async function submitComprovante(ctx, event) {
    event.preventDefault();
    const { apiFetch, closeModal, reloadFinancialSources, showToast } = ctx;
    const form = event.currentTarget;
    const despesaId = document.getElementById("comprovante-despesa-id").value;
    const formValidationMessage = validatePaymentForm(form);

    if (formValidationMessage) {
      showToast(formValidationMessage, "danger");
      return;
    }

    const comprovante = form.comprovante_pagamento.files[0];

    // FormData e usado porque o comprovante e um arquivo real, nao JSON.
    const payload = new FormData();
    payload.append("status_pagamento", "PAGA");
    payload.append("data_pagamento", form.data_pagamento.value);
    payload.append("comprovante_pagamento", comprovante);

    const response = await apiFetch(`/api/despesas/${despesaId}/`, {
      method: "PATCH",
      body: payload,
    });
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      showToast(getErrorMessage(data, "Nao foi possivel registrar o pagamento."), "danger");
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

    comprovanteForm.data_pagamento.addEventListener("input", () => {
      if (comprovanteForm.data_pagamento.value) {
        setPaymentFieldError(comprovanteForm, "data_pagamento", "");
      }
    });
    comprovanteForm.comprovante_pagamento.addEventListener("change", () => {
      const message = validateProofFile(comprovanteForm.comprovante_pagamento.files[0]);
      setPaymentFieldError(comprovanteForm, "comprovante_pagamento", message);
    });

    despesaForm.addEventListener("submit", (event) => submitDespesa(ctx, event));
    comprovanteForm.addEventListener("submit", (event) => submitComprovante(ctx, event));

    await renderFinancas(ctx);
  });
})();
