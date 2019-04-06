﻿#coding=utf-8
import os.path
import shutil
from tornado import escape,web,httpserver,ioloop
from tinydb import TinyDB,Query,where
from datetime import date,timedelta
import json
from botmod import *


st = static()

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
        dbname = escape.url_unescape(dbname)
        params = self.application.db.get(where('kinds') == 'conf')
        if params['mentenance'] is True:
            self.render('mentenance.htm',title=params['title'],db=dbname)
            return
        names = list(self.application.collection())
        names.append(params['info name'])
        if dbname not in names:
            if self.current_user == b'admin':
                self.application.db.table(dbname)
            else:
                raise web.HTTPError(404)
        key = self.get_argument('key','')
        if key:
            table = self.application.db.table(dbname)
            rec = table.get(where('number') == int(key))
            if rec:
                self.render('article.htm',record=rec)
                return
            else:
                raise web.HTTPError(404)
        i = params['count']      
        self.rule = escape.url_unescape(self.get_cookie('aikotoba',''))
        self.na = escape.url_unescape(self.get_cookie("username",u"誰かさん"))
        self.pos = self.application.gpos(dbname,page)
        table = self.application.db.table(dbname)
        self.bool = len(table) >= 10*i
        start = (self.pos-1)*i
        if start < 0:
            start = len(table)-i
            if start < 0:
                start = 0
        rec = sorted(table.all(),key=lambda x: x['number'])[start:start+i]
        if dbname == params['info name']:
            self.rec = rec[::-1]
        else:
            self.rec = rec

    def get(self, dbname, page='0'):
        self.main(dbname,page)
        params = self.application.db.get(where('app') == 'bbs')
        if self.bool is True:
            self.render('modules/full.htm',position=self.pos,records=self.rec,data=params,db=dbname)
            return
        if dbname == params['info name'] and self.current_user != b'admin':
            self.render('modules/info.htm',position=self.pos,records=self.rec,data=params,db=dbname)
        else:
            self.render_admin(dbname)

    def render_admin(self,dbname,title='',com='',ch='checked',er='',img=''):
        params = self.application.db.get(where('app') == 'bbs')
        t = self.get_argument('img','')
        if self.current_user == b'admin':
            s = '<label>URL <input name=img type=text placeholder="src=http://～" value=' + t + '></lbael>'
        else:
            s = '<input type=hidden value=' + t + '>'
        self.render('modules/index.htm',position=self.pos,records=self.rec,data=params,title=title,
            username=self.na,comment=com,db=dbname,aikotoba=self.rule,error=er+img,check=ch,admin=s)

class LoginHandler(BaseHandler):
    def get(self):
        query = self.get_query_argument('next','')
        i = query[1:].find('/')
        if i == -1:
            qs = query[1:]
        else:
            qs = query[1:i+1]
        if qs == '':
            qs = self.application.db.get(where('app') == 'bbs')['info name']
        else:
            qs = escape.url_unescape(qs)
        self.render('login.htm',db=qs)
        
    def post(self):
        dbname = self.get_argument('record','')
        if dbname == '':
            self.redirect('/login')
            return
        pw = self.application.db.get(where('app') == 'bbs')
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
        
class NaviHandler(web.RequestHandler):
    def get(self):
        data = self.application.db.get(where('app') == 'bbs')
        if not data:
            item = {"mentenance":False,"out_words":[u"阿保",u"馬鹿",u"死ね"],"password":"admin",
                    "title2":"<h1 style=color:maroon;font-style:italic;text-align:center>とるね～ど号</h1>",
                    "bad_words":["<style","<link","<script","<img","<a"],"count":30,
                    "title":u"とるね～ど号","info name":"info","kinds":"conf","app":"bbs"}
            self.application.db.insert(item)
            self.application.db.table('info').all()
            na = 'info'
        else:
            na = data['info name']
            if data['mentenance'] is True:
                self.render('mentenance.htm',title=data['title'],db=na)
                return
        col = sorted(self.application.collection())
        self.render('top.htm',coll=col,name=na,full=self.full)

    def full(self,dbname):
        if dbname in self.application.db.tables():
            i = 10*self.application.db.get(where('app') == 'bbs')['count']
            table = self.application.db.table(dbname)
            if len(table) >= i:
                return True
        return False

