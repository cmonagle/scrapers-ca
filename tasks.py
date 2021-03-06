# coding: utf-8
from __future__ import unicode_literals

import codecs
import csv
import importlib
import os
import re

import lxml.html
import requests
from invoke import task
from opencivicdata.divisions import Division
from six import next, StringIO, text_type
from six.moves.urllib.parse import urlsplit
from unidecode import unidecode


# Map Standard Geographical Classification codes to the OCD identifiers of provinces and territories.
province_and_territory_codes_memo = {}

# Map OpenCivicData Division Identifier to Census type name.
ocdid_to_type_name_map = {}


def province_and_territory_codes():
    if not province_and_territory_codes_memo:
        for division in Division.all('ca'):
            if division._type in ('province', 'territory'):
                province_and_territory_codes_memo[division.attrs['sgc']] = division.id
    return province_and_territory_codes_memo


def csv_reader(url):
    """
    Reads a remote CSV file.
    """
    return csv.reader(StringIO(requests.get(url).text))


def slug(name):
    return unidecode(text_type(name).lower().translate({
        ord(' '): '_',
        ord("'"): '_',
        ord('-'): '_',  # dash
        ord('—'): '_',  # m-dash
        ord('–'): '_',  # n-dash
        ord('.'): None,
    }))


def get_definition(division_id, aggregation=False):
    if not ocdid_to_type_name_map:
        # Map census division type codes to names.
        census_division_type_names = {}
        document = lxml.html.fromstring(requests.get('https://www12.statcan.gc.ca/census-recensement/2011/ref/dict/table-tableau/table-tableau-4-eng.cfm').content)
        for abbr in document.xpath('//table/tbody/tr/th[1]/abbr'):
            census_division_type_names[abbr.text_content()] = re.sub(' ?/.+\Z', '', abbr.attrib['title'])

        # Map census subdivision type codes to names.
        census_subdivision_type_names = {}
        document = lxml.html.fromstring(requests.get('https://www12.statcan.gc.ca/census-recensement/2011/ref/dict/table-tableau/table-tableau-5-eng.cfm').content)
        for abbr in document.xpath('//table/tbody/tr/th[1]/abbr'):
            census_subdivision_type_names[abbr.text_content()] = re.sub(' ?/.+\Z', '', abbr.attrib['title'])

        # Map OCD identifiers to census types.
        for division in Division.all('ca'):
            if division._type == 'cd':
                ocdid_to_type_name_map[division.id] = census_division_type_names[division.attrs['classification']]
            elif division._type == 'csd':
                ocdid_to_type_name_map[division.id] = census_subdivision_type_names[division.attrs['classification']]

    codes = province_and_territory_codes()
    division = Division.get(division_id)

    expected = {}
    vowels = ('A', 'À', 'E', 'É', 'I', 'Î', 'O', 'Ô', 'U')

    sections = division_id.split('/')
    ocd_type, ocd_type_id = sections[-1].split(':')

    # Determine the module name, name and classification.
    if ocd_type == 'country':
        expected['module_name'] = 'ca'
        expected['name'] = 'Parliament of Canada'
    elif ocd_type in ('province', 'territory'):
        pattern = 'ca_{}_municipalities' if aggregation else 'ca_{}'
        expected['module_name'] = pattern.format(ocd_type_id)
        if aggregation:
            expected['name'] = '{} Municipalities'.format(division.name)
        elif ocd_type_id in ('nl', 'ns'):
            expected['name'] = '{} House of Assembly'.format(division.name)
        elif ocd_type_id == 'qc':
            expected['name'] = 'Assemblée nationale du Québec'
        else:
            expected['name'] = 'Legislative Assembly of {}'.format(division.name)
    elif ocd_type == 'cd':
        province_or_territory_type_id = codes[ocd_type_id[:2]].split(':')[-1]
        expected['module_name'] = 'ca_{}_{}'.format(province_or_territory_type_id, slug(division.name))
        name_infix = ocdid_to_type_name_map[division_id]
        if name_infix == 'Regional municipality':
            name_infix = 'Regional'
        expected['name'] = '{} {} Council'.format(division.name, name_infix)
    elif ocd_type == 'csd':
        province_or_territory_type_id = codes[ocd_type_id[:2]].split(':')[-1]
        expected['module_name'] = 'ca_{}_{}'.format(province_or_territory_type_id, slug(division.name))
        if ocd_type_id[:2] == '24':
            if division.name[0] in vowels:
                expected['name'] = "Conseil municipal d'{}".format(division.name)
            else:
                expected['name'] = "Conseil municipal de {}".format(division.name)
        else:
            name_infix = ocdid_to_type_name_map[division_id]
            if name_infix in ('Municipality', 'Specialized municipality'):
                name_infix = 'Municipal'
            elif name_infix == 'District municipality':
                name_infix = 'District'
            elif name_infix == 'Regional municipality':
                name_infix = 'Regional'
            expected['name'] = '{} {} Council'.format(division.name, name_infix)
    elif ocd_type == 'arrondissement':
        census_subdivision_type_id = sections[-2].split(':')[-1]
        province_or_territory_type_id = codes[census_subdivision_type_id[:2]].split(':')[-1]
        expected['module_name'] = 'ca_{}_{}_{}'.format(province_or_territory_type_id, slug(Division.get('/'.join(sections[:-1])).name), slug(division.name))
        if division.name[0] in vowels:
            expected['name'] = "Conseil d'arrondissement d'{}".format(division.name)
        elif division.name[:3] == 'Le ':
            expected['name'] = "Conseil d'arrondissement du {}".format(division.name[3:])
        else:
            expected['name'] = "Conseil d'arrondissement de {}".format(division.name)
    else:
        raise Exception('{}: Unrecognized OCD type {}'.format(division_id, ocd_type))

    # Determine the class name.
    class_name_parts = re.split('[ -]', re.sub("[—–]", '-', re.sub("['.]", '', division.name)))
    expected['class_name'] = unidecode(text_type(''.join(word if re.match('[A-Z]', word) else word.capitalize() for word in class_name_parts)))
    if aggregation:
        expected['class_name'] += 'Municipalities'

    # Determine the url.
    expected['url'] = division.attrs['url']

    # Determine the division name.
    expected['division_name'] = division.name

    return expected


