'''
Created on 2016/10/23

@author: fukemasashi
'''
import os.path
import tornado.auth
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
from tornado.options import define,options
import pymongo
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

class IndexHandler(tornado.web.RequestHandler):
    def get(self,dbname,page='0'):
        if self.application.collection(dbname) == False:
            self.render('regist.htm',content='urlが見つかりません')
            return
        params = self.application.db['params'].find_one()  
        i = params['count']      
        na = self.get_cookie('username')
        pos = self.application.gpos(dbname,page)
        col = self.application.db[dbname]
        rec = col.find()
        rec.sort('number')
        start = (pos-1)*i
        if start < 0:
            start = col.count()-i
            if start < 0:
                start = 0
        rec.limit(i)[start:start+i]
        if col.count() >= 10*i:
            self.render('modules/full.htm',position=pos,records=rec,data=params,db=dbname)
            return  
        self.render('modules/index.htm',position=pos,records=rec,data=params,username=na,db=dbname)
        
class LoginHandler(BaseHandler):
    def get(self):
        self.render('login.htm')
        
    def post(self):
        pw = self.application.db['params'].find_one()
        if self.get_argument('password') == pw['password']:
            self.set_current_user('admin')
        dbname = self.get_argument('record')
        self.redirect('/'+dbname+'/admin/0/')
        
class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_current_user()
        db = self.get_argument('db')
        self.redirect('/'+db)
        
class NaviHandler(tornado.web.RequestHandler):
    def get(self):
        coll = self.application.db.collection_names(include_system_collections=False)
        self.render('top.htm',coll=coll)

class RegistHandler(tornado.web.RequestHandler):
    def post(self,dbname):
        if self.application.collection(dbname) == False:
            self.render('regist.htm',content='urlが存在しません')
            return 
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
        article = self.application.db[dbname]
        rec = article.find()
        rec.sort('number',-1)
        if article.count() == 0:
            no = 1
        else:
            item = rec.limit(1)[0]
            no = item['number']+1
        if error == '':
            reg = {'number':no,'name':na,'title':sub,'comment':text,'password':pw,'date':datetime.now()}
            article.insert(reg)
            self.set_cookie('username',na)
            self.redirect('/'+dbname+'#article')
        else:
            self.render('regist.htm',content=error)

class AdminHandler(BaseHandler):
    @tornado.web.authenticated               
    def get(self,dbname,page='0'):
        if dbname == '':
            dbname = self.get_argument('record')
        if self.application.collection(dbname) == False:
            self.render('regist.htm',content='urlが見つかりません')
            return
        self.check_xsrf_cookie()
        coll = self.application.db[dbname] 
        rec = coll.find()                   
        param = self.application.db['params']
        mente = param.find_one()
        pos = self.application.gpos(dbname,page)
        self.render('modules/admin.htm',position=pos,records=rec,mente=mente['mentenance'],password=mente['password'],db=dbname)

class AdminConfHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self,dbname,func):
        if func == 'set':
            coll = self.application.db['params']
            mente = coll.find_one()
            mente['mentenance'] = self.get_argument('mente')  
            mente['password'] = self.get_argument('pass')
            coll.save(mente)     
        elif func == 'del':
            coll = self.application.db[dbname]
            for x in self.get_arguments():
                rec = coll.find_one({'number',x})
                if rec:
                    coll.remove(rec)
        self.redirect('/'+dbname+'/admin/0/')
          
class UserHandler(tornado.web.RequestHandler):
    def post(self,dbname):
        num = int(self.get_argument('number'))
        pas = self.get_argument('password')
        coll = self.application.db[dbname]
        obj = coll.find_one({'number':num})
        if obj and(obj['password'] == pas):
            coll.remove({'number':num})
        self.redirect('/'+dbname)
      
class SearchHandler(tornado.web.RequestHandler):       
    def post(self,dbname):
        self.word = self.get_argument('word1')
        self.radiobox = self.get_argument('filter')
        rec = self.application.db[dbname]
        self.render('modules/search.htm',records=self.mylist(rec),word1=self.word,db=dbname)
    
    def get(self,dbname):
        word = self.get_cookie('search')
        self.render('modules/search.htm',records={},word1=word,db=dbname)
        
    def mylist(self,rec):
        for searchrec in rec.find():       
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
        client = pymongo.MongoClient()
        self.db = client['mydatabase']
        handlers = [(r'/',NaviHandler),(r'/login',LoginHandler),(r'/logout',LogoutHandler),(r'/([a-z]+)',IndexHandler),(r'/([a-z]+)/([0-9]+)/',IndexHandler),
                    (r'/([a-z]+)/admin/([0-9]+)/',AdminHandler),(r'/([a-z]+)/admin/([a-z]+)/',AdminConfHandler),(r'/([a-z]+)/userdel',UserHandler),
                    (r'/([a-z]+)/search',SearchHandler),(r'/([a-z]+)/regist',RegistHandler)]
        settings = {'template_path':os.path.join(os.path.dirname(__file__),'pybbs'),
                        'static_path':os.path.join(os.path.dirname(__file__),'static'),
                        'ui_modules':{'Footer':FooterModule},
                        'cookie_secret':'bZJc2sWbQLKos6GkHn/VB9oXwQt8SOROkRvJ5/xJ89E=',
                        'xsrf_cookies':True,
                        'debug':True,
                        'login_url':'/login'
                        }
        tornado.web.Application.__init__(self,handlers,**settings)
 
    def gpos(self,dbname,page):
        coll = self.db['params']
        params = coll.find_one()
        pos = int(page)
        if pos <= 0:
            pos = 0
        elif (pos-1)*params['count'] >= self.db[dbname].count():
            pos = 0
        return pos
    
    def collection(self,name):
        for x in self.db.collection_names():
            if x == name:
                return True
        else:
            return False
        
if __name__ == '__main__':
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Applications())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
