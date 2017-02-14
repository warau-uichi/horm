# coding: utf-8
import os
from pyramid.view import view_config
import pyramid.httpexceptions as exc

import logging

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)

import pylast

from googleapiclient.discovery import build


logger = logging.getLogger(__name__)

# LINE API
line_bot_api = LineBotApi('CHANNEL_ACCESS_TOKEN')
handler = WebhookHandler('CHANNEL_SECRET')

# Last.fm API
lafm_api_key = 'LASTFM_API_KEY'
lafm_api_secret = 'LASTFM_API_SECRET'
lafm_username = 'LASTFM_USERNAME'
lafm_passwd_hash   = pylast.md5('LASTFM_PASSWD')

network = pylast.LastFMNetwork(api_key = lafm_api_key, api_secret = \
    lafm_api_secret, username = lafm_username, password_hash = lafm_passwd_hash)

# Google API
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.join('/path/to/credentials.json')
yt_data_api_key = 'YOUTUBE_DATA_API_KEY'
yt_api_service_name = 'youtube'
yt_api_version = 'v3'

youtube = build(yt_api_service_name, yt_api_version,
    developerKey=yt_data_api_key)

@view_config(route_name='callback', request_method='POST')
def callback(request):
    signature = request.headers['X-Line-Signature']
    body = request.body.decode('utf-8')
    logger.info(body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        raise exc.HTTPBadRequest()

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text
    elements = text.split('\n')
    artist_str, track_str, repl_msg = None, None, None
    for e in elements:
        if e.startswith('a '):
            artist_str = e[2:]
        elif e.startswith('t '):
            track_str = e[2:]
    if artist_str and track_str:
        track = network.get_track(artist_str.encode('utf-8').decode('utf-8'),
                                  track_str.encode('utf-8').decode('utf-8'))
        rcmds = track.get_similar()
        results = []
        for idx, rcmd in enumerate(rcmds):
            if idx == 3:
                break
            item = rcmd.item
            artist_name = item.artist.name.encode('utf-8').decode('utf-8')
            title = item.title.encode('utf-8').decode('utf-8')
            video_title = '-'.join([artist_name, title])
            search_response = youtube.search().list(
                q=video_title,
                part="id",
                maxResults=1
            ).execute()
            vid = search_response['items'][0]['id']['videoId']
            yt_url = 'https://youtu.be/'+vid
            results.append(video_title)
            results.append(yt_url)
        repl_msg = '\n'.join(results)
        logger.info('msg: {m}'.format(m=repl_msg.encode('utf-8')))

    # elif artist_str and not track_str:

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=repl_msg))

@view_config(route_name='home', renderer='templates/mytemplate.jinja2')
def my_view(request):
    return {'project': 'horm'}
