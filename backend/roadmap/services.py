import time
import datetime
from pymongo import MongoClient
from django.conf import settings
from django.utils import timezone
from collections import defaultdict
from roadmap.models import UserRoadmapProgress
from exams.models import QuizSubmission, Quiz

# Circuit breaker lockout variables
_mongo_client = None
_mongo_failed_until = 0.0

# 1. Seed Templates Definition (loaded from config/roadmap_templates.json)
from core.config_loader import load_roadmap_templates, load_platform_config

def get_seed_templates():
    return load_roadmap_templates()

# 2. Database Connection Helper with circuit breaker
def get_roadmap_collection():
    global _mongo_client, _mongo_failed_until
    current_time = time.time()
    
    if current_time < _mongo_failed_until:
        raise Exception("MongoDB Atlas connection is in lockout period due to previous connection failure.")
        
    try:
        if _mongo_client is None:
            # Short timeout to fail fast
            _mongo_client = MongoClient(settings.MONGO_DB_URI, serverSelectionTimeoutMS=1000)
        
        # Ping to force server selection check
        _mongo_client.admin.command('ping')
        
        db = _mongo_client['govt-cluster']
        col = db['roadmap_templates']
        
        # Ensure indexes are present
        col.create_index("track_slug")
        col.create_index([("track_slug", 1), ("id", 1)], unique=True)
        
        return col
    except Exception as e:
        # Activate circuit breaker lockout for 60 seconds
        _mongo_failed_until = time.time() + 60.0
        print(f"[Warning] MongoDB connection failed in roadmap service ({e}). Lockout activated. Falling back to local data.")
        raise e

# 3. Seeding logic
def seed_roadmap_templates():
    try:
        col = get_roadmap_collection()
        # Check if already seeded
        if col.count_documents({}) == 0:
            now = datetime.datetime.utcnow()
            documents = []
            for item in get_seed_templates():
                doc = item.copy()
                doc['updated_at'] = now
                documents.append(doc)
            col.insert_many(documents)
            print(f"Successfully seeded {len(documents)} roadmap templates in MongoDB.")
            return True
        return False
    except Exception as e:
        print(f"[Warning] Seeding roadmap templates failed: {e}")
        return False