class TitleHandler(NaviHandler):
    def get(self):
        rec = sorted(self.title(),key=lambda x: x['date2'])
        self.render('title.htm',coll=rec,full=self.full)  
        
    def title(self):
        for x in self.application.collection():
            item = {}
            item['name'] = x
            table = self.application.db.table(x)
            i = len(table)
            item['count'] = i            
            if table.contains(where('number') == 1) is True:
                s = table.get(where('number') == 1)['title']
            else:
                s = ''
            item['title'] = s   
            if i == 0:
                item['date'] = ''
                item['date2'] = 0
            else:
                rec = sorted(table.all(),key=lambda k: k['number'])
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
        rec = self.application.db.get(where('app') == 'bbs')
        words = rec['bad_words']
        out = rec['out_words']
        na = self.get_argument('name')
        sub = self.get_argument('title')
        com = self.get_argument('comment',None,False)
        text = ''
        i = 0
        url = []
        error = ''
        for line in com.splitlines():
            for word in out:
                if word in line:
                    error = error + u'禁止ワード.<br>'
                    break
            for word in words:
                if word in line.lower():
                    tag = escape.xhtml_escape(word)
                    error = error + u'タグ違反.('+tag+')<br>'
            i += len(line)   
            obj = re.finditer('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', line)
            for x in obj:
                if x.group() not in url:
                    url.append(x.group())
            j = 0
            for x in line:
                if x == ' ':
                    j += 1
                else:
                    break
            line = line.replace(' ','&nbsp;',j)
            if line == '':
                text += '<p><br>\n</p>'
            else:
                text += '<p>'+self.link(line,dbname)+'<br>\n</p>'
        s = ''
        for x in url:
            s += '<tr><td><a class=livepreview target=_blank href={0}>{0}</a></td></tr>'.format(x)
        if s:
            text += '<table><tr><td>検出URL:</td></tr>'+s+'</table>'
        pw = self.get_argument('password')
        if i == 0:
            error = error + u'本文がありません.<br>'
        elif i > 1000:
            error = error +u'文字数が1,000をこえました.<br>'
        self.rule = escape.url_unescape(self.get_argument('aikotoba'))
        if self.rule != u'げんき':
            error = error + u'合言葉未入力.<br>'
        article = self.application.db.table(dbname)
        if len(article) == 0:
            no = 1
        else:
            item = sorted(article.all(),key=lambda x: x['number'])[len(article)-1]
            no = item['number']+1
        if self.get_argument('show', 'false') == 'true':
            ch = 'checked'
        else:
            ch = ''
        s = datetime.now()
        k = '%Y%m%d %H:%M:%S'
        t = self.get_cookie('time')
        if not ch and t and s - datetime.strptime(escape.url_unescape(t), k) < timedelta(seconds=10):
            error += u'二重送信です.'
        if error == '':
            if ch == 'checked':
                ch = ''
                error = '<p style=color:blue;font-size:2.5em>↓↓プレビュー↓↓</p>\n<p>' + text
        else:
            error = '<p style=color:red>'+error+'</p>'
        img = self.get_argument('img','')
        if img:
            img = '<div style=text-align:center><img src="' + escape.url_unescape(img) + '"/></div>'
        if error == '':
            if not na:
                if self.current_user == b'admin':
                    na = u'管理人'
                else:
                    na = u'誰かさん'
            if sub == '':
                sub = u'タイトルなし.'
            com += img
            text += img
            reg = {'number':no,'name':na,'title':sub,'comment':text,'raw':com,'password':pw,'date':s.strftime('%Y/%m/%d %H:%M')}
            article.insert(reg)
            self.set_cookie('username',escape.url_escape(na))
            self.set_cookie('aikotoba',escape.url_escape(u'げんき'))
            self.set_cookie('time', escape.url_escape(s.strftime(k)))
            self.redirect('/'+dbname+'#article')
        else:
            self.na = na
            self.pos = 0
            self.render_admin(dbname,com=com,title=sub,ch=ch,er=error,img=img)
    
    def link(self,command,database):
        i = 0
        text = ''
        obj = re.finditer('>>[0-9]+',command)
        for x in obj:
            s = '<a class=minpreview data-preview-url=/{0}?key={1} href=/{0}/userdel?job={1}>>>{1}</a>'.format(database,x.group()[2:])
            text += command[i:x.start()]+s
            i = x.end()
        else:
            text += command[i:]
        return text
    
