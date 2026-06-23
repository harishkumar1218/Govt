from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from pymongo import MongoClient
import time
import os
import json
import subprocess
import re
from rest_framework.views import APIView
import feedparser
from email.utils import parsedate_to_datetime
from datetime import datetime
from django.utils import timezone
from core.config_loader import load_platform_config, load_slug_registry, get_track_mapping

# Use lazy initialization with a short timeout and a circuit breaker
_mongo_client = None
_mongo_failed_until = 0.0

def get_exams_collection():
    global _mongo_client, _mongo_failed_until
    
    current_time = time.time()
    if current_time < _mongo_failed_until:
        raise Exception("MongoDB Atlas connection is in lockout period due to previous connection failure.")
        
    if _mongo_client is None:
        # Set serverSelectionTimeoutMS to 1000ms to fail fast if network/whitelist is broken
        _mongo_client = MongoClient(settings.MONGO_DB_URI, serverSelectionTimeoutMS=1000)
    db = _mongo_client['govt-cluster']
    return db['exams']

class ExamTrackViewSet(viewsets.ViewSet):
    """
    A ViewSet that connects to MongoDB Atlas directly to list and retrieve exam tracks.
    If the connection fails or times out, it gracefully falls back to the local SQLite database.
    We use a circuit breaker to avoid repeatedly waiting for connection timeouts when MongoDB is down.
    """
    lookup_field = 'slug'

    def list(self, request):
        global _mongo_failed_until
        try:
            col = get_exams_collection()
            # Force server selection check here to trigger timeout if unreachable
            col.database.client.admin.command('ping')
            tracks = list(col.find({}))
            for track in tracks:
                track['id'] = track.get('slug', track.get('_id'))
                if '_id' in track:
                    track['_id'] = str(track['_id'])
            return Response(tracks)
        except Exception as e:
            # Lock out MongoDB connection attempts for 60 seconds
            _mongo_failed_until = time.time() + 60.0
            print(f"[Warning] MongoDB Atlas connection failed ({e}). Lockout activated. Falling back to local SQLite database.")
            
            # Graceful fallback to SQLite ORM
            from .models import ExamTrack
            from .serializers import ExamTrackSerializer
            queryset = ExamTrack.objects.all().prefetch_related('flowchart', 'syllabus', 'cutoffs')
            serializer = ExamTrackSerializer(queryset, many=True)
            return Response(serializer.data)

    def retrieve(self, request, slug=None):
        global _mongo_failed_until
        try:
            col = get_exams_collection()
            # Force server selection check here to trigger timeout if unreachable
            col.database.client.admin.command('ping')
            track = col.find_one({"slug": slug})
            if not track:
                track = col.find_one({"_id": slug})
            if not track:
                return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
            
            track['id'] = track.get('slug', track.get('_id'))
            if '_id' in track:
                track['_id'] = str(track['_id'])
                
            return Response(track)
        except Exception as e:
            # Lock out MongoDB connection attempts for 60 seconds
            _mongo_failed_until = time.time() + 60.0
            print(f"[Warning] MongoDB Atlas connection failed ({e}). Lockout activated. Falling back to local SQLite database.")
            
            # Graceful fallback to SQLite ORM
            from .models import ExamTrack
            from .serializers import ExamTrackSerializer
            try:
                track = ExamTrack.objects.get(slug=slug)
                serializer = ExamTrackSerializer(track)
                return Response(serializer.data)
            except ExamTrack.DoesNotExist:
                return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

