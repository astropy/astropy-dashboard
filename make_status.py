#!/usr/bin/env python

import sys
from jinja2 import Template
from yaml import load
import requests


def normalize_repo_name(repo):
    # Put the normalization in one place to avoid future copy-paste errors
    return repo.lower()


with open('dashboard.yml') as f:
    config = load(f)

# Use the repo name (owner/repo) as the key instead of just repo. The
# combination of owner/repo should be the same in both the affiliated
# package registry and dashboard.yml.
existing = {normalize_repo_name(package['repo']): package
            for section in config
            for package in section['packages']}

# Also get affiliated packages
registry = requests.get('http://www.astropy.org/affiliated/registry.json').json()['packages']
for section in config:
    if section['name'] == 'Affiliated Packages':
        affiliated = section
        break
else:
    print("Could not find affiliated package section in dashboard.yml")
    sys.exit(1)

for package in registry:
    # There was an issue in that the package name in the affiliated
    # package registry is a separate field (name) but the name in dashboard.yml
    # is the name of the github repo, and the two can differ. A prior version
    # of this code tried to match the affiliated package registry name, i.e.
    # package['name'] to repo part of owner/repo, which doesn't work if the
    # repo name is different than the package name.

    # Since all of the affiliated packages have a github repo, and since
    # the owner/repo should match in dashboard.yml and the affiliated
    # package recipe, use pkg_repo below. In the event that an entry in
    # the affiliated package registry does not have a github repo, raise
    # an exception.
    if 'github.com' in package['repo_url']:
        pkg_repo = package['repo_url'].split('github.com/')[1]
        # Normalize pkg_repo to match what is done above in existing
        pkg_repo = normalize_repo_name(pkg_repo)
    else:
        raise ValueError('The package named {} from the affiliated package '
                         'registry does not have a GitHub '
                         'repository.'.format(package['name']))

    if pkg_repo in existing:
        entry = existing[pkg_repo]
    else:
        entry = {}

    if 'repo' not in entry:
        if pkg_repo:
            entry['repo'] = pkg_repo

    if 'pypi_name' not in entry:
        entry['pypi_name'] = package['pypi_name']
    if 'badges' not in entry:
        entry['badges'] = 'travis, coveralls, rtd, pypi, conda'
    if pkg_repo not in existing:
        affiliated['packages'].append(entry)

for section in config:
    for package in section['packages']:
        package['user'], package['name'] = package['repo'].split('/')
        package['badges'] = [x.strip() for x in package['badges'].split(',')]
        if 'rtd_name' not in package:
            package['rtd_name'] = package['name']
        if 'pypi_name' not in package:
            package['pypi_name'] = package['name']
        if 'appveyor' in package['badges'] and 'appveyor_project' not in package:
            package['appveyor_project'] = package['repo']
        if 'circleci' in package['badges'] and 'circleci_project' not in package:
            package['circleci_project'] = package['repo']
        if 'travis' in package['badges'] and 'travis_project' not in package:
            package['travis_project'] = package['repo']
        if 'conda' in package['badges'] and 'conda_project' not in package:
            package['conda_project'] = 'astropy/' + package['name']

affiliated['packages'] = sorted(affiliated['packages'], key=lambda x: x['name'].lower())

template = Template(open('template.html', 'r').read())


with open('status.html', 'w') as f:
    f.write(template.render(config=config))
