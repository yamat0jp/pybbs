# -*- coding:utf-8 -*-
import os,re,glob
from tornado import escape,web,ioloop,httpserver,httpclient
import pymongo, urllib
from datetime import datetime,timedelta
import json
from bson.objectid import ObjectId #don't remove
from linebot.api import LineBotApi
from linebot.exceptions import (InvalidSignatureError)
from linebot.models import (TextSendMessage)


class BaseHandler(web.RequestHandler):
    def get_current_user(self):
        user = self.get_secure_cookie('admin_user')
        return escape.utf8(user)
    
    def set_current_user(self,username):
        self.set_secure_cookie('admin_user',username)
        
    def clear_current_user(self):
        self.clear_cookie('admin_user')

class IndexHandler(BaseHandler):
    def main(self,dbname,page):
        params = self.application.db['params'].find_one({'app':'bbs'})
        if params['mentenance'] is True:
            self.render('mentenance.htm',title=params['title'],db=dbname)
            return
        if dbname not in self.application.mylist():
            if self.current_user == b'admin':
                coll = self.application.db[dbname]
                coll.insert({})
                coll.remove({})
            else:
                raise web.HTTPError(404)
        key = self.get_argument('key','')
        if key != '':
            table = self.application.db[dbname]
            rec = table.find_one({'number':int(key)})
            if rec:
                self.render('article.htm',record=rec)
                return
            else:
                raise web.HTTPError(404)
        self.rule = escape.url_unescape(self.get_cookie('aikotoba',''))
        self.na = escape.url_unescape(self.get_cookie('username',u'誰かさん'))
        self.pos = self.application.gpos(dbname,page)
        table = self.application.db[dbname]
        i = params['count']
        start = (self.pos-1)*i
        if start < 0:
            start = table.count()-i
            if start < 0:
                start = 0
        rec = table.find()
        self.bool = (dbname == params['info name'])
        if self.bool is True:
            rec.sort('number',-1)
        else:
            rec.sort('number')
        self.rec = rec.skip(start).limit(i)

    def get(self,dbname,page='0'):
        self.main(dbname,page)
        db = self.application.db
        table = db[dbname].find()
        params = db['params'].find_one({'app':'bbs'})
        if table.count() >= 10*params['count']:
            self.render('modules/full.htm',position=self.pos,records=self.rec,data=params,db=dbname)
        if self.bool is True and self.current_user != b'admin':
            self.render('modules/info.htm',position=self.pos,records=self.rec,data=params,db=dbname,error='')
        else:
            self.render_admin(dbname)

    def render_admin(self,dbname,title='',com='',er='',img='',ch='checked'):
        t = self.get_argument('img','')
        params = self.application.db['params'].find_one({'app':'bbs'})
        if self.current_user == b'admin':
            s = '<label><p>URL </p><input name="img" placeholder="src=http://～" value=' + t + '></label>'
        else:
            s = '<input type=hidden>'
        self.render('modules/index.htm',position=self.pos,records=self.rec,data=params,username=self.na,title=title,
            comment=com,db=dbname,aikotoba=self.rule,error=er+img,check=ch,admin=s)

class LoginHandler(BaseHandler):
    def get(self):
        info = self.application.db['params'].find_one({'app':'bbs'})
        query = self.get_query_argument('next','/'+info['info name'])
        i = query[1:].find('/')
        if i == -1:
            qs = query[1:]
        else:
            qs = query[1:i+1]
        self.render('login.htm',db=escape.url_unescape(qs))
        
    def post(self):
        dbname = self.get_argument('record','')
        if dbname == '':
            self.redirect('/login')
            return
        pw = self.application.db['params'].find_one({'app':'bbs'})
        if self.get_argument('password') == pw['password']:
            self.set_current_user('admin')
        if dbname == 'master':
            self.redirect('/master')
        else:
            self.redirect('/'+dbname+'/admin/0/')
        
class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_current_user()
        self.redirect('/login')
 
class JumpHandler(BaseHandler):
    def get(self):
        self.clear_current_user()
        self.redirect('/')
        
