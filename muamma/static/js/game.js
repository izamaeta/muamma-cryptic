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
  const streak = document.querySelector(".streak-count");

  const messages = {
    wrong_length: "Harf sayısı tutmuyor.",
    finished: "Bu bulmacayı zaten bitirdin.",
    no_more_hints: "Başka ipucu yok.",
    no_more_letters: "Daha fazla harf açılamaz.",
  };

  async function post(action, body = {}) {
    const response = await fetch(`/api/puzzles/${id}/${action}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      feedback.textContent = messages[data.error] ?? "Bir sorun oluştu, tekrar dene.";
      return null;
    }
    return data;
  }

  function showSolution(data, message) {
    form.hidden = true;
    helpers.hidden = true;
    feedback.textContent = message;
    solution.querySelector(".answer").textContent = data.answer;
    solution.querySelector(".explanation").textContent = data.explanation;
    solution.hidden = false;
    streak.textContent = data.streak;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    feedback.textContent = "";

    const data = await post("guess", { guess: input.value });
    if (!data) return;

    if (!data.correct) {
      feedback.textContent = "Olmadı, tekrar dene.";
      input.select();
      return;
    }
    showSolution(data, "Doğru!");
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
    } else if (action === "letter") {
      const data = await post("letter");
      if (!data) return;
      pattern.textContent = data.pattern;
      pattern.hidden = false;
    } else if (action === "reveal") {
      const warning =
        section.dataset.streakRisk === "1"
          ? "Cevabı görürsen serin sıfırlanır. Emin misin?"
          : "Cevabı görmek istediğine emin misin?";
      if (!confirm(warning)) return;
      const data = await post("reveal");
      if (data) showSolution(data, "Cevap:");
    }
  });
}