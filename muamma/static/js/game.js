const section = document.querySelector(".puzzle");

if (section) {
  const id = section.dataset.puzzleId;
  const form = section.querySelector(".guess-form");
  const input = form.querySelector("input");
  const helpers = section.querySelector(".helpers");
  const feedback = section.querySelector(".feedback");
  const solution = section.querySelector(".solution");
  const hints = section.querySelector(".hints");
  const pattern = section.querySelector(".pattern");
  const clueText = section.querySelector(".clue-text");
  const tiles = [...section.querySelectorAll(".tile")];
  const streak = document.querySelector(".streak-count");
  const shareButton = section.querySelector(".share-button");
  const countdown = section.querySelector(".countdown");
  const sealCap = document.querySelector(".seal-cap");
  const sealLabel = document.querySelector(".seal-label");
  const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

  const messages = {
    wrong_length: "Harf sayısı tutmuyor.",
    finished: "Bu bulmacayı zaten bitirdin.",
    no_more_hints: "Başka ipucu yok.",
    no_more_letters: "Daha fazla harf açılamaz.",
    rate_limited: "Çok hızlı gidiyorsun, biraz bekle.",
  };

  const lettersOf = (text) =>
    [...text.toLocaleUpperCase("tr")].filter((ch) => /\p{L}/u.test(ch));

  function renderTiles() {
    const typed = lettersOf(input.value);
    tiles.forEach((tile, i) => {
      const before = tile.textContent;
      tile.textContent = typed[i] ?? tile.dataset.given;
      tile.classList.toggle("given", !typed[i] && Boolean(tile.dataset.given));
      if (tile.textContent && tile.textContent !== before) {
        tile.classList.remove("pop");
        tile.offsetWidth;
        tile.classList.add("pop");
      }
    });
  }

  function setGiven(letters) {
    tiles.forEach((tile, i) => {
      tile.dataset.given = letters[i] && letters[i] !== "_" ? letters[i] : "";
    });
    renderTiles();
  }

  function highlight(parts) {
    if (!parts) return;
    const mark = document.createElement("mark");
    mark.className = "definition";
    mark.textContent = parts[1];
    clueText.replaceChildren(parts[0], mark, parts[2]);
  }

  function startCountdown(seconds) {
    if (!seconds) return;
    const end = Date.now() + seconds * 1000;
    const label = countdown.querySelector(".countdown-time");
    countdown.hidden = false;

    const tick = () => {
      const left = Math.max(0, Math.round((end - Date.now()) / 1000));
      if (left === 0) {
        countdown.textContent = "Yeni muamma hazır, sayfayı yenile.";
        return;
      }
      const pad = (n) => String(n).padStart(2, "0");
      label.textContent = `${pad(Math.floor(left / 3600))}:${pad(Math.floor((left % 3600) / 60))}:${pad(left % 60)}`;
      setTimeout(tick, 1000);
    };
    tick();
  }

  function enableShare(text) {
    if (!text) return;
    shareButton.dataset.share = text;
    shareButton.hidden = false;
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
    document.body.dataset.state = "opened";
    if (sealLabel) {
      sealLabel.textContent = solved ? "Mühür kırıldı" : "Mühür açıldı";
    }
    if (solved && sealCap && !sealCap.querySelector(".seal-note")) {
      const note = document.createElement("p");
      note.className = "seal-note";
      note.textContent = "Muamma çözüldü!";
      sealCap.append(note);
    }
  }

  function showSolution(data, message, solved) {
    form.hidden = true;
    helpers.hidden = true;
    input.value = "";
    setGiven(lettersOf(data.answer));
    highlight(data.highlight);
    breakSeal(solved);
    if (solved) {
      tiles.forEach((tile) => {
        tile.classList.remove("given");
        tile.classList.add("solved");
      });
    }
    feedback.textContent = message;
    solution.querySelector(".answer").textContent = data.answer;
    solution.querySelector(".explanation").textContent = data.explanation;
    solution.hidden = false;
    streak.textContent = data.streak;
    enableShare(data.share);
    startCountdown(data.next_in);
  }

  input.addEventListener("input", renderTiles);
  section.querySelector(".tiles").addEventListener("click", () => input.focus());

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    feedback.textContent = "";

    const data = await post("guess", { guess: input.value });
    if (!data) return;

    if (!data.correct) {
      feedback.textContent = "Olmadı, tekrar dene.";
      const group = section.querySelector(".tiles");
      group.classList.remove("shake");
      group.offsetWidth;
      group.classList.add("shake");
      input.select();
      return;
    }
    showSolution(data, "Doğru!", true);
  });

  helpers.addEventListener("click", async (event) => {
    const action = event.target.dataset.action;
    if (!action) return;
    feedback.textContent = "";

    if (action === "hint") {
      const data = await post("hint");
      if (!data) return;
      const item = document.createElement("li");
      item.textContent = data.text;
      hints.append(item);
      highlight(data.highlight);
    } else if (action === "letter") {
      const data = await post("letter");
      if (!data) return;
      pattern.textContent = data.pattern;
      setGiven([...data.pattern.replaceAll(" ", "")]);
    } else if (action === "reveal") {
      const warning =
        section.dataset.streakRisk === "1"
          ? "Mührü açarsan serin sıfırlanır. Emin misin?"
          : "Mührü açmak istediğine emin misin?";
      if (!confirm(warning)) return;
      const data = await post("reveal");
      if (data) showSolution(data, "Cevap:", false);
    }
  });

  shareButton.addEventListener("click", async () => {
    const text = shareButton.dataset.share;
    if (navigator.share) {
      await navigator.share({ text }).catch(() => {});
      return;
    }
    await navigator.clipboard.writeText(text);
    feedback.textContent = "Sonuç panoya kopyalandı.";
  });

  startCountdown(Number(countdown.dataset.seconds));
}