class AdminHandler(BaseHandler):
    @web.authenticated               
    def get(self,dbname,page):
        if dbname == '':
            dbname = self.get_argument('record','')
        params = self.application.db.get(where('app') == 'bbs')
        group = list(self.application.collection())
        group.append(params['info name'])
        if dbname not in group:
            raise web.HTTPError(404)
        table = self.application.db.table(dbname) 
        rec = sorted(table.all(),key=lambda x: x['number'])
        if params['mentenance'] is True:
            check = 'checked=checked'
        else:
            check = ''
        pos = self.application.gpos(dbname,page)
        i = params['count']
        start = (pos-1)*i
        if start < 0:
            start = len(table)-i
            if start < 0:
                start = 0
        self.render('modules/admin.htm',position=pos,
            records=rec[start:start+i],mente=check,password=params['password'],db=dbname)

class AdminConfHandler(BaseHandler):
    @web.authenticated
    def post(self,dbname,func):
        if func == 'set':
            param = self.application.db.get(where('app') == 'bbs')['mentenance']
            if self.get_argument('mente','') == 'on':
                mente = True
                if param != mente:
                    self.store()
            else:
                mente = False  
                if param != mente:
                    self.restore()
            word = self.get_argument('pass','')
            if word == '':
                self.render('regist.htm',content='パスワードを設定してください')
                return
            else:
                self.application.db.update({'mentenance':mente,'password':word},where('kinds') == 'conf')  
        elif func == 'del':
            table = self.application.db.table(dbname)
            for x in self.get_arguments('item'):
                table.remove(where('number') == int(x))
        self.redirect('/'+dbname+'/admin/0/')
        
    def store(self):
        self.application.db.close()
        shutil.copy(st.json,st.bak)
        self.application.db = TinyDB(st.json)
        
    def restore(self):
        database = self.application.db
        bak = TinyDB(st.bak)
        for x in database.tables():
            if x in self.application.collection():
                database.purge_table(x)
                if x in bak.tables():
                    table = database.table(x)
                    table.insert_multiple(bak.table(x).all())
          
class UserHandler(web.RequestHandler):
    def get(self,dbname):
        q = self.get_query_argument('job','0',strip=True)
        self.redirect(self.application.page(dbname,q))
        
    def post(self,dbname):
        number = self.get_argument('number')
        if number.isdigit() is True:
            url = self.application.page(dbname,number)
            if 'password' in self.request.arguments.keys():
                pas = self.get_argument('password')
            else:
                self.redirect(url)
                return
            qwr = Query()
            table = self.application.db.table(dbname)
            num = int(number)
            obj = table.get(qwr.number == num)
            if obj and obj['password'] == pas:
                table.update({'title':u'削除されました','name':'','comment':u'<i><b>投稿者により削除されました</b></i>','raw':''},qwr.number == num)
                self.redirect(url)
                return
        self.redirect('/'+dbname)

