#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2014 hubsif (hubsif@gmx.de)
#
# This program is free software; you can redistribute it and/or modify it under the terms 
# of the GNU General Public License as published by the Free Software Foundation; 
# either version 2 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; 
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. 
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; 
# if not, see <http://www.gnu.org/licenses/>.

##############
# preparations
##############

import xbmc, xbmcplugin, xbmcgui, xbmcaddon
import os, sys, re, json, string, random, time
import xml.etree.ElementTree as ET
import urllib
import urlparse

_addon_id      = 'plugin.video.tk_del'
_addon         = xbmcaddon.Addon(id=_addon_id)
_addon_name    = _addon.getAddonInfo('name')
_addon_handler = int(sys.argv[1])
_addon_url     = sys.argv[0]
_addon_path    = xbmc.translatePath(_addon.getAddonInfo("path") )
__language__   = _addon.getLocalizedString
 
sys.path.append(os.path.join(_addon_path, 'resources', 'lib'))
import mechanize

# don't know if that's needed, as it is already defined in addon.xml
xbmcplugin.setContent(_addon_handler, 'videos')


###########
# functions
###########

def build_url(query):
    return _addon_url + '?' + urllib.urlencode(query)

def get_live(json):
    if 'isLive' in json and json['isLive'] == 'true':
        print 'found islive'
        if json['children']:
            print 'recursing'
            for child in json['children']:
                result = get_live(child)
                if result:
                    return result
        else:
            print 'returning ' + json['href']
            return json['href']


##############
# main routine
##############

import datetime
datetime.datetime.now()
datetime.datetime.utcnow()

browser = mechanize.Browser()
browser.set_handle_robots(False)

# urllib ssl fix
import ssl
from functools import wraps
def sslwrap(func):
    @wraps(func)
    def bar(*args, **kw):
        kw['ssl_version'] = ssl.PROTOCOL_TLSv1
        return func(*args, **kw)
    return bar
ssl.wrap_socket = sslwrap(ssl.wrap_socket)

# get arguments
args = urlparse.parse_qs(sys.argv[2][1:])
mode = args.get('mode', None)

if mode is None:
    # load menu
    response = urllib.urlopen("https://www.telekomeishockey.de/feeds/appfeed.php?type=videolist").read()
    jsonResult = json.loads(response)

    menuitems = set()
    for content in jsonResult['content']:
        menuitems.add(content['mediatype_title'])

    for mediatype in jsonResult['mediatypes']:
        url = build_url({'mode': '1', 'mediatype_id': mediatype['id']})
        li = xbmcgui.ListItem(mediatype['title'].title(), iconImage='DefaultFolder.png')
        xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li, isFolder=True)

    xbmcplugin.addDirectoryItem(handle=_addon_handler, url=build_url({'mode': '2'}), listitem=xbmcgui.ListItem('Wiederholungen nach Mannschaften', iconImage='DefaultFolder.png'), isFolder=True)
    xbmcplugin.addDirectoryItem(handle=_addon_handler, url=build_url({'mode': '3'}), listitem=xbmcgui.ListItem('Zusammenfassungen nach Mannschaften', iconImage='DefaultFolder.png'), isFolder=True)
    xbmcplugin.endOfDirectory(_addon_handler)
elif mode[0] == '1' or mode[0]=='6':
    page=1
    response = urllib.urlopen("https://www.telekomeishockey.de/feeds/appfeed.php?type=videolist&mediatype="+args['mediatype_id'][0]+"&page="+str(page)).read()
    jsonResult = json.loads(response)
    
    for page in range(0,jsonResult['total_pages']):
        response = urllib.urlopen("https://www.telekomeishockey.de/feeds/appfeed.php?type=videolist&mediatype="+args['mediatype_id'][0]+"&page="+str(page+1)).read()
        jsonResult = json.loads(response)

        for content in jsonResult['content']:
            format = '%Y-%m-%d %H:%M:%S'
            now = datetime.datetime.now()
            try:
                start = datetime.datetime.strptime(content['scheduled_start'], format)
            except TypeError:
                start = datetime.datetime(*(time.strptime(content['scheduled_start'], format)[0:6]))
            if start.strftime("%d.%m.%y")==now.strftime("%d.%m.%y"):
                Startzeit=start.strftime("%H:%M")
            else:
                Startzeit=start.strftime("%d.%m. %H:%M")
            url = build_url({'mode': '4', 'id': content['id'], 'scheduled_start': content['scheduled_start'], 'isPay': content['isPay'], 'thumbnailImage': 'https://www.telekomeishockey.de' + content['teaser_image_small']})
            li = xbmcgui.ListItem(content['title_long']+' ('+Startzeit+')', iconImage='https://www.telekomeishockey.de' + content['teaser_image_small'])
            info = {'plot':'Spiel '+content['title_long']+' ('+content['round_1']+': '+content['round_2']+')','date':content['scheduled_start'],}
            li.setInfo('video',info)
            li.setProperty('fanart_image', 'https://www.telekomeishockey.de' + content['teaser_image_big'])
            li.setProperty('IsPlayable', 'true')
            if mode[0]=='6' and (content["team_a_title_short"]==args['team'][0] or content["team_b_title_short"]==args['team'][0]):
                xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li)
            elif mode[0]=='1':
                xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li)
    xbmcplugin.endOfDirectory(_addon_handler)

