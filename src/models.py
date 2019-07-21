from django.db import models
from django.contrib.postgres.fields import ArrayField

class Term(models.Model):
    term_code = models.CharField(default='', max_length=40, primary_key=True)

    def __str__(self):
        return self.term_code

class Course(models.Model):
    term = models.ForeignKey(Term, related_name="courses_offered", on_delete=models.CASCADE)
    course_code = models.CharField(default='', max_length=50, primary_key=True)
    title = models.CharField(default='', max_length=50)
    credit_points = models.IntegerField(default=3,)
    academic_level = models.CharField(default="", max_length=50, null=True)
    
class Section(models.Model):
    section_number = models.CharField(default='', max_length=15, primary_key=True)
    parent_course = models.ForeignKey(Course, related_name="sections_offered", on_delete=models.CASCADE)
    description = models.TextField(default='', max_length=1000)
    faculty = models.CharField(default='', max_length=50)
    phone = models.CharField(default='', max_length=50)
    extension = models.CharField(default='', max_length=50)
    email = models.CharField(default='', max_length=50)
    instructional_method = models.CharField(default='', max_length=50)
    requisite_courses = models.TextField(default='', max_length=300)
    location = models.CharField(default="", max_length=100)
    meeting_info = models.CharField(default='', max_length=300)
    faculty = models.CharField(default='', max_length=50)
    available = models.IntegerField(default=0,)
    max_capacity = models.IntegerField(default=20,)
    status = models.CharField(default='', max_length=10)
