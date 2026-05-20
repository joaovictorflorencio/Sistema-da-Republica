(function () {
  function renderProfile(ctx) {
    const { state } = ctx;
    const user = state.currentUser;

    document.getElementById("perfil-avatar").textContent = (user.first_name || user.username || "R")[0].toUpperCase();
    document.getElementById("perfil-nome-atual").textContent = user.first_name || user.username;
    document.getElementById("perfil-papel-atual").textContent = user.republica_id
      ? user.morador_eh_admin
        ? `Admin da republica - ${user.republica_nome}`
        : `Morador da republica - ${user.republica_nome}`
      : "Sem republica";
    document.getElementById("perfil-username").textContent = `@${user.username}`;
    document.getElementById("perfil-email").textContent = user.email;
    document.getElementById("perfil-republica").textContent = user.republica_nome || "Sem republica";
    document.getElementById("perfil-nome-input").value = user.first_name || "";
    renderRepublicSection(user);
    renderAdminSection(ctx);
    renderDeleteAccountModal(ctx);
  }

  function renderRepublicSection(user) {
    const statusBox = document.getElementById("perfil-republica-status");
    const leaveActions = document.getElementById("perfil-leave-republica-actions");

    if (!statusBox || !leaveActions) return;

    if (user.republica_id) {
      statusBox.innerHTML = `
        <strong>${user.republica_nome}</strong>
        <span class="helper-text">Voce esta vinculado a republica ID ${user.republica_id}. Para trocar de republica, saia desta e faca login novamente.</span>
      `;
      leaveActions.classList.remove("hidden");
      return;
    }

    statusBox.innerHTML = `
      <strong>Sem republica no momento</strong>
      <span class="helper-text">Saia da conta e faca login novamente para escolher entre entrar em uma republica existente ou criar uma nova.</span>
    `;
    leaveActions.classList.add("hidden");
  }

  function getAdminTransferCandidates(ctx) {
    const { state } = ctx;
    return state.currentMoradores.filter(
      (morador) =>
        morador.ativo &&
        morador.usuario &&
        Number(morador.id) !== Number(state.currentUser.morador_id)
    );
  }

  function fillAdminSelect(select, candidates, placeholder) {
    if (!select) return;
    select.innerHTML = "";

    const placeholderOption = document.createElement("option");
    placeholderOption.value = "";
    placeholderOption.textContent = placeholder;
    select.appendChild(placeholderOption);

    candidates.forEach((morador) => {
      const option = document.createElement("option");
      option.value = morador.id;
      option.textContent = `${morador.nome} (@${morador.usuario_username})`;
      select.appendChild(option);
    });
  }

  function renderAdminSection(ctx) {
    const { state } = ctx;
    const card = document.getElementById("perfil-transfer-admin-card");
    const select = document.getElementById("perfil-transfer-admin-select");
    const emptyMessage = document.getElementById("perfil-transfer-admin-empty");
    const submitButton = document.getElementById("perfil-transfer-admin-btn");
    if (!card || !select || !emptyMessage || !submitButton) return;

    const canTransfer = Boolean(state.currentUser.republica_id && state.currentUser.morador_eh_admin);
    card.classList.toggle("hidden", !canTransfer);
    if (!canTransfer) return;

    const candidates = getAdminTransferCandidates(ctx);
    fillAdminSelect(select, candidates, "Escolha um morador");
    const hasCandidates = candidates.length > 0;

    emptyMessage.classList.toggle("hidden", hasCandidates);
    select.disabled = !hasCandidates;
    submitButton.disabled = !hasCandidates;
  }

  function renderDeleteAccountModal(ctx) {
    const { state } = ctx;
    const transferSection = document.getElementById("perfil-delete-admin-transfer-section");
    const transferSelect = document.getElementById("perfil-delete-transfer-admin-select");
    const confirmCheck = document.getElementById("perfil-delete-account-confirm-check");
    const deleteButton = document.getElementById("perfil-delete-account-btn");
    if (!transferSection || !transferSelect || !confirmCheck || !deleteButton) return;

    const needsAdminTransfer = Boolean(state.currentUser.republica_id && state.currentUser.morador_eh_admin);
    const candidates = getAdminTransferCandidates(ctx);
    transferSection.classList.toggle("hidden", !needsAdminTransfer);

    if (needsAdminTransfer) {
      fillAdminSelect(transferSelect, candidates, "Escolha quem assume");
      transferSelect.disabled = candidates.length === 0;
    }

    updateDeleteButtonState(ctx);
  }

  function updateDeleteButtonState(ctx) {
    const { state } = ctx;
    const confirmCheck = document.getElementById("perfil-delete-account-confirm-check");
    const transferSelect = document.getElementById("perfil-delete-transfer-admin-select");
    const deleteButton = document.getElementById("perfil-delete-account-btn");
    if (!confirmCheck || !transferSelect || !deleteButton) return;

    const needsAdminTransfer = Boolean(state.currentUser.republica_id && state.currentUser.morador_eh_admin);
    const hasTransferTarget = !needsAdminTransfer || Boolean(transferSelect.value);
    deleteButton.disabled = !confirmCheck.checked || !hasTransferTarget;
  }

  async function submitProfile(ctx, event) {
    event.preventDefault();
    const { apiFetch, setCurrentUser, showToast } = ctx;
    const form = event.currentTarget;
    const submitButton = form.querySelector("button[type='submit']");

    submitButton.disabled = true;
    submitButton.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Salvando...';

    try {
      const response = await apiFetch("/api/auth/me/", {
        method: "PATCH",
        body: JSON.stringify({
          nome: form.nome.value.trim(),
        }),
      });
      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        const firstError =
          data.detail ||
          Object.values(data)[0]?.[0] ||
          Object.values(data)[0] ||
          "Nao foi possivel atualizar o nome.";
        showToast(String(firstError), "danger");
        return;
      }

      setCurrentUser(data);
      renderProfile(ctx);
      showToast("Nome atualizado com sucesso!", "success");
    } catch (error) {
      showToast("Erro de conexao ao atualizar o perfil.", "danger");
    } finally {
      submitButton.disabled = false;
      submitButton.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Salvar nome';
    }
  }

  async function leaveRepublic(ctx) {
    const { apiFetch, urls, showToast } = ctx;
    const button = document.getElementById("perfil-leave-republica-btn");

    if (!window.confirm("Tem certeza que deseja sair desta republica? Seu historico antigo sera preservado.")) {
      return;
    }

    button.disabled = true;
    button.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Saindo...';

    try {
      const response = await apiFetch(urls.authSairRepublica, { method: "POST" });
      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        showToast(getFirstError(data, "Nao foi possivel sair da republica."), "danger");
        return;
      }

      await apiFetch(urls.authLogout, { method: "POST" }).catch(() => null);
      localStorage.removeItem("gerenciamento_republica_token");
      window.location.href = urls.login;
    } catch (error) {
      showToast("Erro de conexao ao sair da republica.", "danger");
    } finally {
      button.disabled = false;
      button.innerHTML = '<i class="fa-solid fa-right-from-bracket"></i> Sair da republica';
    }
  }

  async function transferAdmin(ctx, moradorId) {
    const { apiFetch, urls, setCurrentUser, showToast } = ctx;
    const response = await apiFetch(urls.authTransferirAdmin, {
      method: "POST",
      body: JSON.stringify({ morador_id: Number(moradorId) }),
    });
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(getFirstError(data, "Nao foi possivel transferir a administracao."));
    }

    if (data.user) {
      setCurrentUser(data.user);
    }

    const current = ctx.state.currentMoradores.find((morador) => Number(morador.id) === Number(ctx.state.currentUser.morador_id));
    const target = ctx.state.currentMoradores.find((morador) => Number(morador.id) === Number(moradorId));
    if (current) current.eh_admin = false;
    if (target) target.eh_admin = true;

    showToast("Administracao transferida com sucesso!", "success");
    renderProfile(ctx);
    return data;
  }

  async function submitTransferAdmin(ctx, event) {
    event.preventDefault();
    const { showToast } = ctx;
    const form = event.currentTarget;
    const button = document.getElementById("perfil-transfer-admin-btn");

    if (!form.morador_id.value) {
      showToast("Escolha quem vai assumir como administrador.", "warning");
      return;
    }

    button.disabled = true;
    button.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Transferindo...';

    try {
      await transferAdmin(ctx, form.morador_id.value);
    } catch (error) {
      showToast(error.message, "danger");
    } finally {
      button.disabled = false;
      button.innerHTML = '<i class="fa-solid fa-user-shield"></i> Transferir administracao';
      renderAdminSection(ctx);
    }
  }

  async function deleteAccount(ctx) {
    const { apiFetch, urls, showToast, closeModal } = ctx;
    const { state } = ctx;
    const button = document.getElementById("perfil-delete-account-btn");
    const transferSelect = document.getElementById("perfil-delete-transfer-admin-select");
    const needsAdminTransfer = Boolean(state.currentUser.republica_id && state.currentUser.morador_eh_admin);

    button.disabled = true;
    button.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Excluindo...';

    try {
      if (needsAdminTransfer) {
        if (!transferSelect.value) {
          showToast("Escolha quem assume como administrador antes de excluir sua conta.", "warning");
          return;
        }
        await transferAdmin(ctx, transferSelect.value);
      }

      const response = await apiFetch(urls.authMe, { method: "DELETE" });
      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        showToast(getFirstError(data, "Nao foi possivel excluir a conta."), "danger");
        return;
      }

      localStorage.removeItem("gerenciamento_republica_token");
      closeModal("modal-delete-account");
      window.location.href = urls.login;
    } catch (error) {
      showToast(error.message || "Erro de conexao ao excluir a conta.", "danger");
    } finally {
      button.disabled = false;
      button.innerHTML = '<i class="fa-solid fa-trash-can"></i> Excluir minha conta';
      updateDeleteButtonState(ctx);
    }
  }

  function getFirstError(data, fallback) {
    if (data.detail) return String(data.detail);
    const firstValue = Object.values(data)[0];
    if (Array.isArray(firstValue)) return String(firstValue[0]);
    if (firstValue) return String(firstValue);
    return fallback;
  }

  window.RABBU_APP.initPage(async (ctx) => {
    renderProfile(ctx);
    document.getElementById("perfil-form").addEventListener("submit", (event) => submitProfile(ctx, event));
    document
      .getElementById("perfil-transfer-admin-form")
      .addEventListener("submit", (event) => submitTransferAdmin(ctx, event));
    document.getElementById("perfil-leave-republica-btn").addEventListener("click", () => leaveRepublic(ctx));
    document.getElementById("perfil-open-delete-account-modal-btn").addEventListener("click", () => {
      document.getElementById("perfil-delete-account-confirm-check").checked = false;
      renderDeleteAccountModal(ctx);
      ctx.openModal("modal-delete-account");
    });
    document
      .getElementById("perfil-delete-account-confirm-check")
      .addEventListener("change", () => updateDeleteButtonState(ctx));
    document
      .getElementById("perfil-delete-transfer-admin-select")
      .addEventListener("change", () => updateDeleteButtonState(ctx));
    document.getElementById("perfil-delete-account-btn").addEventListener("click", () => deleteAccount(ctx));
  });
})();
