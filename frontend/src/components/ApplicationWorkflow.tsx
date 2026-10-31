import { useEffect, useRef, useState } from "react";
import { autofillApplication, getApplications, getResumeVersions, openApplication, prepareApplication,
  statusLabel, updateApplicationStatus, type ApplicationStatus, type AutofillResult, type ResumeVersion } from "../Api";

export default function ApplicationWorkflow({jobId}: {jobId: number}) {
  const [resumes, setResumes] = useState<ResumeVersion[]>([]);
  const [resumeId, setResumeId] = useState<number | null>(null);
  const [application, setApplication] = useState<{id: number; status: ApplicationStatus} | null>(null);
  const [result, setResult] = useState<AutofillResult | null>(null);
  const [busy, setBusy] = useState("Loading");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const lock = useRef(false);
  useEffect(() => {
    let active = true;
    Promise.all([getResumeVersions(), getApplications(jobId)]).then(([versions, applications]) => {
      if (!active) return;
      setResumes(versions.filter(r => r.status === "approved"));
      const existing = applications[0];
      if (existing) {
        setResumeId(existing.resume_version_id);
        setApplication({id: existing.id, status: existing.status});
      }
    }).catch(e => {if (active) setError(e instanceof Error ? e.message : "Unable to load applications.");})
      .finally(() => {if (active) setBusy("");});
    return () => {active = false;};
  }, [jobId]);
  async function run(label: string, action: () => Promise<void>) {
    if (lock.current) return;
    lock.current = true; setBusy(label); setError(""); setNotice("");
    try { await action(); }
    catch (e) {setError(e instanceof Error ? e.message : "Unable to complete application request.");}
    finally {lock.current = false; setBusy("");}
  }
  return <section className="application-section" aria-busy={Boolean(busy)}>
    <h2>Application</h2>
    {error && <p role="alert" className="error">{error}</p>}
    {busy === "Loading" ? <p>Loading applications…</p> : <>
      <label>Approved resume <select value={resumeId ?? ""} disabled={Boolean(busy)} onChange={e => {
        setResumeId(e.target.value ? Number(e.target.value) : null); setApplication(null); setResult(null); setNotice("");
      }}>
        <option value="">Select a resume</option>
        {resumeId && !resumes.some(r => r.id === resumeId) && <option value={resumeId}>Previously selected resume (no longer approved)</option>}
        {resumes.map(r => <option key={r.id} value={r.id}>{r.name} (v{r.version})</option>)}
      </select></label>
      {!resumes.length && <p>Approve a resume in the Resume Library first.</p>}
      <div className="job-actions">
        <button disabled={Boolean(busy) || !resumeId || Boolean(application)} onClick={() => run("Preparing", async () => {
          if (!resumeId) return;
          const prepared = await prepareApplication(jobId, resumeId);
          setApplication({id: prepared.application_id, status: prepared.status});
        })}>Prepare Application</button>
        <button disabled={Boolean(busy) || !application} onClick={() => run("Opening browser", async () => {
          if (!application) return;
          await openApplication(application.id);
          setNotice("Browser opened. Log in, register, dismiss popups, or navigate to the application form manually, then choose Autofill & Upload Resume.");
        })}>Open Application</button>
        <button disabled={Boolean(busy) || !application} onClick={() => run("Autofilling", async () => {
          if (!application) return;
          const filled = await autofillApplication(application.id);
          setResult(filled); setApplication({...application, status: filled.status});
        })}>Autofill &amp; Upload Resume</button>
      </div>
      {application && <>
        <p>Status: <strong>{statusLabel(application.status)}</strong> · Application #{application.id}</p>
        <p>After you review and submit in the browser yourself, mark this application as applied.</p>
        <button disabled={Boolean(busy) || !["preparing", "ready_for_review"].includes(application.status)} onClick={() => run("Updating status", async () => {
          const updated = await updateApplicationStatus(application.id, "applied");
          setApplication({id: updated.id, status: updated.status});
        })}>Mark as Applied</button>
      </>}
    </>}
    {busy && <p role="status">{busy}…</p>}
    {notice && <p role="status">{notice}</p>}
    {result && <div aria-live="polite">
      <h3>{statusLabel(result.status)}</h3>
      <h4>Filled</h4>
      {result.filled_fields.length ? <ul>{result.filled_fields.map(f => <li key={f}>✓ {statusLabel(f)}</li>)}</ul> : <p>No matching fields filled.</p>}
      <p>Resume: {result.resume_uploaded ? "✓ Uploaded" : "Not uploaded — attach the selected resume manually or retry after navigating to the form."}</p>
      {result.skipped_fields.length > 0 && <><h4>Skipped — complete manually if needed</h4><ul>{result.skipped_fields.map(f => <li key={f}>{statusLabel(f)}</li>)}</ul></>}
      {result.manual_review_required && <p>Review the application in the opened browser. Complete any remaining questions manually. The app will never submit the application automatically.</p>}
    </div>}
  </section>;
}