class NaviHandler(web.RequestHandler):
    def get(self):
        if 'params' not in self.application.mylist():
            item = {"mentenance":False,"out_words":[u"阿保",u"馬鹿",u"死ね"],"password":"admin",
                    "title2":"<h1 style=color:maroon;font-style:italic;text-align:center>とるね～ど号</h1>",
                    "bad_words":["<style","<link","<script","<img","<a"],"count":30,
                    "title":u"とるね～ど号","info name":"info",'app':'bbs'}
            self.application.db['params'].insert(item)
            self.application.db['info'].find()
        table = self.application.db['params'].find_one({'app':'bbs'})
        if table['mentenance'] is True:
            self.render('mentenance.htm',title=table['title'],db=table['info name'])
            return
        coll = self.application.coll()
        na = table['info name']
        self.render('top.htm',coll=coll,name=na,full=self.full,new=self.new)

    def full(self,dbname):
        if dbname in self.application.coll():
            i = 10*self.application.db['params'].find_one({'app':'bbs'})['count']
            table = self.application.db[dbname]
            if table.count() >= i:
                return True
        return False

    def new(self,dbname):
        if dbname in self.application.coll():
            table = self.application.db[dbname]
            i = table.count()
            if i == 0:
                return False
            rec = sorted(table.find(),key=lambda x:x['date'])
            time = rec[i-1]['date']
            delta = datetime.now()-datetime.strptime(time,'%Y/%m/%d %H:%M')
            return delta.total_seconds() < 24*3600

class TitleHandler(NaviHandler):
    def get(self):
        rec = sorted(self.title(),key=lambda x: x['date2'])
        self.render('title.htm',coll=rec,full=self.full)  
        
    def title(self):
        for x in self.application.coll():
            item = {}
            item['name'] = x
            table = self.application.db[x]
            i = table.count()
            item['count'] = i            
            tmp = table.find_one({'number':1})
            if tmp:
                s = tmp['title']
            else:
                s = ''
            item['title'] = s   
            if i == 0:
                item['date'] = ''
                item['date2'] = 0
            else:
                rec = table.find().sort('number')
                s = rec[i-1]['date']
                item['date'] = s
                i = datetime.strptime(s,'%Y/%m/%d %H:%M')
                year = datetime.now().year-i.year
                if year == 0:
                    j = 800
                elif year == 1:
                    j = 400
                else:
                    j = 0
                item['date2'] = j+31*(i.month-1)+i.day
            yield item
        
class RegistHandler(IndexHandler):
    def post(self,dbname):
        self.main(dbname,'0')
        if dbname not in self.application.coll(info=True):
            raise web.HTTPError(404)
        params = self.application.db['params'].find_one({'app':'bbs'})
        words = params['bad_words']
        out = params['out_words']
        rule = self.get_argument('aikotoba')
        na = self.get_argument('name')
        sub = self.get_argument('title')
        com = self.get_argument('comment',None,False)
        text = ''
        i = 0
        url = []
        error = ''
        kinsi = False
        for line in com.splitlines():
            if kinsi is False:
                for word in out:
                    if word in line:
                        error += u'禁止ワード.<br>'
                        kinsi = True
                        break
            for word in words:
                if word in line.lower():
                    tag = escape.xhtml_escape(word)
                    error += u'タグ違反.('+tag+')<br>'
            i += len(line)
            obj = re.finditer('http[s]?://(?:[a-zA-Z]|[0-9]|[#$%._?&~+*=/]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', line)
            for x in obj:
                if x.group() not in url:
                    url.append(x.group())
            j = 0
            for x in line:
                if x == ' ':
                    j += 1
                else:
                    break
            if j > 0: 
                line = line.replace(' ','&nbsp;',j)     
            if len(line) == 0:
                text += '<p><br>\n</p>'
            else:
                text += '<p>'+self.link(line,dbname)+'\n</p>'
        if rule != u'げんき':
            error += u'合言葉未入力.<br>'
        s = ''
        for x in url:
            s = s+'<tr><td><a href={0} class=livepreview target=_blank>{0}</a></td></tr>'.format(x)
        if s != '':
            text = text+'<table><tr><td>検出url:</td></tr>'+s+'</table>'
        pw = self.get_argument('password')
        if i > 1000:
            error += u'文字数が1,000をこえました.<br>'
        if na == '':
            if self.current_user == b'admin':
                na = u'管理人'
            else:
                na = u'誰かさん'
        if sub == '':
            sub = u'タイトルなし.'
        article = self.application.db[dbname]
        if article.count() == 0:
            no = 1
        else:            
            items = article.find()
            item = items.sort('number')[article.count()-1]
            no = item['number']+1
        s = datetime.now()
        k = '%Y%m%d%H%M%S'
        if self.get_argument('show', 'false') == 'true':
            ch = 'checked'
        else:
            ch = ''
            t = self.get_cookie('time')
            if t and s - datetime.strptime(escape.url_unescape(t),k) < timedelta(seconds=10):
                error += u'二重送信.'
        img = self.get_argument('img','')
        if img:
            img = '<div style=text-align:center><img src="' + escape.url_unescape(img) + '"/></div>'
        if error == '':
            if ch == 'checked':
                error = '<p style=font-size:2.5em;color:blue>↓↓プレビュー↓↓</p>\n' + text
                ch = ''
            else:
                com += img
                text += img
                reg = {'number': no, 'name': na, 'title': sub, 'comment': text, 'raw': com, 'password': pw,
                    'date': s.strftime('%Y/%m/%d %H:%M')}
                article.insert(reg)
                self.set_cookie('aikotoba', escape.url_escape(rule))
                self.set_cookie('username', escape.url_escape(na))
                self.set_cookie('time',escape.url_escape(s.strftime(k)))
                self.redirect('/' + dbname + '#article')
                return
        else:
            error = '<p style=color:red>' + error + '</p>'
        self.na = na
        self.rule = rule
        self.pos = 0
        self.render_admin(dbname,title=sub,com=com,er=error,ch=ch,img=img)

    def link(self,command,database):
        i = 0
        text = ''
        obj = re.finditer('>>[0-9]+',command)
        for x in obj:
            s = '<a class=minpreview data-preview-url=/{0}?key={1} href=/{0}/userdel?job={1}>>>{1}</a>'.format(database,x.group()[2:])
            text = text+command[i:x.start()]+s
            i = x.end()
        else:
            text = text+command[i:]
        return text
    
