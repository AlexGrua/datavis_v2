from django.contrib import admin
from django.urls import path, include
from analytics.views import home
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),  
    path('analytics/', include('analytics.urls')), 
    path('accounts/', include('django.contrib.auth.urls')), 



]
if settings.DEBUG:  # Only serve media files in development
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)