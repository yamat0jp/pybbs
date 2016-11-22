
import os.path
import shutil,copy
import tornado.auth
import tornado.escape
import tornado.web
from tinydb import TinyDB,Query,where
from tinydb.storages import MemoryStorage
from tinydb.operations import delete
from datetime import datetime

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
                raise tornado.web.HTTPError(404)
                return
        i = params['count']      
        na = tornado.escape.url_unescape(self.get_cookie("username",u"誰かさん"))
        pos = self.application.gpos(dbname,page)
        table = self.application.db.table(dbname)
        start = (pos-1)*i
        if start < 0:
            start = len(table)-i
            if start < 0:
                start = 0
        rec = sorted(table.all(),key=lambda x: x['number'])[start:start+i]
        for x in rec:
            for y in x['comment'].splitlines(True):
                y = '<p>'+y+'<br></p>'
        if len(table) >= 10*i:
            self.render('modules/full.htm',position=pos,records=rec,data=params,db=dbname)
            return
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
        self.render('top.htm',coll=sorted(self.name()),full=self.full)
        
    def name(self):
        for x in self.application.db.tables():
            if x != '_default':
                yield x
                
    def full(self,dbname):
        if dbname in self.application.db.tables():
            i = 10*self.application.db.get(where('kinds') == 'conf')['count']
            table = self.application.db.table(dbname)
            if len(table) >= i:
                return True
        return False

class TitleHandler(NaviHandler):
    def get(self):
        self.render('title.htm',coll=self.name(),full=self.full,
                    count=self.count,title=self.title,update=self.update)            

    def count(self,dbname):
        if dbname in self.application.db.tables():
            return len(self.application.db.table(dbname))
        else:
            return ''

    def title(self,dbname):
        if dbname in self.application.db.tables():
            table = self.application.db.table(dbname)
            if table.contains(where('number') == 1) == True:
                dic = table.get(where('number') == 1)
                return dic['title']
            else:
                return ''
            
    def update(self,dbname):
        if dbname in self.application.db.tables():
            table = self.application.db.table(dbname)
            i = len(table)
            if i == 0:
                return ''
            else:
                rec = sorted(table.all(),key=lambda x: x['number'])
                return rec[i-1]['date']
        
class RegistHandler(tornado.web.RequestHandler):
    def post(self,dbname):
        if self.application.collection(dbname) == False:
            raise tornado.web.HTTPError(404)
            return
        rec = self.application.db.get(where('kinds') == 'conf')
        words = rec['bad_words']
        out = rec['out_words']
        na = self.get_argument('name')
        sub = self.get_argument('title')
        com = self.get_argument('comment')
        text = ''
        i = 0
        error = ''
        for word in out:
            if word in com:
                error = error + u'禁止ワード.'
                break
        for line in com.splitlines(True):
            for word in words:
                if word in line:
                    error = error + u'タグ違反.('+word+')'       
            i += len(line)
            text = text+self.link(line)
        pw = self.get_argument('password')
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
            item = sorted(article.all(),key=lambda x: x['number'])[len(article)-1]
            no = item['number']+1
        if error == '':
            reg = {'number':no,'name':na,'title':sub,'comment':text,'password':pw,'date':datetime.now().strftime('%Y/%m/%d %H:%M')}
            article.insert(reg)
            restart()
            self.set_cookie('username',tornado.escape.url_escape(na))
            self.redirect('/'+dbname+'#article')
        else:
            self.render('regist.htm',content=error)
    
    def link(self,command):
        y = ''
        i = 0
        text = ''
        for x in command.split():
            if (y == '>>')and(x.isdecimal() == True):
                s = '<a href=#'+x+'>'+x+'</a>'
                while -1 < command.find(x,i):
                    j = command.find(x,i)
                    tmp = command[i:j]
                    i = j+len(x)
                    k = tmp.rsplit(None,1)
                    if ((len(k) > 1)and(k[1] == y))or(k[0] == y):
                        text = text+tmp+s                                                                       
                        break
                    else:
                        text = text+tmp+x                        
            y = x    
        if text == '':
            return command
        else:
            if len(command) > i:
                return text+command[i:]
            else:
                return text
    
