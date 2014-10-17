# Canadian Legislative Scrapers

## Usage

Follow the instructions in the [Python Quick Start Guide](https://github.com/opennorth/opennorth.ca/wiki/Python-Quick-Start%3A-OS-X) to install Homebrew, Git, PostGIS, Python 3.3+ and virtualenv.

```
mkvirtualenv scrapers-ca
git clone git://github.com/opencivicdata/scrapers-ca.git
cd scrapers-ca
pip install -r requirements.txt
```

Initialize the database:

```
createdb pupa
psql pupa -c "CREATE EXTENSION postgis;"
pupa dbinit
```

## Run a scraper

    pupa update ca_ab_edmonton

To run only the scraping step and skip the import step add the `--scrape` switch:

    pupa update --scrape ca_ab_edmonton

For documentation on the `pupa` command:

    pupa -h

For documentation on the `update` subcommand:

    pupa update -h

## Create a scraper

Find division identifiers using the [Open Civic Data Division Identifier (OCD-ID) Viewer](http://opennorth.github.io/ocd-id-viewer/) or by browsing the [list of identifiers](https://github.com/opencivicdata/ocd-division-ids/blob/master/identifiers/country-ca.csv). In most cases, a municipality will have a division identifier with a type ID of `csd`. Then, create a scraper with:

    pupa init ca_on_toronto

## Develop a scraper

Read the [Pupa documentation](http://docs.opencivicdata.org/en/latest/scrape/basics.html) or an existing scraper's code.

## Maintenance

The `tidy` task verifies module names, class names, `classification`, `division_name`, `name` and `url` in `__init.py__` files.

    invoke tidy

To check that all sources are credited, run:

    invoke sources

To test [PEP 8](http://www.python.org/dev/peps/pep-0008/) conformance, run:

    flake8 .

To tidy all whitespace, run:

    autopep8 -i -a -r --ignore=E501 .

To check and print jurisdiction URLs:

    invoke urls

Periodically, update the OCD-IDs:

    curl -O https://raw.githubusercontent.com/opencivicdata/ocd-division-ids/master/identifiers/country-ca.csv

Scraper code rarely undergoes code review. The focus is on the quality of the data.

## Bugs? Questions?

This repository is on GitHub: [http://github.com/opencivicdata/scrapers-ca](http://github.com/opencivicdata/scrapers-ca), where your contributions, forks, bug reports, feature requests, and feedback are greatly welcomed.

Copyright (c) 2013 Open North Inc., released under the MIT license
