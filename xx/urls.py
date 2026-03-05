from xx.urls_academics import urlpatterns as academics_urlpatterns
from xx.urls_auth import urlpatterns as auth_urlpatterns
from xx.urls_misc import urlpatterns as misc_urlpatterns
from xx.urls_students import urlpatterns as students_urlpatterns
from xx.urls_users import urlpatterns as users_urlpatterns

urlpatterns = [
    *auth_urlpatterns,
    *users_urlpatterns,
    *students_urlpatterns,
    *academics_urlpatterns,
    *misc_urlpatterns,
]
