import { minutesSeconds, motionOk, play } from "./motion.js";

function closeOnBackdrop(dialog) {
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
}

async function slideIn(dialog) {
  if (!motionOk()) return;
  await play(
    dialog.querySelector(".result-panel"),
    [
      { transform: "translateY(24px) scale(0.96)", opacity: 0 },
      { transform: "translateY(0) scale(1)", opacity: 1 },
    ],
    { duration: 320 }
  );
}

export function revealAsker(dialog) {
  if (!dialog) return () => Promise.resolve(false);

  closeOnBackdrop(dialog);

  return () => new Promise((resolve) => {
    dialog.returnValue = "";
    dialog.addEventListener(
      "close",
      () => resolve(dialog.returnValue === "yes"),
      { once: true }
    );
    dialog.showModal();
    slideIn(dialog);
  });
}

export function resultWindow(dialog) {
  if (!dialog) return null;

  const set = (selector, value) => {
    const element = dialog.querySelector(selector);
    if (element && value !== undefined && value !== null) {
      element.textContent = value;
    }
  };

  closeOnBackdrop(dialog);

  return {
    ready: dialog.dataset.ready === "1",

    fill(data, solved) {
      set(".result-title", solved ? "Tebrikler! Muamma çözüldü" : "Mühür açıldı");
      set(".result-duration", minutesSeconds(data.duration));
      set(".result-guesses", data.guesses);
      set(".result-hints", data.hints);
      set(".result-letters", data.letters);
      set(".result-streak", data.streak);
      dialog.dataset.ready = "1";
    },

    async open() {
      if (dialog.open) return;
      dialog.showModal();
      await slideIn(dialog);
    },
  };
}
