# -*- coding: utf-8 -*-

"""
.. module:: run_db_insert_test_issues.py
   :license: GPL/CeCIL
   :platform: Unix, Windows
   :synopsis: Inserts test issues into the errata db.

.. moduleauthor:: Atef Bennasser <abenasser@ipsl.jussieu.fr>


"""
import argparse
import datetime as dt
import glob
import json
import os
import random
import uuid

import sqlalchemy

import errata
from errata import db
from errata.constants import STATE_CLOSED
from errata.constants import STATE_OPEN
from errata.db.models import Issue
from errata.utils import logger


# Define command line arguments.
_ARGS = argparse.ArgumentParser("Inserts test issues into errata database.")
_ARGS.add_argument(
    "-d", "--dir",
    help="Directory containing test issues in json file format",
    dest="input_dir",
    type=str
    )
_ARGS.add_argument(
    "-c", "--count",
    help="Numbers of issues to insert into database",
    dest="count",
    type=int
    )


# Global now.
_NOW = dt.datetime.now()


def _get_issue(obj):
    """Maps a dictionary decoded from a file to an issue instance.

    """
    issue = Issue()
    issue.date_created = obj['created_at']
    issue.date_updated = obj['last_updated_at']
    issue.date_closed = obj['closed_at']
    issue.description = obj['description']
    issue.institute = obj['institute']
    issue.materials = ",".join(obj['materials'])
    issue.severity = obj['severity'].lower()
    issue.state = STATE_CLOSED if issue.date_closed else STATE_OPEN
    issue.project = obj['project'].lower()
    issue.title = obj['title']
    issue.uid = obj['id']
    issue.url = obj['url']
    issue.workflow = obj['workflow'].lower()

    # TODO get datasets
    issue.dsets = None

    return issue


def _yield_issues(input_dir, count):
    """Yields a large number of issues for testing purposes.

    """
    # Open set of test issues.
    issues = []
    for fpath in glob.iglob("{}/*.json".format(input_dir)):
        with open(fpath, 'r') as fstream:
            issues.append(_get_issue(json.loads(fstream.read())))

    # Get a test issue, update it & yield.
    for i in xrange(count):
        i = issues[i % len(issues)]
        issue = Issue()
        issue.date_created = _NOW - dt.timedelta(days=random.randint(30, 60))
        issue.date_updated = issue.date_created + dt.timedelta(days=2)
        if random.randint(0, 1):
            issue.date_closed = issue.date_updated + dt.timedelta(days=2)
        issue.description = i.description
        issue.institute = random.choice(list(errata.constants.INSTITUTE))
        issue.materials = i.materials
        issue.severity = random.choice(errata.constants.SEVERITY)['key']
        issue.state = random.choice(errata.constants.STATE)['key']
        issue.project = random.choice(list(errata.constants.PROJECT))
        issue.title = unicode(uuid.uuid4())[:50]
        issue.uid = unicode(uuid.uuid4())
        issue.url = i.url
        issue.workflow = random.choice(errata.constants.WORKFLOW)['key']
        yield issue


def _main(args):
    """Main entry point.

    """
    if not os.path.exists(args.input_dir):
        raise ValueError("Input directory is invalid.")

    with db.session.create():
        for issue in _yield_issues(args.input_dir, args.count):
            try:
                db.session.insert(issue)
            except sqlalchemy.exc.IntegrityError:
                logger.log_db("issue skipped (already inserted) :: {}".format(issue.uid))
                db.session.rollback()
            except UnicodeDecodeError:
                logger.log_db('DECODING EXCEPTION')
            else:
                logger.log_db("issue inserted :: {}".format(issue.uid))


# Main entry point.
if __name__ == '__main__':
    _main(_ARGS.parse_args())
