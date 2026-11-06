import {
  useEffect,
  useState,
} from "react";

import {
  findJobs,
  getJobs,
  availabilityLabel,
  verifyJob,
  type Job,
} from "../Api";


interface JobsPageProps {
  onOpenJob: (jobId: number) => void;
}


export default function JobsPage({
  onOpenJob,
}: JobsPageProps) {

  const [roles, setRoles] = useState(
    "Bioinformatics Scientist, Biomedical Data Scientist"
  );

  const [locations, setLocations] = useState(
    "Houston, TX"
  );

  const [days, setDays] = useState(14);

  const [minimumScore, setMinimumScore] =
    useState(60);

  const [remoteOK, setRemoteOK] =
    useState(true);
  const [strictDates, setStrictDates] = useState(false);

  const [jobs, setJobs] =
    useState<Job[]>([]);

  const [loading, setLoading] =
    useState(false);

  const [message, setMessage] =
    useState("");



  useEffect(() => {

    async function load() {

      try {
        const savedJobs = await getJobs();
        setJobs(savedJobs);

      } catch (error) {

        console.error(error);

        setMessage(
          error instanceof Error
            ? error.message
            : "Unable to load job search data."
        );

      }

    }

    load();

  }, []);


  async function search() {

    setLoading(true);
    setMessage("Searching...");

    try {

      const results = await findJobs({

        keywords: roles
          .split(",")
          .map((x) => x.trim())
          .filter(Boolean),

        locations: locations
          .split(/\r?\n/)
          .map((x) => x.trim())
          .filter(Boolean),

        posted_within_days: days,

        remote_ok: remoteOK,

        min_relevance_score: minimumScore,
        strict_dates: strictDates,

      });

      setJobs(results);

      setMessage(
        `Found ${results.length} matching postings. ${results.filter(job => job.availability_status === "open").length} verified open. Results are saved; coverage is limited to discovered Greenhouse and Lever postings.`
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
    <div className = "jobs-page">
      <div className = "jobs-header">

        <div>
          <h1>Job Search</h1>
          <p>Find current Greenhouse and Lever postings, verify availability, and prepare contact autofill.</p>
        </div>
      </div>

      <section className="search-setting">
        <h2>Search Settings</h2>
        <label>
          Target roles/ keywords
          <input
            value ={roles}
            onChange={(e)=>
              setRoles(e.target.value)
            } 

          placeholder="Software Engineer, Data Analyst" />
        </label>

        <label>
          Preferred locations (one per line)

          <textarea
            value={locations}
            onChange={(e) =>
              setLocations(e.target.value)
            }
            placeholder={"Houston, TX\nChicago, IL"}
            rows={3}
          />
        </label>


        <div className="job-options">

        <label>
          Publication window

          <select
            value={days}
            onChange={(e) =>
              setDays(
                Number(e.target.value)
              )
            }
          >
            <option value={1}>
              1 day
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
          Minimum keyword relevance

          <select
            value={minimumScore}
            onChange={(e) =>
              setMinimumScore(
                Number(e.target.value)
              )
            }
          >
            <option value={40}>
              40%
            </option>

            <option value={50}>
              50%
            </option>

            <option value={60}>
              60%
            </option>

            <option value={70}>
              70%
            </option>

            <option value={80}>
              80%
            </option>
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
        <label><input type="checkbox" checked={strictDates} onChange={e => setStrictDates(e.target.checked)} /> Require a known publication date</label>

      </div>


      <p>Unknown publication dates are included unless you require a known date. An open posting is not necessarily a newly posted job.</p>
      <button
        onClick={search}
        disabled={loading}
      >
        {loading
          ? "Searching..."
          : "Find Jobs"}
      </button>


      {message && (
        <p className="job-message">
          {message}
        </p>
      )}

    </section>


    <section className="job-results">

      <h2>
        Matching Jobs
      </h2>


      {!loading && jobs.length === 0 && (
        <p>
          No jobs to display.
        </p>
      )}


      {jobs.map((job) => (

        <article
          key={job.id}
          className="job-card"
        >

          <h3>
            {job.title}
          </h3>


          {job.company && (
            <p>
              {job.company}
            </p>
          )}


          {job.location && (
            <p>
              {job.location}
            </p>
          )}


          {job.final_score != null && (
            <p>
              Keyword relevance:{" "}
              <strong>
                {job.match_score}%
              </strong>
            </p>
          )}


          <p>{job.posted_date_text ? `Published: ${job.posted_date_text}` : "Posting date unknown"}</p>
          <p><strong>{availabilityLabel(job)}</strong>{job.availability_checked_at && ` · Checked ${new Date(job.availability_checked_at).toLocaleString()}`}</p>
          {job.availability_status !== "open" && <button disabled={loading} onClick={async () => {
            setLoading(true);
            try {
              const updated = await verifyJob(job.id);
              setJobs(current => current.map(item => item.id === updated.id ? updated : item));
            } catch (error) {setMessage(error instanceof Error ? error.message : "Verification failed.");}
            finally {setLoading(false);}
          }}>Retry availability check</button>}


          <p>
            Status: {job.status}
          </p>


          {job.snippet && (
            <p className="job-snippet">
              {job.snippet}
            </p>
          )}


          <button
            onClick={() =>
              onOpenJob(job.id)
            }
          >
            Review &amp; Prepare Application
          </button>

        </article>

      ))}


        

      
      </section>
    </div>

    

   

  );
}