class SearchHandler(web.RequestHandler):
    def post(self,dbname=''):
        arg = self.get_argument('word1')
        self.word = arg[:]
        self.radiobox = self.get_argument('filter')  
        self.andor = self.get_argument('type')    
        if dbname == '':
            rec = []
            for x in self.application.collection():
                for y in sorted(self.search(x),key=lambda k: k['number']):
                    y['dbname'] = x
                    rec.append(y)
        else:
            rec = sorted(self.search(dbname),key=lambda x: x['number'])
        self.render('modules/search.htm',records=rec,word1=arg,db=dbname)
    
    def get(self,dbname=''):
        names = list(self.application.collection())
        info = self.application.db.get(where('app') == 'bbs')['info name']
        if info == dbname:
            dbname = info
        elif dbname != '' and dbname not in names:
            raise web.HTTPError(404)
        self.render('modules/search.htm',records=[],word1='',db=dbname)
        
    def search(self,dbname):
        table = self.application.db.table(dbname)    
        andor = self.andor == 'OR'
        color = ''
        element = self.word.split()
        if len(element) == 0:
            element = ['']
        while len(element) < 3:
            element.append(element[0])
        if self.radiobox == 'comment':
            if andor:
                query = (Query().raw.search(element[0])) | (Query().raw.search(element[1])) | (Query().raw.search(element[2]))
                color = 'yellow'
            else:
                query = (Query().raw.search(element[0])) & (Query().raw.search(element[1])) & (Query().raw.search(element[2]))
                color = 'aqua'
        else:
            query = (Query().name == element[0]) | (Query().name == element[1]) | (Query().name == element[2])
        if self.radiobox == 'comment':    
            for x in table.search(query):
                com = ''
                for text in x['raw'].splitlines():                  
                    for word in element:                        
                        if text.find(word) > -1:
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
            for x in table.search(query):
                yield x
                                        
class FooterModule(web.UIModule):
    def render(self,number,url,link):
        return self.render_string('modules/footer.htm',index=number,url=url,link=link)
    
class HeadlineApi(web.RequestHandler):
    def get(self):
        response = {}
        for x in self.application.collection():
            response[x] = self.get_data(x)
        self.write(json.dumps(response,ensure_ascii=False))
    
    def get_data(self,dbname):
        table = self.application.db.table(dbname)
        i = len(table)
        if i == 0:
            return {}
        else:
            rec = sorted(table.all(),key=lambda x: x['title'])[i-1]
            return {'number':rec['number'],'title':rec['title'],'name':rec['name'],'comment':rec['raw'][0:19]}
        
class ArticleApi(web.RequestHandler):
    def get(self,dbname,number):
        if dbname in self.application.collection():
            table = self.application.db.table(dbname)
            response = table.get(where('number') == int(number))
            if not response:
                response = {}
            else:
                del response['comment']
                del response['password']
            self.write(json.dumps(response,ensure_ascii=False))
        else:
            raise web.HTTPError(404)
    
    def post(self,dbname):
        name = self.get_argument('name',u'誰かさん')
        title = self.get_argument('title',u'タイトルなし')
        comment = self.get_argument('comment')
        table = self.application.db.table(dbname)
        table.insert({'name':name,'title':title,'comment':comment})
        
class HelpHandler(web.RequestHandler):
    def get(self):
        self.render('help.htm',req='') 
        
    def post(self):
        com = self.get_argument('help','')
        text = ''
        for line in com.splitlines():
            text +='<p>'+line
        table = self.application.db.table('master')
        time = datetime.now()
        table.insert({'db':'','comment':text,'time':time.strftime('%Y/%m/%d %H:%M')})
        if com == '':
            req = ''
        else:
            req = '送信しました'
        self.render('help.htm',req=req)
        
class MasterHandler(BaseHandler):
    @web.authenticated
    def get(self):
        if self.current_user == b'admin':
            com = self.application.db.table('master').all()
            self.render('master.htm',com=com)
        else:
            raise web.HTTPError(404)
        
