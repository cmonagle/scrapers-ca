# coding: utf-8
from pupa.scrape import Scraper

from utils import csv_reader, CanadianLegislator as Legislator

import re

COUNCIL_PAGE = 'http://www.parl.gc.ca/Parliamentarians/en/members/export?output=CSV'


class CanadaPersonScraper(Scraper):

  # @todo Need to create chambers. Look at import_billy.py.
  # @todo Check if Constituency is unique to Province / Territory.
  def get_people(self):
    for row in csv_reader(COUNCIL_PAGE, header=True, encoding='cp1252'):
      p = Legislator(
        name='%(First Name)s %(Last Name)s' % row,
        post_id=row['Constituency'],
        role='MP',
        chamber='lower',
        party=row['Political Affiliation'],
      )
      p.add_source(COUNCIL_PAGE)
      yield p
