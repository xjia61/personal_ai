import { useEffect, useRef, useState } from "react";
import { autofillApplication, downloadExtensionData, getApplications, getResumeVersions, getJob, verifyJob, availabilityLabel, safeApplicationUrl, openApplication, prepareApplication,
  statusLabel, updateApplicationStatus, type ApplicationStatus, type AutofillResult, type ResumeVersion, type Job } from "../Api";

export default function ApplicationWorkflow({jobId}: {jobId: number}) {
  const [resumes, setResumes] = useState<ResumeVersion[]>([]);
  const [resumeId, setResumeId] = useState<number | null>(null);
  const [application, setApplication] = useState<{id: number; status: ApplicationStatus; application_url: string} | null>(null);
  const [result, setResult] = useState<AutofillResult | null>(null);
  const [busy, setBusy] = useState("Loading");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [job, setJob] = useState<Job | null>(null);
  const lock = useRef(false);
  useEffect(() => {
    let active = true;
    Promise.all([getResumeVersions(), getApplications(jobId), getJob(jobId)]).then(([versions, applications, savedJob]) => {
      if (!active) return;
      setResumes(versions.filter(r => r.status === "approved"));
      setJob(savedJob);
      const existing = applications[0];
      if (existing) {
        setResumeId(existing.resume_version_id);
        setApplication({id: existing.id, status: existing.status, application_url: existing.application_url});
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
    {job && <>
      <p><strong>{availabilityLabel(job)}</strong>{job.availability_checked_at && ` · Checked ${new Date(job.availability_checked_at).toLocaleString()}`}</p>
      <p>{job.posted_date_text ? `Published: ${job.posted_date_text}` : "Posting date unknown"}</p>
      <button disabled={Boolean(busy)} onClick={() => run("Checking availability", async () => {
        setJob(await verifyJob(jobId));
      })}>Check availability</button>
      {job.availability_status !== "open" && <p>Verify this posting before preparing it. Unsupported URLs cannot be exported for extension autofill.</p>}
    </>}
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
        <button disabled={Boolean(busy) || !resumeId || Boolean(application) || job?.availability_status === "unavailable"} onClick={() => run("Preparing", async () => {
          if (!resumeId) return;
          const prepared = await prepareApplication(jobId, resumeId);
          setJob(await getJob(jobId));
          setApplication({id: prepared.application_id, status: prepared.status, application_url: prepared.application_url});
        })}>Verify &amp; Prepare Application</button>
        <button disabled={Boolean(busy) || !application} onClick={() => run("Opening browser", async () => {
          if (!application) return;
          await openApplication(application.id);
          setNotice("Browser opened. Log in, register, dismiss popups, or navigate to the application form manually, then choose Autofill & Upload Resume.");
        })}>Open Local Automation Browser</button>
        <button disabled={Boolean(busy) || !application} onClick={() => run("Autofilling", async () => {
          if (!application) return;
          const filled = await autofillApplication(application.id);
          setResult(filled); setApplication({...application, status: filled.status});
        })}>Autofill &amp; Upload Resume</button>
      </div>
      {application && <>
        <h3>Use your own Chrome browser</h3>
        <p>Download contact details, open the official application page in Chrome, then import the file in the Career Agent extension. The file contains your contact information. Upload the selected resume and submit manually.</p>
        <button disabled={Boolean(busy)} onClick={() => run("Exporting contact details", async () => {
          await downloadExtensionData(application.id);
          setNotice("Import the downloaded JSON file in the extension. Autofill runs only when you click its Fill contact fields button.");
        })}>Download Extension Data</button>
        {safeApplicationUrl(application.application_url) && <p>
          <a href={safeApplicationUrl(application.application_url)} target="_blank" rel="noreferrer">Open Official Application ↗</a>
        </p>}
        <p>Status: <strong>{statusLabel(application.status)}</strong> · Application #{application.id}</p>
        <p>After you review and submit in the browser yourself, mark this application as applied.</p>
        <button disabled={Boolean(busy) || !["preparing", "ready_for_review"].includes(application.status)} onClick={() => run("Updating status", async () => {
          const updated = await updateApplicationStatus(application.id, "applied");
          setApplication({id: updated.id, status: updated.status, application_url: updated.application_url});
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
