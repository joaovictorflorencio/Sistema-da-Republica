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
    document.getElementById("perfil-leave-republica-btn").addEventListener("click", () => leaveRepublic(ctx));
  });
})();
