# -*- coding:utf-8 -*-
import os,re
from tornado import escape,web,ioloop,httpserver
import pymongo
from datetime import datetime,date
import json
from bson.objectid import ObjectId #don't remove
from botmod import *

class BaseHandler(web.RequestHandler):
    def get_current_user(self):
        user = self.get_secure_cookie('admin_user')
        return escape.utf8(user)
    
    def set_current_user(self,username):
        self.set_secure_cookie('admin_user',username)
        
    def clear_current_user(self):
        self.clear_cookie('admin_user')

class IndexHandler(BaseHandler):
    def get(self,dbname,page='0'):
        params = self.application.db['params'].find_one()
        if params['mentenance'] == True:
            self.render('mentenance.htm',title=params['title'],db=dbname)
            return
        if self.application.collection(dbname) == False:
            if self.current_user == b'admin':
                coll = self.application.db[dbname]
                coll.insert({})
                coll.remove({})
            else:
                raise web.HTTPError(404)
                return
        key = self.get_argument('key','')
        if key:
            table = self.application.db[dbname]
            rec = table.find_one({'number':int(key)})
            if rec:
                self.render('article.htm',record=rec)
                return
            else:
                web.HTTPError(404)
                return
        i = params['count']      
        rule = escape.url_unescape(self.get_cookie('aikotoba',''))
        na = escape.url_unescape(self.get_cookie('username',u'誰かさん'))
        pos = self.application.gpos(dbname,page)
        table = self.application.db[dbname]
        start = (pos-1)*i
        if start < 0:
            start = table.count()-i
            if start < 0:
                start = 0
        rec = table.find()
        bool = (dbname == params['info name']) 
        if bool == True:
            rec.sort('number',-1)
        else:
            rec.sort('number')
        rec.skip(start).limit(i)
        if table.count() >= 10*i:
            self.render('modules/full.htm',position=pos,records=rec,data=params,db=dbname)
            return
        if (bool == True)and(self.current_user != b'admin'):
            self.render('modules/info.htm',position=pos,records=rec,data=params,db=dbname)
        else:
            self.render('modules/index.htm',position=pos,records=rec,data=params,username=na,db=dbname,aikotoba=rule)
        
class LoginHandler(BaseHandler):
    def get(self):
        query = self.get_query_argument('next','')            
        i = query[1:].find('/')
        if i == -1:
            qs = query[1:]
        else:
            qs = query[1:i+1]
        self.render('login.htm',db=qs)
        
    def post(self):
        pw = self.application.db['params'].find_one()
        if self.get_argument('password') == pw['password']:
            self.set_current_user('admin')
        dbname = self.get_argument('record')
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
        if self.application.collection('params') == False:
            item = {"mentenance":False,"out_words":[u"阿保",u"馬鹿",u"死ね"],"password":"admin",
                    "title2":"<h1 style=color:gray;text-align:center>pybbs</h1>",
                    "bad_words":["<style","<link","<script","<img"],"count":30,
                    "title":"pybbs","info name":"info"}
            self.application.db['params'].insert(item)
        coll,na = self.name()                
        self.render('top.htm',coll=coll,name=na,full=self.full)
                  
    def name(self):
        coll = sorted(self.application.coll(),key=str.lower)
        na = self.application.db['params'].find_one()['info name']
        if na in coll:
            coll.remove(na)
        else:
            na = ''
        return coll,na
            
    def full(self,dbname):
        if dbname in self.application.db.collection_names():
            i = 10*self.application.db['params'].find_one()['count']
            table = self.application.db[dbname]
            if table.count() >= i:
                return True
        return False

class TitleHandler(NaviHandler):
    def get(self):
        rec = sorted(self.title(),key=lambda x: x['date2'])
        self.render('title.htm',coll=rec,full=self.full)  
        
    def title(self):
        name = self.application.coll()
        for x in name:
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
        
