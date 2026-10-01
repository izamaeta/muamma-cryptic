import {
  countUp,
  logoHop,
  minutesSeconds,
  motionOk,
  play,
  pulse,
  revealWords,
  sparkBurst,
  springIn,
} from "./motion.js";

export function closeOnBackdrop(dialog) {
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
}

export async function slideIn(dialog) {
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

  const setNumber = (selector, value) => {
    const element = dialog.querySelector(selector);
    if (!element || typeof value !== "number") return;
    element.textContent = value;
    countUp(element, value);
  };

  closeOnBackdrop(dialog);

  return {
    ready: dialog.dataset.ready === "1",

    fill(data, solved) {
      set(".result-title", solved ? "Tebrikler! Muamma çözüldü" : "Mühür açıldı");
      set(".result-duration", minutesSeconds(data.duration));
      setNumber(".result-guesses", data.guesses);
      setNumber(".result-hints", data.hints);
      setNumber(".result-letters", data.letters);
      setNumber(".result-streak", data.streak);

      const community = dialog.querySelector(".result-community");
      if (community && data.community) {
        community.textContent = data.community;
        community.hidden = false;
      }

      dialog.dataset.ready = "1";
    },

    async open(celebrate) {
      if (dialog.open) return;
      dialog.showModal();
      if (!motionOk()) return;
      if (!celebrate) {
        await slideIn(dialog);
        return;
      }

      const panel = dialog.querySelector(".result-panel");
      const logo = dialog.querySelector(".result-logo");
      const share = dialog.querySelector(".result-action:not([hidden])");

      const running = [
        springIn(panel),
        logoHop(logo),
        sparkBurst(dialog.querySelector(".result-logo-wrap")),
        revealWords(dialog.querySelector(".result-title")),
      ];
      if (share) running.push(pulse(share));
      await Promise.all(running);
    },
  };
}
