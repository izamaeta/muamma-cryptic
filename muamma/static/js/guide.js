// Upgrades the guide page: the sections become tabs and the anatomy clue
// highlights its own explanation. Without this file the page still reads as
// plain sections, so nothing here may be required to understand it.

function buildTabs(holder) {
  const panels = [...holder.querySelectorAll(".guide-panel")];
  if (panels.length < 2) return;

  const tablist = document.createElement("div");
  tablist.className = "tablist";
  tablist.role = "tablist";

  const tabs = panels.map((panel, index) => {
    const tab = document.createElement("button");
    tab.type = "button";
    tab.className = "tab";
    tab.role = "tab";
    tab.id = `tab-${panel.id}`;
    tab.textContent = panel.dataset.label;
    tab.setAttribute("aria-controls", panel.id);
    tablist.append(tab);

    panel.role = "tabpanel";
    panel.setAttribute("aria-labelledby", tab.id);
    panel.querySelector(".guide-panel-title").hidden = true;
    if (index > 0) panel.hidden = true;
    return tab;
  });

  function select(index, moveFocus) {
    tabs.forEach((tab, i) => {
      const current = i === index;
      tab.setAttribute("aria-selected", String(current));
      tab.tabIndex = current ? 0 : -1;
      panels[i].hidden = !current;
    });
    if (moveFocus) tabs[index].focus();
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => select(index, false));
    tab.addEventListener("keydown", (event) => {
      const last = tabs.length - 1;
      const moves = {
        ArrowRight: index === last ? 0 : index + 1,
        ArrowLeft: index === 0 ? last : index - 1,
        Home: 0,
        End: last,
      };
      if (event.key in moves) {
        event.preventDefault();
        select(moves[event.key], true);
      }
    });
  });

  holder.prepend(tablist);
  select(0, false);
}

function wireAnatomy(box) {
  const parts = [...box.querySelectorAll(".anatomy-clue .part")];
  const rows = [...box.querySelectorAll(".anatomy-row")];

  const highlight = (key) => {
    rows.forEach((row) => row.classList.toggle("lit", row.dataset.part === key));
    parts.forEach((part) => part.classList.toggle("lit", part.dataset.part === key));
  };

  parts.forEach((part) => {
    const key = part.dataset.part;
    part.addEventListener("mouseenter", () => highlight(key));
    part.addEventListener("focus", () => highlight(key));
    part.addEventListener("click", () => highlight(key));
  });

  box.addEventListener("mouseleave", () => highlight(null));
}

const tabHolder = document.querySelector("[data-tabs]");
if (tabHolder) buildTabs(tabHolder);

const anatomy = document.querySelector("[data-anatomy]");
if (anatomy) wireAnatomy(anatomy);
