#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import config
from sanic import response
from app import app
from app import cache
from app.models.site import Site
from app.models.comment import Comment
from app.helpers.hashing import md5
from app.services import processor

logger = logging.getLogger(__name__)


@app.route("/comments", methods=['GET'])
def query_comments(request):

    comments = []
    try:
        token = request.args.get('token', '')
        url = request.args.get('url', '')

        logger.info('retrieve comments for token %s, url %s' % (token, url))
        for comment in Comment.select(Comment).join(Site).where(
                (Comment.url == url) &
                (Comment.published.is_null(False)) &
                (Site.token == token)).order_by(+Comment.published):
            d = {}
            d['author'] = comment.author_name
            d['content'] = comment.content
            if comment.author_site:
                d['site'] = comment.author_site
            if comment.author_email:
                d['avatar'] = md5(comment.author_email.strip().lower())
            d['date'] = comment.published.strftime("%Y-%m-%d %H:%M:%S")
            logger.debug(d)
            comments.append(d)
        r = response.json({'data': comments})
    except:
        logger.warn('bad request')
        r = response.json({'data': []}, status=400)
    return r


#@cache.cached(timeout=300)
@app.route("/comments/count", methods=['GET'])
def get_comments_count(request):
    try:
        token = request.args.get('token', '')
        url = request.args.get('url', '')
        count = Comment.select(Comment).join(Site).where(
            (Comment.url == url) &
            (Comment.published.is_null(False)) &
            (Site.token == token)).count()
        r = response.json({'count': count})
    except:
        r = response.json({'count': 0})
    return r


@app.route("/comments", methods=['POST'])
def new_comment(request):

    try:
        data = request.json
        logger.info(data)

        # validate token: retrieve site entity
        token = data.get('token', '')
        site = Site.select().where(Site.token == token).get()
        if site is None:
            logger.warn('Unknown site %s' % token)
            return response.text('BAD_REQUEST', status=400)

        # honeypot for spammers
        captcha = data.get('captcha', '')
        if captcha:
            logger.warn('discard spam: data %s' % data)
            return response.text('BAD_REQUEST', status=400)

        processor.enqueue({'request': 'new_comment', 'data': data})

    except:
        logger.exception("new comment failure")
        return response.text('BAD_REQUEST', status=400)

    return response.text('OK')


@app.route("/report", methods=['GET'])
def report(request):

    try:
        token = request.args.get('token', '')
        secret = request.args.get('secret', '')

        if secret != config.SECRET:
            logger.warn('Unauthorized request')
            return response.text('UNAUTHORIZED', status=401)

        site = Site.select().where(Site.token == token).get()
        if site is None:
            logger.warn('Unknown site %s' % token)
            return response.text('', status=404)

        processor.enqueue({'request': 'report', 'data': token})


    except:
        logger.exception("report failure")
        return response.text('ERROR', status=500)

    return response.text('OK')


@app.route("/accept", methods=['GET'])
def accept_comment(request):

    try:
        id = request.args.get('comment', '')
        secret = request.args.get('secret', '')

        if secret != config.SECRET:
            logger.warn('Unauthorized request')
            return response.text('UNAUTHORIZED', status=401)

        processor.enqueue({'request': 'late_accept', 'data': id})

    except:
        logger.exception("accept failure")
        return response.text('', status=500)

    return response.text('PUBLISHED')


@app.route("/reject", methods=['GET'])
def reject_comment(request):

    try:
        id = request.args.get('comment', '')
        secret = request.args.get('secret', '')

        if secret != config.SECRET:
            logger.warn('Unauthorized request')
            return response.text('UNAUTHORIZED', status=401)

        processor.enqueue({'request': 'late_reject', 'data': id})

    except:
        logger.exception("reject failure")
        return response.text('ERROR', status=500)

    return response.text('REJECTED')