@task
def urls():
    for module_name in os.listdir('.'):
        if os.path.isdir(module_name) and module_name not in ('.git', '_cache', '_data', '__pycache__', 'csv', 'disabled'):
            module = importlib.import_module('{}.people'.format(module_name))
            class_name = next(key for key in module.__dict__.keys() if 'PersonScraper' in key)
            if module.__dict__[class_name].__bases__[0].__name__ == 'CSVScraper':
                if module.__dict__.get('COUNCIL_PAGE'):
                    print('{:<60} Delete COUNCIL_PAGE'.format(module_name))
            else:
                if module.__dict__.get('COUNCIL_PAGE'):
                    print('{:<60} {}'.format(module_name, module.__dict__['COUNCIL_PAGE']))
                else:
                    print('{:<60} Missing COUNCIL_PAGE'.format(module_name))


@task
def tidy():
    # Map OCD identifiers to styles of address.
    leader_styles = {}
    member_styles = {}
    for gid in range(3):
        reader = csv_reader('https://docs.google.com/spreadsheets/d/11qUKd5bHeG5KIzXYERtVgs3hKcd9yuZlt-tCTLBFRpI/pub?single=true&gid={}&output=csv'.format(gid))
        next(reader)
        for row in reader:
            key = row[0]
            leader_styles[key] = row[2]
            member_styles[key] = row[3]

    for module_name in os.listdir('.'):
        division_ids = set()
        jurisdiction_ids = set()

        if os.path.isdir(module_name) and module_name not in ('.git', '_cache', '_data', '__pycache__', 'csv', 'disabled') and not module_name.endswith('_candidates'):
            metadata = module_name_to_metadata(module_name)

            # Ensure division_id is unique.
            division_id = metadata['division_id']
            if division_id in division_ids:
                raise Exception('{}: Duplicate division_id {}'.format(module_name, division_id))
            else:
                division_ids.add(division_id)

            # Ensure jurisdiction_id is unique.
            jurisdiction_id = metadata['jurisdiction_id']
            if jurisdiction_id in jurisdiction_ids:
                raise Exception('{}: Duplicate jurisdiction_id {}'.format(module_name, jurisdiction_id))
            else:
                jurisdiction_ids.add(jurisdiction_id)

            expected = get_definition(division_id, bool(module_name.endswith('_municipalities')))

            # Ensure presence of url and styles of address.
            if not member_styles.get(division_id):
                print('{:<60} Missing member style of address: {}'.format(module_name, division_id))
            if not leader_styles.get(division_id):
                print('{:<60} Missing leader style of address: {}'.format(module_name, division_id))
            url = metadata['url']
            if url and not expected['url']:
                parsed = urlsplit(url)
                if parsed.scheme not in ('http', 'https') or parsed.path or parsed.query or parsed.fragment:
                    print('{:<60} Check: {}'.format(module_name, url))

            # Warn if the name or classification may be incorrect.
            name = metadata['name']
            if name != expected['name']:
                print('{:<60} Expected {}'.format(name, expected['name']))
            classification = metadata['classification']
            if classification != 'legislature':
                print('{:<60} Expected legislature'.format(classification))

            # Name the classes correctly.
            class_name = metadata['class_name']
            if class_name != expected['class_name']:
                # @note This for-loop will only run if the class name in __init__.py is incorrect.
                for basename in os.listdir(module_name):
                    if basename.endswith('.py'):
                        with codecs.open(os.path.join(module_name, basename), 'r', 'utf8') as f:
                            content = f.read()
                        with codecs.open(os.path.join(module_name, basename), 'w', 'utf8') as f:
                            content = content.replace(class_name + '(', expected['class_name'] + '(')
                            f.write(content)

            # Set the division_name and url appropriately.
            division_name = metadata['division_name']
            if division_name != expected['division_name'] or (expected['url'] and url != expected['url']):
                with codecs.open(os.path.join(module_name, '__init__.py'), 'r', 'utf8') as f:
                    content = f.read()
                with codecs.open(os.path.join(module_name, '__init__.py'), 'w', 'utf8') as f:
                    if division_name != expected['division_name']:
                        content = content.replace('= ' + division_name, '= ' + expected['division_name'])
                    if expected['url'] and url != expected['url']:
                        content = content.replace(url, expected['url'])
                    f.write(content)

            # Name the module correctly.
            if module_name != expected['module_name']:
                print('{:<60} Expected {}'.format(module_name, expected['module_name']))


