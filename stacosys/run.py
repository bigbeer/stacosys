#!/usr/bin/python
# -*- coding: UTF-8 -*-

import argparse
import logging
import os

from flask import Flask
from flask_apscheduler import APScheduler

from conf import config


# configure logging
def configure_logging(level):
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    ch = logging.StreamHandler()
    ch.setLevel(level)
    # create formatter
    formatter = logging.Formatter('[%(asctime)s] %(name)s %(levelname)s %(message)s')
    # add formatter to ch
    ch.setFormatter(formatter)
    # add ch to logger
    root_logger.addHandler(ch)


class JobConfig(object):

    JOBS = []

    SCHEDULER_EXECUTORS = {'default': {'type': 'threadpool', 'max_workers': 4}}

    def __init__(self, imap_polling_seconds, new_comment_polling_seconds):
        self.JOBS = [
            {
                'id': 'fetch_mail',
                'func': 'core.cron:fetch_mail_answers',
                'trigger': 'interval',
                'seconds': imap_polling_seconds,
            },
            {
                'id': 'submit_new_comment',
                'func': 'core.cron:submit_new_comment',
                'trigger': 'interval',
                'seconds': new_comment_polling_seconds,
            },
        ]


def stacosys_server(config_pathname):

    app = Flask(__name__)
    config.initialize(config_pathname, app)

    # configure logging
    logger = logging.getLogger(__name__)
    configure_logging(logging.INFO)
    logging.getLogger('werkzeug').level = logging.WARNING
    logging.getLogger('apscheduler.executors').level = logging.WARNING

    # initialize database
    from core import database

    database.setup()

    # cron email fetcher
    app.config.from_object(
        JobConfig(
            config.get_int(config.IMAP_POLLING), config.get_int(config.COMMENT_POLLING)
        )
    )
    scheduler = APScheduler()
    scheduler.init_app(app)
    scheduler.start()

    logger.info('Start Stacosys application')

    # generate RSS for all sites
    from core import rss

    rss.generate_all()

    # start Flask
    from interface import api

    logger.info('Load interface %s' % api)

    from interface import form

    logger.info('Load interface %s' % form)

    app.run(
        host=config.get(config.HTTP_HOST),
        port=config.get(config.HTTP_PORT),
        debug=False,
        use_reloader=False,
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('config', help='config path name')
    args = parser.parse_args()
    stacosys_server(args.config)
