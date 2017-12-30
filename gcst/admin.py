from django.contrib import admin
from .models import Fcst,Loc

admin.site.register(Fcst)
admin.site.register(Loc)
# OR
#class PollAdmin(admin.ModelAdmin):
#	fields = ['pub_date', 'question']
#admin.site.register(Poll, PollAdmin)
# OR
#class PollAdmin(admin.ModelAdmin):
#fieldsets = [
#	(None,               {'fields': ['question']}),  # None=no title for that fieldset
#	('Date information', {'fields': ['pub_date']}),
#		OR ('Date information', {'fields': ['pub_date'], 'classes': ['collapse']}),
#	]

