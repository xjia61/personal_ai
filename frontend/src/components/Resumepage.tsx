import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import {
  getResumeVersions,
  createResume,
  updateResume,
  approveResume,
  createResumeRevision,
} from "../Api";

import type {
  ResumeInput,
  ResumeVersion,
} from "../Api";


interface ResumeForm {
  name: string;
  content: string;
  roles: string;
  skills: string;
}

const emptyForm: ResumeForm = {
  name: "",
  content: "",
  roles: "",
  skills: "",
};

const splitTags = (value: string) =>
  value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);


export default function ResumePage() {
  const [resumes, setResumes] = useState<ResumeVersion[]>([]);
  const [form, setForm] = useState<ResumeForm>({ ...emptyForm });

  const [editingId, setEditingId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function refresh() {
    setResumes(await getResumeVersions());
  }

  useEffect(() => {
    getResumeVersions()
      .then(setResumes)
      .catch((err) => setError(String(err)));
  }, []);

  function resetForm() {
    setForm({ ...emptyForm });
    setEditingId(null);
  }

  function edit(resume: ResumeVersion) {
    setEditingId(resume.id);
    setForm({
      name: resume.name,
      content: resume.content,
      roles: resume.role_tags.join(", "),
      skills: resume.skill_tags.join(", "),
    });

    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const data: ResumeInput = {
      name: form.name,
      content: form.content,
      role_tags: splitTags(form.roles),
      skill_tags: splitTags(form.skills),
    };

    setBusy(true);
    setError("");

    try {
      if (editingId === null) {
        await createResume(data);
      } else {
        await updateResume(editingId, data);
      }

      await refresh();
      resetForm();
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  async function runAction(
    action: () => Promise<ResumeVersion>,
    editResult = false
  ) {
    setBusy(true);
    setError("");

    try {
      const result = await action();
      await refresh();

      if (editResult) {
        edit(result);
      } else {
        resetForm();
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      style={{
        maxWidth: 900,
        margin: "0 auto",
        padding: 24,
        width: "100%",
        overflowY: "auto",
      }}
    >
      <h2>Resume Library</h2>

      <p>
        Save tailored resumes, manage versions,
        and reuse approved documents.
      </p>

      {error && (
        <p role="alert" style={{ color: "crimson" }}>
          {error}
        </p>
      )}

      <form
        onSubmit={save}
        style={{
          display: "grid",
          gap: 12,
          marginBottom: 32,
        }}
      >
        <h3>
          {editingId === null
            ? "New Resume"
            : "Edit Draft"}
        </h3>

        <label>
          Resume Name
          <input
            required
            value={form.name}
            onChange={(event) =>
              setForm({
                ...form,
                name: event.target.value,
              })
            }
            placeholder="Software Engineer Resume"
          />
        </label>

        <label>
          Target Roles
          <input
            value={form.roles}
            onChange={(event) =>
              setForm({
                ...form,
                roles: event.target.value,
              })
            }
            placeholder="Software Engineer, Backend Developer"
          />
        </label>

        <label>
          Skills
          <input
            value={form.skills}
            onChange={(event) =>
              setForm({
                ...form,
                skills: event.target.value,
              })
            }
            placeholder="Python, React, SQL, Docker"
          />
        </label>

        <label>
          Resume Content
          <textarea
            required
            rows={14}
            value={form.content}
            onChange={(event) =>
              setForm({
                ...form,
                content: event.target.value,
              })
            }
            placeholder="Paste your resume here..."
            style={{ width: "100%" }}
          />
        </label>

        <div style={{ display: "flex", gap: 10 }}>
          <button type="submit" disabled={busy}>
            {busy ? "Saving..." : "Save Draft"}
          </button>

          {editingId !== null && (
            <button type="button" onClick={resetForm}>
              Cancel
            </button>
          )}
        </div>
      </form>

      <h3>Saved Resumes ({resumes.length})</h3>

      {resumes.length === 0 && (
        <p>No resumes saved yet.</p>
      )}

      {resumes.map((resume) => (
        <div
          key={resume.id}
          style={{
            border: "1px solid #ccc",
            borderRadius: 8,
            padding: 16,
            marginBottom: 12,
          }}
        >
          <h4>
            {resume.name} — V{resume.version}
          </h4>

          <p>
            Status: <strong>{resume.status}</strong>
          </p>

          {resume.profile_changed && (
            <p style={{ color: "#b7791f" }}>
              Master Profile has changed since approval.
              Review this resume before reusing it.
            </p>
          )}

          {resume.role_tags.length > 0 && (
            <p>Roles: {resume.role_tags.join(", ")}</p>
          )}

          {resume.skill_tags.length > 0 && (
            <p>Skills: {resume.skill_tags.join(", ")}</p>
          )}

          <details>
            <summary>Preview Resume</summary>
            <pre
              style={{
                whiteSpace: "pre-wrap",
                overflowWrap: "anywhere",
              }}
            >
              {resume.content}
            </pre>
          </details>

          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 10,
              marginTop: 12,
            }}
          >
            {resume.status === "draft" ? (
              <>
                <button
                  disabled={busy}
                  onClick={() => edit(resume)}
                >
                  Edit
                </button>

                <button
                  disabled={busy}
                  onClick={() => {
                    if (window.confirm(
                      "Approve and lock this resume version?"
                    )) {
                      void runAction(
                        () => approveResume(resume.id)
                      );
                    }
                  }}
                >
                  Approve
                </button>
              </>
            ) : (
              <button
                disabled={busy}
                onClick={() =>
                  void runAction(
                    () => createResumeRevision(resume.id),
                    true
                  )
                }
              >
                Create New Version
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}