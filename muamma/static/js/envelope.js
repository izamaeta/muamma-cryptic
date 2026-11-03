import { motionOk, play, wait } from "./motion.js";

const EASE_STAMP = "cubic-bezier(.2,.9,.25,1)";
const EASE_FALL = "cubic-bezier(.5,0,.9,.4)";
const EASE_FLAP = "cubic-bezier(.4,0,.2,1)";

function finished(animation) {
  return animation.finished.catch(() => {});
}

function createEnvelope() {
  const stage = document.querySelector(".env-stage");
  if (!stage) return null;

  const flap = stage.querySelector(".env-flap");
  const mouthGlow = stage.querySelector(".env-mouth-glow");
  const letter = stage.querySelector(".env-letter");
  const letterDate = letter?.querySelector(".env-letter-date");
  const letterTitle = letter?.querySelector(".env-letter-title");
  const faceDate = stage.querySelector(".env-face-date")?.textContent ?? "";
  const faceTitle = stage.querySelector(".env-face-title");
  const mount = stage.querySelector(".env-seal-mount");
  const sealGlow = stage.querySelector(".env-seal-glow");
  const sealRing = stage.querySelector(".env-seal-ring");
  const whole = stage.querySelector(".gs-whole");
  const cracked = stage.querySelector(".gs-cracked");
  const pieces = [...stage.querySelectorAll(".gs-piece")];
  const flash = stage.querySelector(".env-flash");
  const flecks = stage.querySelector(".env-flecks");

  function loadDeferred() {
    const images = [...stage.querySelectorAll("img.env-deferred")];
    if (!images.length) return Promise.resolve();

    return new Promise((resolve) => {
      const schedule = window.requestIdleCallback ?? ((fn) => setTimeout(fn, 1));
      schedule(
        () => {
          const decoding = images.map((img) => {
            img.src = img.dataset.src;
            delete img.dataset.src;
            img.classList.remove("env-deferred");
            return img.decode ? img.decode().catch(() => {}) : Promise.resolve();
          });
          Promise.all(decoding).then(resolve);
        },
        { timeout: 300 }
      );
    });
  }

  const ready = loadDeferred();

  function rise() {
    return play(
      stage,
      [
        { opacity: 0, transform: "translateY(12px)" },
        { opacity: 1, transform: "translateY(0)" },
      ],
      { duration: 350, easing: "ease-out" }
    ).then(() =>
      motionOk()
        ? Promise.all([
            play(
              sealGlow,
              [{ opacity: 0 }, { opacity: 0.96 }, { opacity: 1 }],
              { duration: 1 }
            ),
            play(
              whole,
              [
                { transform: "translate(-50%, -50%) scale(1.4)", opacity: 0 },
                { transform: "translate(-50%, -50%) scale(1)", opacity: 1 },
              ],
              { duration: 420, easing: EASE_STAMP }
            ),
            play(
              sealRing,
              [
                { transform: "translate(-50%, -50%) scale(0.9)", opacity: 0.3 },
                { transform: "translate(-50%, -50%) scale(1.5)", opacity: 0 },
              ],
              { duration: 500 }
            ),
          ])
        : Promise.resolve()
    );
  }

  function shake() {
    return play(
      stage,
      [
        { transform: "rotate(0deg) translateX(0)" },
        { transform: "rotate(-2deg) translateX(-3px)" },
        { transform: "rotate(2deg) translateX(3px)" },
        { transform: "rotate(-1deg) translateX(-2px)" },
        { transform: "rotate(1deg) translateX(2px)" },
        { transform: "rotate(0deg) translateX(0)" },
      ],
      { duration: 260 }
    );
  }

  function spawnFlecks(count) {
    if (!flecks) return [];
    return Array.from({ length: count }, () => {
      const dot = document.createElement("span");
      dot.className = "env-fleck";
      flecks.append(dot);
      const angle = Math.random() * 2 * Math.PI;
      const distance = 30 + Math.random() * 60;
      const animation = dot.animate(
        [
          { transform: "translate(-50%, -50%) scale(1)", opacity: 1 },
          {
            transform: `translate(calc(-50% + ${Math.cos(angle) * distance}px), calc(-50% + ${
              Math.sin(angle) * distance + 40
            }px)) scale(0.6)`,
            opacity: 0,
          },
        ],
        { duration: 600 + Math.random() * 300, easing: EASE_FALL, fill: "forwards" }
      );
      return { dot, animation };
    });
  }

  function openFlap(quiet) {
    if (!flap) return Promise.resolve();
    const duration = quiet ? 750 : 600;
    const animation = flap.animate(
      [{ transform: "rotateX(0deg)" }, { transform: "rotateX(-180deg)" }],
      { duration, easing: EASE_FLAP, fill: "forwards" }
    );
    setTimeout(() => {
      flap.style.zIndex = "3";
    }, duration / 2);
    const shadow = stage.querySelector(".env-flap-shadow");
    if (shadow) play(shadow, [{ opacity: 1 }, { opacity: 0 }], { duration: 200 });
    if (mouthGlow) {
      play(
        mouthGlow,
        [
          { transform: "translate(-50%, -50%) scale(0.6)", opacity: 0 },
          { transform: "translate(-50%, -50%) scale(1.2)", opacity: quiet ? 0.15 : 0.6 },
          { transform: "translate(-50%, -50%) scale(1)", opacity: quiet ? 0.15 : 0.3 },
        ],
        { duration }
      );
    }
    return finished(animation).then(() => {
      flap.style.zIndex = "";
    });
  }

  function riseLetter(quiet) {
    if (!letter) return Promise.resolve();
    const animation = letter.animate(
      [
        { transform: "translate(-50%, 40px) rotate(-1.5deg)", opacity: 0 },
        { transform: "translate(-50%, -58px) rotate(-1.5deg)", opacity: 0, offset: 0.6 },
        { transform: "translate(-50%, -52px) rotate(0deg)", opacity: 1 },
      ],
      { duration: quiet ? 690 : 550, easing: "cubic-bezier(.2,.8,.3,1.1)", fill: "forwards" }
    );
    return finished(animation).then(() => {
      letter.style.transform = "";
      letter.style.opacity = "";
    });
  }

  async function settle(solved) {
    document.body.dataset.state = "opened";
    if (faceTitle) {
      faceTitle.textContent = solved ? "Muamma çözüldü!" : "Cevaba bakıldı";
    }
    if (letter) {
      letter.classList.toggle("reveal", !solved);
    }
    if (letterDate) letterDate.textContent = faceDate;
    if (letterTitle) letterTitle.textContent = solved ? "Mühür kırıldı" : "Mühür açıldı";
    if (flap) flap.style.zIndex = "";
    if (letter) {
      letter.style.transform = "";
      letter.style.opacity = "";
    }
  }

  function pieceVector(piece) {
    const dx = parseFloat(getComputedStyle(piece).getPropertyValue("--dx")) || 0;
    const dy = parseFloat(getComputedStyle(piece).getPropertyValue("--dy")) || 0;
    const d = parseFloat(getComputedStyle(stage).getPropertyValue("--seal-d")) || 64;
    return { dx, dy, d };
  }

  // T+330..1000 (solve) or straight after the crossfade (reveal): the seal
  // separates into its six pieces and falls, passing behind the card.
  function burstAndFall(quiet) {
    cracked.hidden = true;
    pieces.forEach((piece) => {
      piece.hidden = false;
    });

    const running = pieces.map((piece) => {
      const { dx, dy, d } = pieceVector(piece);
      const assembled = 0.92;
      const burst = quiet ? 1.3 : 1.8 + Math.random() * 0.8;
      const ax = dx * assembled * d;
      const ay = dy * assembled * d;
      const bx = dx * burst * d;
      const by = dy * burst * d;
      const fallBy = quiet ? 170 : 220;
      const rotate = quiet ? (-14 + Math.random() * 28) : -40 + Math.random() * 80;
      const delay = quiet ? 0 : Math.random() * 60;
      const duration = quiet ? 400 : 670;
      const animation = piece.animate(
        [
          { transform: `translate(calc(-50% + ${ax}px), calc(-50% + ${ay}px)) rotate(0deg)`, opacity: 1 },
          {
            transform: `translate(calc(-50% + ${bx}px), calc(-50% + ${by}px)) rotate(${rotate * 0.6}deg)`,
            opacity: 1,
            offset: 0.65,
          },
          {
            transform: `translate(calc(-50% + ${bx}px), calc(-50% + ${by + fallBy}px)) rotate(${rotate}deg)`,
            opacity: 0,
          },
        ],
        { duration, delay, easing: EASE_FALL, fill: "forwards" }
      );
      return finished(animation);
    });

    if (sealGlow && quiet) play(sealGlow, [{ opacity: 0.5 }, { opacity: 0 }], { duration: 200 });

    return Promise.all(running);
  }

  // T+0..330: the tension and the crack. A quiet reveal skips the tension
  // (no translateY, no glow) and crossfades slowly instead.
  async function crack(dramatic) {
    const shadow = mount?.querySelector(".gs-shadow");

    if (!dramatic) {
      whole.hidden = true;
      play(shadow, [{ opacity: 0.6 }, { opacity: 0 }], { duration: 400, fill: "forwards" });
      await play(cracked, [{ opacity: 0 }, { opacity: 1 }], { duration: 200 });
      return;
    }

    await Promise.all([
      play(stage, [{ transform: "translateY(0)" }, { transform: "translateY(-4px)" }], { duration: 200 }),
      play(sealGlow, [{ opacity: 0 }, { opacity: 0.5 }], { duration: 200 }),
    ]);

    whole.hidden = true;
    play(shadow, [{ opacity: 0.6 }, { opacity: 0 }], { duration: 250, fill: "forwards" });
    await Promise.all([
      play(cracked, [{ opacity: 0 }, { opacity: 1 }], { duration: 60 }),
      play(
        stage,
        [
          { transform: "translateY(-4px) rotate(0deg)" },
          { transform: "translateY(-4px) rotate(-1.6deg)", offset: 0.5 },
          { transform: "translateY(0) rotate(0deg)" },
        ],
        { duration: 140 }
      ),
    ]);
    if (navigator.vibrate) navigator.vibrate(25);
    await wait(30);
  }

  // T+330 (solve) / right after the crossfade (reveal): the flash that
  // covers swapping the cracked seal for its six pieces, which then burst
  // and fall while the flap opens and the letter rises underneath them.
  function flashAndScatter(quiet) {
    cracked.hidden = true;
    pieces.forEach((piece) => {
      piece.hidden = false;
    });

    const flecksRunning = quiet ? [] : spawnFlecks((navigator.hardwareConcurrency ?? 8) <= 4 ? 6 : 8);
    const flashRunning = quiet
      ? Promise.resolve()
      : finished(
          flash.animate(
            [
              { opacity: 0, transform: "translate(-50%, -50%) scale(0.6)" },
              { opacity: 0.9, transform: "translate(-50%, -50%) scale(1.1)", offset: 0.3 },
              { opacity: 0.3, transform: "translate(-50%, -50%) scale(1.4)" },
            ],
            { duration: 300, fill: "forwards" }
          )
        );

    const burstPromise = burstAndFall(quiet);
    const flapPromise = wait(quiet ? 0 : 120).then(() => openFlap(quiet));
    const letterPromise = wait(quiet ? 260 : 520).then(() => riseLetter(quiet));

    return Promise.all([flashRunning, burstPromise, flapPromise, letterPromise]).finally(() => {
      flecksRunning.forEach(({ dot }) => dot.remove());
    });
  }

  async function run(solved, quiet) {
    try {
      if (!motionOk() || document.hidden) {
        await settle(solved);
        return;
      }
      await ready;
      await crack(!quiet);
      await flashAndScatter(quiet);
    } finally {
      await settle(solved);
    }
  }

  return {
    rise,
    shake,
    solve: () => run(true, false),
    reveal: () => run(false, true),
  };
}

// game.js is the only importer (loaded unconditionally on every page with
// a band), so this module runs exactly once per page.
const envelope = createEnvelope();
envelope?.rise();

export default envelope;
