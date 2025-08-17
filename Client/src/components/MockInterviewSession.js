import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './Questions.css'; // Import the stylesheet
import InterviewSummary from './InterviewSummary';

function MockInterviewSession() {
    const { sessionId } = useParams();
    const navigate = useNavigate();
    const [session, setSession] = useState(null);
    const [userAnswer, setUserAnswer] = useState('');
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');

    const fetchSession = async () => {
        const token = localStorage.getItem('token');
        if (!token) {
            setError("Authentication required.");
            setIsLoading(false);
            return;
        }

        try {
            const response = await fetch(`/api/interviews/${sessionId}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Failed to fetch session data.');
            setSession(data.session);
        } catch (err) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchSession();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [sessionId]);

    const handleSubmitAnswer = async () => {
        setError('');
        // Add validation to ensure an answer is provided
        if (!userAnswer.trim()) {
            setError("Please select an option or provide an answer before submitting.");
            return;
        }

        const token = localStorage.getItem('token');
        try {
            const response = await fetch(`/api/interviews/${sessionId}/answer`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ answer: userAnswer })
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Failed to submit answer.');

            setUserAnswer(''); // Clear textarea
            fetchSession(); // Refresh session state to get next question
        } catch (err) {
            setError(err.message);
        }
    };

    const handleFinishInterview = async () => {
        setError('');
        const token = localStorage.getItem('token');
        try {
            const response = await fetch(`/api/interviews/${sessionId}/finish`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Failed to finish interview.');

            // Refresh to show completed state
            fetchSession();
        } catch (err) {
            setError(err.message);
        }
    };

    const renderQuestionInput = () => {
        if (!currentQuestion) return null;

        switch (currentQuestion.type) {
            case 'multiple_choice':
                return (
                    <div className="question-options-container">
                        {currentQuestion.options.map((option, index) => (
                            <div key={index} className="radio-option">
                                <input
                                    type="radio"
                                    id={`option-${index}`}
                                    name="mcq-options"
                                    value={option}
                                    checked={userAnswer === option}
                                    onChange={(e) => setUserAnswer(e.target.value)}
                                />
                                <label htmlFor={`option-${index}`}>{option}</label>
                            </div>
                        ))}
                    </div>
                );

            case 'true_false':
                return (
                    <div className="question-options-container">
                        <div className="radio-option">
                            <input
                                type="radio"
                                id="option-true"
                                name="tf-options"
                                value="true"
                                checked={userAnswer === 'true'}
                                onChange={(e) => setUserAnswer(e.target.value)}
                            />
                            <label htmlFor="option-true">True</label>
                        </div>
                        <div className="radio-option">
                            <input
                                type="radio"
                                id="option-false"
                                name="tf-options"
                                value="false"
                                checked={userAnswer === 'false'}
                                onChange={(e) => setUserAnswer(e.target.value)}
                            />
                            <label htmlFor="option-false">False</label>
                        </div>
                    </div>
                );

            default: // Handles 'open_ended', 'short_answer', 'coding'
                return (
                    <textarea
                        value={userAnswer}
                        onChange={(e) => setUserAnswer(e.target.value)}
                        placeholder="Type your answer here..."
                        rows="10"
                        className="answer-textarea"
                    />
                );
        }
    };

    if (isLoading) return <p>Loading interview session...</p>;
    if (error) return <p style={{ color: 'red' }}>Error: {error}</p>;
    if (!session) return <p>No session data found.</p>;

    const currentQuestionIndex = session.current_question_index;
    const totalQuestions = session.questions.length;
    const isInterviewOver = currentQuestionIndex >= totalQuestions;
    const currentQuestion = !isInterviewOver ? session.questions[currentQuestionIndex] : null;

    if (session.status === 'completed') {
        return (
            <div className="mock-interview-container">
                <InterviewSummary session={session} />
                <div className="summary-actions">
                    <button className="action-btn" onClick={() => navigate('/templates')}>
                        Back to Templates
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="mock-interview-container">
            <div className="interview-header">
                <h2>Mock Interview: {session.template_name}</h2>
                <p className="interview-progress">Question {Math.min(currentQuestionIndex + 1, totalQuestions)} of {totalQuestions}</p>
            </div>
            <hr />

            {isInterviewOver ? (
                <div className="interview-completed-container">
                    <h3>You've answered all questions!</h3>
                    <p>Click below to finish and save your session.</p>
                    <button onClick={handleFinishInterview} className="action-btn finish-btn">
                        Finish Interview
                    </button>
                </div>
            ) : (
                <div className="question-card-interview">
                    <p className="question-text-interview">{currentQuestion.question_text}</p>
                    {renderQuestionInput()}
                    <button onClick={handleSubmitAnswer} className="action-btn" disabled={!userAnswer.trim()}>
                        Submit Answer & Next Question
                    </button>
                </div>
            )}
        </div>
    );
}

export default MockInterviewSession;