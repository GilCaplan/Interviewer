import React from 'react';
import { useParams, Link } from 'react-router-dom';

function FeaturePage({ features }) {
  const { featureId } = useParams();
  const featureIndex = parseInt(featureId);

  // Make sure we have valid features and a valid index
  if (!features || featureIndex < 0 || featureIndex >= features.length) {
    return (
      <div className="feature-page">
        <h2>Feature Not Found</h2>
        <p>Sorry, the requested feature could not be found.</p>
        <Link to="/" className="back-button">Back to Features</Link>
      </div>
    );
  }

  const feature = features[featureIndex];
  const isInterviewQuestions = feature.name.toLowerCase().includes('interview question');

  // Detailed descriptions for each feature type
  const getDetailedDescription = (featureName) => {
    const name = featureName.toLowerCase();

    if (name.includes('programming')) {
      return (
        <>
          <p>Enhance your coding skills with our extensive collection of programming challenges.</p>
          <ul>
            <li>Practice problems in multiple languages (Python, Java, JavaScript, C++)</li>
            <li>Algorithmic challenges at various difficulty levels</li>
            <li>Data structure implementations</li>
            <li>Real interview questions from top tech companies</li>
          </ul>
          <p>Coming soon: Code execution environment and automated test cases.</p>
        </>
      );
    } else if (name.includes('puzzle') || name.includes('riddle')) {
      return (
        <>
          <p>Sharpen your logical thinking with our collection of puzzles and riddles.</p>
          <ul>
            <li>Brain teasers and mind benders</li>
            <li>Mathematical puzzles</li>
            <li>Logic problems</li>
            <li>Pattern recognition challenges</li>
          </ul>
          <p>Coming soon: Interactive puzzle-solving tools and hint system.</p>
        </>
      );
    } else if (name.includes('interview question')) {
      return (
        <>
          <p>Prepare for technical interviews with commonly asked questions.</p>
          <ul>
            <li>Language-specific technical questions</li>
            <li>System design problems</li>
            <li>Database and SQL queries</li>
            <li>Web development concepts</li>
          </ul>
          <div className="feature-actions">
            <Link to="/user-questions" className="feature-action-btn">
              My Questions
            </Link>
            <Link to="/llm-questions" className="feature-action-btn ai-btn">
              Generate AI Questions
            </Link>
          </div>
          <p>Coming soon: AI-powered feedback on your answers.</p>
        </>
      );
    } else if (name.includes('behavior')) {
      return (
        <>
          <p>Master the art of behavioral interviews with practice questions and guidance.</p>
          <ul>
            <li>STAR method response templates</li>
            <li>Questions about teamwork and leadership</li>
            <li>Conflict resolution scenarios</li>
            <li>Questions about your strengths and weaknesses</li>
          </ul>
          <p>Coming soon: Video response recording and analysis.</p>
        </>
      );
    } else if (name.includes('case')) {
      return (
        <>
          <p>Tackle complex business cases that test your analytical and problem-solving abilities.</p>
          <ul>
            <li>Business strategy problems</li>
            <li>Market sizing questions</li>
            <li>Financial analysis scenarios</li>
            <li>Product management cases</li>
          </ul>
          <p>Coming soon: Interactive case frameworks and calculation tools.</p>
        </>
      );
    } else if (name.includes('mock')) {
      return (
        <>
          <p>Experience realistic interview simulations with our mock interview system.</p>
          <ul>
            <li>AI-powered interviewers</li>
            <li>Peer matching for practice sessions</li>
            <li>Timed interview environments</li>
            <li>Performance feedback</li>
          </ul>
          <p>Coming soon: Video recording and professional reviewer options.</p>
        </>
      );
    } else {
      return (
        <p>This feature will help you prepare for your interviews more effectively. Check back soon for more details as we continue to develop this part of the application.</p>
      );
    }
  };

  return (
    <div className="feature-page">
      <h2>{feature.name}</h2>
      <div className="feature-description">
        {getDetailedDescription(feature.name)}
      </div>

      <div className="navigation-buttons">
        <Link to="/" className="back-button">Back to Features</Link>
        {isInterviewQuestions && (
          <>
            <Link to="/user-questions" className="llm-button">My Questions</Link>
            <Link to="/llm-questions" className="llm-button">AI Questions</Link>
          </>
        )}
      </div>

      {/* ✅ Inserted button to create dummy template */}
      {isInterviewQuestions && (
        <div style={{ marginTop: "20px" }}>
          <button
            onClick={() => {
/*              fetch("http://localhost:5000/questions/insert_dummy")
                .then(res => res.json())
                .then(data => alert("Dummy template created! ID: " + data.id))
                .catch(err => {
                  console.error(err);
                  alert("Failed to create dummy template lol.");
                });*/
              fetch("http://localhost:5000/questions/insert_dummy")
              .then(async res => {
                if (!res.ok) {
                  const err = await res.json().catch(() => ({}));
                  throw new Error(err.message || "Unknown error from server");
                }
                return res.json();
              })
              .then(data => {
                alert("✅ Dummy template created! ID: " + data.id);
              })
              .catch(err => {
                console.error("❌ Error creating template:", err);
                alert("Failed to create dummy template: " + err.message);
              });
            }}
            style={{
              padding: "10px 20px",
              fontSize: "16px",
              backgroundColor: "#4CAF50",
              color: "white",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer"
            }}
          >
            ➕ Create Dummy Template
          </button>
        </div>
      )}

    </div>
  );
}

export default FeaturePage;