# 4. Retrieval and Merging Service
def get_roadmap_for_track(user, track_slug):
    # Try seeding if needed (noop if already seeded)
    seed_roadmap_templates()
    
    templates = []
    use_fallback = False
    
    try:
        col = get_roadmap_collection()
        templates = list(col.find({"track_slug": track_slug, "is_active": True}))
        # Sort templates by order
        templates.sort(key=lambda x: x.get('order', 99))
        
        # Clean MongoDB specific fields
        for t in templates:
            t['id'] = t.get('id', str(t.get('_id')))
            if '_id' in t:
                del t['_id']
            if 'updated_at' in t:
                t['updated_at'] = str(t['updated_at'])
    except Exception:
        use_fallback = True
        
    if use_fallback or not templates:
        # Load from get_seed_templates() fallback
        templates = [t.copy() for t in get_seed_templates() if t['track_slug'] == track_slug and t['is_active']]
        templates.sort(key=lambda x: x.get('order', 99))
        
    if not templates:
        return None  # Invalid track or no items found

    # Fetch user's completion progress from SQLite
    progress_qs = UserRoadmapProgress.objects.filter(user=user, track_slug=track_slug)
    progress_dict = {p.roadmap_item_id: p for p in progress_qs}
    
    # Merge template with progress status
    completed_count = 0
    total_count = len(templates)
    
    merged_items = []
    for t in templates:
        item_id = t['id']
        progress = progress_dict.get(item_id)
        
        status = 'not_started'
        completed_at = None
        
        if progress:
            status = progress.status
            completed_at = progress.completed_at.isoformat() if progress.completed_at else None
            if status == 'completed':
                completed_count += 1
                
        merged_items.append({
            **t,
            'status': status,
            'completed_at': completed_at
        })
        
    # Calculate progress percentages
    progress_percentage = MathRound(completed_count, total_count)
    
    # Run recommendation engine
    recommendation = calculate_recommendation(user, track_slug, merged_items)
    
    # Get mock test statistics
    mock_test_avg = calculate_mock_test_average(user, track_slug)
    weekly_streak = calculate_weekly_streak(user)

    # Group into phases for frontend expectation
    grouped_phases_dict = defaultdict(list)
    for item in merged_items:
        phase_name = item.get('phase', 'Phase 1')
        grouped_phases_dict[phase_name].append({
            'id': item['id'],
            'title': item['title'],
            'type': item['type'],
            'status': item['status'],
            'estimatedHours': item.get('estimated_hours', item.get('estimated_days', 1)),
            'weightage': item.get('weightage', 'Medium'),
            'description': item['description'],
            'resources': item.get('resources', []),
            'prerequisites': item.get('prerequisites', []),
            'tags': item.get('tags', [])
        })
        
    phases = []
    phase_keys = sorted(grouped_phases_dict.keys(), key=lambda k: min(n['id'] for n in grouped_phases_dict[k]))
    for idx, phase_name in enumerate(phase_keys):
        # Sort nodes in this phase by ID or order
        nodes = grouped_phases_dict[phase_name]
        phases.append({
            'id': f"phase-{idx + 1}",
            'title': phase_name,
            'nodes': nodes
        })

    return {
        'track_slug': track_slug,
        'overall_completion': progress_percentage,
        'completed_count': completed_count,
        'total_count': total_count,
        'weekly_streak': weekly_streak,
        'mock_test_avg': mock_test_avg,
        'strengths': recommendation['strengths'],
        'weaknesses': recommendation['weak_subject_tags'],
        'phases': phases,
        'recommended_next_item_id': recommendation['recommended_next_item_id'],
        'priority_reason': recommendation['priority_reason'],
        'weak_subject_tags': recommendation['weak_subject_tags']
    }

# 5. Recommendation Engine
def _get_recommendation_config():
    return load_platform_config()['recommendation']

def map_topic_to_subjects(topic):
    matched = []
    for sub in _get_recommendation_config()['standard_subjects']:
        if sub.lower() in topic.lower():
            matched.append(sub)
    if not matched:
        return [topic]
    return matched

