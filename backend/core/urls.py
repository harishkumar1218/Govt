from django.contrib import admin
from django.urls import path, include
from accounts.views import GoogleLogin, AppleLogin
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('dj_rest_auth.urls')),
    path('auth/google/', GoogleLogin.as_view(), name='google_login'),
    path('auth/apple/', AppleLogin.as_view(), name='apple_login'),
    path('api/', include('exams.urls')),
    path('api/rag/', include('rag_pipeline.urls')),
    path('api/roadmap/', include('roadmap.urls')),
    path('api/essay/', include('essay.urls')),
    path('api/threads/', include('threads.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