class AlertHandler(web.RequestHandler):
    def get(self):
        db = self.get_query_argument('db')
        num = self.get_query_argument('num')
        jump = self.application.page(db,num)
        n = int(num)
        item = self.application.db.table(db).get(where('number') == n)
        link = '<p><a href={0}>{0}</a>'.format(jump)
        time = datetime.now()
        d = date.weekday(time)
        data = {'comment':item['comment']+link,'time':time.strftime('%Y/%m/%d'),
                'link':jump,'date':d,'db':db,'num':n}
        temp = self.application.db.table('temp')
        id = temp.insert(data)
        temp.remove(where('date') != d)
        self.render('alert.htm',com=data['comment'],num=id)
    
    def post(self):
        id = int(self.get_argument('num'))
        table = self.application.db.table('temp')
        tb = table.get(eid=id)
        table.remove(eids=[id])
        link = tb['link']
        if self.get_argument('admit','') == 'ok':
            com = self.get_argument('com')
            tb['comment'] = com+tb['comment']
            del tb['date']
            table = self.application.db.table('master')
            table.insert(tb)
        self.redirect(link)
        
class CleanHandler(web.RequestHandler):
    def post(self):
        bool = self.get_argument('all','false').lower()
        table = self.application.db.table('master')
        if bool == 'true':
            table.purge()
        elif bool == 'false':
            for x in table.all():
                if x['db'] == '':
                    table.remove(doc_ids=[x.doc_id])
                    continue
                tb = self.application.db.table(x['db'])
                item = tb.get(where('number') == x['num'])
                if not item or item['raw'] == '':
                    table.remove(doc_ids=[x.doc_id])
        self.redirect('/master')
                    
class Application(web.Application):    
    def __init__(self):
        self.db = TinyDB(st.json)
        handlers = [(r'/',NaviHandler),(r'/login',LoginHandler),(r'/logout',LogoutHandler),(r'/title',TitleHandler),
                    (r'/headline/api',HeadlineApi),(r'/read/api/([a-zA-Z0-9_%]+)/([0-9]+)',ArticleApi),(r'/write/api/([a-zA-Z0-9_%]+)',ArticleApi),
                    (r'/help',HelpHandler),(r'/master/*',MasterHandler),(r'/alert',AlertHandler),(r'/search',SearchHandler),(r'/clean',CleanHandler),
                    (r'/callback',WebHookHandler),
                    (r'/([a-zA-Z0-9_%]+)',IndexHandler),(r'/([a-zA-Z0-9_%]+)/([0-9]+)/*',IndexHandler),
                    (r'/([a-zA-Z0-9_%]+)/admin/([0-9]+)/*',AdminHandler),(r'/([a-zA-Z0-9_%]+)/admin/([a-z]+)/*',AdminConfHandler),(r'/([a-zA-Z0-9_%]+)/userdel',UserHandler),
                    (r'/([a-zA-Z0-9_%]+)/search',SearchHandler),(r'/([a-zA-Z0-9_%]+)/regist',RegistHandler)]
        settings = {'template_path':os.path.join(os.path.dirname(__file__),'templates'),
                        'static_path':os.path.join(os.path.dirname(__file__),'static'),
                        'ui_modules':{'Footer':FooterModule},
                        'cookie_secret':'bZJc2sWbQLKo6GkHn/VB9oXwQt8SOROkRvJ5/xJ89Eo=',
                        'xsrf_cookies':True,
                        'debug':True,
                        'login_url':'/login'
                        }
        web.Application.__init__(self,handlers,**settings)
 
    def gpos(self,dbname,page):
        params = self.db.get(where('app') == 'bbs')
        pos = int(page)
        if pos <= 0:
            pos = 0
        elif (pos-1)*params['count'] >= len(self.db.table(dbname)):
            pos = 0
        return pos

    def page(self, dbname, number):
        tb = self.db.table(dbname)
        rec = tb.count(where('number') <= int(number))
        s = self.db.get(where('app') == 'bbs')
        conf = int(s['count'])
        if len(tb.all()) - rec >= conf:
            return '/'+ dbname + str(1 + rec // conf) + '#'+number
        else:
            return '/'+dbname+'#'+number

    def collection(self):
        info = self.db.get(where('app') == 'bbs')['info name']
        names = ['master','_default','temp',info]
        for name in self.db.tables() - set(names):
            if name[-3:] != '_bot':
                yield name

if __name__ == '__main__':
    http_server = httpserver.HTTPServer(Application())
    http_server.listen(5000)
    ioloop.IOLoop.instance().start()
