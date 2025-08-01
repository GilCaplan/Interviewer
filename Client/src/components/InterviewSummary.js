import React from 'react';
import './Questions.css'; // Reuse our existing stylesheet

/**
 * Decodes HTML entities from a string by leveraging the browser's DOM parser.
 * This is a safe way to convert entities like '&amp;' or '&#x27;' back to their character equivalents.
 * @param {string | any} text The string containing HTML entities, or any other type.
 * @returns {string} The decoded string.
 */
const decodeHTMLEntities = (text) => {
    if (typeof text !== 'string') return text;
    const textArea = document.createElement('textarea');
    textArea.innerHTML = text;
    return textArea.value;
};

function InterviewSummary({ session }) {
    if (!session) return null;

    const correctAnswers = session.answers.filter(a => a.is_correct).length;
    const totalAnswered = session.answers.length;
    const score = totalAnswered > 0 ? (correctAnswers / totalAnswered) * 100 : 0;

    const calculateDuration = () => {
        if (!session.started_at || !session.ended_at) return 'N/A';
        // Handle MongoDB's date format from the server
        const start = new Date(session.started_at.$date || session.started_at);
        const end = new Date(session.ended_at.$date || session.ended_at);
        const diffMs = end - start;
        if (isNaN(diffMs)) return 'N/A';

        const diffMins = Math.floor(diffMs / 60000);
        const diffSecs = Math.round((diffMs % 60000) / 1000);
        return `${diffMins} min ${diffSecs} sec`;
    };

    return (
        <div className="interview-summary-container">
            <h2>Interview Results: {session.template_name}</h2>

            <div className="summary-metrics">
                <div className="metric-card">
                    <h3>Score</h3>
                    <p className="metric-value">{Math.round(score)}%</p>
                    <p className="metric-details">({correctAnswers} / {totalAnswered} correct)</p>
                </div>
                <div className="metric-card">
                    <h3>Time Taken</h3>
                    <p className="metric-value">{calculateDuration()}</p>
                    <p className="metric-details">Total duration of the session</p>
                </div>
                <div className="metric-card">
                    <h3>Performance</h3>
                    <div className="performance-chart">
                        <div
                            className="chart-bar correct"
                            style={{ width: `${score}%` }}
                            title={`${correctAnswers} Correct`}
                        ></div>
                    </div>
                    <p className="metric-details">Correct vs. Incorrect Answers</p>
                </div>
            </div>

            <h3>Results Breakdown</h3>
            <ul className="results-breakdown-list">
                {session.questions.slice(0, totalAnswered).map((question, index) => {
                    const userAnswer = session.answers.find(a => a.question_index === index);
                    if (!userAnswer) return null;

                    const isCorrect = userAnswer.is_correct;
                    const displayCorrectAnswer = typeof userAnswer.correct_answer === 'boolean'
                        ? userAnswer.correct_answer.toString().charAt(0).toUpperCase() + userAnswer.correct_answer.toString().slice(1)
                        : decodeHTMLEntities(userAnswer.correct_answer);

                    return (
                        <li key={index} className={`result-item ${isCorrect ? 'correct' : 'incorrect'}`}>
                            <div className="result-header">
                                <strong>Q{index + 1}: {question.question_text}</strong>
                                <span className="result-indicator">{isCorrect ? '✔ Correct' : '✖ Incorrect'}</span>
                            </div>
                            <div className="result-body">
                                <p><strong>Your Answer:</strong> {userAnswer.answer || "No answer provided"}</p>
                                {!isCorrect && (
                                    <>
                                        <p><strong>Correct Answer:</strong> {displayCorrectAnswer}</p>
                                        {question.explanation && (
                                            <p className="explanation-text">
                                                <strong>Explanation:</strong> {decodeHTMLEntities(question.explanation)}
                                            </p>
                                        )}
                                    </>
                                )}
                            </div>
                        </li>
                    );
                })}
            </ul>
        </div>
    );
}

export default InterviewSummary;