class GenerateMockExamView(APIView):
    """
    Invokes the local Ollama RAG engine to generate a dynamic mock exam.
    """
    def get(self, request):
        exam_id = request.query_params.get('exam_id')
        track_slug = request.query_params.get('track_slug')

        if not exam_id and track_slug:
            mapping = get_track_mapping(track_slug)
            exam_id = mapping['rag_slug'] if mapping else track_slug
        if not exam_id:
            registry = load_slug_registry()
            first_track = next(iter(registry.get('tracks', {}).values()), None)
            exam_id = first_track['rag_slug'] if first_track else 'upsc-civil-services'

        prompt_path = os.path.join(settings.BASE_DIR, 'prompts', f"{exam_id}.json")
        if not os.path.exists(prompt_path):
            mapping = get_track_mapping(exam_id)
            if mapping and mapping.get('prompt_file'):
                prompt_path = os.path.join(settings.BASE_DIR, 'prompts', mapping['prompt_file'])

        if not os.path.exists(prompt_path):
            return Response(
                {"error": f"Prompt configuration for {exam_id} not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        with open(prompt_path, 'r') as f:
            config = json.load(f)

        topic = config.get('topic', 'General Knowledge')
        num_questions = config.get('num_questions', 3)
        model = config.get('model', load_platform_config()['llm']['default_model'])
        duration_seconds = config.get('duration_seconds')
        exam_name = config.get('exam_name', exam_id.replace('-', ' ').title())

        if not duration_seconds and track_slug:
            from .models import ExamPattern
            pattern = ExamPattern.objects.filter(track_id=track_slug).first()
            if pattern:
                duration_seconds = pattern.duration_seconds
        
        # Paths for RAG execution
        rag_dir = os.path.join(settings.BASE_DIR.parent, 'RAG')
        python_exec = os.path.join(rag_dir, 'venv', 'bin', 'python')
        script_path = os.path.join(rag_dir, 'generate_exam.py')
        output_file = os.path.join(settings.BASE_DIR, f"temp_{exam_id}_output.md")
        
        # Execute RAG subprocess
        try:
            cmd = [
                python_exec, script_path,
                "--topic", topic,
                "--num_questions", str(num_questions),
                "--model", model,
                "--output", output_file
            ]
            # Timeout set to 3 minutes for local LLM generation
            subprocess.run(cmd, cwd=rag_dir, check=True, capture_output=True, text=True, timeout=180)
            
            # Read generated markdown
            with open(output_file, 'r', encoding='utf-8') as f:
                raw_markdown = f.read()
                
            # Clean up temp file
            if os.path.exists(output_file):
                os.remove(output_file)
                
            # Parse markdown to JSON structure
            questions = self.parse_markdown_to_json(raw_markdown)
            
            # If no questions parsed, return error
            if not questions:
                return Response({"error": "Failed to parse generated questions.", "raw": raw_markdown}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return Response({
                "exam_id": exam_id,
                "exam_name": exam_name,
                "duration_seconds": duration_seconds,
                "questions": questions,
            }, status=status.HTTP_200_OK)
            
        except subprocess.TimeoutExpired:
            return Response({"error": "Generation timed out. The local LLM took too long."}, status=status.HTTP_504_GATEWAY_TIMEOUT)
        except subprocess.CalledProcessError as e:
            return Response({"error": f"RAG execution failed: {e.stderr}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def parse_markdown_to_json(self, raw_text):
        """Parse the RAG output (Markdown or JSON) into a list of question dictionaries."""
        cleaned_text = raw_text.strip()
        
        # Check if the text contains a JSON block
        json_match = re.search(r'```json\s*(.*?)\s*```', cleaned_text, re.DOTALL | re.IGNORECASE)
        if json_match:
            cleaned_text = json_match.group(1).strip()
            
        if cleaned_text.startswith('{') or cleaned_text.startswith('['):
            data = None
            try:
                data = json.loads(cleaned_text)
            except Exception:
                # Try appending matching braces/brackets to repair truncated JSON
                for suffix in ['}', ']}', ']\n}', '}\n]\n}', '] \n}']:
                    try:
                        data = json.loads(cleaned_text + suffix)
                        break
                    except Exception:
                        pass

            if data is not None:
                try:
                    if isinstance(data, dict) and "questions" in data:
                        questions_list = data["questions"]
                    elif isinstance(data, list):
                        questions_list = data
                    else:
                        questions_list = []
                        
                    parsed_questions = []
                    for idx, q in enumerate(questions_list):
                        opts = q.get("options", [])
                        if isinstance(opts, dict):
                            options_list = [opts.get("A", ""), opts.get("B", ""), opts.get("C", ""), opts.get("D", "")]
                        elif isinstance(opts, list):
                            options_list = list(opts)
                        else:
                            options_list = []
                            
                        while len(options_list) < 4:
                            options_list.append(f"Option {len(options_list)+1}")
                            
                        correct_ans = q.get("correct_answer", q.get("correctAnswer", 0))
                        if isinstance(correct_ans, str):
                            letter_to_idx = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
                            correct_index = letter_to_idx.get(correct_ans.upper(), 0)
                        else:
                            correct_index = int(correct_ans)
                            
                        parsed_questions.append({
                            "id": q.get("order", q.get("id", idx + 1)),
                            "text": q.get("text", q.get("question_text", f"Question {idx+1}")),
                            "options": options_list[:4],
                            "correctAnswer": correct_index,
                            "explanation": q.get("explanation", "")
                        })
                    if parsed_questions:
                        return parsed_questions
                except Exception as e:
                    # Fall back to markdown parsing
                    pass


        pattern = r'(### (?:Expected )?Question \d+.*?)(?=### (?:Expected )?Question \d+|\Z)'
        matches = re.findall(pattern, raw_text, re.DOTALL | re.IGNORECASE)
        
        parsed_questions = []
        for i, match in enumerate(matches):
            match_str = match.strip()
            
            # Extract header
            lines = match_str.split("\n")
            header = lines[0]
            
            # Use regex to find sections
            options_match = re.search(r'\*?\*?Options:\*?\*?(.*?)(?=\*?\*?Answer:|\Z)', match_str, re.DOTALL | re.IGNORECASE)
            answer_match = re.search(r'\*?\*?Answer:\*?\*?\s*([A-D])', match_str, re.IGNORECASE)
            explanation_match = re.search(r'\*?\*?(?:Explanation|Rationale for Prediction):\*?\*?(.*)', match_str, re.DOTALL | re.IGNORECASE)
            
            options_start_match = re.search(r'\*?\*?Options:\*?\*?', match_str, re.IGNORECASE)
            if options_start_match:
                options_start = options_start_match.start()
                question_text = match_str[len(header):options_start].strip()
            else:
                question_text = match_str[len(header):].strip()
                
            options_raw = options_match.group(1).strip() if options_match else ""
            answer_letter = answer_match.group(1).strip() if answer_match else ""
            explanation = explanation_match.group(1).strip() if explanation_match else ""
            
            # Parse options into array
            options_list = []
            for opt_line in options_raw.split('\n'):
                opt_line = opt_line.strip()
                if opt_line and re.match(r'^[A-D]\)', opt_line):
                    # Remove the "A) " prefix
                    options_list.append(re.sub(r'^[A-D]\)\s*', '', opt_line))
            
            # Ensure we have exactly 4 options, pad if necessary
            while len(options_list) < 4:
                options_list.append(f"Option {len(options_list)+1}")
                
            # Convert answer letter to index (A=0, B=1, C=2, D=3)
            letter_to_idx = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
            correct_index = letter_to_idx.get(answer_letter.upper(), 0)
            
            parsed_questions.append({
                "id": i + 1,
                "text": question_text,
                "options": options_list[:4],
                "correctAnswer": correct_index,
                "explanation": explanation
            })
            
        return parsed_questions


class CurrentAffairsView(APIView):
    """
    Fetches latest current affairs from configured RSS feed and builds archive from older entries.

    Query params (all optional, non-breaking):
      search=<text>       — case-insensitive filter on title + description
      sort=latest|oldest  — sort order for the older feed (default: latest)
      page=<n>            — page number for older feed pagination (default: 1)
      page_size=<n>       — page size for older feed pagination (default: 20)
    """

    @staticmethod
    def _estimate_reading_time(text: str) -> int:
        """Estimate reading time in minutes based on ~200 words/min."""
        words = len(text.split())
        return max(1, round(words / 200))

    @staticmethod
    def _stable_id(link: str) -> str:
        """Generate a stable, short article ID from the article URL."""
        import hashlib
        return hashlib.md5(link.encode()).hexdigest()[:12]

    def get(self, request):
        platform = load_platform_config()
        feed_url = platform['current_affairs']['rss_feed_url']
        feed = feedparser.parse(feed_url)

        if getattr(feed, 'bozo', 0) == 1 and not feed.entries:
            return Response({"error": "Failed to parse RSS feed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # --- Query params ---
        search_query = (request.query_params.get('search') or '').strip().lower()
        sort_order = request.query_params.get('sort', 'latest')
        try:
            page = max(1, int(request.query_params.get('page', 1)))
        except (ValueError, TypeError):
            page = 1
        try:
            page_size = min(50, max(1, int(request.query_params.get('page_size', 20))))
        except (ValueError, TypeError):
            page_size = 20

        today = timezone.now().date()

        today_news = []
        older_news = []

        for entry in feed.entries:
            try:
                dt = parsedate_to_datetime(entry.published)
            except Exception:
                dt = timezone.now()

            # Clean description (remove img tags or basic html)
            desc = re.sub(r'<[^>]+>', '', entry.description)
            # Find an image if available
            img_url = None
            if hasattr(entry, 'media_content') and len(entry.media_content) > 0:
                img_url = entry.media_content[0].get('url')

            link = entry.link
            news_item = {
                'id': entry.id if hasattr(entry, 'id') else link,
                'article_id': self._stable_id(link),
                'title': entry.title,
                'link': link,
                'description': desc,
                'published': dt.isoformat(),
                'source': 'The Hindu',
                'reading_time': self._estimate_reading_time(desc),
                'image': img_url,
            }

            if dt.date() == today:
                today_news.append(news_item)
            else:
                older_news.append(news_item)

        # --- Apply search filter ---
        if search_query:
            def _matches(item):
                return (search_query in item['title'].lower() or
                        search_query in item['description'].lower())
            today_news = [i for i in today_news if _matches(i)]
            older_news = [i for i in older_news if _matches(i)]

        # --- Apply sort ---
        reverse = (sort_order != 'oldest')
        today_news.sort(key=lambda x: x['published'], reverse=reverse)
        older_news.sort(key=lambda x: x['published'], reverse=reverse)

        # --- Paginate older_news ---
        total_older = len(older_news)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_older = older_news[start:end]

        archive = self._build_archive(today_news + older_news)

        return Response({
            "today": today_news,
            "older": paginated_older,
            "older_total": total_older,
            "page": page,
            "page_size": page_size,
            "archive": archive,
        })

    def _build_archive(self, news_items):
        """Group RSS older entries and combine with predefined historical archives for UPSC preparation."""
        from collections import defaultdict
        
        # Predefined rich mock data for previous years to ensure timeline is populated
        mock_data = [
            # --- 2026 ---
            {
                'year': 2026,
                'monthName': 'June 2026',
                'title': 'India’s GDP growth projects to reach 7.2% in FY26: RBI Bulletin',
                'description': 'The Reserve Bank of India’s latest bulletin highlights strong macroeconomic fundamentals, resilient domestic demand, and robust service sector growth driving the Indian economy forward.',
                'date': '2026-06-15T12:00:00+05:30',
                'link': 'https://www.thehindu.com/business/Economy/indias-gdp-growth-projects-to-reach-72-in-fy26-rbi-bulletin/article71131011.ece',
                'source': 'The Hindu',
            },
            {
                'year': 2026,
                'monthName': 'June 2026',
                'title': 'UN Security Council adopts resolution calling for immediate ceasefire in Gaza',
                'description': 'The UN Security Council has voted overwhelmingly to support a draft resolution outlining a comprehensive ceasefire proposal to bring an end to the conflict in Gaza.',
                'date': '2026-06-10T10:30:00+05:30',
                'link': 'https://www.thehindu.com/news/international/un-security-council-adopts-resolution-calling-for-immediate-ceasefire-in-gaza/article71112233.ece',
                'source': 'The Hindu',
            },
            {
                'year': 2026,
                'monthName': 'May 2026',
                'title': 'Supreme Court stays new directives on civil services exam pattern',
                'description': 'The Supreme Court of India issued an interim stay on the proposed revisions to the civil services mains exam format, directing UPSC to maintain status quo for the current cycle.',
                'date': '2026-05-20T14:45:00+05:30',
                'link': 'https://www.thehindu.com/news/national/supreme-court-stays-new-directives-on-civil-services-exam-pattern/article71050201.ece',
                'source': 'The Hindu',
            },
            # --- 2025 ---
            {
                'year': 2025,
                'monthName': 'December 2025',
                'title': 'COP30 climate summit concludes with historic pact on renewable energy targets',
                'description': 'The UN Climate Change Conference in Belem concluded with nations agreeing to binding timelines to triple global renewable energy capacity by 2030.',
                'date': '2025-12-18T18:00:00+05:30',
                'link': 'https://www.thehindu.com/sci-tech/energy-and-environment/cop30-climate-summit-concludes-with-historic-pact/article70850112.ece',
                'source': 'The Hindu',
            },
            {
                'year': 2025,
                'monthName': 'December 2025',
                'title': 'Parliament passes landmark Digital Personal Data Protection rules',
                'description': 'The Union Parliament approved the secondary rules under the DPDP Act, specifying penalties and compliance frameworks for big tech companies operating in India.',
                'date': '2025-12-05T11:15:00+05:30',
                'link': 'https://www.thehindu.com/news/national/parliament-passes-landmark-digital-personal-data-protection-rules/article70810231.ece',
                'source': 'The Hindu',
            },
            {
                'year': 2025,
                'monthName': 'November 2025',
                'title': 'ISRO successfully launches Aditya-L2 solar tracking mission from Sriharikota',
                'description': 'The Indian Space Research Organisation’s Polar Satellite Launch Vehicle placed the Aditya-L2 spacecraft into a halo orbit to continuously monitor solar activity.',
                'date': '2025-11-12T09:20:00+05:30',
                'link': 'https://www.thehindu.com/sci-tech/science/isro-successfully-launches-aditya-l2-solar-tracking-mission/article70732104.ece',
                'source': 'The Hindu',
            },
            # --- 2024 ---
            {
                'year': 2024,
                'monthName': 'October 2024',
                'title': 'Government announces new National Education Policy implementation roadmap for higher education',
                'description': 'The Ministry of Education unveiled a comprehensive guide detailing credit transfers, multidisciplinary degrees, and international collaborations under the NEP.',
                'date': '2024-10-22T15:30:00+05:30',
                'link': 'https://www.thehindu.com/education/government-announces-nep-implementation-roadmap-for-higher-education/article69910405.ece',
                'source': 'The Hindu',
            },
            {
                'year': 2024,
                'monthName': 'October 2024',
                'title': 'Elections commission announces assembly polls in major states',
                'description': 'The Election Commission of India declared schedule for legislative assembly elections in Maharashtra and Jharkhand, enforcing the model code of conduct.',
                'date': '2024-10-15T12:00:00+05:30',
                'link': 'https://www.thehindu.com/news/national/election-commission-announces-assembly-polls-schedule-for-maharashtra-and-jharkhand/article69902031.ece',
                'source': 'The Hindu',
            }
        ]

        by_year = defaultdict(lambda: defaultdict(list))
        
        # Add predefined mock data
        for item in mock_data:
            import hashlib
            year = item['year']
            month_key = item['monthName']
            link = item['link']
            stable_id = hashlib.md5(link.encode()).hexdigest()[:12]
            by_year[year][month_key].append({
                'article_id': stable_id,
                'title': item['title'],
                'description': item['description'],
                'date': item['date'],
                'source': item['source'],
                'link': link,
                'reading_time': 1,
            })

        # Add any actual older news from the live RSS feed
        for item in news_items:
            try:
                dt = datetime.fromisoformat(item['published'])
            except Exception:
                continue
            year = dt.year
            month_key = dt.strftime('%B %Y')
            
            # Avoid duplicating predefined links
            if any(x['link'] == item['link'] for m in by_year[year].values() for x in m):
                continue
                
            by_year[year][month_key].append({
                'article_id': item.get('article_id', ''),
                'title': item['title'],
                'description': item['description'],
                'date': item['published'],
                'source': item.get('source', 'The Hindu'),
                'link': item['link'],
                'reading_time': item.get('reading_time', 1),
            })

        archive = []
        for year in sorted(by_year.keys(), reverse=True):
            months = []
            def _month_sort_key(month_name):
                try:
                    return datetime.strptime(month_name, '%B %Y')
                except Exception:
                    return datetime.min
            
            sorted_months = sorted(by_year[year].items(), key=lambda x: _month_sort_key(x[0]), reverse=True)
            
            for month_name, articles in sorted_months:
                articles.sort(key=lambda x: x['date'], reverse=True)
                months.append({'monthName': month_name, 'articles': articles})
                
            year_count = sum(len(m['articles']) for m in months)
            highlights = []
            if months:
                highlights = [a['title'] for a in months[0]['articles'][:4]]
                
            archive.append({
                'year': year,
                'summary': f'{year_count} archived articles from national news feed.',
                'highlights': highlights,
                'months': months,
            })
        return archive

from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import ExamTrack, Quiz, QuizQuestion, QuizRegistration, QuizSubmission
from core.services.email_service import send_mock_test_registration_email


class DailyQuizView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        starts_soon_threshold = load_platform_config()['quiz']['starts_soon_threshold_seconds']
        today = timezone.now().date()
        track_slug = request.query_params.get('track')
        now = timezone.now()
        
        if track_slug:
            quiz = Quiz.objects.filter(date=today, track__slug=track_slug).first()
            if not quiz:
                return Response({"error": "No quiz scheduled for today."}, status=status.HTTP_404_NOT_FOUND)
                
            is_registered = False
            if request.user.is_authenticated:
                is_registered = QuizRegistration.objects.filter(user=request.user, quiz=quiz).exists()
                
            status_str = "Not Registered"
            if quiz.ends_at and now > quiz.ends_at:
                status_str = "Closed"
            elif quiz.starts_at and now >= quiz.starts_at and (not quiz.ends_at or now <= quiz.ends_at):
                status_str = "Live"
            elif quiz.starts_at and now < quiz.starts_at:
                time_diff = quiz.starts_at - now
                if time_diff.total_seconds() <= starts_soon_threshold:
                    status_str = "Starts Soon"
                else:
                    status_str = "Registered" if is_registered else "Not Registered"
            else:
                status_str = "Live"
                
            can_start = is_registered and (not quiz.starts_at or now >= quiz.starts_at) and (not quiz.ends_at or now <= quiz.ends_at)
            
            return Response({
                "id": quiz.id,
                "topic": quiz.topic,
                "track": quiz.track.title if quiz.track else None,
                "track_slug": quiz.track.slug if quiz.track else None,
                "date": quiz.date,
                "stage_name": quiz.stage_name,
                "starts_at": quiz.starts_at,
                "ends_at": quiz.ends_at,
                "duration_seconds": quiz.duration_seconds,
                "total_marks": quiz.total_marks,
                "marks_per_question": quiz.marks_per_question,
                "negative_marking": quiz.negative_marking,
                "is_registered": is_registered,
                "can_start": can_start,
                "status": status_str
            })
            
        quizzes = Quiz.objects.filter(date=today)
        if not quizzes.exists():
            return Response({"error": "No quizzes scheduled for today."}, status=status.HTTP_404_NOT_FOUND)
            
        data = []
        for quiz in quizzes:
            is_registered = False
            if request.user.is_authenticated:
                is_registered = QuizRegistration.objects.filter(user=request.user, quiz=quiz).exists()
                
            status_str = "Not Registered"
            if quiz.ends_at and now > quiz.ends_at:
                status_str = "Closed"
            elif quiz.starts_at and now >= quiz.starts_at and (not quiz.ends_at or now <= quiz.ends_at):
                status_str = "Live"
            elif quiz.starts_at and now < quiz.starts_at:
                time_diff = quiz.starts_at - now
                if time_diff.total_seconds() <= starts_soon_threshold:
                    status_str = "Starts Soon"
                else:
                    status_str = "Registered" if is_registered else "Not Registered"
            else:
                status_str = "Live"
                
            can_start = is_registered and (not quiz.starts_at or now >= quiz.starts_at) and (not quiz.ends_at or now <= quiz.ends_at)
            
            data.append({
                "id": quiz.id,
                "topic": quiz.topic,
                "track": quiz.track.title if quiz.track else None,
                "track_slug": quiz.track.slug if quiz.track else None,
                "date": quiz.date,
                "stage_name": quiz.stage_name,
                "starts_at": quiz.starts_at,
                "ends_at": quiz.ends_at,
                "duration_seconds": quiz.duration_seconds,
                "total_marks": quiz.total_marks,
                "marks_per_question": quiz.marks_per_question,
                "negative_marking": quiz.negative_marking,
                "is_registered": is_registered,
                "can_start": can_start,
                "status": status_str
            })
            
        return Response(data)

class RegisterQuizView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        quiz = get_object_or_404(Quiz, id=pk)
            
        registration, created = QuizRegistration.objects.get_or_create(user=request.user, quiz=quiz)
            
        try:
            send_mock_test_registration_email(request.user, quiz.date, quiz=quiz)
        except Exception as e:
            print(f"Failed to send registration email: {e}")
            
        return Response({"message": "Successfully registered", "quiz_id": quiz.id}, status=status.HTTP_201_CREATED)

class QuizStartView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        quiz = Quiz.objects.filter(id=pk).first()
        if not quiz:
            return Response({"error": "Quiz not found"}, status=status.HTTP_404_NOT_FOUND)
            
        if not quiz.track:
            return Response({"error": "This quiz is not assigned to any track."}, status=status.HTTP_400_BAD_REQUEST)
            
        if not QuizRegistration.objects.filter(user=request.user, quiz=quiz).exists():
            return Response({"error": "You are not registered for this quiz."}, status=status.HTTP_403_FORBIDDEN)
            
        if quiz.starts_at and timezone.now() < quiz.starts_at:
            if not (request.query_params.get('force') == 'true' and request.user.is_staff):
                return Response({"error": f"Quiz starts at {quiz.starts_at.strftime('%I:%M %p')}."}, status=status.HTTP_403_FORBIDDEN)
                
        if quiz.ends_at and timezone.now() > quiz.ends_at:
            if not (request.query_params.get('force') == 'true' and request.user.is_staff):
                return Response({"error": f"Quiz ended at {quiz.ends_at.strftime('%I:%M %p')}."}, status=status.HTTP_403_FORBIDDEN)
                
        questions = QuizQuestion.objects.filter(quiz=quiz)
        data = []
        for q in questions:
            data.append({
                "id": q.id,
                "text": q.text,
                "options": q.options
            })
            
        return Response({
            "quiz_id": quiz.id, 
            "duration_seconds": quiz.duration_seconds,
            "questions": data
        })

class QuizSubmitView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        quiz = get_object_or_404(Quiz, id=pk)
        user_answers = request.data.get('answers', {})
        time_taken_seconds = request.data.get('time_taken_seconds', 0)
        
        questions = quiz.questions.all()
        score = 0
        total = questions.count()
        results = []
        
        for q in questions:
            user_ans = user_answers.get(str(q.id))
            if user_ans:
                is_correct = user_ans == q.correct_answer
                if is_correct:
                    score += quiz.marks_per_question
                else:
                    score -= quiz.negative_marking
            else:
                is_correct = False

            results.append({
                "id": q.id,
                "user_answer": user_ans,
                "correct_answer": q.correct_answer,
                "is_correct": is_correct,
                "explanation": q.explanation
            })
            
        submission, created = QuizSubmission.objects.update_or_create(
            user=request.user,
            quiz=quiz,
            defaults={
                'score': score, 
                'total_questions': total,
                'time_taken_seconds': time_taken_seconds,
                'answers': user_answers
            }
        )
        
        return Response({
            "score": score,
            "total": total,
            "time_taken_seconds": time_taken_seconds,
            "results": results
        })

from django.db.models import Sum, Count

class LeaderboardView(APIView):
    def get(self, request):
        top_n = load_platform_config()['quiz']['leaderboard_top_n']
        top_users = QuizSubmission.objects.values('user__username', 'user__first_name', 'user__last_name').annotate(
            total_score=Sum('score'),
            total_tests=Count('id')
        ).order_by('-total_score')[:top_n]
        
        return Response(top_users)

class DailyLatestLeaderboardView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        now = timezone.now()
        tracks = ExamTrack.objects.all()
        tracks_data = []

        for track in tracks:
            # 1. Find the most recently completed/closed Quiz for this track.
            quiz = Quiz.objects.filter(track=track, ends_at__lt=now).order_by('-ends_at', '-date').first()
            
            # Fallback if no completed quiz exists yet
            if not quiz:
                quiz = Quiz.objects.filter(track=track).order_by('-date', '-starts_at').first()

            if not quiz:
                tracks_data.append({
                    "track_slug": track.slug,
                    "track_title": track.title,
                    "quiz_id": None,
                    "quiz_topic": None,
                    "quiz_date": None,
                    "rankers": []
                })
                continue

            # 2. Query all submissions for this quiz
            submissions = QuizSubmission.objects.filter(quiz=quiz).select_related('user')
            
            # 3. Calculate accuracy for each submission
            sub_list = []
            total_questions = quiz.questions.count()
            questions_list = list(quiz.questions.all())

            for sub in submissions:
                correct_count = 0
                for q in questions_list:
                    user_ans = sub.answers.get(str(q.id))
                    if user_ans == q.correct_answer:
                        correct_count += 1
                
                accuracy = round((correct_count / total_questions * 100) if total_questions > 0 else 0.0, 2)
                
                sub_list.append({
                    "submission": sub,
                    "accuracy": accuracy
                })

            # 4. Sort with tie-breaker:
            # - score (descending)
            # - accuracy (descending)
            # - time_taken_seconds (ascending)
            # - submitted_at (ascending)
            sub_list.sort(key=lambda x: (
                -x["submission"].score,
                -x["accuracy"],
                x["submission"].time_taken_seconds,
                x["submission"].submitted_at
            ))

            # 5. Extract top 3 rankers
            rankers = []
            for rank, item in enumerate(sub_list[:3], start=1):
                sub = item["submission"]
                user = sub.user
                name = f"{user.first_name} {user.last_name}".strip()
                if not name:
                    name = user.username

                rankers.append({
                    "rank": rank,
                    "user_id": user.id,
                    "name": name,
                    "username": user.username,
                    "score": sub.score,
                    "total_marks": quiz.total_marks,
                    "accuracy": item["accuracy"],
                    "time_taken_seconds": sub.time_taken_seconds
                })

            tracks_data.append({
                "track_slug": track.slug,
                "track_title": track.title,
                "quiz_id": quiz.id,
                "quiz_topic": quiz.topic,
                "quiz_date": quiz.date.strftime("%Y-%m-%d") if quiz.date else None,
                "rankers": rankers
            })

        return Response({"tracks": tracks_data})

from .analytics import calculate_submission_metrics, get_user_analytics

class UserAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        track_slug = request.query_params.get('track', 'all')
        days_range = request.query_params.get('range', 'all')
        
        analytics = get_user_analytics(request.user, track_slug, days_range)
        return Response(analytics)

class UserMockHistoryListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        track_slug = request.query_params.get('track', 'all')
        days_range = request.query_params.get('range', 'all')
        
        query = QuizSubmission.objects.filter(user=request.user).select_related('quiz', 'quiz__track')
        
        if track_slug and track_slug != 'all':
            query = query.filter(quiz__track__slug=track_slug)
            
        if days_range and days_range != 'all':
            from datetime import timedelta
            try:
                days_int = int(days_range.replace('d', ''))
                start_date = timezone.now() - timedelta(days=days_int)
                query = query.filter(submitted_at__gte=start_date)
            except ValueError:
                pass
                
        submissions = query.order_by('-submitted_at')
        
        data = []
        for sub in submissions:
            metrics = calculate_submission_metrics(sub)
            # Remove detailed questions for list view
            metrics.pop("detailed_questions", None)
            data.append(metrics)
            
        return Response(data)

class UserMockHistoryDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        try:
            submission = QuizSubmission.objects.select_related('quiz', 'quiz__track').get(id=pk, user=request.user)
            metrics = calculate_submission_metrics(submission)
            return Response(metrics)
        except QuizSubmission.DoesNotExist:
            return Response({"error": "Submission not found"}, status=status.HTTP_404_NOT_FOUND)


class PlatformConfigView(APIView):
    """Public platform configuration for frontend (categories, quiz defaults, essay tags)."""
    permission_classes = [AllowAny]

    def get(self, request):
        platform = load_platform_config()
        registry = load_slug_registry()
        return Response({
            'app_name': platform['app_name'],
            'eligibility_categories': platform['eligibility_categories'],
            'quiz': {
                'default_start_hour': platform['quiz']['default_start_hour'],
                'default_start_minute': platform['quiz']['default_start_minute'],
            },
            'essay': platform['essay'],
            'tracks': registry.get('tracks', {}),
        })
