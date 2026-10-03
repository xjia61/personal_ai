import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import {
  getCareerRecords,
  saveCareerRecord,
  deleteCareerRecord,
} from "../Api";

import type {
  CareerCategory,
  CareerRecord,
  CareerRecordInput,
} from "../Api";


interface RecordForm {
  category: CareerCategory;
  title: string;
  organization: string;
  start_date: string;
  end_date: string;
  description: string;
  skills: string;
}

const emptyForm: RecordForm = {
  category: "work",
  title: "",
  organization: "",
  start_date: "",
  end_date: "",
  description: "",
  skills: "",
};

const categoryLabels: Record<CareerCategory, string> = {
  education: "Education",
  work: "Work Experience",
  project: "Project",
  skill: "Skill",
  certification: "Certification",
};


export default function CareerPage() {
  const [records, setRecords] = useState<CareerRecord[]>([]);
  const [form, setForm] = useState<RecordForm>({ ...emptyForm });

  const [editingId, setEditingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function refreshRecords() {
    const data = await getCareerRecords();
    setRecords(data);
  }

  useEffect(() => {
    getCareerRecords()
      .then(setRecords)
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  }, []);

  function resetForm() {
    setForm({ ...emptyForm });
    setEditingId(null);
  }

  function editRecord(record: CareerRecord) {
    setEditingId(record.id);

    setForm({
      category: record.category,
      title: record.title,
      organization: record.organization ?? "",
      start_date: record.start_date ?? "",
      end_date: record.end_date ?? "",
      description: record.description,
      skills: record.skills.join(", "),
    });
  }

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setSaving(true);
    setError("");

    const payload: CareerRecordInput = {
      category: form.category,
      title: form.title.trim(),
      organization: form.organization.trim() || null,
      start_date: form.start_date || null,
      end_date: form.end_date || null,
      description: form.description.trim(),
      skills: form.skills
        .split(",")
        .map((skill) => skill.trim())
        .filter(Boolean),
    };

    try {
      await saveCareerRecord(
        payload,
        editingId === null ? undefined : editingId
      );

      await refreshRecords();
      resetForm();
    } catch (err) {
      setError(String(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: number) {
    if (!window.confirm("Delete this career record?")) {
      return;
    }

    try {
      setError("");
      await deleteCareerRecord(id);
      await refreshRecords();

      if (editingId === id) {
        resetForm();
      }
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <div
      style={{
        maxWidth: 850,
        margin: "0 auto",
        padding: 24,
        width: "100%",
        overflowY: "auto",
      }}
    >
      <h2>Master Career Profile</h2>

      <p>
        Manage your education, work experience,
        projects, skills, and certifications.
      </p>

      {error && (
        <p role="alert" style={{ color: "crimson" }}>
          {error}
        </p>
      )}

      <form
        onSubmit={handleSave}
        style={{
          display: "grid",
          gap: 12,
          marginBottom: 32,
        }}
      >
        <h3>
          {editingId === null
            ? "Add Career Record"
            : "Edit Career Record"}
        </h3>

        <label>
          Category
          <select
            value={form.category}
            onChange={(e) =>
              setForm({
                ...form,
                category: e.target.value as CareerCategory,
              })
            }
          >
            {Object.entries(categoryLabels).map(
              ([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              )
            )}
          </select>
        </label>

        <label>
          Title
          <input
            required
            value={form.title}
            onChange={(e) =>
              setForm({
                ...form,
                title: e.target.value,
              })
            }
            placeholder="Job title, degree, or project name"
          />
        </label>

        <label>
          Organization
          <input
            value={form.organization}
            onChange={(e) =>
              setForm({
                ...form,
                organization: e.target.value,
              })
            }
            placeholder="Company, university, or organization"
          />
        </label>

        <label>
          Start Date
          <input
            type="month"
            value={form.start_date}
            onChange={(e) =>
              setForm({
                ...form,
                start_date: e.target.value,
              })
            }
          />
        </label>

        <label>
          End Date (leave blank if ongoing)
          <input
            type="month"
            value={form.end_date}
            onChange={(e) =>
              setForm({
                ...form,
                end_date: e.target.value,
              })
            }
          />
        </label>

        <label>
          Description
          <textarea
            rows={5}
            value={form.description}
            onChange={(e) =>
              setForm({
                ...form,
                description: e.target.value,
              })
            }
            placeholder="Responsibilities, achievements, and results"
          />
        </label>

        <label>
          Skills (separate with commas)
          <input
            value={form.skills}
            onChange={(e) =>
              setForm({
                ...form,
                skills: e.target.value,
              })
            }
            placeholder="Python, SQL, Docker"
          />
        </label>

        <div style={{ display: "flex", gap: 10 }}>
          <button type="submit" disabled={saving}>
            {saving ? "Saving..." : "Save Record"}
          </button>

          {editingId !== null && (
            <button type="button" onClick={resetForm}>
              Cancel
            </button>
          )}
        </div>
      </form>

      <h3>Career Records ({records.length})</h3>

      {loading && <p>Loading...</p>}

      {!loading && records.length === 0 && (
        <p>No records yet. Add your first record above.</p>
      )}

      {records.map((record) => (
        <div
          key={record.id}
          style={{
            border: "1px solid #ccc",
            borderRadius: 8,
            padding: 16,
            marginBottom: 12,
          }}
        >
          <small>{categoryLabels[record.category]}</small>

          <h4>{record.title}</h4>

          {record.organization && (
            <p>{record.organization}</p>
          )}

          {(record.start_date || record.end_date) && (
            <p>
              {record.start_date || "Unknown"}
              {" — "}
              {record.end_date || "Present"}
            </p>
          )}

          {record.description && (
            <p style={{ whiteSpace: "pre-wrap" }}>
              {record.description}
            </p>
          )}

          {record.skills.length > 0 && (
            <p>
              <strong>Skills:</strong>{" "}
              {record.skills.join(", ")}
            </p>
          )}

          <div style={{ display: "flex", gap: 10 }}>
            <button onClick={() => editRecord(record)}>
              Edit
            </button>

            <button
              onClick={() => handleDelete(record.id)}
            >
              Delete
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}