import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

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

    if (isLoading) return <p>Loading interview session...</p>;
    if (error) return <p style={{ color: 'red' }}>Error: {error}</p>;
    if (!session) return <p>No session data found.</p>;

    const currentQuestionIndex = session.current_question_index;
    const totalQuestions = session.questions.length;
    const isInterviewOver = currentQuestionIndex >= totalQuestions;
    const currentQuestion = !isInterviewOver ? session.questions[currentQuestionIndex] : null;

    if (session.status === 'completed') {
        return (
            <div style={{ padding: '20px 40px', textAlign: 'center' }}>
                <h2>Interview Completed!</h2>
                <p>You have successfully completed the mock interview for "{session.template_name}".</p>
                <p>You can review your answers later (feature coming soon!).</p>
                <button onClick={() => navigate('/')}>Back to Home</button>
            </div>
        );
    }

    return (
        <div style={{ padding: '20px 40px' }}>
            <h2>Mock Interview: {session.template_name}</h2>
            <p>Status: {session.status}</p>
            <hr />

            {isInterviewOver ? (
                <div>
                    <h3>You've answered all questions!</h3>
                    <p>Click below to finish and save your session.</p>
                    <button onClick={handleFinishInterview} style={{ padding: '10px 20px', backgroundColor: 'green', color: 'white', border: 'none', borderRadius: '5px' }}>
                        Finish Interview
                    </button>
                </div>
            ) : (
                <div>
                    <h3>Question {currentQuestionIndex + 1} of {totalQuestions}</h3>
                    <p style={{ fontSize: '1.2em', fontWeight: 'bold' }}>{currentQuestion.question_text}</p>

                    <textarea
                        value={userAnswer}
                        onChange={(e) => setUserAnswer(e.target.value)}
                        placeholder="Type your answer here..."
                        rows="10"
                        style={{ width: '100%', boxSizing: 'border-box', padding: '10px', fontSize: '16px', marginTop: '10px' }}
                    />
                    <button onClick={handleSubmitAnswer} style={{ marginTop: '10px', padding: '10px 20px' }} >
                        Submit Answer & Next Question
                    </button>
                </div>
            )}
        </div>
    );
}

export default MockInterviewSession;