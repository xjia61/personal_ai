import {validateHandoff, fillContactFields} from "./autofill.js";

let handoff = null;
const file = document.querySelector("#handoff");
const fill = document.querySelector("#fill");
const selection = document.querySelector("#selection");
const result = document.querySelector("#result");
let generation = 0;
function clear() {
  generation++;
  handoff = null;
  file.value = "";
  fill.disabled = true;
  selection.textContent = "No application selected.";
  result.textContent = "";
}
document.querySelector("#clear").addEventListener("click", clear);
file.addEventListener("change", async () => {
  handoff = null;
  fill.disabled = true;
  selection.textContent = "No application selected.";
  result.textContent = "";
  const current = ++generation;
  try {
    const selected = file.files[0];
    if (!selected || selected.size > 32 * 1024) throw new Error("Choose an application JSON file smaller than 32 KB.");
    const parsed = validateHandoff(JSON.parse(await selected.text()));
    if (current !== generation) return;
    handoff = parsed;
    selection.textContent = `Application #${handoff.application_id} · ${handoff.resume.name} (v${handoff.resume.version}) · ${new URL(handoff.application_url).hostname}`;
    fill.disabled = false;
  } catch (error) {
    if (current === generation) result.textContent = error.message;
  }
});
fill.addEventListener("click", async () => {
  if (!handoff) return;
  fill.disabled = true;
  try {
    const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
    if (!tab?.id) throw new Error("Open the selected application in Chrome first.");
    const [response] = await chrome.scripting.executeScript({
      target: {tabId: tab.id}, func: fillContactFields,
      args: [handoff.fields, handoff.application_url],
    });
    if (!response?.result) throw new Error("Unable to fill this page. Complete it manually.");
    result.textContent = `Filled: ${response.result.filled.join(", ") || "none"}\nSkipped: ${response.result.skipped.join(", ") || "none"}\nReview the form and upload your selected resume manually. Embedded forms may require opening the direct ATS page.`;
  } catch (error) {
    result.textContent = error.message;
  } finally {
    fill.disabled = !handoff;
  }
});
