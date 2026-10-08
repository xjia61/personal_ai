import {
  useEffect,
  useState,
} from "react";

import {
  findJobs,
  getJobs,
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
          .split(",")
          .map((x) => x.trim())
          .filter(Boolean),

        posted_within_days: days,

        remote_ok: remoteOK,

        min_relevance_score: minimumScore,

      });

      setJobs(results);

      setMessage(
        `Found ${results.length} jobs.`
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
          <p>Search jobs by keywords, location, date, and relevance. </p>
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
          Preferred locations

          <input
            value={locations}
            onChange={(e) =>
              setLocations(e.target.value)
            }
            placeholder="Houston, TX, Remote"
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
          Minimum relevance

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

      </div>


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
              Relevance:{" "}
              <strong>
                {job.final_score}%
              </strong>
            </p>
          )}


          {job.posted_date_text && (
            <p>
              Posted:{" "}
              {job.posted_date_text}
            </p>
          )}


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
            View Details
          </button>

        </article>

      ))}


        

      
      </section>
    </div>

    

   

  );
}