@task
def sources_and_assertions():
    for module_name in os.listdir('.'):
        if os.path.isdir(module_name) and module_name not in ('.git', '_cache', '_data', '__pycache__', 'csv', 'disabled'):
            path = os.path.join(module_name, 'people.py')
            with codecs.open(path, 'r', 'utf-8') as f:
                content = f.read()

                source_count = content.count('add_source')
                request_count = content.count('lxmlize') + content.count('self.get(') + content.count('requests.get')
                if source_count < request_count:
                    print('Expected {} sources after {} requests {}'.format(source_count, request_count, path))

                if 'CSVScraper' not in content and 'assert len(' not in content:
                    print("Expected an assertion like: assert len(councillors), 'No councillors found' {}".format(path))


def module_name_to_metadata(module_name):
    """
    Copied from `reports.utils`.
    """
    module = importlib.import_module(module_name)
    for obj in module.__dict__.values():
        division_id = getattr(obj, 'division_id', None)
        if division_id:
            return {
                'class_name': obj.__name__,
                'division_id': division_id,
                'division_name': getattr(obj, 'division_name', None),
                'name': getattr(obj, 'name', None),
                'url': getattr(obj, 'url', None),
                'classification': getattr(obj, 'classification', None),
                'jurisdiction_id': '{}/{}'.format(division_id.replace('ocd-division', 'ocd-jurisdiction'), getattr(obj, 'classification', 'legislature')),
            }
