
import tornado.wsgi
import wsgiref.simple_server
import os.path
import tornado.auth
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
from tornado.options import define,options
from tinydb import TinyDB,Query,where
from tinydb.operations import delete
from datetime import datetime

define('port',default=8000,help='run on the given port.',type=int)

class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        user = self.get_secure_cookie('admin_user')
        return tornado.escape.utf8(user)
    
    def set_current_user(self,username):
        self.set_secure_cookie('admin_user',username)
        
    def clear_current_user(self):
        self.clear_cookie('admin_user')

class IndexHandler(BaseHandler):
    def get(self,dbname,page='0'):
        params = self.application.db.get(where('kinds') == 'conf')
        if params['mentenance'] == True:
            self.render('mentenance.htm',title=params['title'],db=dbname)
        if self.application.collection(dbname) == False:
            if self.current_user == b'admin':
                self.application.db.table(dbname)
            else:
                self.render('regist.htm',content='urlが見つかりません')
        i = params['count']      
        na = self.get_cookie('username')
        pos = self.application.gpos(dbname,page)
        table = self.application.db.table(dbname)
        start = (pos-1)*i
        if start < 0:
            start = len(table)-i
            if start < 0:
                start = 0
        rec = table.all()[start:start+i]
        if len(table) >= 10*i:
            self.render('modules/full.htm',position=pos,records=rec,data=params,db=dbname)  
        self.render('modules/index.htm',position=pos,records=rec,data=params,username=na,db=dbname)
        
class LoginHandler(BaseHandler):
    def get(self):
        self.render('login.htm')
        
    def post(self):
        pw = self.application.db.get(where('kinds') == 'conf')
        if self.get_argument('password') == pw['password']:
            self.set_current_user('admin')
        dbname = self.get_argument('record')
        self.redirect('/'+dbname+'/admin/0/')
        
class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_current_user()
        self.redirect('/login')
        
class NaviHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('top.htm',coll=self.name())
        
    def name(self):
        for x in self.application.db.tables():
            if x != '_default':
                yield x

class RegistHandler(tornado.web.RequestHandler):
    def post(self,dbname):
        if self.application.collection(dbname) == False:
            self.render('regist.htm',content='urlが存在しません')
        words = ['<link','<script','<style','<img']
        out = ['ばか','死ね','あほ']
        na = self.get_argument('name')
        sub = self.get_argument('title')
        com = self.get_argument('comment')
        text = ''
        i = 0
        error = ''
        for line in com.splitlines(True):
            for word in words:
                if word in line:
                    error = error + u'タグ違反.('+word+')'       
            text = text+'<p>'+line
            i += len(line)
        for word in out:
            if word in text:
                error = error + u'禁止ワード.'
                break
        pw = self.get_argument('password')
        if na == '':
            na = u'誰かさん'
        if sub == '':
            sub = u'タイトルなし.'
        if i == 0:
            error = error + u'本文がありません.'
        elif i > 1000:
            error = error +u'文字数が1,000をこえました.'
        article = self.application.db.table(dbname)
        if len(article) == 0:
            no = 1
        else:
            item = article.get(where('number') == len(article))
            no = item['number']+1
        if error == '':
            reg = {'number':no,'name':na,'title':sub,'comment':text,'password':pw,'date':1}#datetime.today()}
            article.insert(reg)
            self.set_cookie('username',na)
            self.redirect('/'+dbname+'#article')
        else:
            self.render('regist.htm',content=error)

class AdminHandler(BaseHandler):
    @tornado.web.authenticated               
    def get(self,dbname,page='0'):
        if dbname == '':
            dbname = self.get_argument('record','')
        if self.application.collection(dbname) == False:
            self.render('regist.htm',content='urlが見つかりません')
        table = self.application.db.table(dbname) 
        rec = table.all()                   
        mente = self.application.db.get(where('kinds') == 'conf')
        if mente['mentenance'] == True:
            check = 'checked=checked'
        else:
            check = ''
        pos = self.application.gpos(dbname,page)
        self.render('modules/admin.htm',position=pos,records=rec,mente=check,password=mente['password'],db=dbname)

class AdminConfHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self,dbname,func):
        if func == 'set':
            if self.get_argument('mente','') == 'on':
                mente = True
            else:
                mente = False  
            word = self.get_argument('pass','')
            if word == '':
                self.render('regist.htm',content='パスワードを設定してください')
            else:
                self.application.db.update({'mentenance':mente,'password':word},where('kinds') == 'conf')     
        elif func == 'del':
            table = self.application.db.table(dbname)
            for x in self.get_argument('item','0'):
                table.remove(where('number') == int(x))
        self.redirect('/'+dbname+'/admin/0/')
          
class UserHandler(tornado.web.RequestHandler):
    def post(self,dbname):
        num = int(self.get_argument('number'))
        pas = self.get_argument('password')
        table = self.application.db.table(dbname)
        qwr = Query()
        obj = table.get(qwr.number == num)
        if obj and(obj['password'] == pas):
            table.remove(qwr.number == num)
        self.redirect('/'+dbname)
      
class SearchHandler(tornado.web.RequestHandler):       
    def post(self,dbname):
        self.word = self.get_argument('word1')
        self.radiobox = self.get_argument('filter')
        self.set_cookie('search',self.word)
        table = self.application.db.table(dbname)
        self.render('modules/search.htm',records=self.mylist(table.all()),word1=self.word,db=dbname)
    
    def get(self,dbname):
        word = self.get_cookie('search')
        self.render('modules/search.htm',records={},word1=word,db=dbname)
        
    def mylist(self,rec):
        for searchrec in rec:       
            if self.radiobox == 'name':
                if searchrec['name'].find(self.word) == True:
                    yield searchrec
            else:
                if searchrec['comment'].find(self.word) == True:
                    yield searchrec
        
class FooterModule(tornado.web.UIModule):
    def render(self,number,url,link):
        return self.render_string('modules/footer.htm',index=number,url=url,link=link)
    
class Applications(tornado.web.Application):    
    def __init__(self):
        self.db = TinyDB('static/db/db.json')
        handlers = [(r'/',NaviHandler),(r'/login',LoginHandler),(r'/logout',LogoutHandler),(r'/([a-zA-Z0-9_]+)',IndexHandler),(r'/([a-zA-Z0-9_]+)/([0-9]+)/',IndexHandler),
                    (r'/([a-zA-Z0-9_]+)/admin/([0-9]+)/',AdminHandler),(r'/([a-zA-Z0-9_]+)/admin/([a-z]+)/',AdminConfHandler),(r'/([a-zA-Z0-9_]+)/userdel',UserHandler),
                    (r'/([a-zA-Z0-9_]+)/search',SearchHandler),(r'/([a-zA-Z0-9_]+)/regist',RegistHandler)]
        settings = {'template_path':os.path.join(os.path.dirname(__file__),'pybbs'),
                        'static_path':os.path.join(os.path.dirname(__file__),'static'),
                        'ui_modules':{'Footer':FooterModule},
                        'cookie_secret':'bZJc2sWbQLKos6GkHn/VB9oXwQt8SOROkRvJ5/xJ89E=',
                        'xsrf_cookies':True,
                        #'debug':True,
                        'login_url':'/login'
                        }
        tornado.web.Application.__init__(self,handlers,**settings)
 
    def gpos(self,dbname,page):
        params = self.db.get(where('kinds') == 'conf')
        pos = int(page)
        if pos <= 0:
            pos = 0
        elif (pos-1)*params['count'] >= len(self.db.table(dbname)):
            pos = 0
        return pos
    
    def collection(self,name):
        for x in self.db.tables():
            if x == name:
                return True
        else:
            return False
        
if __name__ == '__main__':
    tornado.options.parse_command_line()
    wsgi_app = tornado.wsgi.WSGIAdapter(Application())
    server = wsgiref.simple_server.make_server('',8888,wsgi_app)
    server.server_forever()
    
