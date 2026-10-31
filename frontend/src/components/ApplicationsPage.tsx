import { useEffect, useState } from "react";
import { applicationStatuses, getApplications, safeApplicationUrl, statusLabel, updateApplicationStatus,
  type ApplicationRecord, type ApplicationStatus } from "../Api";

export default function ApplicationsPage({onOpenJob}: {onOpenJob: (id: number) => void}) {
  const [applications, setApplications] = useState<ApplicationRecord[]>([]);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState<number | null>(null);
  const [error, setError] = useState("");
  async function load() {
    setLoading(true); setError("");
    try {setApplications(await getApplications());}
    catch (e) {setError(e instanceof Error ? e.message : "Unable to load applications.");}
    finally {setLoading(false);}
  }
  useEffect(() => {void load();}, []);
  async function changeStatus(application: ApplicationRecord, status: ApplicationStatus) {
    setPending(application.id); setError("");
    try {
      const updated = await updateApplicationStatus(application.id, status);
      setApplications(current => current.map(a => a.id === updated.id ? updated : a));
    } catch (e) {setError(e instanceof Error ? e.message : "Unable to update status.");}
    finally {setPending(null);}
  }
  const visible = applications.filter(a => !filter || a.status === filter);
  return <main className="applications-page">
    <h1>Applications</h1>
    <p>Track applications you review and submit yourself. Status changes only update this tracker.</p>
    <div className="job-actions">
      <label>Filter by status <select value={filter} onChange={e => setFilter(e.target.value)}>
        <option value="">All statuses</option>
        {applicationStatuses.map(s => <option key={s} value={s}>{statusLabel(s)}</option>)}
      </select></label>
      <button onClick={load} disabled={loading || pending !== null}>Refresh</button>
    </div>
    {error && <p role="alert" className="error">{error}</p>}
    {loading ? <p role="status">Loading applications…</p> : visible.length === 0 ?
      <p>{applications.length ? "No applications match this status." : "No applications yet. Open a job and choose Prepare Application to get started."}</p> :
      <div className="application-table"><table>
        <thead><tr><th>Company / Role</th><th>Status</th><th>Resume Used</th><th>Created</th><th>Links</th></tr></thead>
        <tbody>{visible.map(a => <tr key={a.id}>
          <td><strong>{a.company || "Company unavailable"}</strong><br />{a.job_title}</td>
          <td><select aria-label={`Status for ${a.job_title} at ${a.company || "company"}`} value={a.status}
            disabled={pending !== null} onChange={e => changeStatus(a, e.target.value as ApplicationStatus)}>
            {!applicationStatuses.includes(a.status) && <option value={a.status}>{statusLabel(a.status)}</option>}
            {applicationStatuses.map(s => <option key={s} value={s}>{statusLabel(s)}</option>)}
          </select>{pending === a.id && <span role="status"> Saving…</span>}</td>
          <td>{a.resume_name} (v{a.resume_version})</td>
          <td>{new Date(a.created_at).toLocaleDateString()}</td>
          <td><button onClick={() => onOpenJob(a.job_id)}>Open Job</button>{safeApplicationUrl(a.application_url) &&
            <p><a href={safeApplicationUrl(a.application_url)} target="_blank" rel="noreferrer">Application Link ↗</a></p>}</td>
        </tr>)}</tbody>
      </table></div>}
  </main>;
}
