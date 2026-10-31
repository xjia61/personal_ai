export function validateHandoff(data) {
  if (!data || data.format !== "career-agent-autofill-v1" ||
      !Number.isInteger(data.application_id) || data.application_id < 1 ||
      !data.fields || typeof data.fields !== "object" ||
      !data.resume || !Number.isInteger(data.resume.id) ||
      typeof data.resume.name !== "string" || !Number.isInteger(data.resume.version)) {
    throw new Error("Import a Career Agent application export.");
  }
  const url = new URL(data.application_url);
  if (url.protocol !== "https:" || !["boards.greenhouse.io", "job-boards.greenhouse.io", "jobs.lever.co"].includes(url.hostname)
      || url.username || url.password || url.port) {
    throw new Error("Use an official Greenhouse or Lever application URL.");
  }
  const fields = {};
  for (const key of ["first_name", "last_name", "email", "phone", "linkedin_url", "github_url", "portfolio_url"]) {
    const value = data.fields[key] ?? "";
    if (typeof value !== "string" || value.length > 1000) throw new Error("Invalid contact field.");
    fields[key] = value;
  }
  return {...data, fields};
}

// Self-contained: Chrome serializes this function into the selected tab.
export function fillContactFields(fields, expectedUrl) {
  const actual = new URL(location.href);
  const expected = new URL(expectedUrl);
  const hosts = ["boards.greenhouse.io", "job-boards.greenhouse.io", "jobs.lever.co"];
  const path = url => url.pathname.replace(/\/apply\/?$/, "").replace(/\/$/, "");
  if (actual.protocol !== "https:" || !hosts.includes(actual.hostname) ||
      actual.origin !== expected.origin || path(actual) !== path(expected) ||
      actual.searchParams.get("gh_jid") !== expected.searchParams.get("gh_jid")) {
    throw new Error("Open the exact application page from your exported application first.");
  }
  const specs = [
    ["full_name", /^(full\s*name|name)\s*\*?$/i, ["name", "full_name", "fullName"], "name"],
    ["first_name", /^(first\s*name)\s*\*?$/i, ["first_name", "firstName", "firstname"], "given-name"],
    ["last_name", /^(last\s*name|surname)\s*\*?$/i, ["last_name", "lastName", "lastname"], "family-name"],
    ["email", /^(e-?mail(?: address)?)\s*\*?$/i, ["email"], "email"],
    ["phone", /^(phone|mobile)( number)?\s*\*?$/i, ["phone", "telephone", "mobile"], "tel"],
    ["linkedin_url", /^linkedin( (url|profile))?\s*\*?$/i, ["linkedin", "linkedin_url", "urls[LinkedIn]"], ""],
    ["github_url", /^github( (url|profile))?\s*\*?$/i, ["github", "github_url", "urls[GitHub]"], ""],
    ["portfolio_url", /^(portfolio|website|personal site)( url)?\s*\*?$/i, ["portfolio", "website", "portfolio_url", "urls[Portfolio]"], ""],
  ];
  const filled = [], skipped = [];
  const inputs = [...document.querySelectorAll("input")];
  for (const [key, labelPattern, names, autocomplete] of specs) {
    const value = key === "full_name"
      ? (fields.first_name && fields.last_name ? `${fields.first_name} ${fields.last_name}` : "")
      : fields[key];
    const matches = inputs.filter(input => {
      if (!["text", "email", "tel", "url"].includes(input.type) || input.disabled || input.readOnly ||
          input.getClientRects().length === 0) return false;
      const labels = [...(input.labels || [])].map(label => label.textContent.trim());
      labels.push(input.getAttribute("aria-label") || "");
      // Never use a technical name to override a visibly sensitive question.
      if (labels.some(label => /password|signature|salary|sponsor|authorization|gender|race|ethnic|veteran|disability|captcha|verification|legal/i.test(label))) return false;
      return labels.some(label => labelPattern.test(label)) ||
        names.some(name => name.toLowerCase() === input.name.toLowerCase() || name.toLowerCase() === input.id.toLowerCase()) ||
        Boolean(autocomplete && input.autocomplete === autocomplete);
    });
    if (!value || matches.length !== 1 || matches[0].value.trim()) {
      skipped.push(key);
      continue;
    }
    const input = matches[0];
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(input, value);
    input.dispatchEvent(new Event("input", {bubbles: true}));
    input.dispatchEvent(new Event("change", {bubbles: true}));
    (input.value === value ? filled : skipped).push(key);
  }
  return {filled, skipped, manual_review_required: true};
}
