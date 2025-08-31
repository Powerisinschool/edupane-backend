from django.contrib import admin
from .models import Category, Course, Enrollment, Material, Deadline
from .models_notification import Notification

admin.site.register([Category, Course, Enrollment, Material, Deadline, Notification])