class AdminHandler(BaseHandler):
    @web.authenticated               
    def get(self,dbname,page='0'):
        if dbname == '':
            dbname = self.get_argument('record','')
        table = self.application.db[dbname]
        rec = table.find().sort('number')                   
        mente = self.application.db['params'].find_one({'app':'bbs'})
        if mente['mentenance'] is True:
            check = 'checked=checked'
        else:
            check = ''
        pos = self.application.gpos(dbname,page)
        i = mente['count']
        start = (pos-1)*i
        if start < 0:
            start = table.count()-i
            if start < 0:
                start = 0
        rec.skip(start).limit(i)
        self.render('modules/admin.htm',position=pos,records=rec,mente=check,password=mente['password'],db=dbname)

class AdminConfHandler(BaseHandler):
    @web.authenticated
    def post(self,dbname,func):
        if func == 'set':
            param = self.application.db['params'].find_one({'app':'bbs'})
            if self.get_argument('mente','') == 'on':
                mente = True
            else:
                mente = False  
            word = self.get_argument('pass','')
            if word == '':
                self.render('regist.htm',content='パスワードを設定してください')
                return
            else:
                param['mentenance']=mente
                param['password']=word  
                self.application.db['params'].save(param)
        elif func == 'del':
            table = self.application.db[dbname]
            for x in self.get_arguments('item'):
                table.remove({'number':int(x)})
        self.redirect('/'+dbname+'/admin/0/')
          
class UserHandler(web.RequestHandler):
    def get(self,dbname):
        q = self.get_query_argument('job','0',strip=True)
        self.redirect(self.application.page(dbname,q))
        
    def post(self,dbname):
        number = self.get_argument('number')
        if number.isdigit() is True:
            num = int(number)
            url = self.application.page(dbname,number)
            if 'password' in self.request.arguments.keys():
                pas = self.get_argument('password')
            else:
                self.redirect(url)
                return
            table = self.application.db[dbname]
            obj = table.find_one({'number':num})
            if obj and(obj['password'] == pas):
                table.update({'number':num},{'$set':{'title':u'削除されました','name':'','comment':u'<i><b>投稿者により削除されました</b></i>','raw':''}})
                self.redirect(url)
                return
        self.redirect('/'+dbname)

