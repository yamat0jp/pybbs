
import os.path
import shutil,re
import tornado.escape
import tornado.web
import tornado.httpserver
import tornado.ioloop
import tornado.options
from tornado.options import define,options
from tinydb import TinyDB,Query,where
from tinydb.operations import delete
from datetime import datetime,date
import json

define('port',default=8000,help='run on the given port',type=int)

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
            return
        if self.application.collection(dbname) == False:
            if self.current_user == b'admin':
                self.application.db.table(dbname)
            else:
                raise tornado.web.HTTPError(404)
                return
        key = self.get_argument('key','')
        if key:
            table = self.application.db.table(dbname)
            rec = table.get(where('number') == int(key))
            if rec:
                self.render('article.htm',record=rec)
                return
            else:
                raise tornado.web.HTTPError(404)
                return
        i = params['count']      
        rule = tornado.escape.url_unescape(self.get_cookie('aikotoba',''))
        na = tornado.escape.url_unescape(self.get_cookie("username",u"誰かさん"))
        pos = self.application.gpos(dbname,page)
        table = self.application.db.table(dbname)
        start = (pos-1)*i
        if start < 0:
            start = len(table)-i
            if start < 0:
                start = 0
        bool = (dbname == params['info name'])
        rec = sorted(table.all(),key=lambda x: x['number'])[start:start+i]
        if bool == True:
            rec = rec[::-1]
        if len(table) >= 10*i:
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
        pw = self.application.db.get(where('kinds') == 'conf')
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
        
class NaviHandler(tornado.web.RequestHandler):              
    def get(self):
        col,na = self.name()
        if self.application.collection('params') == False:
            item = {"mentenance":False,"out_words":[u"阿保",u"馬鹿",u"死ね"],"password":"admin",
                    "title2":"<h1 style=color:gray;text-align:center>pybbs</h1>",
                    "bad_words":["<style","<link","<script","<img"],"count":30,
                    "title":"pybbs","info name":"info"}
            self.application.db.insert(item)
        self.render('top.htm',coll=col,name=na,full=self.full)
        
    def name(self):
        names = self.application.db.tables()
        na = self.application.db.get(where('kinds') == 'conf')['info name']
        for s in ['_default','master','temp']:
            if s in names:
                names.remove(s)
        if na in names:
            names.remove(na)
        else:
            na = ''
        return sorted(names),na
                
    def full(self,dbname):
        if dbname in self.application.db.tables():
            i = 10*self.application.db.get(where('kinds') == 'conf')['count']
            table = self.application.db.table(dbname)
            if len(table) >= i:
                return True
        return False

class TitleHandler(NaviHandler):
    def get(self):
        rec = sorted(self.title(),key=lambda x: x['date2'])
        self.render('title.htm',coll=rec,full=self.full)  
        
    def title(self):
        names = self.application.db.tables()
        for s in ['_default','master','temp']:
            if s in names:
                names.remove(s)
        for x in names:
            item = {}
            item['name'] = x
            table = self.application.db.table(x)
            i = len(table)
            item['count'] = i            
            if table.contains(where('number') == 1) == True:
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
        
class RegistHandler(tornado.web.RequestHandler):
    def post(self,dbname):
        if self.application.collection(dbname) == False:
            raise tornado.web.HTTPError(404)
            return
        self.database = dbname
        rec = self.application.db.get(where('kinds') == 'conf')
        words = rec['bad_words']
        out = rec['out_words']
        na = self.get_argument('name')
        sub = self.get_argument('title')
        com = self.get_argument('comment',None,False)
        text = ''
        i = 0
        url = []
        error = ''
        for word in out:
            if word in com:
                error = error + u'禁止ワード.'
                break
        for line in com.splitlines(True):
            if error != '':
                break
            for word in words:
                if word in line.lower():
                    error = error + u'タグ違反.('+word+')'       
            i += len(line)   
            obj = re.finditer('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', line)
            for x in obj:
                if x.group() not in url:
                    url.append(x.group())
            if re.match(' ',line):
                line = line.replace(' ','&nbsp;',1)
            text = text+'<p>'+self.link(line)+'<br></p>'
        s = ''
        for x in url:
            s = s+'<tr><td><a class=livepreview target=_blank href={0}>{0}</a></td></tr>'.format(x)
        if s:
            text = text+'<table><tr><td>検出URL:</td></tr>'+s+'</table>'
        pw = self.get_argument('password')
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
            if not na:
                na = u'誰かさん'
            if sub == '':
                sub = u'タイトルなし.'
            s = datetime.now()
            reg = {'number':no,'name':na,'title':sub,'comment':text,'raw':com,'password':pw,'date':s.strftime('%Y/%m/%d %H:%M')}
            article.insert(reg)
            self.set_cookie('username',tornado.escape.url_escape(na))
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
    @tornado.web.authenticated               
    def get(self,dbname,page):
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
          
