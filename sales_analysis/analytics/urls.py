from django.urls import path, include
from .views import (
    home,
    upload_file,
    process_file,
    register,
    dashboard,
    select_headers,
    charts,
    share_chart,
    view_shared_chart,
    CustomPasswordResetConfirmView,
)
from django.contrib.auth.views import LoginView, LogoutView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', home, name='home'),
    path('signup/', register, name='signup'),
    path('login/', LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', LogoutView.as_view(template_name='accounts/logout.html'), name='logout'),
    path('upload/', upload_file, name='upload'),
    path('process_file/<int:file_id>/', process_file, name='process_file'),
    path('select/<int:file_id>/', select_headers, name='select'),
    path('charts/<int:file_id>/', charts, name='charts'),
    path('dashboard/<int:file_id>/', dashboard, name='dashboard'),
    path('share_chart/<int:file_id>/<str:chart_type>/', share_chart, name='share_chart'),
    path('password_reset/', include('django.contrib.auth.urls')), 
    path('accounts/password_reset_confirm/<uidb64>/<token>/', CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('analytics/shared_charts/<str:chart_id>/<str:chart_type>/', view_shared_chart, name='view_shared_chart'),
    
    

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)