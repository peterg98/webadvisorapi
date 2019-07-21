from rest_framework import routers
from . import views
from rest_framework_nested.routers import NestedSimpleRouter
from django.conf.urls import url, include

term_router = routers.DefaultRouter()
term_router.register(r'terms', views.TermViewSet)

course_router = NestedSimpleRouter(term_router, r'terms', lookup="term")
course_router.register(r'courses', views.CourseViewSet)

sections_router = NestedSimpleRouter(course_router, r'courses', lookup='parent_course')
sections_router.register(r'sections', views.SectionViewSet)

urlpatterns = [
    url(r'^', include(term_router.urls)),
    url(r'^', include(course_router.urls)),
    url(r'^', include(sections_router.urls)),
]