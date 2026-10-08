import { useEffect, useState } from "react";

import {
  getJob,
  recommendResume,
} from "../Api";

import type {
  Job,
  ResumeRecommendation,
} from "../Api";


interface JobDetailPageProps {
  jobId: number;
  onBack: () => void;
}


export default function JobDetailPage({
  jobId,
  onBack,
}: JobDetailPageProps) {

  const [job, setJob] =
    useState<Job | null>(null);

  const [resumeRecommendation, setResumeRecommendation] =
    useState<ResumeRecommendation | null>(null);

  const [loading, setLoading] =
    useState(true);

  const [resumeLoading, setResumeLoading] =
    useState(false);

  const [error, setError] =
    useState("");


  useEffect(() => {

    setLoading(true);
    setError("");

    getJob(jobId)
      .then(setJob)
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));

  }, [jobId]);


  async function handleFindResume() {

    setResumeLoading(true);
    setError("");

    try {

      const result =
        await recommendResume(jobId);

      setResumeRecommendation(result);

    } catch (err) {

      setError(String(err));

    } finally {

      setResumeLoading(false);
    }
  }


  if (loading) {
    return (
      <div style={{ padding: 24 }}>
        Loading job...
      </div>
    );
  }


  if (!job) {
    return (
      <div style={{ padding: 24 }}>

        <button onClick={onBack}>
          ← Back to Jobs
        </button>

        <p>
          {error || "Job not found"}
        </p>

      </div>
    );
  }


  return (
    <div
      style={{
        maxWidth: 950,
        margin: "0 auto",
        padding: 24,
        width: "100%",
        overflowY: "auto",
      }}
    >

      <button onClick={onBack}>
        ← Back to Jobs
      </button>


      <header style={{ marginTop: 24 }}>

        <h2>{job.title}</h2>

        <h3>{job.company}</h3>

        {job.location && (
          <p>{job.location}</p>
        )}

        {job.posted_date_text && (
          <p>
            Posted: {job.posted_date_text}
          </p>
        )}

      </header>


      <hr />


      <section>

        <h3>Job Description</h3>

        <p
          style={{
            whiteSpace: "pre-wrap",
            lineHeight: 1.5,
          }}
        >
          {job.snippet ||
            "No job description saved yet."}
        </p>

        {job.source_url && (
          <p>
            <a
              href={job.source_url}
              target="_blank"
              rel="noreferrer"
            >
              View Source
            </a>
          </p>
        )}

      </section>


      <hr />


      <section>

        <h3>Match Analysis</h3>

        {job.final_score != null ? (
          <p>
            Overall Match:{" "}
            <strong>
              {job.final_score}
            </strong>
          </p>
        ) : (
          <p>
            Match analysis has not been completed.
          </p>
        )}

      </section>


      <hr />


      <section>

        <h3>Resume Recommendation</h3>

        {!resumeRecommendation && (
          <button
            onClick={handleFindResume}
            disabled={resumeLoading}
          >
            {resumeLoading
              ? "Checking..."
              : "Find Best Resume"}
          </button>
        )}


        {resumeRecommendation && (
          <div>

            {resumeRecommendation.resume_id ? (
              <>
                <p>
                  <strong>
                    {
                      resumeRecommendation
                        .resume_name
                    }
                    {" — V"}
                    {
                      resumeRecommendation
                        .version
                    }
                  </strong>
                </p>

                <p>
                  Resume Match:{" "}
                  <strong>
                    {
                      resumeRecommendation
                        .score
                    }
                    %
                  </strong>
                </p>

                <p>
                  Recommendation:{" "}
                  <strong>
                    {
                      resumeRecommendation
                        .action
                    }
                  </strong>
                </p>

                {resumeRecommendation
                  .matched_skills.length > 0 && (
                  <p>
                    Matched Skills:{" "}
                    {resumeRecommendation
                      .matched_skills
                      .join(", ")}
                  </p>
                )}

              </>
            ) : (
              <p>
                No approved resume found.
                A new resume will be needed.
              </p>
            )}

          </div>
        )}

      </section>


      {error && (
        <p
          role="alert"
          style={{ color: "crimson" }}
        >
          {error}
        </p>
      )}

    </div>
  );
}