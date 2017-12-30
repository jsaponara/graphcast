from django.db import models

class Loc(models.Model):
    zipcode=models.CharField(max_length=5)
    city=models.CharField(max_length=20)
    state=models.CharField(max_length=2)
    lat=models.FloatField()
    lon=models.FloatField()
    def __unicode__(self):
        return 'Loc for %s'%(self.zipcode)

class Fcst(models.Model):
    ondelete = False
    loc=models.ForeignKey(Loc, ondelete)
    def __unicode__(self):
        return 'Fcst for %s'%(self.loc)