class AdminHandler(BaseHandler):
    @tornado.web.authenticated               
    def get(self,dbname,page='0'):
        if dbname == '':
            dbname = self.get_argument('record','')
        if self.application.collection(dbname) == False:
            raise tornado.web.HTTPError(404)
            return
        table = self.application.db.table(dbname) 
        rec = sorted(table.all(),key=lambda x: x['number'])                   
        mente = self.application.db.get(where('kinds') == 'conf')
        if mente['mentenance'] == True:
            check = 'checked=checked'
        else:
            check = ''
        pos = self.application.gpos(dbname,page)
        i = mente['count']
        start = (pos-1)*i
        if start < 0:
            start = len(table)-i
            if start < 0:
                start = 0
        restart()
        self.application.db = TinyDB(st.json)
        self.render('modules/admin.htm',position=pos,records=rec[start:start+i],mente=check,password=mente['password'],db=dbname)

class AdminConfHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self,dbname,func):
        if func == 'set':
            param = self.application.db.get(where('kinds') == 'conf')['mentenance']
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
        restart()
        self.redirect('/'+dbname+'/admin/0/')
        
    def store(self):
        self.application.db.close()
        shutil.copy(st.json,st.bak)
        self.application.db = TinyDB(st.json)
        
    def restore(self):
        database = self.application.db
        bak = TinyDB(st.bak)
        for x in database.tables():
            if self.application.collection(x) == True:
                database.purge_table(x)
                if x in bak.tables():
                    table = database.table(x)
                    table.insert_multiple(bak.table(x).all())
        restart()
          
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
        self.word = tornado.escape.url_unescape(self.get_argument('word1'))
        self.radiobox = self.get_argument('filter')
        self.set_cookie('search',tornado.escape.url_escape(self.word))         
        table = self.application.db.table(dbname)
        #rec = table.search(where(radiobox).search(word))
        #rec = sorted(rec,key=lambda x: x['number'])
        rec = self.search(dbname)
        self.render('modules/search.htm',records=rec,word1=self.word,db=dbname)
    
    def get(self,dbname):
        if self.application.collection(dbname) == False:
            raise tornado.web.HTTPError(404)
            return
        word = self.get_cookie('search')
        self.render('modules/search.htm',records=[],word1=word,db=dbname)
        
    def search(self,name):
        table = self.application.db.table(name)
        mem = TinyDB(storage=MemoryStorage)
        for word in self.word.split():
            for x in table.search(where('comment').search(word)):
                if self.radiobox == 'comment':
                    result = ''
                    for text in x['comment'].splitlines(True):                  
                        if text.find(word) > -1:
                            result = result+'<p style=background-color:yellow>'+text+'</p>'                            
                        else:
                            result = result+'<p>'+text+'</p>'
                    if mem.get(where('number') == x['number']) == None:
                        i = mem.insert(x)
                        mem.update({'comment':result},eids=[i])   
                else:
                    rec = table.search(where('name').search(word))
                    return sorted(rec,key=lambda x: x['number'])     
        rec = sorted(mem.all(),key=lambda x: x['number'])
        mem.close()
        return rec
                                            
class FooterModule(tornado.web.UIModule):
    def render(self,number,url,link):
        return self.render_string('modules/footer.htm',index=number,url=url,link=link)
    
class Application(tornado.web.Application):    
    def __init__(self):
        self.db = TinyDB(st.json)
        handlers = [(r'/',NaviHandler),(r'/login',LoginHandler),(r'/logout',LogoutHandler),(r'/title',TitleHandler),
                    (r'/([a-zA-Z0-9_]+)',IndexHandler),(r'/([a-zA-Z0-9_]+)/([0-9]+)/',IndexHandler),
                    (r'/([a-zA-Z0-9_]+)/admin/([0-9]+)/',AdminHandler),(r'/([a-zA-Z0-9_]+)/admin/([a-z]+)/',AdminConfHandler),(r'/([a-zA-Z0-9_]+)/userdel',UserHandler),
                    (r'/([a-zA-Z0-9_]+)/search',SearchHandler),(r'/([a-zA-Z0-9_]+)/regist',RegistHandler)]
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

class static():
    json = 'static/db/db.json'
    bak = 'static/db/bak.json'

st = static()
app = Application()

def restart():
    pass
    #app.db.close()
    #app.db = TinyDB(st.json)    
