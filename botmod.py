# -*- coding: utf-8 -*-
"""
Created on Sat Sep  1 11:18:39 2018

@author: fuke masasi
"""

import tornado.ioloop
import tornado.web
import tornado.escape
import os, re, glob
from tinydb import *
import dbjson
from datetime import datetime
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError
from linebot.models import TextSendMessage


class WebHookHandler(tornado.web.RequestHandler):        
    def main(self, no):
        #pz = pytz.timezone('Asia/Tokyo')
        now = datetime.now()#pz)
        t = now.hour
        w = now.weekday()
        if (w < 5)and(t >= 9)and(t < 16):
            return u'仕事中.'
        table, na = self.users()
        item = table.find({'no':re.compile(no,re.IGNORECASE)})
        if item.count() == 1:
            x = item[0]
            ans = x['name']+'\n'+x['no']
        elif item.count() > 1:
            ans = ''    
            obj = list(item)
            list1 = sorted(obj, key=lambda k:k['name'])
            for x in list1:
                if x['name'] == list1[0]['name']:
                    ans += x['name']+'\n'+x['no']+'\n'
                else:
                    break
            else:
                return ans       
            ans = self.itr(sorted(list1, key=lambda k:k['no']))
        else:
            ans = self.itr(table.find().sort('no'))
            ans = '-*-'+na+' list-*-\n'+ans
        return ans
    
    def itr(self, item):
        ans = ''
        for x in item:
            ans += '【'+x['no']+'】 '
        return ans
    
    def help(self):
        s = '-*-database names-*-\n'
        out = ['objectlabs-system','objectlabs-system.admin.collections','users_bot']
        for x in self.database.collection_names(include_system_collections=False):
            if not x in out and x[-4:] == '_bot':
                s += x[:-4]+'\n'
        return s
    
    def setting(self, dbname):
        dbname = dbname.lower()+'_bot'
        ca = self.database.tables()
        ca.remove('users_bot')
        if dbname in ca:
            db = self.database['users_bot']
            item = db.get(where('name') == self.uid)
            if item['dbname'] == dbname:
                return False
            else:
                db.update({'name':self.uid, 'dbname':dbname},where('name') == self.uid)
                return True
        return False

    def users(self):
        db = self.database.table('users_bot')
        item = db.get(where('name') == self.uid)
        x = item['dbname']
        return self.database.table(x), x[:-4]
                          
    def post(self):
        '''
        signature = self.request.headers['X-Line-Signature']
        body = self.request.body
        parser = WebhookParser(ch)
        try:
            parser.parse(body, signature)
        except InvalidSignatureError:
            tornado.web.HTTPError(404)
            return
        '''
        dic = tornado.escape.json_decode(self.request.body)              
        for event in dic['events']:
            if 'replyToken' in event.keys():
                self.uid = event['source']['userId']
                self.database = TinyDB(st.json) 
                bot = 'users_bot'      
                tb = self.database.table(bot)         
                if event['type'] == 'unfollow':
                    tb.remove(where('name') == self.uid)
                    return
                elif event['type'] == 'join':
                    if not tb.get(where('name') == self.uid):
                        item = tb['params'].get(where('app') == 'bot')
                        if not item:
                            de = '_bot'
                        else:
                            de = item['default']
                        tb.insert({'name':self.uid, 'dbname':de})
                    return
                x = event['message']['text']                
                if self.setting(x):
                    te = u'設定完了.'
                elif x == '?':
                    te = self.help()
                else:
                    te = self.main(x)
                linebot.reply_message(event['replyToken'], TextSendMessage(text=te))

class InitHandler(tornado.web.RequestHandler):
    def get(self):        
        de = self.get_argument('default', '')
        if de == '':
            self.write('set default db name')
            return
        self.db = TinyDB(st.json)
        self.db['params'].insert({'app':'bot', 'default':de+'_bot'})
        for x in glob.glob('./*.txt'):
            f = open(x)
            data = f.read()
            f.close()
            self.main(x[2:-4].lower(), data)
    
    def main(self, name, data):
        if name == 'requirements':
            return
        item = []
        dic = None
        for x in data.split('\n'):
            if len(x) > 0 and x[0] == '@':
                dic = {}
                dic['name'] = x[1:]
            elif dic:
                dic['no'] = x
                item.append(dic)
        table = self.db.table(name+'_bot')
        table.purge()
        for x in item:
            table.insert(x)
                     
class VarParam():
    file = open('.env','r')
    str = file.readline()
    while str:
        if str[:12] == 'Access_Token':
            token = str[13:]
        elif str[:14] == 'Channel_Secret':
            ch = str[15:]
        str = file.readline()

var = VarParam()
st = dbjson.static()

    