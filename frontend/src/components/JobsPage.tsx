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
} from "../Api";


export default function JobsPage() {

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


  async function saveProfile() {

    setMessage("Saving...");

    try {

      await saveJobProfile({

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

          </article>

        ))}

      </section>

    </div>
  );
}