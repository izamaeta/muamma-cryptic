const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");

export const motionOk = () => !reduced.matches;

export const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export function play(element, keyframes, options) {
  if (!motionOk() || !element) return Promise.resolve();
  const animation = element.animate(keyframes, { easing: "ease-out", ...options });
  return animation.finished.catch(() => {});
}

export function minutesSeconds(total) {
  const seconds = Math.max(0, Math.round(Number(total) || 0));
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

const FLIP = [
  { transform: "rotateY(0deg)" },
  { transform: "rotateY(90deg)" },
  { transform: "rotateY(0deg)" },
];

async function flip(tile, apply) {
  const animation = tile.animate(FLIP, { duration: 320, easing: "ease-in-out" });
  await wait(160);
  apply(tile);
  await animation.finished.catch(() => {});
}

export async function flipTile(tile, apply) {
  if (!motionOk()) {
    apply(tile);
    return;
  }
  await flip(tile, apply);
}

export async function flipTiles(tiles, apply) {
  if (!motionOk()) {
    tiles.forEach(apply);
    return;
  }
  const step = Math.min(90, 700 / Math.max(tiles.length, 1));
  const running = [];
  for (const tile of tiles) {
    running.push(flip(tile, apply));
    await wait(step);
  }
  await Promise.all(running);
}

export async function dropLetters(slots) {
  if (!motionOk() || !slots.length) return () => {};

  const running = slots.map((slot, i) =>
    slot.animate(
      [
        { transform: "translateY(0)", opacity: 1 },
        { transform: "translateY(26px)", opacity: 0 },
      ],
      { duration: 260, delay: i * 50, easing: "ease-in", fill: "forwards" }
    )
  );

  await Promise.all(running.map((animation) => animation.finished.catch(() => {})));
  return () => running.forEach((animation) => animation.cancel());
}

export function riseIn(element) {
  return play(
    element,
    [
      { transform: "translateY(16px)", opacity: 0 },
      { transform: "translateY(0)", opacity: 1 },
    ],
    { duration: 400 }
  );
}

export async function spinNumber(element, value) {
  if (!element) return;
  if (!motionOk()) {
    element.textContent = value;
    return;
  }
  const animation = element.animate(
    [
      { transform: "rotateX(0deg) scale(1)" },
      { transform: "rotateX(90deg) scale(1.2)" },
      { transform: "rotateX(0deg) scale(1)" },
    ],
    { duration: 500, easing: "ease-in-out" }
  );
  await wait(250);
  element.textContent = value;
  await animation.finished.catch(() => {});
}

export async function fadeWash(wash) {
  if (!wash || !motionOk()) return;
  wash.classList.add("active");
  await play(wash, [{ opacity: 1 }, { opacity: 0 }], { duration: 700 });
  wash.classList.remove("active");
}

export function flash(element, className, ms = 520) {
  if (!motionOk() || !element) return;
  element.classList.remove(className);
  void element.offsetWidth;
  element.classList.add(className);
  setTimeout(() => element.classList.remove(className), ms);
}

export async function toast(message) {
  const element = document.createElement("p");
  element.className = "toast";
  element.setAttribute("role", "status");
  element.textContent = message;
  document.body.append(element);

  await play(
    element,
    [
      { transform: "translateY(12px)", opacity: 0 },
      { transform: "translateY(0)", opacity: 1 },
    ],
    { duration: 200 }
  );
  await wait(1600);
  await play(element, [{ opacity: 1 }, { opacity: 0 }], { duration: 250 });
  element.remove();
}

export function countUp(element, target, prefix = "") {
  if (!motionOk()) return;

  const duration = 700;
  const start = performance.now();

  const step = (now) => {
    const ratio = Math.min(1, (now - start) / duration);
    element.textContent = prefix + Math.round(target * ratio);
    if (ratio < 1) requestAnimationFrame(step);
  };
  element.textContent = `${prefix}0`;
  requestAnimationFrame(step);
}