class SearchHandler(web.RequestHandler):
    def post(self,dbname=''):
        arg = self.get_argument('word1')
        self.word = arg[:]
        self.andor = self.get_argument('type')
        self.radiobox = self.get_argument('filter')       
        if dbname == '':
            rec = []
            for x in self.application.coll():
                moji = self.search(x)
                for y in sorted(moji,key=lambda k: k['number']):
                    y['dbname'] = x
                    rec.append(y) 
        else:
            rec = sorted(self.search(dbname),key=lambda x: x['number'])
        self.render('modules/search.htm',records=rec,word1=arg,db=dbname)

    def get(self,dbname=''):
        if dbname not in self.application.coll(info=True) and dbname != '':
            raise web.HTTPError(404)
        self.render('modules/search.htm',records=[],word1='',db=dbname)
    
    def search(self,dbname):
        table = self.application.db[dbname]    
        andor = self.andor == 'OR'
        element = self.word.split()
        elm = []
        for x in element:
            if x != '':
                elm.append(re.escape(x))
        if self.radiobox == 'comment':
            query = []
            for qu in elm:
                query.append({'raw':re.compile(qu,re.IGNORECASE)})
            if len(query) == 0:
                return
            if andor:    
                result = table.find({'$or':query})
                color = 'yellow'
            else:
                result = table.find({'$and':query})
                color = 'aqua'
            for x in result:
                com = ''
                i = 0
                for text in x['raw'].splitlines():
                    for y in text:
                        if y == ' ':
                            i += 1
                        else:
                            break
                    text = text.replace(' ','&nbsp;',i)                  
                    for y in element:                        
                        if y.lower() in text.lower():
                            com += '<p style=background-color:'+color+'>'+text+'<br></p>'  
                            break                          
                    else:
                        if text == '':
                            com += '<br>'
                        else:
                            com += '<p>'+text+'</p>'
                x['comment'] = com
                yield x       
        else:
            query = []
            for x in element:
                if x != '':
                    query.append({'name':x})
            if len(query) == 0:
                return
            for x in table.find({'$or':query}):
                yield x  
                
class HelpHandler(web.RequestHandler):
    def get(self):
        self.render('help.htm',req='')
    
    def post(self):
        com = self.get_argument('help','')
        line = com.splitlines(True)
        com = ''
        for x in line:
            com += '<p>'+x
        time = datetime.now()
        db = self.application.db['master']
        db.insert({'comment':com,'time':time.strftime('%Y/%m/%d')})
        self.render('help.htm',req='送信しました')
       
class MasterHandler(BaseHandler):
    @web.authenticated  
    def get(self):
        if self.current_user == b'admin':
            com = self.application.db['master'].find()
            sum = self.application.db['temp'].find().count()
            self.render('master.htm',com=com,sum=sum)
        else:
            raise web.HTTPError(404)
    
class AlertHandler(web.RequestHandler):
    def get(self):
        db = self.get_query_argument('db')
        num = self.get_query_argument('num')
        table = self.application.db[db]
        tb = table.find_one({'number':int(num)})
        com = tb['comment']
        time = datetime.now().strftime('%Y/%m/%d')
        link = self.application.page(db,num)
        jump = '<p><a href={0}>{0}</a>'.format(link)
        d = datetime.now().weekday()
        table = self.application.db['temp']
        table.remove({'date':{'$ne':d}})
        result = table.insert(
            {'comment':com+jump,'time':time,'link':link,'date':d,'db':db,'num':num})
        self.render('alert.htm',com=com+jump,num=str(result))
        
    def post(self):
        id = ObjectId(self.get_argument('num'))
        table = self.application.db['temp']
        tb = table.find_one({'_id':id})      
        link = tb['link']
        com = self.get_argument('com')
        table.remove({'_id':id})
        if self.get_argument('cancel','') == 'cancel':
            self.redirect(link)
            return
        if com != '':
            tb['comment'] = com+tb['comment']
        del tb['date']
        table = self.application.db['master']
        table.insert(tb)
        self.redirect(link)
        
class CleanHandler(web.RequestHandler):
    def post(self):
        bool = self.get_argument('all', 'false').lower()
        table = self.application.db['master']
        if bool == 'true':
            table.remove()
            self.application.db['temp'].remove()
        elif bool == 'false':
            for x in list(table.find()):           
                if not 'num' in x.keys():
                    table.remove({'_id':x['_id']})
                else:
                    item = self.application.db[x['db']].find_one({'number':int(x['num'])})
                    if (not item)or(item['raw'] == ''):
                        table.remove({'_id':x['_id']})   
        com = self.application.db['master'].find()
        sum = self.application.db['temp'].find().count()
        self.render('master.htm', com=com, sum=sum)
                                        
