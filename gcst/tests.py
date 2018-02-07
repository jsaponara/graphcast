"""
cd gcst
python ../manage.py test gcst
# then follow instructions in output highlighted by '***'
"""

from __future__ import print_function

from django.template import Template
from django.test import TestCase

from gcst.locate import find
from gcst.gcst import fcstgfx

testZip = '08540'

class SimpleTest(TestCase):
    def test_locate_find(self):
        locationInfo = find(testZip)   # returns {'city': 'Princeton', 'lat': '40.357439', 'loc': '08540', 'lon': '-74.64922', 'state': 'NJ', 'zipc': '08540'}
        self.assertEqual(
            tuple(locationInfo[key] for key in 'city state lat lon zipc'.split()),
            ('Princeton', 'NJ', '40.357439', '-74.64922', '08540')
        )

    def test_gcst_fcstgfx(self):
        locationInfo = find(testZip)
        fcstInfo = fcstgfx(locationInfo)
        # some fields will be missing for NoData test
        #self.assertIn('fcstAsOfTime', fcstInfo.keys())
        self.assertIn('svgs', fcstInfo.keys())
        try:
            #with open('templates/index.html') as f:
            with open('templates/test.html') as f:
                template = f.read()
            content = template.replace('SVGS_GO_HERE', fcstInfo['svgs'])
            #content = Template(template).render(fcstInfo)
                # No DjangoTemplates backend is configured.
                # need a backend: https://stackoverflow.com/questions/43834226/
                    #from django.conf import settings
                    #TEMPLATES = [
                    #    {
                    #        'BACKEND': 'django.template.backends.django.DjangoTemplates',
                    #        #'DIRS': ['/path/to/template'],
                    #    }
                    #]
                    #print(settings.TEMPLATES)
                    #settings.configure(TEMPLATES=TEMPLATES)
                # but too late to configure: RuntimeError: Settings already configured
            fname = testZip + '.html'
            with open(fname, 'w') as f:
                f.write(content)
            print('     *** Wrote file:',fname)
            print('     *** Now start http server and browse to that file')
            print('     *** To start http server: python3 -m http.server OR python2 -m SimpleHTTPServer')
        except Exception as e:
            print('tried to write example html file but encountered exception:',e)

