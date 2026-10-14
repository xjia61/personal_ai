import { useEffect, useState } from "react";

import {
  getJob,
  recommendResume,
  getJobRequirements,
  analyzeJobRequirements,
  getResumeVersions,
} from "../Api";

import type {
  Job,
  ResumeRecommendation,
  JobRequirement,
  ResumeVersion,
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

  const [
      requirements,
      setRequirements
    ] = useState<JobRequirement | null>(null);

    const [
      analyzingRequirements,
      setAnalyzingRequirements
    ] = useState(false);

    const[requirementsError, setRequirementsError] = useState("");

    const [approvedResumes, setApprovedResumes] = useState<ResumeVersion[]>([]);

    const [selectedResumeId, setSelectedResumeId] = useState<number | null>(null);
 

  
  useEffect(() => {

    async function load() {

      try {

        setLoading(true);

        const jobData =
          await getJob(jobId);

        setJob(jobData);

        const cachedRequirements =
          await getJobRequirements(jobId);

        setRequirements(
          cachedRequirements
        );

        const resumes = await getResumeVersions();
        const approved = resumes.filter(
          (resume) =>resume.status === "approved"
        );
        setApprovedResumes(approved);

      } catch (error) {
        console.error(error);
        setRequirementsError(
          "Failed to analyze job requirements"

        );

      

      } finally {

        setLoading(false);

      }

    }

    load();

  }, [jobId]);
  {/*
  useEffect(() => {

    setLoading(true);
    setError("");

    getJob(jobId)
      .then(setJob)
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));

    getJobRequirements(jobId)
      .then(setRequirements)
      .catch((error) =>
        console.error(error)
      );

  }, [jobId]);
  */}

  

  async function handleAnalyzeRequirements() {

  setAnalyzingRequirements(true);
  setError("");

  try {

    const result =
      await analyzeJobRequirements(
        jobId
      );

    setRequirements(result);

  } catch (error) {

    setError(
      error instanceof Error
        ? error.message
        : "Requirement analysis failed."
    );

  } finally {

    setAnalyzingRequirements(false);

  }
}


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

      <hr />

      <section>

        <h3>Job Requirements</h3>

        {!requirements ? (

          <button
            onClick={
              handleAnalyzeRequirements
            }
            disabled={
              analyzingRequirements
            }
          >
            {analyzingRequirements
              ? "Analyzing..."
              : "Analyze Requirements"}
          </button>

        ) : (

          <div>

            {requirements.summary && (
              <p>
                {requirements.summary}
              </p>
            )}


            <h4>Required</h4>

            {requirements.required_items.length === 0 ? (
              <p>
                No clearly required qualifications
                identified.
              </p>
            ) : (

              <ul>

                {requirements.required_items.map(
                  (item, index) => (

                    <li key={index}>
                      <strong>
                        {item.category}
                      </strong>
                      {": "}
                      {item.text}
                    </li>

                  )
                )}

              </ul>

            )}


            <h4>Preferred</h4>

            {requirements.preferred_items.length === 0 ? (
              <p>
                No clearly preferred qualifications
                identified.
              </p>
            ) : (

              <ul>

                {requirements.preferred_items.map(
                  (item, index) => (

                    <li key={index}>
                      <strong>
                        {item.category}
                      </strong>
                      {": "}
                      {item.text}
                    </li>

                  )
                )}

              </ul>

            )}


            {requirements
              .unclassified_items
              .length > 0 && (
              <>
                <h4>
                  Other Qualifications
                </h4>

                <ul>

                  {requirements
                    .unclassified_items
                    .map((item, index) => (

                      <li key={index}>
                        <strong>
                          {item.category}
                        </strong>
                        {": "}
                        {item.text}
                      </li>

                    ))}

                </ul>
              </>
            )}


            {requirements
              .responsibilities
              .length > 0 && (
              <>
                <h4>
                  Responsibilities
                </h4>

                <ul>

                  {requirements
                    .responsibilities
                    .map(
                      (
                        responsibility,
                        index
                      ) => (

                        <li key={index}>
                          {responsibility}
                        </li>

                      )
                    )}

                </ul>
              </>
            )}


            <small>
              {requirements.cached
                ? "Loaded from saved analysis."
                : "New analysis saved."}
            </small>

          </div>

        )}

      </section>
      <hr />

      <section className="requirements-section">
        <h2>Requirements Analysis</h2>

        {!requirements ? (
          <>
            <p>
              Requirements have not been analyzed yet.
            </p>

            <button
              onClick={handleAnalyzeRequirements}
              disabled={analyzingRequirements}
            >
              {analyzingRequirements
                ? "Analyzing..."
                : "Analyze Requirements"}
            </button>

            {requirementsError && (
              <p>{requirementsError}</p>
            )}
          </>
        ) : (
          <>
            <h3>Summary</h3>
            <p>{requirements.summary}</p>

            <h3>Required</h3>

            {requirements.required_items.length === 0 ? (
              <p>No explicit required qualifications found.</p>
            ) : (
              <ul>
                {requirements.required_items.map(
                  (item, index) => (
                    <li key={index}>
                      <strong>{item.category}:</strong>{" "}
                      {item.text}
                    </li>
                  )
                )}
              </ul>
            )}

            <h3>Preferred</h3>

            {requirements.preferred_items.length === 0 ? (
              <p>No explicit preferred qualifications found.</p>
            ) : (
              <ul>
                {requirements.preferred_items.map(
                  (item, index) => (
                    <li key={index}>
                      <strong>{item.category}:</strong>{" "}
                      {item.text}
                    </li>
                  )
                )}
              </ul>
            )}

            {requirements.unclassified_items.length > 0 && (
              <>
                <h3>Other Qualifications</h3>

                <ul>
                  {requirements.unclassified_items.map(
                    (item, index) => (
                      <li key={index}>
                        {item.text}
                      </li>
                    )
                  )}
                </ul>
              </>
            )}

            <h3>Responsibilities</h3>

            <ul>
              {requirements.responsibilities.map(
                (item, index) => (
                  <li key={index}>{item}</li>
                )
              )}
            </ul>
          </>
        )}
      </section>

      <section className="application-section">
        <h2>Prepare Application</h2>

        {approvedResumes.length === 0 ? (
          <p>
            No approved resumes available.
            Approve a resume in the Resume Library first.
          </p>
        ) : (
          <>
            <label>
              Resume
            </label>

            <select
              value={selectedResumeId ?? ""}
              onChange={(e) =>
                setSelectedResumeId(
                  Number(e.target.value)
                )
              }
            >
              <option value="">
                Select a resume
              </option>

              {approvedResumes.map((resume) => (
                <option
                  key={resume.id}
                  value={resume.id}
                >
                  {resume.name}
                  {" "}
                  (v{resume.version})
                </option>
              ))}
            </select>

            <button
              disabled={selectedResumeId === null}
              onClick={() => {
                console.log(
                  "Preparing application:",
                  {
                    jobId,
                    resumeId: selectedResumeId,
                  }
                );
              }}
            >
              Prepare Application
            </button>
          </>
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