class FooterModule(web.UIModule):
    def render(self,number,url,link):
        return self.render_string('modules/footer.htm',index=number,url=url,link=link)
    
class HeadlineApi(web.RequestHandler):
    def get(self):
        response = {}
        for coll in self.application.coll():
            table = self.application.db[coll]
            if table.count() == 0:
                mydict = {}
            else:
                text = table.find().sort('number')[table.count()-1]
                mydict = {'number':text['number'],'name':text['name'],'title':text['title'],'comment':text['raw'][0:20]}
            response[coll] = mydict                 
        self.write(json.dumps(response,ensure_ascii=False))
        
class ArticleApi(web.RequestHandler):
    def get(self,dbname,number):
        response = None
        if dbname in self.application.coll():
            table = self.application.db[dbname]
            response = table.find_one({'number':int(number)})      
        if not response:
            response = {}
        else:
            del response['_id']
            del response['comment']
            del response['password']
        self.write(json.dumps(response,ensure_ascii=False))      

class ListApi(web.RequestHandler):
    def get(self,dbname):
        response = None
        if dbname in self.application.coll():
            table = self.application.db[dbname]
            response = {}
            for data in table.find().sort('number'):
                response[data['number']] = data['raw'][0:20]
        if not response:
            response = {}
        self.write(json.dumps(response,ensure_ascii=False))

class WebHookHandler(web.RequestHandler):
    def main(self, no):
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
        for x in self.application.mylist():
            if x not in out and x[-4:] == '_bot' and x != '_bot':
                s += x[:-4]+'\n'
        return s
    
    def setting(self, dbname):
        dbname = dbname.lower()+'_bot'
        ca = self.application.mylist()
        if 'users_bos' in ca:
            ca.remove('users_bot')
        if dbname in ca:
            db = self.application.db['users_bot']
            item = db.find_one({'name':self.uid})
            if item['dbname'] == dbname:
                return False
            else:
                db.update({'name':self.uid}, {'name':self.uid, 'dbname':dbname})
                return True
        return False

    def users(self):
        db = self.application.db['users_bot']
        item = db.find_one({'name':self.uid})
        x = item['dbname']
        return self.application.db[x], x[:-4]
                          
    def post(self):
        '''
        signature = self.request.headers['X-Line-Signature']
        body = self.request.body
        parser = WebhookParser(self.application.ch)
        try:
            parser.parse(body, signature)
        except InvalidSignatureError:
            web.HTTPError(404)
            return
        '''
        dic = escape.json_decode(self.request.body)              
        for event in dic['events']:
            if 'replyToken' in event.keys():
                self.uid = event['source']['userId']
                bot = 'users_bot'               
                if event['type'] == 'unfollow':
                    self.application.db[bot].remove({'name':self.uid})
                    return
                elif event['type'] != 'message' or event['message']['type'] != 'text':
                    return
                item = self.application.db['params'].find_one({'app':'bot'})
                if item:
                    de = item['default']
                else:
                    de = '_bot'         
                if item and 'access_token' in item.keys():
                    token = item['access_token']
                else:      
                    token =self.application.tk
                if bot not in self.application.mylist() or not self.application.db[bot].find_one({'name':self.uid}):
                    db = self.application.db[bot]
                    db.insert({'name':self.uid, 'dbname':de})
                x = event['message']['text']     
                if self.setting(x):
                    te = u'設定完了.'
                elif x == '?':
                    te = self.help()
                else:
                    te = self.main(x)
                linebot = LineBotApi(token)            
                linebot.reply_message(event['replyToken'], TextSendMessage(text=te))

class InitHandler(web.RequestHandler):
    def get(self):        
        de = self.get_argument('default', '')     
        if de == '':
            names = self.application.mylist()
            db = []
            for x in names:
                if x[-4:] == '_bot' and x != 'users_bot':
                    db.append(x[:-4])
            self.render('init.htm',db=db)
            return
        tb = self.application.db['params']
        if tb.find_one({'app':'bot'}):
            tb.update({'app':'bot'}, {'app':'bot', 'default':de+'_bot'})
        else:
            tb.insert({'app':'bot', 'default':de+'_bot'})
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
        table = self.application.db[name+'_bot']
        table.remove()
        for x in item:
            table.insert(x) 
            
