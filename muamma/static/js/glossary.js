import { closeOnBackdrop, slideIn } from "./result.js";

const dialog = document.querySelector(".glossary");
const buttons = [...document.querySelectorAll(".glossary-open")];

if (dialog && buttons.length) {
  const search = dialog.querySelector(".glossary-search");
  const empty = dialog.querySelector(".glossary-empty");
  const words = [...dialog.querySelectorAll(".chip[data-word]")];
  const types = [...dialog.querySelectorAll(".glossary-type")];
  const groups = [...dialog.querySelectorAll(".glossary-group")];

  const fold = (text) => text.toLocaleLowerCase("tr").trim();

  function filter() {
    const query = fold(search.value);

    words.forEach((word) => {
      word.hidden = Boolean(query) && !fold(word.dataset.word).includes(query);
    });
    types.forEach((type) => {
      type.hidden = [...type.querySelectorAll(".chip[data-word]")].every((w) => w.hidden);
    });
    groups.forEach((group) => {
      group.hidden = [...group.querySelectorAll(".glossary-type")].every((t) => t.hidden);
    });
    empty.hidden = groups.some((group) => !group.hidden);
  }

  closeOnBackdrop(dialog);
  search.addEventListener("input", filter);

  // a text field swallows the first Escape to undo the typing; close instead,
  // so Escape behaves the same here as in every other window
  search.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      dialog.close();
    }
  });

  buttons.forEach((button) =>
    button.addEventListener("click", () => {
      if (dialog.open) return;
      search.value = "";
      filter();
      dialog.showModal();
      slideIn(dialog);
    })
  );
}
