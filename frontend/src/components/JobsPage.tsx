import {
  useEffect,
  useState,
} from "react";

import {
  findJobs,
  getJobProfile,
  getJobs,
  saveJobProfile,
  type Job,
  resolveJobLink,
  setApplicationLink,
  prepareApplication,
  updateJobStatus,
  uploadResume,
} from "../Api";


export default function JobsPage() {
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [linkedin, setLinkedin] = useState("");

  const [actionJobId, setActionJobId] =
    useState<number | null>(null);

  const [resume, setResume] = useState("");

  const [roles, setRoles] = useState(
    "Bioinformatics Scientist, Biomedical Data Scientist"
  );

  const [locations, setLocations] = useState(
    "Houston, TX, Remote"
  );

  const [days, setDays] = useState(14);

  const [minimumScore, setMinimumScore] =
    useState(60);

  const [remoteOK, setRemoteOK] =
    useState(true);

  const [jobs, setJobs] =
    useState<Job[]>([]);

  const [loading, setLoading] =
    useState(false);

  const [message, setMessage] =
    useState("");


  useEffect(() => {

    async function load() {

      try {

        const profile =
          await getJobProfile();

        setFirstName(profile.first_name || "");
        setLastName(profile.last_name || "");
        setEmail(profile.email || "");
        setPhone(profile.phone || "");
        setLinkedin(profile.linkedin_url || "");

        setResume(profile.resume_text);

        setRoles(
          profile.target_roles.join(", ")
        );

        setLocations(
          profile.preferred_locations.join(", ")
        );

        setDays(
          profile.posted_within_days
        );

        setMinimumScore(
          profile.min_match_score
        );

        setRemoteOK(
          profile.remote_ok
        );

        const savedJobs =
          await getJobs();

        setJobs(savedJobs);

      } catch (error) {

        console.error(error);

      }
    }

    load();

  }, []);

  function replaceJob(updated: Job) {
    setJobs((current) =>
      current.map((job) =>
        job.id === updated.id ? updated : job
      )
    );
  }


  async function resolveLink(job: Job) {
    setActionJobId(job.id);
    setMessage("Resolving official application link...");

    try {
      const updated = await resolveJobLink(job.id);

      replaceJob(updated);

      if (updated.link_status === "verified_ats") {
        setMessage(
          "The job was found in the official ATS."
        );
      } else {
        setMessage(
          "Automatic verification was unsuccessful. " +
          "You can confirm the official link manually."
        );
      }
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Unable to resolve the link."
      );
    } finally {
      setActionJobId(null);
    }
  }


  async function confirmOfficialLink(job: Job) {
    const url = window.prompt(
      "Paste the official application URL " +
      "you verified on the company's website:"
    );

    if (!url) return;

    setActionJobId(job.id);

    try {
      const updated = await setApplicationLink(
        job.id,
        url.trim()
      );

      replaceJob(updated);
      setMessage("Application link saved.");
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Unable to save the link."
      );
    } finally {
      setActionJobId(null);
    }
  }


  async function startApply(job: Job) {
    setActionJobId(job.id);

    try {
      const result = await prepareApplication(job.id);

      setMessage(
        result.state === "error"
          ? "Browser failed to start. Check backend logs."
          : "Browser launch requested. Review the form " +
            "and submit it yourself."
      );
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Unable to start the application."
      );
    } finally {
      setActionJobId(null);
    }
  }


  async function markApplied(job: Job) {
    if (
      !window.confirm(
        "Have you successfully submitted this application?"
      )
    ) {
      return;
    }

    try {
      const updated = await updateJobStatus(
        job.id,
        "applied"
      );

      replaceJob(updated);
      setMessage("Job marked as applied.");
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Unable to update the job."
      );
    }
  }


  async function saveProfile() {

    setMessage("Saving...");

    try {

      await saveJobProfile({
        first_name: firstName,
        last_name: lastName,
        email: email,
        phone: phone,
        linkedin_url: linkedin,

        resume_text: resume,

        target_roles: roles
          .split(",")
          .map((x) => x.trim())
          .filter(Boolean),

        preferred_locations: locations
          .split(",")
          .map((x) => x.trim())
          .filter(Boolean),

        remote_ok: remoteOK,

        posted_within_days: days,

        min_match_score: minimumScore,
      });

      setMessage("Profile saved.");

    } catch (error) {

      setMessage(
        error instanceof Error
          ? error.message
          : "Unable to save profile."
      );
    }
  }


  async function search() {

    setLoading(true);

    setMessage("Searching...");

    try {

      await saveProfile();

      const results =
        await findJobs();

      setJobs(results);

      setMessage(
        `Found ${results.length} matching jobs.`
      );

    } catch (error) {

      setMessage(
        error instanceof Error
          ? error.message
          : "Search failed."
      );

    } finally {

      setLoading(false);

    }
  }


  return (
    <div className="jobs-page">

      <div className="jobs-header">

        <div>
          <h1>Job Search</h1>
          <p>
            Resume-based job discovery and ranking
          </p>
        </div>

        <button
          onClick={search}
          disabled={loading}
        >
          {loading
            ? "Searching..."
            : "Find Jobs"}
        </button>

      </div>


      <section className="job-profile">

        <h2>Job Profile</h2>

        <label>
          Target roles
          <input
            value={roles}
            onChange={(e) =>
              setRoles(e.target.value)
            }
          />
        </label>


        <label>
          Preferred locations
          <input
            value={locations}
            onChange={(e) =>
              setLocations(e.target.value)
            }
          />
        </label>


        <div className="job-options">

          <label>
            Posted within

            <select
              value={days}
              onChange={(e) =>
                setDays(
                  Number(e.target.value)
                )
              }
            >
              <option value={1}>
                24 hours
              </option>

              <option value={7}>
                7 days
              </option>

              <option value={14}>
                14 days
              </option>

              <option value={30}>
                30 days
              </option>
            </select>
          </label>


          <label>
            Minimum match

            <select
              value={minimumScore}
              onChange={(e) =>
                setMinimumScore(
                  Number(e.target.value)
                )
              }
            >
              <option value={50}>50%</option>
              <option value={60}>60%</option>
              <option value={70}>70%</option>
              <option value={80}>80%</option>
            </select>
          </label>


          <label className="remote-option">

            <input
              type="checkbox"
              checked={remoteOK}
              onChange={(e) =>
                setRemoteOK(
                  e.target.checked
                )
              }
            />

            Remote OK

          </label>

        </div>


        <label>
          Resume

          <textarea
            className="resume-box"
            value={resume}
            onChange={(e) =>
              setResume(e.target.value)
            }
            placeholder="Paste your resume text here..."
          />
        </label>

        <label>
          First name
          <input
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
          />
        </label>

        <label>
          Last name
          <input
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
          />
        </label>

        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>

        <label>
          Phone
          <input
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
          />
        </label>

        <label>
          LinkedIn
          <input
            value={linkedin}
            onChange={(e) => setLinkedin(e.target.value)}
          />
        </label>

        <label>
          Resume file for applications (PDF / DOCX)
          <input
            type="file"
            accept=".pdf,.docx"
            onChange={async (e) => {
              const file = e.target.files?.[0];

              if (!file) return;

              try {
                await uploadResume(file);
                setMessage("Resume uploaded successfully.");
              } catch (error) {
                setMessage(
                  error instanceof Error
                    ? error.message
                    : "Upload failed."
                );
              }
            }}
          />
        </label>


        <button
          className="secondary-button"
          onClick={saveProfile}
        >
          Save Profile
        </button>

        {message && (
          <span className="job-message">
            {message}
          </span>
        )}

      </section>


      <section className="job-results">

        <h2>
          Matching Jobs
        </h2>

        {jobs.map((job) => (

          <article
            key={job.id}
            className="job-card"
          >

            <div className="score">
              {Math.round(
                job.final_score
              )}%
            </div>


            <div className="job-info">

              <h3>
                {job.title}
              </h3>

              <div className="job-meta">

                {job.company}

                {job.location &&
                  ` · ${job.location}`}

              </div>


              <div className="job-scores">

                Resume:
                {" "}
                {Math.round(
                  job.match_score
                )}%

                {" · "}

                Freshness:
                {" "}
                {Math.round(
                  job.freshness_score
                )}%

              </div>


              {job.snippet && (

                <p>
                  {job.snippet.slice(
                    0,
                    350
                  )}
                </p>

              )}

              <div className="job-scores">

                Preliminary match:
                {" "}
                {Math.round(job.match_score)}%

                {" · "}

                Posted:
                {" "}
                {job.posted_date_text || "Not verified"}

                {" · "}

                Location:
                {" "}
                {job.location || "Not verified"}

              </div>
             

                

            </div>

            {/**/}

            <div className="job-actions">

              <a
                href={job.source_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                Source
              </a>

              <button
                onClick={() => resolveLink(job)}
                disabled={actionJobId === job.id}
              >
                Resolve Link
              </button>

              <button
                onClick={() => confirmOfficialLink(job)}
                disabled={actionJobId === job.id}
              >
                Set Official Link
              </button>

              {job.application_url && (
                <a
                  href={job.application_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Official Application
                </a>
              )}

              <button
                disabled={
                  actionJobId === job.id ||
                  !job.application_url ||
                  ![
                    "verified_ats",
                    "user_confirmed",
                  ].includes(job.link_status)
                }
                onClick={() => startApply(job)}
              >
                Prepare Application
              </button>

              <button
                onClick={() => markApplied(job)}
                disabled={job.status === "applied"}
              >
                {job.status === "applied"
                  ? "Applied ✓"
                  : "Mark Applied"}
              </button>

            </div>

            {/**/}

          </article>

        ))}

      </section>

    </div>
  );
}