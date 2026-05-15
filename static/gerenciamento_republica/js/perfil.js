(function () {
  function renderProfile(ctx) {
    const { state } = ctx;
    const user = state.currentUser;

    document.getElementById("perfil-avatar").textContent = (user.first_name || user.username || "R")[0].toUpperCase();
    document.getElementById("perfil-nome-atual").textContent = user.first_name || user.username;
    document.getElementById("perfil-papel-atual").textContent = user.morador_eh_admin
      ? `Admin da republica - ${user.republica_nome || "Sem republica"}`
      : `Morador da republica - ${user.republica_nome || "Sem republica"}`;
    document.getElementById("perfil-username").textContent = `@${user.username}`;
    document.getElementById("perfil-email").textContent = user.email;
    document.getElementById("perfil-republica").textContent = user.republica_nome || "Sem republica";
    document.getElementById("perfil-nome-input").value = user.first_name || "";
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

  window.RABBU_APP.initPage(async (ctx) => {
    renderProfile(ctx);
    document.getElementById("perfil-form").addEventListener("submit", (event) => submitProfile(ctx, event));
  });
})();
