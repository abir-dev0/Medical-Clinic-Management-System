from django.contrib import admin
from .models import Specialite, Creneau, CompteRendu

# Register your models here.
admin.site.register(Specialite)
admin.site.register(Creneau)
admin.site.register(CompteRendu)
