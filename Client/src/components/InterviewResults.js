import React from 'react';
import { Link } from 'react-router-dom';
import './Questions.css';
import './Interview.css';

/**
 * Decodes HTML entities from a string by leveraging the browser's DOM parser.
 */
const decodeHTMLEntities = (text) => {
    if (typeof text !== 'string' || !text) return '';
    const textArea = document.createElement('textarea');
    textArea.innerHTML = text;
    return textArea.value;
};

function InterviewResults({ session }) {
    if (!session) return null;

    // Add defensive checks to prevent errors if arrays are missing
    const questions = session.questions || [];
    const answers = session.answers || [];
    const totalQuestions = questions.length;
    const totalAnswered = answers.length;
    
    // Calculate correct answers based on the is_correct field from answers
    const correctAnswers = answers.filter(a => a.is_correct).length;
    const score = totalAnswered > 0 ? (correctAnswers / totalAnswered) * 100 : 0;

    const calculateDuration = () => {
        if (!session.started_at || !session.ended_at) return 'N/A';
        const start = new Date(session.started_at);
        const end = new Date(session.ended_at);
        const diffMs = end - start;
        if (isNaN(diffMs)) return 'N/A';

        const diffMins = Math.floor(diffMs / 60000);
        const diffSecs = Math.round((diffMs % 60000) / 1000);
        return `${diffMins} min ${diffSecs} sec`;
    };

    const getPerformanceLevel = (score) => {
        if (score >= 90) return { level: 'Excellent', color: '#4CAF50' };
        if (score >= 80) return { level: 'Good', color: '#8BC34A' };
        if (score >= 70) return { level: 'Fair', color: '#FFC107' };
        if (score >= 60) return { level: 'Needs Improvement', color: '#FF9800' };
        return { level: 'Poor', color: '#F44336' };
    };

    const performance = getPerformanceLevel(score);

    return (
        <div className="interview-results-container">
            <h2>🎯 Interview Completed!</h2>
            <h3>{session.template_name}</h3>

            <div className="results-summary">
                <div className="metric-card primary">
                    <h3>Overall Score</h3>
                    <p className="metric-value" style={{ color: performance.color }}>
                        {totalAnswered > 0 ? `${Math.round(score)}%` : 'N/A'}
                    </p>
                    <p className="metric-details">
                        {correctAnswers} out of {totalAnswered} correct
                        {totalAnswered < totalQuestions && ` (${totalQuestions - totalAnswered} skipped)`}
                    </p>
                    <div className="performance-badge" style={{ backgroundColor: performance.color }}>
                        {performance.level}
                    </div>
                </div>

                <div className="metric-card">
                    <h3>⏱️ Time Taken</h3>
                    <p className="metric-value">{calculateDuration()}</p>
                    <p className="metric-details">Total interview duration</p>
                </div>

                <div className="metric-card">
                    <h3>📊 Progress</h3>
                    <div className="progress-visualization">
                        <div className="progress-circle">
                            <div 
                                className="progress-fill" 
                                style={{ 
                                    background: `conic-gradient(${performance.color} 0deg ${score * 3.6}deg, #e0e0e0 ${score * 3.6}deg 360deg)` 
                                }}
                            >
                                <span className="progress-text">{Math.round(score)}%</span>
                            </div>
                        </div>
                    </div>
                    <p className="metric-details">Questions answered correctly</p>
                </div>
            </div>

            {/* Performance Insights */}
            <div className="performance-insights">
                <h3>📈 Performance Insights</h3>
                <div className="insights-grid">
                    {score >= 80 && (
                        <div className="insight-card positive">
                            <span className="insight-icon">🎉</span>
                            <p>Great job! You demonstrated strong knowledge in this area.</p>
                        </div>
                    )}
                    {score < 60 && (
                        <div className="insight-card needs-work">
                            <span className="insight-icon">📚</span>
                            <p>Consider reviewing the topics covered and practicing more questions.</p>
                        </div>
                    )}
                    {totalAnswered < totalQuestions && (
                        <div className="insight-card info">
                            <span className="insight-icon">⏰</span>
                            <p>You skipped {totalQuestions - totalAnswered} questions. Try to answer all questions for a complete assessment.</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Detailed Results */}
            <div className="detailed-results">
                <h3>📋 Question-by-Question Results</h3>
                <div className="results-list">
                    {questions.map((question, index) => {
                        const userAnswer = answers.find(a => a.question_index === index);
                        const isAnswered = userAnswer !== undefined;
                        const isCorrect = userAnswer?.is_correct || false;

                        return (
                            <div key={index} className={`result-item ${!isAnswered ? 'unanswered' : isCorrect ? 'correct' : 'incorrect'}`}>
                                <div className="result-header">
                                    <div className="question-info">
                                        <span className="question-number">Q{index + 1}</span>
                                        <span className="question-type">{question.question_type?.replace('_', ' ') || 'Question'}</span>
                                    </div>
                                    <div className="result-indicator">
                                        {!isAnswered ? (
                                            <span className="status skipped">⚪ Skipped</span>
                                        ) : isCorrect ? (
                                            <span className="status correct">✅ Correct</span>
                                        ) : (
                                            <span className="status incorrect">❌ Incorrect</span>
                                        )}
                                    </div>
                                </div>

                                <div className="result-content">
                                    <div className="question-text">
                                        <strong>Question:</strong> {decodeHTMLEntities(question.question_text)}
                                    </div>
                                    
                                    {isAnswered && (
                                        <div className="answer-section">
                                            <div className="user-answer">
                                                <strong>Your Answer:</strong> 
                                                <span className={isCorrect ? 'correct-answer' : 'incorrect-answer'}>
                                                    {userAnswer.answer || "No answer provided"}
                                                </span>
                                            </div>
                                            
                                            {userAnswer.correct_answer && (
                                                <div className="correct-answer">
                                                    <strong>Correct Answer:</strong> 
                                                    <span className="expected-answer">
                                                        {typeof userAnswer.correct_answer === 'boolean'
                                                            ? userAnswer.correct_answer.toString().charAt(0).toUpperCase() + userAnswer.correct_answer.toString().slice(1)
                                                            : decodeHTMLEntities(userAnswer.correct_answer)}
                                                    </span>
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {question.explanation && !isCorrect && (
                                        <div className="explanation">
                                            <strong>💡 Explanation:</strong> 
                                            <span className="explanation-text">
                                                {decodeHTMLEntities(question.explanation)}
                                            </span>
                                        </div>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Next Steps */}
            <div className="next-steps">
                <h3>🚀 What's Next?</h3>
                <div className="action-buttons">
                    <Link to="/templates" className="button primary">
                        Try Another Template
                    </Link>
                    <button 
                        onClick={() => window.print()} 
                        className="button tertiary"
                    >
                        Print Results
                    </button>
                </div>
            </div>
        </div>
    );
}

export default InterviewResults;