elif mode[0] == '4':
    scheduled_start = args['scheduled_start'][0]
    now = datetime.datetime.now()
    format = '%Y-%m-%d %H:%M:%S'
    try:
        start = datetime.datetime.strptime(scheduled_start, format)
    except TypeError:
        start = datetime.datetime(*(time.strptime(scheduled_start, format)[0:6]))

    start= start-datetime.timedelta(0,0,0,0,0,1) #Stream eine Stunde vorher beginnen
        
    if now < start-datetime.timedelta(0,0,0,0,0,1):
        xbmcgui.Dialog().ok(_addon_name, __language__(30004), "", start.strftime("%d.%m.%Y %H:%M"))
    else:
        if args['isPay'][0] == 'True':
            if not _addon.getSetting('username'):
                xbmcgui.Dialog().ok(_addon_name, __language__(30003))
                _addon.openSettings()
            else:
                browser.open("https://www.telekomeishockey.de/service/oauth/login.php?headto=https://www.telekomeishockey.de/del")
                browser.select_form(name="login")
                browser.form['pw_usr'] = _addon.getSetting('username')
                browser.form['pw_pwd'] = _addon.getSetting('password')
                browser.submit()
        
        browser.open("https://www.telekomeishockey.de/videoplayer/player.php?play=" + args['id'][0])
        response = browser.response().read()
        
        if 'class="subscription_error"' in response:
            xbmcgui.Dialog().ok(_addon_name, __language__(30005))
            sys.exit(0)
            
        mobileUrl = re.search('mobileUrl: \"(.*?)\"', response).group(1)

        browser.open(mobileUrl)
        response = browser.response().read()
        
        xmlroot = ET.ElementTree(ET.fromstring(response))
        playlisturl = xmlroot.find('token').get('url')
        auth = xmlroot.find('token').get('auth')
        
        listitem = xbmcgui.ListItem(path=playlisturl + "?hdnea=" + auth, thumbnailImage=args['thumbnailImage'][0])
        xbmcplugin.setResolvedUrl(_addon_handler, True, listitem)
elif mode[0] == '2' or mode[0] == '3':
    Mannschaften=[["Augsburger Panther","AUG"],['Eisbären Berlin',"EBB"],["Pinguins Bremerhaven","BHV"],["Düsseldorfer EG","DEG"],["ERC Ingolstadt","ING"],["Iserlohn Roosters","IEC"],["Krefeld Pinguine","KEV"],["Kölner Haie","KEC"],["Adler Mannheim","MAN"],["EHC Red Bull München","MUC"],["Thomas Sabo Ice Tigers","NIT"],["Schwenninger Wild Wings","SWW"],["Straubing Tigers","STR"],["Grizzlys Wolfsburg","WOB"]]
    menuitems = set()
    for team in Mannschaften:
        if mode[0]=='2':
            url = build_url({'mode': '6', 'mediatype_id':'3','team': team[1]})
        else:
            url = build_url({'mode': '6', 'mediatype_id':'5','team': team[1]})
        li = xbmcgui.ListItem(team[0], iconImage='https://www.telekomeishockey.de/assets/img/teams/teamL_'+team[1]+'.png')
        xbmcplugin.addDirectoryItem(handle=_addon_handler, url=url, listitem=li, isFolder=True)
    xbmcplugin.endOfDirectory(_addon_handler)
