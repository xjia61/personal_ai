import test from "node:test";
import assert from "node:assert/strict";
import {validateHandoff, fillContactFields} from "../autofill.js";

const sample = () => ({format: "career-agent-autofill-v1", application_id: 1,
  application_url: "https://jobs.lever.co/example/job-id", fields: {email: "test@example.invalid"},
  resume: {id: 2, name: "Approved resume", version: 3}});

test("handoff contains only allowed contact fields", () => {
  const data = sample();
  data.fields.requires_sponsorship = true;
  data.fields.password = "never-transfer";
  const validated = validateHandoff(data);
  assert.equal(validated.fields.email, data.fields.email);
  assert.equal(validated.fields.password, undefined);
  assert.equal(validated.fields.requires_sponsorship, undefined);
});

test("rejects unsupported URLs, credential URLs, and lookalike hosts", () => {
  for (const url of ["http://jobs.lever.co/example/job-id", "https://jobs.lever.co.evil.invalid/job",
    "https://example.invalid/job", "https://user:secret@jobs.lever.co/example/job-id", "javascript:alert(1)"]) {
    assert.throws(() => validateHandoff({...sample(), application_url: url}));
  }
});

test("rejects malformed or oversized fields", () => {
  assert.throws(() => validateHandoff({}));
  assert.throws(() => validateHandoff({...sample(), application_id: -1}));
  assert.throws(() => validateHandoff({...sample(), fields: {email: false}}));
  assert.throws(() => validateHandoff({...sample(), fields: {email: "x".repeat(1001)}}));
});

test("refuses a different application before reading the DOM", () => {
  globalThis.location = {href: "https://jobs.lever.co/example/different-job"};
  try {
    assert.throws(() => fillContactFields({}, sample().application_url), /exact application/);
  } finally {
    delete globalThis.location;
  }
});

test("extension requests only temporary user-invoked access", async () => {
  const {readFile} = await import("node:fs/promises");
  const manifest = JSON.parse(await readFile(new URL("../manifest.json", import.meta.url), "utf8"));
  assert.deepEqual(manifest.permissions, ["activeTab", "scripting"]);
  assert.equal(manifest.host_permissions, undefined);
  assert.equal(manifest.content_scripts, undefined);
});