class RegistHandler(web.RequestHandler):
    def post(self,dbname):
        if self.application.collection(dbname) == False:
            raise web.HTTPError(404)
            return
        self.database = dbname
        rec = self.application.db['params'].find_one()
        words = rec['bad_words']
        out = rec['out_words']
        rule = self.get_argument('aikotoba')
        na = self.get_argument('name')
        sub = self.get_argument('title')
        com = self.get_argument('comment',None,False)
        text = ''
        i = 0
        url = []
        error = ''
        if rule != u'げんき':
            error = u'合言葉未入力.'
        for word in out:
            if word in com:
                error += u'禁止ワード.'
                break
        for line in com.splitlines():
            if error:
                break
            for word in words:
                if word in line.lower():
                    error += u'タグ違反.('+word+')'       
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
            if j > 0: 
                line = line.replace(' ','&nbsp;',j)     
            if len(line) == 0:
                text += '<br>'
            else:
                text += '<p>'+self.link(line)+'</p>'
        s = ''
        for x in url:
            s = s+'<tr><td><a href={0} class=livepreview target=_blank>{0}</a></td></tr>'.format(x)
        if s:         
            text = text+'<table><tr><td>検出url:</td></tr>'+s+'</table>';
        pw = self.get_argument('password')
        if i > 1000:
            error += +u'文字数が1,000をこえました.'
        if na == '':
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
        if error == '':
            self.set_cookie('aikotoba',escape.url_escape(rule))
            s = datetime.now()
            reg = {'number':no,'name':na,'title':sub,'comment':text,'raw':com,'password':pw,'date':s.strftime('%Y/%m/%d %H:%M')}
            article.insert(reg)
            self.set_cookie('username',escape.url_escape(na))
            self.redirect('/'+dbname+'#article')
        else:
            self.render('regist.htm',content=error)
    
    def link(self,command):
        i = 0
        text = ''
        obj = re.finditer('>>[0-9]+',command)
        for x in obj:
            s = '<a class=minpreview data-preview-url=/{0}?key={1} href=/{0}/userdel?job={1}>>>{1}</a>'.format(self.database,x.group()[2:])
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
        if self.application.collection(dbname) == False:
            raise web.HTTPError(404)
            return
        table = self.application.db[dbname] 
        rec = table.find().sort('number')                   
        mente = self.application.db['params'].find_one()
        if mente['mentenance'] == True:
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
            param = self.application.db['params'].find_one()
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
        num = self.page(dbname,int(q))
        self.redirect('/{0}{1}#{2}'.format(dbname,num,q))
        
    def post(self,dbname):
        number = self.get_argument('number')
        if number.isdigit() == True:
            num = int(number)
            pas = self.get_argument('password')
            table = self.application.db[dbname]
            obj = table.find_one({'number':num})
            if obj and(obj['password'] == pas):
                table.update({'number':num},{'$set':{'title':u'削除されました','name':'','comment':u'<i><b>投稿者により削除されました</b></i>','raw':''}})
                self.redirect('/'+dbname+self.page(dbname,num)+'#'+number)
            else:
                self.redirect('/'+dbname)
                
    def page(self,table,number):
        tb = self.application.db[table]
        rec = tb.find({'number':{'$lte':number}}).count()
        conf = self.application.db['params'].find_one()
        if tb.find().count()-rec >= conf['count']:
            return '/'+str(1+rec//conf['count'])+'/'
        else:
            return ''
      
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
        if self.application.collection(dbname) == False and dbname != '':
            raise web.HTTPError(404)
            return
        self.render('modules/search.htm',records=[],word1='',db=dbname)
    
    def search(self,dbname):
        table = self.application.db[dbname]    
        andor = self.andor == 'OR'
        element = self.word.split()
        if len(element) == 0:
            element = ['']
        while len(element) < 3:
            element.append(element[0])
        elm = []
        for i in range(3):
            elm.append(re.escape(element[i]))
        if self.radiobox == 'comment':
            query = [{'raw':re.compile(elm[0],re.IGNORECASE)},
                        {'raw':re.compile(elm[1],re.IGNORECASE)},
                        {'raw':re.compile(elm[2],re.IGNORECASE)}
                        ]
            if andor:    
                result = table.find({'$or':query})
                color = 'yellow'
            else:
                result = table.find({'$and':query})
                color = 'aqua'
            for x in result:
                com = ''
                for text in x['raw'].splitlines():
                    for y in text:
                        if y == ' ':
                            i += 1
                        else:
                            break
                    text = text.replace(' ','&nbsp;',i)                  
                    for i in range(3):                        
                        if element[i].lower() in text.lower():
                            com = com +'<p style=background-color:'+color+'>'+text+'<br></p>'  
                            break                          
                    else:
                        if text == '':
                            com += '<br>'
                        else:
                            com += '<p>'+text+'</p>'
                x['comment'] = com
                yield x       
        else:
            for x in table.find({'$or':[{'name':element[0]},{'name':element[1]},{'name':element[2]}]}):
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
            self.render('master.htm',com=com)
        else:
            raise web.HTTPError(404)
    
class AlertHandler(UserHandler):
    def get(self):
        db = self.get_query_argument('db')
        num = self.get_query_argument('num')
        tb = self.application.db[db].find_one({'number':int(num)})
        com = tb['comment']
        time = datetime.now().strftime('%Y/%m/%d')
        s = self.page(db,int(num))
        link = '/'+db+s+'#'+num  
        jump = '<p><a href={0}>{0}</a>'.format(link)
        result = self.application.db['temp'].insert(
            {'comment':com+jump,'time':time,'link':link,
             'date':date.weekday(datetime.now()),'db':db,'num':num})
        self.render('alert.htm',com=com+jump,num=str(result))
        
    def post(self):
        id = ObjectId(self.get_argument('num'))
        table = self.application.db['temp']
        tb = table.find_one({'_id':id})      
        link = tb['link']
        com = self.get_argument('com')
        table.remove({'_id':id})
        table.remove({'date':{'$ne':date.weekday(datetime.now())}})
        if self.get_argument('cancel','') == 'cancel':
            self.redirect(link)
            return
        if com != '':
            tb['comment'] = com+tb['comment']
        del tb['date']
        table = self.application.db['master']
        table.insert(tb)
        self.redirect(link)
        
class ClearnHandler(web.RequestHandler):
    def get(self):
        bool = self.get_argument(all, False)
        table = self.application.db['master']
        if bool:
            table.remove()
        else:
            for x in table.find_all():
                item = self.application.db[x['db']]
                if not item.find_one({'number':x['num']}):
                    table.remove({'_id':x['_id']})       
                                        
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
        if self.application.collection(dbname) == True:
            table = self.application.db[dbname]
            response = table.find_one({'number':int(number)})      
        if response == None:
           response = {}
        else:
            del response['_id']
            del response['comment']
            del response['password']
        self.write(json.dumps(response,ensure_ascii=False))      
            
    def post(self,dbname,name,title,article):
        coll = self.application.db[dbname] 
        coll.insert({'name':name,'title':title,'comment':article})
        
class ListApi(web.RequestHandler):
    def get(self,dbname):
        if self.application.collection(dbname) == True:
            table = self.application.db[dbname]
            response = {}
            for data in table.find().sort('number'):
                response[data['number']] = data['raw'][0:20]
        if response == None:
            response = {}
        self.write(json.dumps(response,ensure_ascii=False))
           
class Application(web.Application):    
    def __init__(self):
        handlers = [(r'/',NaviHandler),(r'/login',LoginHandler),(r'/logout',LogoutHandler),(r'/title',TitleHandler),
                    (r'/headline/api',HeadlineApi),(r'/read/api/([a-zA-Z0-9_]+)/([0-9]+)',ArticleApi),
                    (r'/write/api/([a-zA-Z0-9_]+)/()/()/()',ArticleApi),(r'/list/api/([a-zA-Z0-9]+)',ListApi),
                    (r'/help',HelpHandler),(r'/master',MasterHandler),(r'/alert',AlertHandler),(r'/jump',JumpHandler),
                    (r'/callback',WebHookHandler),(r'/init',InitHandler),(r'/search',SearchHandler),
                    (r'/([a-zA-Z0-9_]+)',IndexHandler),(r'/([a-zA-Z0-9_]+)/([0-9]+)/',IndexHandler),
                    (r'/([a-zA-Z0-9_]+)/admin/([0-9]+)/*',AdminHandler),(r'/([a-zA-Z0-9_]+)/admin/([a-z]+)/*',AdminConfHandler),(r'/([a-zA-Z0-9_]+)/userdel',UserHandler),
                    (r'/([a-zA-Z0-9_]+)/search',SearchHandler),(r'/([a-zA-Z0-9_]+)/regist',RegistHandler)]
        settings = {'template_path':os.path.join(os.path.dirname(__file__),'templates'),
                        'static_path':os.path.join(os.path.dirname(__file__),'static'),
                        'ui_modules':{'Footer':FooterModule},
                        'cookie_secret':os.environ['cookie'],
                        'xsrf_cookies':True,
                        #'debug':True,
                        'login_url':'/login'
                        }
        web.Application.__init__(self,handlers,**settings)
 
    def gpos(self,dbname,page):
        params = self.db['params'].find_one()
        pos = int(page)
        if pos <= 0:
            pos = 0
        elif (pos-1)*params['count'] >= self.db[dbname].count():
            pos = 0
        return pos
    
    def collection(self,name):
        if name in self.db.collection_names():
            return True
        else:
            return False

    def coll(self):
        name = self.db.collection_names()
        for x in ['objectlabs-system.admin.collections','objectlabs-system','system.indexes',
                  'params','master','temp']:
            if x in name:
                name.remove(x)
        for x in name:
            if x[-4:] == '_bot':
                name.remove(x)
        return name

if __name__ == '__main__':
    app = Application()
    http_server = httpserver.HTTPServer(app)
    conn = pymongo.MongoClient(var.uri,13678)
    app.db = conn[var.ac]
    port = int(os.environ.get('PORT',5000))
    http_server.listen(port)
    ioloop.IOLoop.instance().start()