class TokenHandler(web.RequestHandler):
    def on_response(self, response):
        dic = escape.json_decode(response.body)
        token = dic['access_token']
        table = self.application.db['params']
        data = {'app':'bot', 'access_token':token}
        if table.find_one({'app':'bot'}):
            table.save(data)
        else:
            table.insert(data)
        self.finish()

    #@web.asynchronous
    def get(self):
        url = 'https://api.line.me/v2/oauth/accessToken'
        headers = 'application/x-www-form-urlencoded'
        data = {'grant_type':'client_credentials', 'client_id':self.application.id, 'client_secret':self.application.ch}
        body = urllib.parse.urlencode(data)
        req = httpclient.HTTPRequest(url=url,method='POST',headers=headers,body=body)
        http = httpclient.AsyncHTTPClient()
        http.fetch(req, callback=self.on_response)

class Application(web.Application):
    #ch = os.environ['Channel_Secret']
    uri = os.environ['MONGODB_URI']
    ac = os.environ['ACCOUNT']
    #tk = os.environ['Access_Token']
    db = pymongo.MongoClient(uri)[ac]
    def __init__(self):
        handlers = [(r'/',NaviHandler),(r'/login',LoginHandler),(r'/logout',LogoutHandler),(r'/title',TitleHandler),
                    (r'/headline/api',HeadlineApi),(r'/read/api/([a-zA-Z0-9_%]+)/([0-9]+)',ArticleApi),
                    (r'/write/api/([a-zA-Z0-9_%]+)/()/()/()',ArticleApi),(r'/list/api/([a-zA-Z0-9_%]+)',ListApi),
                    (r'/help',HelpHandler),(r'/master',MasterHandler),(r'/alert',AlertHandler),(r'/jump',JumpHandler),
                    (r'/callback',WebHookHandler),(r'/init',InitHandler),(r'/search',SearchHandler),(r'/clean',CleanHandler),(r'/token',TokenHandler),
                    (r'/([a-zA-Z0-9_%]+)',IndexHandler),(r'/([a-zA-Z0-9_%]+)/([0-9]+)/',IndexHandler),
                    (r'/([a-zA-Z0-9_%]+)/admin/([0-9]+)/*',AdminHandler),(r'/([a-zA-Z0-9_%]+)/admin/([a-z]+)/*',AdminConfHandler),(r'/([a-zA-Z0-9_%]+)/userdel',UserHandler),
                    (r'/([a-zA-Z0-9_%]+)/search',SearchHandler),(r'/([a-zA-Z0-9_%]+)/regist',RegistHandler)]
        settings = {'template_path':os.path.join(os.path.dirname(__file__),'templates'),
                        'static_path':os.path.join(os.path.dirname(__file__),'static'),
                        'ui_modules':{'Footer':FooterModule},
                        'cookie_secret':os.environ['cookie'],
                        'xsrf_cookies':False,
                        #'debug':True,
                        'login_url':'/login'
                        }
        super().__init__(handlers,**settings)
 
    def gpos(self,dbname,page):
        params = self.db['params'].find_one({'app':'bbs'})
        pos = int(page)
        if pos <= 0:
            pos = 0
        elif (pos-1)*params['count'] >= self.db[dbname].count():
            pos = 0
        return pos

    def page(self,dbname,number):
        table = self.db[dbname]
        rec = table.find({'number':{'$lte':int(number)}}).count()
        s = self.db['params'].find_one({'app':'bbs'})
        conf = int(s['count'])
        if table.find().count() - rec >= conf:
            return '/'+dbname+'/'+str(1+rec//conf)+'/#'+number
        else:
            return '/'+dbname+'#'+number

    def mylist(self):
        return self.db.list_collection_names()[:]

    def coll(self,info=False):
        name = self.mylist()
        item = self.db['params'].find_one({'app':'bbs'})
        target = ['objectlabs-system', 'objectlabs-system.admin.collections', 'system.indexes',
            'params', 'master', 'temp']
        if info is False:
            target.append(item['info name'])
        for x in target:
            name.remove(x)
        for x in name:
            if x[-4:] == '_bot':
                name.remove(x)
        return sorted(name)
   
if __name__ == '__main__':
    app = Application()
    http_server = httpserver.HTTPServer(app)
    port = int(os.environ.get('PORT',5000))
    http_server.listen(port)
    ioloop.IOLoop.instance().start()
