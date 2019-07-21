from . import models
from . import serializers
from rest_framework import viewsets

class TermViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.TermSerializer
    queryset = models.Term.objects.all()

class CourseViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.CourseSerializer
    queryset = models.Course.objects.all()

class SectionViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.SectionSerializer
    queryset = models.Section.objects.all()
