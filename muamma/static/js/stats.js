import { countUp, motionOk } from "./motion.js";
import { closeOnBackdrop, slideIn } from "./result.js";

const dialog = document.querySelector(".stats-window");
const buttons = [...document.querySelectorAll(".stats-open")];

if (dialog && buttons.length) {
  const list = dialog.querySelector(".stats");
  const empty = dialog.querySelector(".stats-empty");

  closeOnBackdrop(dialog);

  async function load() {
    try {
      const response = await fetch("/api/me/stats", {
        headers: { Accept: "application/json" },
      });
      return response.ok ? await response.json() : null;
    } catch {
      return null;
    }
  }

  function show(data) {
    const nothing = data.daily_played === 0 && data.practice_solved === 0;
    list.hidden = nothing;
    empty.hidden = !nothing;
    if (nothing) return;

    for (const element of dialog.querySelectorAll(".count")) {
      const value = data[element.dataset.key] ?? 0;
      element.textContent = value;
      if (motionOk()) countUp(element, value);
    }
  }

  async function open() {
    if (dialog.open) return;
    dialog.showModal();
    slideIn(dialog);

    const data = await load();
    if (data) show(data);
  }

  buttons.forEach((button) => button.addEventListener("click", open));
}
