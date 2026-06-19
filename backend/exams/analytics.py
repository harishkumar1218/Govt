from django.db.models import Sum, Count, Avg, F
from datetime import timedelta
from django.utils import timezone
from .models import QuizSubmission, QuizQuestion

def calculate_submission_metrics(submission):
    """
    Given a QuizSubmission, calculate deep metrics.
    """
    quiz = submission.quiz
    questions = quiz.questions.all()
    
    total_questions = questions.count()
    max_score = total_questions * quiz.marks_per_question if total_questions > 0 else 100.0
    
    attempted = 0
    correct = 0
    incorrect = 0
    
    user_answers = submission.answers or {}
    
    detailed_questions = []
    
    for q in questions:
        q_id_str = str(q.id)
        user_ans = user_answers.get(q_id_str)
        is_correct = False
        marks_awarded = 0.0
        
        if user_ans:
            attempted += 1
            if user_ans == q.correct_answer:
                correct += 1
                is_correct = True
                marks_awarded = quiz.marks_per_question
            else:
                incorrect += 1
                marks_awarded = -quiz.negative_marking
                
        detailed_questions.append({
            "id": q.id,
            "order": q.order,
            "text": q.text,
            "options": q.options,
            "user_answer": user_ans,
            "correct_answer": q.correct_answer,
            "is_correct": is_correct,
            "marks_awarded": marks_awarded,
            "explanation": q.explanation,
            "subject": q.subject,
            "difficulty": q.difficulty
        })
        
    skipped = total_questions - attempted
    accuracy = (correct / attempted * 100) if attempted > 0 else 0.0
    percentage = (submission.score / max_score * 100) if max_score > 0 else 0.0
    avg_time_per_question = (submission.time_taken_seconds / total_questions) if total_questions > 0 else 0
    
    # Calculate rank for this specific quiz
    better_submissions = QuizSubmission.objects.filter(quiz=quiz, score__gt=submission.score).count()
    rank = better_submissions + 1
    total_participants = QuizSubmission.objects.filter(quiz=quiz).count()
    percentile = ((total_participants - rank) / total_participants * 100) if total_participants > 1 else 100.0
    
    return {
        "submission_id": submission.id,
        "quiz_id": quiz.id,
        "track_slug": quiz.track.slug if quiz.track else "general",
        "track_title": quiz.track.title if quiz.track else "General",
        "quiz_topic": quiz.topic,
        "stage_name": quiz.stage_name,
        "quiz_date": quiz.date,
        "submitted_at": submission.submitted_at,
        "score": round(submission.score, 2),
        "max_score": round(max_score, 2),
        "percentage": round(percentage, 2),
        "total_questions": total_questions,
        "attempted": attempted,
        "correct": correct,
        "incorrect": incorrect,
        "skipped": skipped,
        "accuracy": round(accuracy, 2),
        "time_taken_seconds": submission.time_taken_seconds,
        "average_time_per_question": round(avg_time_per_question, 2),
        "rank": rank,
        "total_participants": total_participants,
        "percentile": round(percentile, 2),
        "detailed_questions": detailed_questions
    }

def get_user_analytics(user, track_slug=None, days=None):
    """
    Get aggregated analytics for a user.
    """
    query = QuizSubmission.objects.filter(user=user).select_related('quiz', 'quiz__track')
    
    if track_slug and track_slug != 'all':
        query = query.filter(quiz__track__slug=track_slug)
        
    if days and days != 'all':
        try:
            days_int = int(days.replace('d', ''))
            start_date = timezone.now() - timedelta(days=days_int)
            query = query.filter(submitted_at__gte=start_date)
        except ValueError:
            pass
            
    submissions = list(query.order_by('submitted_at'))
    
    total_tests = len(submissions)
    if total_tests == 0:
        return {"total_tests": 0}
        
    total_score = 0
    total_max_score = 0
    total_time = 0
    total_questions = 0
    total_attempted = 0
    total_correct = 0
    
    best_score_pct = -100
    worst_score_pct = 200
    
    trend_scores = []
    trend_accuracies = []
    trend_dates = []
    
    for sub in submissions:
        metrics = calculate_submission_metrics(sub)
        
        total_score += sub.score
        total_max_score += metrics['max_score']
        total_time += sub.time_taken_seconds
        total_questions += metrics['total_questions']
        total_attempted += metrics['attempted']
        total_correct += metrics['correct']
        
        pct = metrics['percentage']
        if pct > best_score_pct: best_score_pct = pct
        if pct < worst_score_pct: worst_score_pct = pct
        
        trend_scores.append(round(pct, 2))
        trend_accuracies.append(metrics['accuracy'])
        trend_dates.append(sub.submitted_at.strftime('%Y-%m-%d'))
        
    avg_score_pct = (total_score / total_max_score * 100) if total_max_score > 0 else 0
    avg_accuracy = (total_correct / total_attempted * 100) if total_attempted > 0 else 0
    avg_time_per_q = (total_time / total_questions) if total_questions > 0 else 0
    
    # Calculate streak (consecutive days with at least one submission)
    streak = 0
    if submissions:
        dates = sorted(list(set([s.submitted_at.date() for s in submissions])), reverse=True)
        today = timezone.now().date()
        
        current_date = today
        if dates and dates[0] == today:
            streak = 1
            idx = 1
        elif dates and dates[0] == today - timedelta(days=1):
            streak = 1
            current_date = today - timedelta(days=1)
            idx = 1
        else:
            idx = 0
            
        while idx < len(dates) and streak > 0:
            if dates[idx] == current_date - timedelta(days=1):
                streak += 1
                current_date = dates[idx]
                idx += 1
            else:
                break
                
    # Readiness score (0-100)
    # 40% avg score, 30% accuracy, 30% consistency (streak/frequency)
    readiness = (avg_score_pct * 0.4) + (avg_accuracy * 0.3) + (min(streak, 7) / 7 * 30)
    
    # Risk Profile
    risk_profile = "Balanced"
    if avg_accuracy < 50 and avg_time_per_q < 30:
        risk_profile = "Fast but Careless"
    elif avg_accuracy > 80 and avg_time_per_q > 90:
        risk_profile = "Slow but Accurate"
    elif avg_accuracy < 40 and total_attempted > (total_questions * 0.8):
        risk_profile = "Too Many Guesses"
        
    # Overall Rank
    user_total_score = QuizSubmission.objects.filter(user=user).aggregate(total=Sum('score'))['total'] or 0
    rank = QuizSubmission.objects.values('user').annotate(total=Sum('score')).filter(total__gt=user_total_score).count() + 1
    
    return {
        "total_tests": total_tests,
        "avg_score_percentage": round(avg_score_pct, 2),
        "best_score_percentage": round(best_score_pct, 2),
        "worst_score_percentage": round(worst_score_pct, 2),
        "avg_accuracy": round(avg_accuracy, 2),
        "avg_time_per_question": round(avg_time_per_q, 2),
        "total_time_spent_seconds": total_time,
        "streak": streak,
        "readiness_score": round(readiness, 2),
        "risk_profile": risk_profile,
        "rank": rank,
        "trend_scores": trend_scores,
        "trend_accuracies": trend_accuracies,
        "trend_dates": trend_dates
    }
