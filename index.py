
import os
import re
import tornado.escape
import tornado.web
import pymongo
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
        params = self.application.db['params'].find_one()
        if params['mentenance'] == True:
            self.render('mentenance.htm',title=params['title'],db=dbname)
        if self.application.collection(dbname) == False:
            if self.current_user == b'admin':
                coll = self.application.db[dbname]
                coll.insert({})
                coll.remove({})
            else:
                raise tornado.web.HTTPError(404)
                return
        i = params['count']      
        na = tornado.escape.url_unescape(self.get_cookie("username",u"誰かさん"))
        pos = self.application.gpos(dbname,page)
        table = self.application.db[dbname]
        start = (pos-1)*i
        if start < 0:
            start = table.count()-i
            if start < 0:
                start = 0
        rec = table.find()
        rec.sort('number')
        rec.skip(start).limit(i)
        if table.count() >= 10*i:
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
        self.redirect('/login')
        
class NaviHandler(tornado.web.RequestHandler):
    def get(self):                  
        coll = sorted(self.application.coll(),key=str.lower)                
        self.render('top.htm',coll=coll,full=self.full)
                      
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
        
class RegistHandler(tornado.web.RequestHandler):
    def post(self,dbname):
        if self.application.collection(dbname) == False:
            raise tornado.web.HTTPError(404)
            return
        rec = self.application.db['params'].find_one()
        words = rec['bad_words']
        out = rec['out_words']
        na = self.get_argument('name')
        sub = self.get_argument('title')
        com = self.get_argument('comment')
        text = ''
        i = 0
        url = ''
        error = ''
        for word in out:
            if word in com:
                error = error + u'禁止ワード.'
                break
        for line in com.splitlines(True):
            if error:
                break
            for word in words:
                if word in line.lower():
                    error = error + u'タグ違反.('+word+')'       
            i += len(line)
            if not url:
                url = re.search('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', line).group(0)
            if re.match(' ',line):
                line = line.replace(' ','&nbsp;',1)
            text = text+'<p>'+self.link(line)+'<br></p>'
        if url:
           text = text+'検出url:<a href={0} class=livepreview>{0}</a>'.format(url) 
        pw = self.get_argument('password')
        if i == 0:
            error = error + u'本文がありません.'
        elif i > 1000:
            error = error +u'文字数が1,000をこえました.'
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
            s = datetime.now()
            reg = {'number':no,'name':na,'title':sub,'comment':text,'raw':com,'password':pw,'date':s.strftime('%Y/%m/%d %H:%M')}
            article.insert(reg)
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
    @tornado.web.authenticated
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
          
class UserHandler(tornado.web.RequestHandler):
    def post(self,dbname):
        num = self.get_argument('number')
        if num.isdigit() == True:
            num = int(num)
            pas = self.get_argument('password')
            table = self.application.db[dbname]
            obj = table.find_one({'number':num})
            if obj and(obj['password'] == pas):
                table.remove({'number':num})
        self.redirect('/'+dbname)
      
class SearchHandler(tornado.web.RequestHandler):       
    def post(self,dbname):
        self.word = tornado.escape.url_unescape(self.get_argument('word1'))
        self.radiobox = self.get_argument('filter')
        self.set_cookie('search',tornado.escape.url_escape(self.word))         
        rec = sorted(self.search(dbname),key=lambda x: x['number'])
        self.render('modules/search.htm',records=rec,word1=self.word,db=dbname)
    
    def get(self,dbname):
        if self.application.collection(dbname) == False:
            raise tornado.web.HTTPError(404)
            return
        word = self.get_cookie('search','')
        word = tornado.escape.url_unescape(word)
        self.render('modules/search.htm',records=[],word1=word,db=dbname)
        
    def search(self,dbname):
        table = self.application.db[dbname]    
        element = self.word.split()
        if len(element) == 0:
            element = ['']
        while len(element) < 3:
            element.append(element[0])
        if self.radiobox == 'comment':    
            for x in table.find({'$or':[{'raw':re.compile(element[0])},{'raw':re.compile(element[1])},{'raw':re.compile(element[2])}]}):
                com = ''
                for text in x['raw'].splitlines(True):                  
                    for word in self.word.split():                        
                        if text.find(word) > -1:
                            com = com +'<p style=background-color:yellow>'+text+'<br></p>'  
                            break                          
                    else:
                        com = com+'<p>'+text+'<br></p>'
                x['comment'] = com
                yield x       
        else:
            for x in table.find({'$or':[{'name':element[0]},{'name':element[1]},{'name':element[2]}]}):
                yield x    
                                        
class FooterModule(tornado.web.UIModule):
    def render(self,number,url,link):
        return self.render_string('modules/footer.htm',index=number,url=url,link=link)
    
class Application(tornado.web.Application):    
    def __init__(self):
        handlers = [(r'/',NaviHandler),(r'/login',LoginHandler),(r'/logout',LogoutHandler),(r'/title',TitleHandler),
                    (r'/([a-zA-Z0-9_]+)',IndexHandler),(r'/([a-zA-Z0-9_]+)/([0-9]+)/',IndexHandler),
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
        for x in ['params','objectlabs-system.admin.collections','objectlabs-system','system.indexes']:
            if x in name:
                name.remove(x)
        return name

app = Application()
MONGOLAB_URI = 'mongodb://kainushi:1234abcd@ds113678.mlab.com:13678/heroku_n905jfw2'
conn = pymongo.MongoClient(MONGOLAB_URI,13678)
app.db = conn.heroku_n905jfw2
