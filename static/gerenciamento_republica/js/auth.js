(function () {
  const tokenKey = "gerenciamento_republica_token";
  const loginUrl = window.RABBU_AUTH.loginUrl;
  const signupUrl = window.RABBU_AUTH.signupUrl;
  const loginPageUrl = window.RABBU_AUTH.loginPageUrl;
  const redirectUrl = window.RABBU_AUTH.redirectUrl;

  if (localStorage.getItem(tokenKey)) {
    window.location.href = redirectUrl;
    return;
  }

  function showAlert(type, msg) {
    const errorBox = document.getElementById("globalError");
    const successBox = document.getElementById("globalSuccess");

    if (type === "error") {
      document.getElementById("errorText").innerText = msg;
      errorBox.style.display = "flex";
      successBox.style.display = "none";
    } else {
      document.getElementById("successText").innerText = msg;
      successBox.style.display = "flex";
      errorBox.style.display = "none";
    }

    setTimeout(() => {
      errorBox.style.display = "none";
      successBox.style.display = "none";
    }, 3000);
  }

  window.toggleVisibility = function (inputId, iconId) {
    const input = document.getElementById(inputId);
    const icon = document.getElementById(iconId);
    if (input.type === "password") {
      input.type = "text";
      icon.classList.remove("fa-eye");
      icon.classList.add("fa-eye-slash");
    } else {
      input.type = "password";
      icon.classList.remove("fa-eye-slash");
      icon.classList.add("fa-eye");
    }
  };

  function setupSignupModeToggle() {
    const buttons = document.querySelectorAll("[data-signup-mode]");
    if (!buttons.length) return;

    const existingSection = document.getElementById("signup-existing-section");
    const newSection = document.getElementById("signup-new-section");
    const existingInput = document.getElementById("signup-republica");
    const newNameInput = document.getElementById("signup-new-republica-name");
    const newAddressInput = document.getElementById("signup-new-republica-address");

    function activate(mode) {
      buttons.forEach((button) => {
        button.classList.toggle("active", button.dataset.signupMode === mode);
      });
      existingSection.classList.toggle("active", mode === "existing");
      newSection.classList.toggle("active", mode === "new");

      if (mode === "existing") {
        newNameInput.value = "";
        newAddressInput.value = "";
      } else {
        existingInput.value = "";
      }
    }

    buttons.forEach((button) => {
      button.addEventListener("click", () => activate(button.dataset.signupMode));
    });
  }

  setupSignupModeToggle();

  const loginForm = document.getElementById("loginForm");
  if (loginForm) {
    loginForm.addEventListener("submit", async function (event) {
      event.preventDefault();

      const btn = document.getElementById("btn-submit-login");
      btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Entrando...';
      btn.disabled = true;

      try {
        const response = await fetch(loginUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: document.getElementById("login-email").value.trim(),
            password: document.getElementById("login-password").value,
          }),
        });
        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
          showAlert("error", data.detail || "Nao foi possivel realizar o login.");
          return;
        }

        localStorage.setItem(tokenKey, data.token);
        showAlert("success", "Login realizado com sucesso!");
        setTimeout(() => {
          window.location.href = redirectUrl;
        }, 600);
      } catch (error) {
        showAlert("error", "Erro de conexao com o servidor.");
      } finally {
        btn.innerHTML = '<span>Entrar</span><i class="fa-solid fa-arrow-right-to-bracket"></i>';
        btn.disabled = false;
      }
    });
  }

  const signupForm = document.getElementById("signupForm");
  if (signupForm) {
    signupForm.addEventListener("submit", async function (event) {
      event.preventDefault();

      const btn = document.getElementById("btn-submit-signup");
      btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Criando...';
      btn.disabled = true;

      try {
        const republicaValue = document.getElementById("signup-republica").value.trim();
        const novaRepublicaNome = document.getElementById("signup-new-republica-name").value.trim();
        const novaRepublicaEndereco = document.getElementById("signup-new-republica-address").value.trim();
        const response = await fetch(signupUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            nome: document.getElementById("signup-name").value.trim(),
            username: document.getElementById("signup-username").value.trim(),
            email: document.getElementById("signup-email").value.trim(),
            password: document.getElementById("signup-password").value,
            password_confirm: document.getElementById("signup-password-confirm").value,
            republica: republicaValue ? Number(republicaValue) : null,
            nova_republica_nome: novaRepublicaNome,
            nova_republica_endereco: novaRepublicaEndereco,
          }),
        });
        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
          const firstError =
            data.detail ||
            Object.values(data)[0]?.[0] ||
            Object.values(data)[0] ||
            "Nao foi possivel criar a conta.";
          showAlert("error", String(firstError));
          return;
        }

        localStorage.setItem(tokenKey, data.token);
        showAlert("success", "Conta criada com sucesso!");
        setTimeout(() => {
          window.location.href = redirectUrl;
        }, 700);
      } catch (error) {
        showAlert("error", "Erro de conexao com o servidor.");
      } finally {
        btn.innerHTML = '<span>Criar conta</span><i class="fa-solid fa-user-plus"></i>';
        btn.disabled = false;
      }
    });
  }
})();
