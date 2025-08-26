from flask import Blueprint, request, jsonify, current_app
from bson import ObjectId
from datetime import datetime
from .auth import token_required
from .llm_service import LLMService
from .database import interview_sessions_collection, evaluations_collection, templates_collection
import json

evaluations_bp = Blueprint('evaluations_bp', __name__)

@evaluations_bp.route('/api/evaluations/sessions', methods=['GET'])
@token_required
def get_completed_sessions(current_user):
    """
    Get list of completed interview sessions available for evaluation
    Supports filtering by subject, user, graded status, etc.
    """
    # Get query parameters for filtering
    subject = request.args.get('subject')
    sub_subject = request.args.get('sub_subject')
    user_filter = request.args.get('user')
    graded_only = request.args.get('graded') == 'true'
    ungraded_only = request.args.get('ungraded') == 'true'
    limit = min(int(request.args.get('limit', 20)), 100)
    skip = int(request.args.get('skip', 0))
    
    try:
        # Build filter query
        query = {"status": "completed"}
        
        # Get sessions and populate with template info
        
        # Find completed sessions
        sessions_cursor = interview_sessions_collection.find(query).sort("ended_at", -1).skip(skip).limit(limit)
        sessions = list(sessions_cursor)
        
        # Populate with template and evaluation info
        enriched_sessions = []
        for session in sessions:
            # Get template info
            template = templates_collection.find_one({"_id": session.get("template_id")})
            if template:
                # Apply subject filters
                if subject and template.get("category", "").lower() != subject.lower():
                    continue
                if sub_subject and template.get("sub_category", "").lower() != sub_subject.lower():
                    continue
                
                # Check if already evaluated
                evaluation = evaluations_collection.find_one({"session_id": session["_id"]})
                is_graded = evaluation is not None
                
                # Apply graded/ungraded filters
                if graded_only and not is_graded:
                    continue
                if ungraded_only and is_graded:
                    continue
                
                # Apply user filter
                if user_filter and session.get("user_id") != user_filter:
                    continue
                
                # Build response object
                session_info = {
                    "session_id": str(session["_id"]),
                    "user_id": session.get("user_id"),
                    "template_name": session.get("template_name"),
                    "template_category": template.get("category"),
                    "template_sub_category": template.get("sub_category", ""),
                    "difficulty": template.get("difficulty"),
                    "completed_at": session.get("ended_at").isoformat() if session.get("ended_at") else None,
                    "total_questions": len(session.get("answers", [])),
                    "is_graded": is_graded,
                    "evaluation_id": str(evaluation["_id"]) if evaluation else None,
                    "score": evaluation.get("total_score") if evaluation else None
                }
                enriched_sessions.append(session_info)
        
        return jsonify({
            "sessions": enriched_sessions,
            "total_count": len(enriched_sessions),
            "has_more": len(enriched_sessions) == limit
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching completed sessions: {e}")
        return jsonify({"error": "Failed to fetch sessions"}), 500

@evaluations_bp.route('/api/evaluations/session/<session_id>', methods=['GET'])
@token_required
def get_session_for_evaluation(current_user, session_id):
    """
    Get detailed interview session data for evaluation
    """
    try:
        session_oid = ObjectId(session_id)
    except Exception:
        return jsonify({"error": "Invalid session ID format"}), 400
    
    try:
        sessions_collection = interview_sessions_collection
        templates_collection = templates_collection
        
        # Get session details
        session = sessions_collection.find_one({"_id": session_oid, "status": "completed"})
        if not session:
            return jsonify({"error": "Completed session not found"}), 404
        
        # Get template details
        template = templates_collection.find_one({"_id": session.get("template_id")})
        if not template:
            return jsonify({"error": "Template not found"}), 404
        
        # Check if already evaluated
        evaluation = evaluations_collection.find_one({"session_id": session_oid})
        
        # Prepare response
        evaluation_data = {
            "session_id": str(session["_id"]),
            "user_id": session.get("user_id"),
            "template_name": session.get("template_name"),
            "template_category": template.get("category"),
            "difficulty": template.get("difficulty"),
            "completed_at": session.get("ended_at").isoformat() if session.get("ended_at") else None,
            "answers": [],
            "is_already_graded": evaluation is not None,
            "existing_evaluation": str(evaluation["_id"]) if evaluation else None
        }
        
        # Process answers with question details
        answers = session.get("answers", [])
        questions = session.get("questions", [])
        
        for i, answer in enumerate(answers):
            question_data = questions[i] if i < len(questions) else {}
            
            answer_info = {
                "question_index": answer.get("question_index", i),
                "question_text": answer.get("question_text", question_data.get("question_text")),
                "question_type": question_data.get("question_type"),
                "user_answer": answer.get("answer"),
                "correct_answer": answer.get("correct_answer"),
                "is_correct": answer.get("is_correct", False),
                "submitted_at": answer.get("submitted_at").isoformat() if answer.get("submitted_at") else None,
                "hints": question_data.get("hints", []),
                "options": question_data.get("options", []) if question_data.get("question_type") == "multiple_choice" else None
            }
            evaluation_data["answers"].append(answer_info)
        
        return jsonify(evaluation_data), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching session for evaluation: {e}")
        return jsonify({"error": "Failed to fetch session details"}), 500

@evaluations_bp.route('/api/evaluations/evaluate', methods=['POST'])
@token_required
def evaluate_session(current_user):
    """
    Submit evaluation/grading for an interview session
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400
    
    required_fields = ["session_id", "scores", "total_score", "feedback"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400
    
    try:
        session_id = ObjectId(data["session_id"])
    except Exception:
        return jsonify({"error": "Invalid session ID format"}), 400
    
    try:
        # Verify session exists and is completed
        session = interview_sessions_collection.find_one({"_id": session_id, "status": "completed"})
        if not session:
            return jsonify({"error": "Completed session not found"}), 404
        
        # Check if already evaluated
        existing_evaluation = evaluations_collection.find_one({"session_id": session_id})
        if existing_evaluation:
            return jsonify({"error": "Session already evaluated"}), 400
        
        # Validate scores data
        scores = data["scores"]
        if not isinstance(scores, list):
            return jsonify({"error": "Scores must be an array"}), 400
        
        # Create evaluation document
        evaluation_doc = {
            "session_id": session_id,
            "evaluator_user_id": current_user["user_id"],
            "evaluated_user_id": session.get("user_id"),
            "template_id": session.get("template_id"),
            "scores": scores,
            "total_score": data["total_score"],
            "feedback": data["feedback"],
            "evaluation_method": data.get("evaluation_method", "manual"),  # manual, llm, self
            "created_at": datetime.utcnow(),
            "evaluation_criteria": data.get("evaluation_criteria", {}),
            "recommendations": data.get("recommendations", [])
        }
        
        # Insert evaluation
        result = evaluations_collection.insert_one(evaluation_doc)
        evaluation_id = str(result.inserted_id)
        
        return jsonify({
            "message": "Evaluation submitted successfully",
            "evaluation_id": evaluation_id,
            "total_score": data["total_score"]
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error evaluating session: {e}")
        return jsonify({"error": "Failed to submit evaluation"}), 500

@evaluations_bp.route('/api/evaluations/llm-evaluate', methods=['POST'])
@token_required
def llm_evaluate_session(current_user):
    """
    Use LLM service to automatically evaluate an interview session
    """
    data = request.get_json()
    if not data or "session_id" not in data:
        return jsonify({"error": "Session ID is required"}), 400
    
    try:
        session_id = ObjectId(data["session_id"])
    except Exception:
        return jsonify({"error": "Invalid session ID format"}), 400
    
    try:
        # Get session for evaluation
        session = interview_sessions_collection.find_one({"_id": session_id, "status": "completed"})
        if not session:
            return jsonify({"error": "Completed session not found"}), 404
        
        # Check if LLM service is available
        if not LLMService.is_available():
            return jsonify({"error": "LLM service is not available"}), 503
        
        # Prepare data for LLM evaluation
        answers = session.get("answers", [])
        template_name = session.get("template_name", "Interview")
        
        # Build evaluation prompt
        evaluation_prompt = f"""
Please evaluate this interview session for "{template_name}".

Instructions:
1. Score each answer on a scale of 0-100
2. Provide specific feedback for each answer
3. Give an overall score and general feedback
4. Suggest areas for improvement

Questions and Answers:
"""
        
        for i, answer in enumerate(answers):
            evaluation_prompt += f"""
Question {i+1}: {answer.get('question_text', 'N/A')}
Correct Answer: {answer.get('correct_answer', 'N/A')}
Student Answer: {answer.get('answer', 'N/A')}
Auto-marked Correct: {answer.get('is_correct', False)}

"""
        
        evaluation_prompt += """
Please respond in the following JSON format:
{
    "scores": [
        {"question_index": 0, "score": 85, "feedback": "Good understanding but missing key details"},
        ...
    ],
    "total_score": 78,
    "overall_feedback": "Strong performance overall...",
    "recommendations": ["Focus on...", "Practice more..."]
}
"""
        
        # Get LLM evaluation
        llm_response = LLMService.generate_response(evaluation_prompt)
        if not llm_response:
            return jsonify({"error": "Failed to get LLM evaluation"}), 500
        
        try:
            # Parse LLM response as JSON
            evaluation_result = json.loads(llm_response)
            
            # Create evaluation document
            evaluation_doc = {
                "session_id": session_id,
                "evaluator_user_id": "llm_service",
                "evaluated_user_id": session.get("user_id"),
                "template_id": session.get("template_id"),
                "scores": evaluation_result.get("scores", []),
                "total_score": evaluation_result.get("total_score", 0),
                "feedback": evaluation_result.get("overall_feedback", ""),
                "evaluation_method": "llm",
                "created_at": datetime.utcnow(),
                "recommendations": evaluation_result.get("recommendations", []),
                "llm_raw_response": llm_response
            }
            
            # Check if already evaluated
            existing_evaluation = evaluations_collection.find_one({"session_id": session_id})
            if existing_evaluation:
                return jsonify({"error": "Session already evaluated"}), 400
            
            # Insert evaluation
            result = evaluations_collection.insert_one(evaluation_doc)
            evaluation_id = str(result.inserted_id)
            
            return jsonify({
                "message": "LLM evaluation completed successfully",
                "evaluation_id": evaluation_id,
                "evaluation": {
                    "total_score": evaluation_result.get("total_score"),
                    "overall_feedback": evaluation_result.get("overall_feedback"),
                    "recommendations": evaluation_result.get("recommendations", []),
                    "detailed_scores": evaluation_result.get("scores", [])
                }
            }), 201
            
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid LLM response format"}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error in LLM evaluation: {e}")
        return jsonify({"error": "Failed to complete LLM evaluation"}), 500

@evaluations_bp.route('/api/evaluations/<evaluation_id>', methods=['GET'])
@token_required
def get_evaluation_details(current_user, evaluation_id):
    """
    Get detailed evaluation results
    """
    try:
        evaluation_oid = ObjectId(evaluation_id)
    except Exception:
        return jsonify({"error": "Invalid evaluation ID format"}), 400
    
    try:
        evaluation = evaluations_collection.find_one({"_id": evaluation_oid})
        if not evaluation:
            return jsonify({"error": "Evaluation not found"}), 404
        
        # Get session and template details
        session = interview_sessions_collection.find_one({"_id": evaluation["session_id"]})
        template = templates_collection.find_one({"_id": evaluation["template_id"]}) if session else None
        
        # Prepare response
        evaluation_details = {
            "evaluation_id": str(evaluation["_id"]),
            "session_id": str(evaluation["session_id"]),
            "evaluator_user_id": evaluation.get("evaluator_user_id"),
            "evaluated_user_id": evaluation.get("evaluated_user_id"),
            "template_name": session.get("template_name") if session else "Unknown",
            "template_category": template.get("category") if template else "Unknown",
            "total_score": evaluation.get("total_score"),
            "scores": evaluation.get("scores", []),
            "feedback": evaluation.get("feedback"),
            "recommendations": evaluation.get("recommendations", []),
            "evaluation_method": evaluation.get("evaluation_method", "manual"),
            "created_at": evaluation.get("created_at").isoformat() if evaluation.get("created_at") else None,
            "evaluation_criteria": evaluation.get("evaluation_criteria", {})
        }
        
        return jsonify(evaluation_details), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching evaluation details: {e}")
        return jsonify({"error": "Failed to fetch evaluation details"}), 500

@evaluations_bp.route('/api/evaluations/export/<session_id>', methods=['GET'])
@token_required
def export_evaluation_results(current_user, session_id):
    """
    Export evaluation results in various formats (JSON by default, could extend to PDF)
    """
    try:
        session_oid = ObjectId(session_id)
    except Exception:
        return jsonify({"error": "Invalid session ID format"}), 400
    
    format_type = request.args.get('format', 'json').lower()
    
    try:
        # Get session, evaluation, and template
        session = interview_sessions_collection.find_one({"_id": session_oid})
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        evaluation = evaluations_collection.find_one({"session_id": session_oid})
        if not evaluation:
            return jsonify({"error": "Evaluation not found"}), 404
        
        template = templates_collection.find_one({"_id": session["template_id"]})
        
        # Build comprehensive export data
        export_data = {
            "evaluation_summary": {
                "session_id": str(session["_id"]),
                "evaluation_id": str(evaluation["_id"]),
                "user_id": session.get("user_id"),
                "template_name": session.get("template_name"),
                "template_category": template.get("category") if template else "Unknown",
                "difficulty": template.get("difficulty") if template else "Unknown",
                "completed_at": session.get("ended_at").isoformat() if session.get("ended_at") else None,
                "evaluated_at": evaluation.get("created_at").isoformat() if evaluation.get("created_at") else None,
                "total_score": evaluation.get("total_score"),
                "evaluation_method": evaluation.get("evaluation_method")
            },
            "detailed_results": {
                "overall_feedback": evaluation.get("feedback"),
                "recommendations": evaluation.get("recommendations", []),
                "question_by_question": []
            }
        }
        
        # Add question-by-question analysis
        answers = session.get("answers", [])
        scores = evaluation.get("scores", [])
        
        for i, answer in enumerate(answers):
            score_data = next((s for s in scores if s.get("question_index") == i), {})
            
            question_result = {
                "question_number": i + 1,
                "question_text": answer.get("question_text"),
                "user_answer": answer.get("answer"),
                "correct_answer": answer.get("correct_answer"),
                "auto_marked_correct": answer.get("is_correct", False),
                "evaluator_score": score_data.get("score"),
                "evaluator_feedback": score_data.get("feedback")
            }
            export_data["detailed_results"]["question_by_question"].append(question_result)
        
        # Add statistics
        if scores:
            individual_scores = [s.get("score", 0) for s in scores if isinstance(s.get("score"), (int, float))]
            if individual_scores:
                export_data["statistics"] = {
                    "average_question_score": sum(individual_scores) / len(individual_scores),
                    "highest_question_score": max(individual_scores),
                    "lowest_question_score": min(individual_scores),
                    "questions_above_80": len([s for s in individual_scores if s >= 80]),
                    "total_questions": len(individual_scores)
                }
        
        if format_type == 'json':
            return jsonify(export_data), 200
        else:
            return jsonify({"error": f"Unsupported export format: {format_type}"}), 400
            
    except Exception as e:
        current_app.logger.error(f"Error exporting evaluation results: {e}")
        return jsonify({"error": "Failed to export results"}), 500

@evaluations_bp.route('/api/evaluations/stats/template/<template_id>', methods=['GET'])
@token_required
def get_template_evaluation_stats(current_user, template_id):
    """
    Get evaluation statistics for a specific template
    """
    try:
        # Find template by public template_id
        template = templates_collection.find_one({"template_id": template_id})
        if not template:
            return jsonify({"error": "Template not found"}), 404
        
        template_oid = template["_id"]
        
        # Get all evaluations for this template
        evaluations = list(evaluations_collection.find({"template_id": template_oid}))
        
        if not evaluations:
            return jsonify({
                "template_id": template_id,
                "template_name": template.get("template_name"),
                "stats": {
                    "total_evaluations": 0,
                    "average_score": 0,
                    "usage_count": 0
                }
            }), 200
        
        # Calculate statistics
        total_scores = [e.get("total_score", 0) for e in evaluations]
        average_score = sum(total_scores) / len(total_scores) if total_scores else 0
        
        # Get usage stats from sessions
        total_sessions = interview_sessions_collection.count_documents({"template_id": template_oid})
        completed_sessions = interview_sessions_collection.count_documents({
            "template_id": template_oid, 
            "status": "completed"
        })
        
        stats = {
            "template_id": template_id,
            "template_name": template.get("template_name"),
            "template_category": template.get("category"),
            "stats": {
                "total_evaluations": len(evaluations),
                "average_score": round(average_score, 2),
                "highest_score": max(total_scores) if total_scores else 0,
                "lowest_score": min(total_scores) if total_scores else 0,
                "usage_count": total_sessions,
                "completion_rate": round((completed_sessions / total_sessions * 100), 2) if total_sessions > 0 else 0,
                "evaluation_rate": round((len(evaluations) / completed_sessions * 100), 2) if completed_sessions > 0 else 0
            }
        }
        
        return jsonify(stats), 200
        
    except Exception as e:
        current_app.logger.error(f"Error fetching template stats: {e}")
        return jsonify({"error": "Failed to fetch template statistics"}), 500