def calculate_recommendation(user, track_slug, merged_items):
    # Fetch quiz submissions for track-based performance analysis
    submissions = QuizSubmission.objects.filter(user=user, quiz__track_id=track_slug)
    
    subject_scores = defaultdict(list)
    for sub in submissions:
        quiz = sub.quiz
        # Determine actual max possible score based on questions if available
        q_count = quiz.questions.count()
        if q_count > 0:
            max_possible = q_count * quiz.marks_per_question
        else:
            max_possible = quiz.total_marks or 100.0
            
        if max_possible > 0:
            percentage = (sub.score / max_possible) * 100.0
            subjects = map_topic_to_subjects(quiz.topic)
            for subject in subjects:
                subject_scores[subject].append(percentage)
            
    rec_cfg = _get_recommendation_config()
    weak_threshold = rec_cfg['weak_threshold']
    strength_threshold = rec_cfg['strength_threshold']

    weak_subject_tags = []
    strengths = []
    for subject, scores in subject_scores.items():
        avg = sum(scores) / len(scores)
        if avg < weak_threshold:
            weak_subject_tags.append(subject)
        elif avg >= strength_threshold:
            strengths.append(subject)
            
    # Filter incomplete items
    completed_ids = {item['id'] for item in merged_items if item['status'] == 'completed'}
    incomplete_items = [item for item in merged_items if item['status'] != 'completed']
    
    if not incomplete_items:
        return {
            'recommended_next_item_id': None,
            'priority_reason': "Incredible work! You have completed all roadmap milestones.",
            'weak_subject_tags': weak_subject_tags,
            'strengths': strengths
        }
        
    # Helper to check if prerequisites are completed
    def prerequisites_completed(item):
        prereqs = item.get('prerequisites', [])
        return all(p in completed_ids for p in prereqs)
        
    # Categorize incomplete items
    eligible_items = [item for item in incomplete_items if prerequisites_completed(item)]
    blocked_items = [item for item in incomplete_items if not prerequisites_completed(item)]
    
    if not eligible_items:
        # If all incomplete items are blocked, fallback to first blocked item's prerequisite
        # Let's find what is blocking the first blocked item
        first_blocked = blocked_items[0]
        missing_prereq = next((p for p in first_blocked.get('prerequisites', []) if p not in completed_ids), None)
        if missing_prereq:
            prereq_item = next((item for item in merged_items if item['id'] == missing_prereq), None)
            if prereq_item:
                return {
                    'recommended_next_item_id': prereq_item['id'],
                    'priority_reason': f"Recommended prerequisite '{prereq_item['title']}' to unlock subsequent modules.",
                    'weak_subject_tags': weak_subject_tags,
                    'strengths': strengths
                }
        # Generic fallback
        fallback_item = incomplete_items[0]
        return {
            'recommended_next_item_id': fallback_item['id'],
            'priority_reason': "Unlock the next phase by starting this item.",
            'weak_subject_tags': weak_subject_tags,
            'strengths': strengths
        }
        
    # Prioritize eligible items belonging to weak subjects
    weak_priority_item = None
    matched_weak_subject = None
    
    for item in eligible_items:
        tags = item.get('tags', [])
        for tag in tags:
            for ws in weak_subject_tags:
                if tag.lower() in ws.lower() or ws.lower() in tag.lower():
                    weak_priority_item = item
                    matched_weak_subject = ws
                    break
            if weak_priority_item:
                break
        if weak_priority_item:
            break
            
    if weak_priority_item:
        return {
            'recommended_next_item_id': weak_priority_item['id'],
            'priority_reason': f"Prioritized '{weak_priority_item['title']}' to help strengthen your weak area in {matched_weak_subject} based on quiz attempts.",
            'weak_subject_tags': weak_subject_tags,
            'strengths': strengths
        }
        
    # Default recommendation: first eligible item in sequence
    rec_item = eligible_items[0]
    return {
        'recommended_next_item_id': rec_item['id'],
        'priority_reason': "Recommended next step in your study plan.",
        'weak_subject_tags': weak_subject_tags,
        'strengths': strengths
    }

# 6. Helper stats calculators
def calculate_mock_test_average(user, track_slug):
    submissions = QuizSubmission.objects.filter(user=user, quiz__track_id=track_slug)
    if not submissions.exists():
        return 0
    scores = []
    for s in submissions:
        quiz = s.quiz
        q_count = quiz.questions.count()
        if q_count > 0:
            total = q_count * quiz.marks_per_question
        else:
            total = quiz.total_marks or 100.0
        if total > 0:
            scores.append((s.score / total) * 100.0)
    return int(sum(scores) / len(scores)) if scores else 0

def calculate_weekly_streak(user):
    # Retrieve dates of submissions in the last 30 days
    thirty_days_ago = timezone.now() - datetime.timedelta(days=30)
    submissions = QuizSubmission.objects.filter(user=user, submitted_at__gte=thirty_days_ago)
    
    dates = {s.submitted_at.date() for s in submissions}
    if not dates:
        return 0
        
    # Simple streak calculation
    today = timezone.now().date()
    streak = 0
    current_date = today
    
    # If no submission today, check if yesterday had one to maintain streak
    if today not in dates:
        current_date = today - datetime.timedelta(days=1)
        if current_date not in dates:
            return 0
            
    while current_date in dates:
        streak += 1
        current_date -= datetime.timedelta(days=1)
        
    return streak

def MathRound(val, total):
    if total == 0:
        return 0
    return int((val / total) * 100)
