(function () {
  const tokenKey = "gerenciamento_republica_token";
  const loginUrl = window.RABBU_AUTH.loginUrl;
  const signupUrl = window.RABBU_AUTH.signupUrl;
  const loginPageUrl = window.RABBU_AUTH.loginPageUrl;
  const redirectUrl = window.RABBU_AUTH.redirectUrl;
  const viaCepBaseUrl = window.RABBU_AUTH.viaCepBaseUrl;
  const mapsSearchBaseUrl = window.RABBU_AUTH.mapsSearchBaseUrl;

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

  function setFieldError(inputId, message) {
    const input = document.getElementById(inputId);
    const wrapper = input?.closest(".input-wrapper");
    const error = document.getElementById(`${inputId}-error`);
    const hasError = Boolean(message);

    if (!input || !wrapper || !error) return;

    wrapper.classList.toggle("has-error", hasError);
    error.textContent = message || "";
    error.classList.toggle("active", hasError);
    input.setAttribute("aria-invalid", hasError ? "true" : "false");
  }

  function clearFieldError(inputId) {
    setFieldError(inputId, "");
  }

  function validateSignupPasswords(options = {}) {
    const showGlobalAlert = options.showGlobalAlert === true;
    const passwordInput = document.getElementById("signup-password");
    const confirmInput = document.getElementById("signup-password-confirm");

    if (!passwordInput || !confirmInput) {
      return true;
    }

    const password = passwordInput.value;
    const confirmPassword = confirmInput.value;
    let isValid = true;

    if (!password.trim()) {
      setFieldError("signup-password", "A senha e obrigatoria.");
      isValid = false;
    } else {
      clearFieldError("signup-password");
    }

    if (!confirmPassword.trim()) {
      setFieldError("signup-password-confirm", "Confirme a senha para continuar.");
      isValid = false;
    } else if (password && password !== confirmPassword) {
      setFieldError("signup-password-confirm", "As senhas precisam ser iguais.");
      if (showGlobalAlert) {
        showAlert("error", "As senhas precisam ser iguais.");
      }
      isValid = false;
    } else {
      clearFieldError("signup-password-confirm");
    }

    return isValid;
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

  function onlyDigits(value) {
    return String(value || "").replace(/\D/g, "");
  }

  function formatCep(value) {
    const digits = onlyDigits(value).slice(0, 8);
    if (digits.length <= 5) return digits;
    return `${digits.slice(0, 5)}-${digits.slice(5)}`;
  }

  function composeRepublicAddress() {
    const street = document.getElementById("signup-new-republica-street")?.value.trim() || "";
    const number = document.getElementById("signup-new-republica-number")?.value.trim() || "";
    const neighborhood = document.getElementById("signup-new-republica-neighborhood")?.value.trim() || "";
    const city = document.getElementById("signup-new-republica-city")?.value.trim() || "";
    const state = (document.getElementById("signup-new-republica-state")?.value || "").trim().toUpperCase();
    const cep = formatCep(document.getElementById("signup-new-republica-cep")?.value || "");
    const complement = document.getElementById("signup-new-republica-complement")?.value.trim() || "";

    const firstLineParts = [street, number && `numero ${number}`].filter(Boolean);
    const secondLineParts = [neighborhood, city && state ? `${city} - ${state}` : city || state].filter(Boolean);
    const extraParts = [complement, cep && `CEP ${cep}`].filter(Boolean);

    return [firstLineParts.join(", "), secondLineParts.join(", "), extraParts.join(", ")]
      .filter(Boolean)
      .join(" | ");
  }

  function updateRepublicAddressPreview() {
    const addressInput = document.getElementById("signup-new-republica-address");
    if (!addressInput) return "";
    const composed = composeRepublicAddress();
    addressInput.value = composed;
    return composed;
  }

  function clearRepublicAddressFields() {
    [
      "signup-new-republica-cep",
      "signup-new-republica-street",
      "signup-new-republica-number",
      "signup-new-republica-neighborhood",
      "signup-new-republica-city",
      "signup-new-republica-state",
      "signup-new-republica-complement",
      "signup-new-republica-address",
    ].forEach((id) => {
      const field = document.getElementById(id);
      if (field) field.value = "";
    });
  }

  function setupRepublicAddressHelpers() {
    const cepInput = document.getElementById("signup-new-republica-cep");
    const addressPreview = document.getElementById("signup-new-republica-address");
    const searchButton = document.getElementById("signup-cep-search-btn");
    const mapButton = document.getElementById("signup-open-map-btn");

    if (!cepInput || !addressPreview) return;
    let cepLookupInProgress = false;

    const syncIds = [
      "signup-new-republica-street",
      "signup-new-republica-number",
      "signup-new-republica-neighborhood",
      "signup-new-republica-city",
      "signup-new-republica-state",
      "signup-new-republica-complement",
    ];

    syncIds.forEach((id) => {
      const field = document.getElementById(id);
      if (!field) return;
      field.addEventListener("input", updateRepublicAddressPreview);
    });

    cepInput.addEventListener("input", () => {
      cepInput.value = formatCep(cepInput.value);
      updateRepublicAddressPreview();
    });

    async function searchCep() {
      if (cepLookupInProgress) return;

      const cep = onlyDigits(cepInput.value);
      if (cep.length !== 8) {
        showAlert("error", "Informe um CEP valido com 8 digitos.");
        return;
      }

      cepLookupInProgress = true;
      if (searchButton) {
        searchButton.disabled = true;
        searchButton.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Buscando...';
      }

      try {
        const response = await fetch(`${viaCepBaseUrl}${cep}/json/`);
        const data = await response.json();

        if (!response.ok || data.erro) {
          showAlert("error", "Nao foi possivel localizar esse CEP.");
          return;
        }

        document.getElementById("signup-new-republica-street").value = data.logradouro || "";
        document.getElementById("signup-new-republica-neighborhood").value = data.bairro || "";
        document.getElementById("signup-new-republica-city").value = data.localidade || "";
        document.getElementById("signup-new-republica-state").value = (data.uf || "").toUpperCase();
        updateRepublicAddressPreview();
        showAlert("success", "Endereco preenchido a partir do CEP.");
      } catch (error) {
        showAlert("error", "Erro ao consultar o CEP.");
      } finally {
        cepLookupInProgress = false;
        if (searchButton) {
          searchButton.disabled = false;
          searchButton.innerHTML = '<i class="fa-solid fa-magnifying-glass-location"></i> Buscar CEP';
        }
      }
    }

    cepInput.addEventListener("blur", () => {
      if (onlyDigits(cepInput.value).length === 8) {
        searchCep();
      }
    });

    if (searchButton) {
      searchButton.addEventListener("click", searchCep);
    }

    if (mapButton) {
      mapButton.addEventListener("click", () => {
        const composed = updateRepublicAddressPreview();
        if (!composed) {
          showAlert("error", "Preencha o endereco da republica para abrir o mapa.");
          return;
        }
        window.open(`${mapsSearchBaseUrl}${encodeURIComponent(composed)}`, "_blank", "noopener,noreferrer");
      });
    }

    return {
      clear: clearRepublicAddressFields,
      getAddress: updateRepublicAddressPreview,
    };
  }

  const republicAddressHelpers = setupRepublicAddressHelpers();

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
        if (republicAddressHelpers) {
          republicAddressHelpers.clear();
        } else {
          newAddressInput.value = "";
        }
      } else {
        existingInput.value = "";
        if (republicAddressHelpers) {
          republicAddressHelpers.getAddress();
        }
      }
    }

    buttons.forEach((button) => {
      button.addEventListener("click", () => activate(button.dataset.signupMode));
    });
  }

  setupSignupModeToggle();

  function setupSignupPasswordValidation() {
    const passwordInput = document.getElementById("signup-password");
    const confirmInput = document.getElementById("signup-password-confirm");

    if (!passwordInput || !confirmInput) return;

    passwordInput.addEventListener("input", () => {
      if (passwordInput.value.trim()) {
        clearFieldError("signup-password");
      }

      if (confirmInput.value.trim()) {
        validateSignupPasswords();
      }
    });

    confirmInput.addEventListener("input", () => {
      if (confirmInput.value.trim()) {
        validateSignupPasswords();
      } else {
        clearFieldError("signup-password-confirm");
      }
    });

    passwordInput.addEventListener("blur", () => {
      validateSignupPasswords();
    });

    confirmInput.addEventListener("blur", () => {
      validateSignupPasswords();
    });
  }

  setupSignupPasswordValidation();

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

      if (!validateSignupPasswords({ showGlobalAlert: true })) {
        return;
      }

      const btn = document.getElementById("btn-submit-signup");
      btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Criando...';
      btn.disabled = true;

      try {
        const republicaValue = document.getElementById("signup-republica").value.trim();
        const novaRepublicaNome = document.getElementById("signup-new-republica-name").value.trim();
        const signupMode = document.querySelector("[data-signup-mode].active")?.dataset.signupMode || "existing";
        const novaRepublicaEndereco = republicAddressHelpers
          ? republicAddressHelpers.getAddress().trim()
          : document.getElementById("signup-new-republica-address").value.trim();

        if (signupMode === "new" && !novaRepublicaEndereco) {
          showAlert("error", "Preencha o endereco da nova republica antes de continuar.");
          return;
        }

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
