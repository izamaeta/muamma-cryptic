const STORAGE_KEY = "muamma-theme";
const root = document.documentElement;

function storedTheme() {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function applyTheme(theme) {
  if (theme === "dark" || theme === "light") {
    root.dataset.theme = theme;
  } else {
    delete root.dataset.theme;
  }
}

function isDark() {
  // light unless the reader has asked for dark; the system is not consulted
  return root.dataset.theme === "dark";
}

applyTheme(storedTheme());

document.addEventListener("DOMContentLoaded", () => {
  const button = document.querySelector(".theme-toggle");
  if (!button) return;

  const describe = () => {
    const dark = isDark();
    button.setAttribute("aria-pressed", String(dark));
    button.setAttribute("aria-label", dark ? "Açık temaya geç" : "Koyu temaya geç");
  };

  button.addEventListener("click", () => {
    const next = isDark() ? "light" : "dark";
    applyTheme(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* private mode: the choice lasts for this page only */
    }
    describe();
  });

  describe();
});
