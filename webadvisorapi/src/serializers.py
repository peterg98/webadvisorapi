from rest_framework_nested.relations import NestedHyperlinkedRelatedField
from rest_framework_nested.serializers import NestedHyperlinkedModelSerializer
from rest_framework import serializers
from . import models

class TermSerializer(serializers.HyperlinkedModelSerializer):
    courses_offered = NestedHyperlinkedRelatedField(
        many=True,
        read_only=True,
        view_name='course-detail',
        parent_lookup_kwargs={'term_pk': 'term__pk'}
    )
    class Meta:
        model = models.Term
        fields = ('url', 'term_code', 'courses_offered')

class CourseSerializer(serializers.HyperlinkedModelSerializer):
    sections_offered = NestedHyperlinkedRelatedField(
        many=True,
        read_only=True,
        view_name='section-detail',
        parent_lookup_kwargs={'parent_course_pk': 'parent_course__pk', 'term_pk': 'parent_course__term'} 
        #map URL lookup fields from child model fields. e.g. /terms/term_pk/courses/parent_course_pk/sections
        #e.g. parent_course__pk refers to the parent_course of the Section field, and __pk is the primary key of
        #that parent_course, which will be a Course object
    )
    url = serializers.HyperlinkedRelatedField(
        read_only=True,
        view_name='course-detail',
    )
    class Meta:
        model = models.Course
        fields = ('url', 'term', 'course_code', 'title', 'credit_points', 
                'sections_offered', 'academic_level')


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Section
        fields = ('section_number', 'parent_course', 'description', 'faculty',
        'phone', 'extension', 'email', 'instructional_method', 'requisite_courses',
        'location', 'meeting_info', 'faculty', 'available', 'max_capacity', 'status')