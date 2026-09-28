const section = document.querySelector(".puzzle");

if (section) {
  const form = section.querySelector(".guess-form");
  const input = form.querySelector("input");
  const feedback = section.querySelector(".feedback");
  const solution = section.querySelector(".solution");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    feedback.textContent = "";

    const response = await fetch(`/api/puzzles/${section.dataset.puzzleId}/guess`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ guess: input.value }),
    });
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      feedback.textContent =
        data.error === "wrong_length" ? "Harf sayısı tutmuyor." : "Bir sorun oluştu, tekrar dene.";
      return;
    }

    if (!data.correct) {
      feedback.textContent = "Olmadı, tekrar dene.";
      input.select();
      return;
    }

    form.hidden = true;
    feedback.textContent = "Doğru!";
    solution.querySelector(".answer").textContent = data.answer;
    solution.querySelector(".explanation").textContent = data.explanation;
    solution.hidden = false;
  });
}