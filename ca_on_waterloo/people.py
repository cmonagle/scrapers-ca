from __future__ import unicode_literals
from utils import CSVScraper


class WaterlooPersonScraper(CSVScraper):
    csv_url = 'http://opendata.city-of-waterloo.opendata.arcgis.com/datasets/594698f0bbcd4c20b72977194d2b97b8_0.csv'
    corrections = {
        'district name': {
            'ward 2': 'Ward 2',
        },
    }

    def header_converter(self, s):
        return s.lower().replace('_', ' ')