class UserHandler(tornado.web.RequestHandler):
    table = None
    def get(self,dbname):
        self.table = self.application.db.table(dbname)
        q = self.get_query_argument('job','0',strip=True)
        num = self.page(int(q))        
        if num == '':
            self.redirect('/{0}#{1}'.format(dbname,q))           
        else:
            self.redirect('/{0}{1}#{2}'.format(dbname,num,q))
        
    def post(self,dbname):
        number = self.get_argument('number')
        if number.isdigit() == True:
            num = int(number)
            pas = self.get_argument('password')
            self.table = self.application.db.table(dbname)
            qwr = Query()
            obj = self.table.get(qwr.number == num)
            if obj and(obj['password'] == pas):
                self.table.update({'title':u'削除されました','name':'','comment':u'<i><b>投稿者により削除されました</b></i>'},qwr.number == num)
                self.redirect('/{0}{1}#{2}'.format(dbname,self.page(num),number))
            else:
                self.redirect('/'+dbname)
                
    def page(self,number):
        if self.table != None:
            rec = self.table.count(where('number') <= number)
            conf = self.application.db.get(where('kinds') == 'conf')
            if len(self.table)-rec >= conf['count']:
                return '/'+str(1+rec//conf['count'])+'/'
            else:
                return ''
      
class SearchHandler(tornado.web.RequestHandler):       
    def post(self,dbname):
        arg = self.get_argument('word1')
        self.word = arg 
        self.radiobox = self.get_argument('filter')      
        rec = sorted(self.search(dbname),key=lambda x: x['number'])
        self.render('modules/search.htm',records=rec,word1=arg,db=dbname)
    
    def get(self,dbname):
        if self.application.collection(dbname) == False:
            raise tornado.web.HTTPError(404)
            return
        self.render('modules/search.htm',records=[],word1='',db=dbname)
        
    def search(self,dbname):
        table = self.application.db.table(dbname)    
        element = self.word.split()
        if len(element) == 0:
            element = ['']
        while len(element) < 3:
            element.append(element[0])
        if self.radiobox == 'comment':
            query = (Query().raw.search(element[0])) | (Query().raw.search(element[1])) | (Query().raw.search(element[2]))
        else:
            query = (Query().name == element[0]) | (Query().name == element[1]) | (Query().name == element[2])
        if self.radiobox == 'comment':    
            for x in table.search(query):
                com = ''
                for text in x['raw'].splitlines(True):                  
                    for word in element:                        
                        if text.find(word) > -1:
                            com = com +'<p style=background-color:yellow>'+text+'<br></p>'  
                            break                          
                    else:
                        com = com+'<p>'+text+'<br></p>'
                x['comment'] = com
                yield x       
        else:
            for x in table.search(query):
                yield x
                                        
class FooterModule(tornado.web.UIModule):
    def render(self,number,url,link):
        return self.render_string('modules/footer.htm',index=number,url=url,link=link)
    
class HeadlineApi(tornado.web.RequestHandler):
    def get(self):
        response = {}
        for x in self.application.db.tables():
            if x != '_default':
                response[x] = self.get_data(x)           
        self.write(json.dumps(response,ensure_ascii=False))
    
    def get_data(self,dbname):
        table = self.application.db.table(dbname)
        i = len(table)
        if i == 0:
            return {}
        else:
            rec = sorted(table.all(),key=lambda x: x['number'])[i-1]
            return {'number':rec['number'],'title':rec['title'],'name':rec['name'],'comment':rec['raw'][0:19]}
        
class ArticleApi(tornado.web.RequestHandler):
    def get(self,dbname,number):
        if self.application.collection(dbname) == True:
            table = self.application.db.table(dbname)
            response = table.get(where('number') == int(number))
            if response == None:
                response = {}
            else:
                del response['comment']
            self.write(json.dumps(response,ensure_ascii=False))
        else:
            tornado.web.HTTPError(404)
    
    def post(self,dbname):
        name = self.get_argument('name',u'誰かさん')
        title = self.get_argument('title',u'タイトルなし')
        comment = self.get_argument('comment')
        table = self.application.db.table(dbname)
        table.insert({'name':name,'title':title,'comment':comment})
        
class HelpHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('help.htm',req='') 
        
    def post(self):
        com = self.get_argument('help','')
        text = ''
        for line in com.splitlines():
            text +='<p>'+line
        table = self.application.db.table('master')
        time = datetime.now()
        table.insert({'comment':text,'time':time.strftime('%Y/%m/%d %H:%M')})
        if com == '':
            req = ''
        else:
            req = '送信しました'
        self.render('help.htm',req=req)
        
class MasterHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        if self.current_user == b'admin':
            com = self.application.db.table('master').all()
            self.render('master.htm',com=com)
        else:
            raise tornado.web.HTTPError(404)
        
class AlertHandler(UserHandler):
    def get(self):
        db = self.get_query_argument('db')
        num = self.get_query_argument('num')
        self.table = self.application.db.table(db)
        tb = self.table.get(where('number') == int(num))
        s = self.page(int(num))
        jump = '/'+db+s+'#'+num
        link = '<p><a href={0}>{0}</a>'.format(jump)
        time = datetime.now()
        data = {'comment':tb['comment']+link,'time':time.strftime('%Y/%m/%d'),
                'link':jump,'date':date.weekday(time)}
        id = self.application.db.table('temp').insert(data)
        self.render('alert.htm',com=data['comment'],num=id)
    
    def post(self):
        id = int(self.get_argument('num'))
        table = self.application.db.table('temp')
        tb = table.get(eid=id)
        link = tb['link']
        table.remove(eids=[id])
        table.remove(where('date') != date.weekday(datetime.now()))
        if self.get_argument('admit','') == 'ok':
            com = self.get_argument('com')
            tb['comment'] = com+tb['comment']
            del tb['date']
            table = self.application.db.table('master')
            table.insert(tb)
        self.redirect(link)
        
class Application(tornado.web.Application):    
    def __init__(self):
        self.db = TinyDB(st.json)             
        handlers = [(r'/',NaviHandler),(r'/login',LoginHandler),(r'/logout',LogoutHandler),(r'/title',TitleHandler),
                    (r'/headline/api',HeadlineApi),(r'/read/api/([a-zA-Z0-9_]+)/([0-9]+)',ArticleApi),(r'/write/api/([a-zA-Z0-9_]+)',ArticleApi),
                    (r'/help',HelpHandler),(r'/master/*',MasterHandler),(r'/alert',AlertHandler),
                    (r'/([a-zA-Z0-9_]+)',IndexHandler),(r'/([a-zA-Z0-9_]+)/([0-9]+)/*',IndexHandler),
                    (r'/([a-zA-Z0-9_]+)/admin/([0-9]+)/*',AdminHandler),(r'/([a-zA-Z0-9_]+)/admin/([a-z]+)/*',AdminConfHandler),(r'/([a-zA-Z0-9_]+)/userdel',UserHandler),
                    (r'/([a-zA-Z0-9_]+)/search',SearchHandler),(r'/([a-zA-Z0-9_]+)/regist',RegistHandler)]
        settings = {'template_path':os.path.join(os.path.dirname(__file__),'templates'),
                        'static_path':os.path.join(os.path.dirname(__file__),'static'),
                        'ui_modules':{'Footer':FooterModule},
                        'cookie_secret':'bZJc2sWbQLKo6GkHn/VB9oXwQt8SOROkRvJ5/xJ89Eo=',
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
        if name in self.db.tables():
            return True
        else:
            return False

class static():
    json = 'static/db/db.json'
    bak = 'static/db/bak.json'

st = static()
if __name__ == '__main__':
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
