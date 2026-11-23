# SPDX-License-Identifier: GPL-3.0-or-later
"""1.16.1 (issue #22): folder ID tags from Sonarr / Radarr / Jellyfin / Plex naming are not part of the
title, so automatic matching searches AniList and AnimeThemes for the real name; AniList's "not found"
(HTTP 404) reads as "not identified", not as an error. Offline."""
import io
import sys
import urllib.error
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'preludarr'))
import app

results = []
def check(name, ok):
    results.append(bool(ok))
    print(('PASS ' if ok else 'FAIL ') + name)

for folder in ('Black Clover (2017) [tvdbid-331753]', 'Black Clover (2017) {tvdb-331753}',
               'Black Clover (2017) {imdb-tt7441658}', 'Black Clover (2017) [imdbid-tt7441658]',
               'Black Clover (2017) {tmdb-73223}', 'Black Clover (2017) [tmdbid-73223]',
               'Black Clover (2017) {anidb-12345}', 'Black Clover (2017) {tvdb-331753} {imdb-tt7441658}',
               'Black Clover (2017) - imdb-tt7441658', 'Black Clover (2017)'):
    check(f'{folder!r} -> title and year', (app.clean(folder), app.year(folder)) == ('Black Clover', 2017))
check('A tag in the middle is removed too', app.clean('Berserk {tvdb-73752} (1997)') == 'Berserk')
check('Real brackets in a title are kept', app.clean('Steins;Gate [Remastered] (2011)') == 'Steins;Gate [Remastered]')
check('A title with "id" in it is untouched', app.clean('Tvdb Squid (2020)') == 'Tvdb Squid')
check('No year, no tag', (app.clean('Monster'), app.year('Monster')) == ('Monster', None))

sent = []
def answer(url, body=None, **kwargs):
    sent.append(body)
    return {'data': {'Media': {'seasonYear': 2017, 'title': {'romaji': 'Black Clover'}}}}
with patch.object(app, 'request_json', side_effect=answer):
    media = app.anilist('Black Clover (2017) [tvdbid-331753]')
check('AniList is asked for the plain title', sent[0]['variables']['s'] == 'Black Clover' and media['seasonYear'] == 2017)

def not_found(*args, **kwargs):
    raise urllib.error.HTTPError('https://graphql.anilist.co', 404, 'Not Found', {}, io.BytesIO(b''))
with patch.object(app, 'request_json', side_effect=not_found):
    check("AniList's 404 means not identified", app.anilist('Some unknown title') is None)

def outage(*args, **kwargs):
    raise urllib.error.HTTPError('https://graphql.anilist.co', 500, 'Server Error', {}, io.BytesIO(b''))
with patch.object(app, 'request_json', side_effect=outage):
    try:
        app.anilist('Black Clover')
        check('Other AniList errors still surface', False)
    except urllib.error.HTTPError:
        check('Other AniList errors still surface', True)

print('%s/%s passed' % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
