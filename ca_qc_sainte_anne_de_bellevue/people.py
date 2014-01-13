from pupa.scrape import Scraper, Legislator

from utils import lxmlize, CanadianScraper

import re

COUNCIL_PAGE = 'http://www.ville.sainte-anne-de-bellevue.qc.ca/Democratie.aspx'


class SainteAnneDeBellevuePersonScraper(CanadianScraper):

  def get_people(self):
    page = lxmlize(COUNCIL_PAGE)

    councillors = page.xpath('//div[@id="content"]//td')
    councillors = [x for x in councillors if x.text_content().strip()]
    images = page.xpath('//div[@id="content"]//td//img/@src')
    for i, councillor in enumerate(councillors):
      if 'Maire' in councillor.text_content():
        name = councillor.xpath('.//a')[0].text_content()
        district = 'Sainte-Anne-de-Bellevue'
        role = 'Mayor'
      else:
        name = re.findall(r'(?<=[0-9]).*', councillor.text_content(), flags=re.DOTALL)[0].strip()
        district = re.findall(r'(.*[0-9])', councillor.text_content())[0].replace('Conseiller', '')
        role = 'Councillor'

      p = Legislator(name=name, post_id=district)
      p.add_source(COUNCIL_PAGE)
      p.role = role

      p.image = images[i]

      email = councillor.xpath('.//a')
      if email:
        email = email[0].attrib['href'].replace('mailto:', '')
        p.add_contact('email', email, None)
      yield p
