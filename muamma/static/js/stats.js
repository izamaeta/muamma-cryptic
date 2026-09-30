import { countUp } from "./motion.js";

for (const element of document.querySelectorAll(".stats .count")) {
  const match = element.textContent.trim().match(/^(\D*)(\d+)$/);
  if (match) countUp(element, Number(match[2]), match[1]);
}
