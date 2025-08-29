import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';

function SessionRoom() {
  const { sessionId } = useParams();
  const [sessionData, setSessionData] = useState(null);

  useEffect(() => {
    fetch(`http://localhost:5001/sessions/${sessionId}`)
      .then(res => res.json())
      .then(data => setSessionData(data))
      .catch(err => console.error("Failed to load session", err));
  }, [sessionId]);

  if (!sessionData) {
    return <p>Loading session...</p>;
  }

  return (
    <div style={{ padding: '20px 40px' }}>
      <h2>Interview Session: {sessionId}</h2>
      <p><strong>Started by:</strong> {sessionData.host || 'Unknown'}</p>

      <h3>Questions:</h3>
      <ul>
        {sessionData.template.questions.map((q, index) => (
          <li key={index} style={{ marginBottom: '20px' }}>
            <p><strong>Q{index + 1}:</strong> {q.question_text}</p>
            <ul>
              {q.choices.map((choice, i) => (
                <li key={i}>{choice}</li>
              ))}
            </ul>
            {/* You can later add an input/textarea for answering */}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default SessionRoom;