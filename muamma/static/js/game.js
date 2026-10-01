import {
  dropLetters,
  fadeWash,
  flash,
  flipTile,
  flipTiles,
  minutesSeconds,
  motionOk,
  riseIn,
  spinNumber,
  toast,
  wait,
} from "./motion.js";
import { resultWindow, revealAsker } from "./result.js";

const section = document.querySelector(".puzzle");

if (section) {
  const id = section.dataset.puzzleId;
  const form = section.querySelector(".guess-form");
  const input = form.querySelector("input");
  const helpers = section.querySelector(".helpers");
  const feedback = section.querySelector(".feedback");
  const solution = section.querySelector(".solution");
  const hints = section.querySelector(".hints");
  const wrongList = section.querySelector(".wrong-guesses");
  const pattern = section.querySelector(".pattern");
  const clueText = section.querySelector(".clue-text");
  const tileBox = section.querySelector(".tiles");
  const tiles = [...section.querySelectorAll(".tile")];
  const streak = document.querySelector(".streak-count");
  const shareButtons = [...section.querySelectorAll(".share-button")];
  const countdowns = [...section.querySelectorAll(".countdown")];
  const openResult = section.querySelector(".result-open");
  const timer = section.querySelector(".chip.timer");
  const wash = document.querySelector(".band-wash");
  const sealCap = document.querySelector(".seal-cap");
  const sealLabel = document.querySelector(".seal-label");
  const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
  const result = resultWindow(section.querySelector(".result"));
  const askReveal = revealAsker(section.querySelector(".confirm"));

  const messages = {
    wrong_length: "Harf sayısı tutmuyor.",
    finished: "Bu bulmacayı zaten bitirdin.",
    no_more_hints: "Başka ipucu yok.",
    no_more_letters: "Daha fazla harf açılamaz.",
    rate_limited: "Çok hızlı gidiyorsun, biraz bekle.",
  };

  let busy = false;

  async function run(task) {
    if (busy) return;
    busy = true;
    section.dataset.busy = "1";
    try {
      await task();
    } finally {
      busy = false;
      section.dataset.busy = "";
    }
  }

  const limit = Number(input.dataset.letters) || 64;
  let undrop = null;

  const lettersOf = (text) =>
    [...text.toLocaleUpperCase("tr")].filter((ch) => /\p{L}/u.test(ch));

  const slotOf = (tile) => tile.querySelector(".letter");

  const onlyLetters = (text) =>
    [...text].filter((ch) => /\p{L}/u.test(ch)).slice(0, limit).join("");

  function renderTiles() {
    const typed = lettersOf(input.value);
    tiles.forEach((tile, i) => {
      const slot = slotOf(tile);
      const before = slot.textContent;
      const next = typed[i] ?? tile.dataset.given;
      slot.textContent = next;
      tile.classList.toggle("filled", Boolean(next));
      tile.classList.toggle("given", !typed[i] && Boolean(tile.dataset.given));
      if (next && next !== before) {
        flash(tile, "pop", 160);
      }
    });
  }

  function cancelDrop() {
    if (!undrop) return;
    undrop();
    undrop = null;
  }

  async function clearTyped() {
    const falling = tiles
      .filter((tile) => !tile.dataset.given && slotOf(tile).textContent)
      .map(slotOf);

    undrop = await dropLetters(falling);
    input.value = "";
    renderTiles();
    cancelDrop();
  }

  function setGiven(letters) {
    tiles.forEach((tile, i) => {
      tile.dataset.given = letters[i] && letters[i] !== "_" ? letters[i] : "";
    });
    renderTiles();
  }

  function highlight(parts, fresh) {
    if (!parts) return;
    const mark = document.createElement("mark");
    mark.className = "definition";
    if (fresh && motionOk()) mark.classList.add("ink");
    mark.textContent = parts[1];
    clueText.replaceChildren(parts[0], mark, parts[2]);
  }

  function startCountdown(seconds) {
    if (!seconds) return;
    const end = Date.now() + seconds * 1000;
    const pad = (n) => String(n).padStart(2, "0");
    countdowns.forEach((element) => {
      element.hidden = false;
    });

    const tick = () => {
      const left = Math.max(0, Math.round((end - Date.now()) / 1000));
      countdowns.forEach((element) => {
        const label = element.querySelector(".countdown-time");
        if (left === 0) {
          element.textContent = "Yeni muamma hazır, sayfayı yenile.";
        } else if (label) {
          label.textContent = `${pad(Math.floor(left / 3600))}:${pad(
            Math.floor((left % 3600) / 60)
          )}:${pad(left % 60)}`;
        }
      });
      if (left > 0) setTimeout(tick, 1000);
    };
    tick();
  }

  let elapsed = Number(timer?.dataset.elapsed) || 0;
  let ticking = null;

  function startTimer() {
    if (!timer || timer.dataset.running !== "1") return;
    ticking = setInterval(() => {
      elapsed += 1;
      timer.textContent = minutesSeconds(elapsed);
    }, 1000);
  }

  function stopTimer(seconds) {
    if (ticking) {
      clearInterval(ticking);
      ticking = null;
    }
    if (!timer) return;
    timer.dataset.running = "0";
    if (typeof seconds === "number") timer.textContent = minutesSeconds(seconds);
  }

  function enableShare(text) {
    if (!text) return;
    shareButtons.forEach((button) => {
      button.dataset.share = text;
      button.hidden = false;
    });
  }

  function addWrongGuess(text) {
    if (!text) return;
    const item = document.createElement("li");
    item.textContent = text;
    wrongList.append(item);
    riseIn(item);
  }

  async function post(action, body = {}) {
    const response = await fetch(`/api/puzzles/${id}/${action}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify(body),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      feedback.textContent = messages[data.error] ?? "Bir sorun oluştu, tekrar dene.";
      return null;
    }
    return data;
  }

  function breakSeal(solved) {
    if (sealLabel) {
      sealLabel.textContent = solved ? "Mühür kırıldı" : "Mühür açıldı";
    }
    if (solved && sealCap && !sealCap.querySelector(".seal-note")) {
      const note = document.createElement("p");
      note.className = "seal-note";
      note.textContent = "Muamma çözüldü!";
      sealCap.append(note);
    }
    const fading = fadeWash(wash);
    document.body.dataset.state = "opened";
    return fading;
  }

  async function finish(data, message, solved) {
    form.hidden = true;
    helpers.hidden = true;
    input.value = "";
    setGiven(lettersOf(data.answer));
    highlight(data.highlight);
    feedback.textContent = message;

    if (solved) {
      await flipTiles(tiles, (tile) => {
        tile.classList.remove("given");
        tile.classList.add("solved");
      });
    }

    stopTimer(data.duration);
    const sealing = breakSeal(solved);
    await wait(motionOk() ? 200 : 0);

    solution.querySelector(".answer").textContent = data.answer;
    solution.querySelector(".explanation").textContent = data.explanation;
    solution.hidden = false;
    if (openResult) openResult.hidden = false;
    enableShare(data.share);
    startCountdown(data.next_in);

    await Promise.all([riseIn(solution), spinNumber(streak, data.streak), sealing]);

    if (result) {
      result.fill(data, solved);
      await result.open(solved);
    }
  }

  const TILE_MIN = 20;
  const TILE_GAP = 4;
  const TIGHT_GAP = 2;

  function fitTiles() {
    // measure without the scrolling state, or the row would stay wide
    tileBox.classList.remove("scrollable");

    const longest = Math.max(
      ...[...tileBox.querySelectorAll(".tile-group")].map((group) => group.children.length),
      1
    );
    const max = parseFloat(getComputedStyle(tileBox).getPropertyValue("--tile-max")) || 54;
    const room = tileBox.clientWidth - 12;
    const fits = (room - (longest - 1) * TILE_GAP) / longest;
    const size = Math.max(TILE_MIN, Math.min(max, fits));

    // at the floor a few pixels can be the difference between a centred row
    // and a scrolling one, so close the gaps before giving up on fitting
    const gap = size > TILE_MIN ? TILE_GAP : TIGHT_GAP;

    tileBox.style.setProperty("--tile-gap", `${gap}px`);
    tileBox.style.setProperty("--tile-size", `${size.toFixed(1)}px`);
    tileBox.style.setProperty("--tile-font", `${(size * 0.48).toFixed(1)}px`);

    // left-align only while the row really overflows; otherwise it stays centred
    if (tileBox.scrollWidth > tileBox.clientWidth + 1) {
      tileBox.classList.add("scrollable");
    }
  }

  // the card can change width without the window doing so, and a late font
  // can shift the layout after the first measurement
  new ResizeObserver(fitTiles).observe(tileBox);
  if (document.fonts) document.fonts.ready.then(fitTiles);
  fitTiles();

  input.addEventListener("input", () => {
    cancelDrop();
    const cleaned = onlyLetters(input.value);
    if (cleaned !== input.value) input.value = cleaned;
    renderTiles();
  });
  tileBox.addEventListener("click", () => input.focus());

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    run(async () => {
      feedback.textContent = "";
      const guess = input.value;
      const data = await post("guess", { guess });
      if (!data) return;

      if (!data.correct) {
        feedback.textContent = "Olmadı, tekrar dene.";
        flash(tileBox, "shake", 340);
        flash(tileBox, "wrong", 540);
        addWrongGuess(lettersOf(guess).join(""));
        await wait(motionOk() ? 260 : 0);
        await clearTyped();
        input.focus();
        return;
      }
      await finish(data, "Doğru!", true);
    });
  });

  helpers.addEventListener("click", (event) => {
    const action = event.target.dataset.action;
    if (!action) return;

    run(async () => {
      feedback.textContent = "";

      if (action === "hint") {
        const data = await post("hint");
        if (!data) return;
        const item = document.createElement("li");
        item.textContent = data.text;
        hints.append(item);
        riseIn(item);
        highlight(data.highlight, true);
      } else if (action === "letter") {
        const data = await post("letter");
        if (!data) return;
        pattern.textContent = data.pattern;

        const letters = [...data.pattern.replaceAll(" ", "")];
        const opened = data.position;
        const tile = tiles[opened];
        tiles.forEach((other, i) => {
          if (i === opened) return;
          other.dataset.given = letters[i] && letters[i] !== "_" ? letters[i] : "";
        });
        renderTiles();
        if (tile) {
          await flipTile(tile, () => {
            tile.dataset.given = letters[opened];
            renderTiles();
          });
        }
      } else if (action === "reveal") {
        if (!(await askReveal())) return;
        const data = await post("reveal");
        if (data) await finish(data, "Cevap:", false);
      }
    });
  });

  shareButtons.forEach((button) => {
    button.addEventListener("click", async () => {
      const text = button.dataset.share;
      if (navigator.share) {
        await navigator.share({ text }).catch(() => {});
        return;
      }
      try {
        await navigator.clipboard.writeText(text);
        toast("Kopyalandı");
      } catch {
        feedback.textContent = "Kopyalanamadı, metni elle seçebilirsin.";
      }
    });
  });

  if (openResult && result) {
    openResult.addEventListener("click", () => result.open());
    openResult.hidden = !result.ready;
  }

  startTimer();
  startCountdown(Number(countdowns[0]?.dataset.seconds));
  riseIn(section);
}
