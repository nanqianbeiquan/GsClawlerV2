# coding=gbk
import PackageTool
import requests
import os
from PIL import Image
from bs4 import BeautifulSoup
import json
import re
from FuJianConfig import *
import datetime
from requests.exceptions import RequestException
import sys
import time
from gs import MSSQL
import random
import subprocess
# from Tables_dict import *
from gs.Searcher import Searcher
from gs.Searcher import get_args
from gs.KafkaAPI import KafkaAPI
import requests
requests.packages.urllib3.disable_warnings()

class FuJianSearcher(Searcher):
    search_result_json = None
    pattern = re.compile("\s")
    cur_mc = ''
    cur_code = ''
    json_result_data = []
    today = None
    # kafka = KafkaAPI("GSCrawlerTest")
    session_token = None
    cur_time = None
    verify_ip = None
    # save_tag_a = None
    load_func_dict = {}

    def __init__(self):
        super(FuJianSearcher, self).__init__(use_proxy=True)
        self.headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:47.0) Gecko/20100101 Firefox/47.0",
                        "Host": "wsgs.fjaic.gov.cn",
                        "Accept": "*/*",                            # 与网站上的区别
                        "Accept-Encoding": "gzip, deflate",
                        "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
                        "Connection": "keep-alive",
                        "Referer": "http://wsgs.fjaic.gov.cn/creditpub/home",
                        "Upgrade-Insecure-Requests": "1",           #为啥加这段
                        "Content-type": "application/json"
                        }
        # self.cur_time = '%d' % (time.time() * 1000)
        self.get_session_token()
        self.get_verify_ip()
        # self.json_result = {}
        self.set_config()
        time=datetime.datetime.now()
        self.time=time.strftime('%Y%m%d')
        self.load_func_dict[u'动产抵押登记信息'] = self.load_dongchandiyadengji
        self.load_func_dict[u'动产抵押信息'] = self.load_dongchandiyadengji
        self.load_func_dict[u'股权出质登记信息'] = self.load_guquanchuzhidengji
        self.load_func_dict[u'行政处罚信息'] = self.load_xingzhengchufa
        self.load_func_dict[u'经营异常信息'] = self.load_jingyingyichang
        self.load_func_dict[u'严重违法信息'] = self.load_yanzhongweifa
        self.load_func_dict[u'严重违法失信信息'] = self.load_yanzhongweifa
        self.load_func_dict[u'抽查检查信息'] = self.load_chouchajiancha
        self.load_func_dict[u'基本信息'] = self.load_jiben
        self.load_func_dict[u'股东信息'] = self.load_gudong
        self.load_func_dict[u'发起人信息'] = self.load_gudong
        self.load_func_dict[u'变更信息'] = self.load_biangeng
        self.load_func_dict[u'主要人员信息'] = self.load_zhuyaorenyuan
        self.load_func_dict[u'分支机构信息'] = self.load_fenzhijigou
        self.load_func_dict[u'清算信息'] = self.load_qingsuan
        self.load_func_dict[u'参加经营的家庭成员姓名'] = self.load_jiatingchengyuan     # Modified by Jing
        self.load_func_dict[u'投资人信息'] = self.load_touziren     #Modified by Jing
        self.load_func_dict[u'合伙人信息'] = self.load_hehuoren     #Modified by Jing    
        self.load_func_dict[u'成员名册'] = self.load_chengyuanmingce     #Modified by Jing
        self.load_func_dict[u'撤销信息'] = self.load_chexiao     #Modified by Jing
        self.load_func_dict[u'主管部门（出资人）信息'] = self.load_DICInfo     #Modified by Jing

    def set_config(self):
        self.plugin_path = os.path.join(sys.path[0], '../fu_jian/ocr/type34.bat')
        self.group = 'Crawler'  # 正式
        self.kafka = KafkaAPI("GSCrawlerResult")  # 正式
        # self.group = 'CrawlerTest'  # 测试
        # self.kafka = KafkaAPI("GSCrawlerTest")  # 测试
        self.topic = 'GsSrc35'
        self.province = u'福建省'
        self.kafka.init_producer()

    def get_verify_ip(self):
        url = 'http://wsgs.fjaic.gov.cn/creditpub/security/verify_ip'
        r = self.post_request(url, timeout=20)#,verify=False
        self.verify_ip = r.text

    def get_verify_keyword(self, keyword):
        url = "http://wsgs.fjaic.gov.cn/creditpub/security/verify_keyword"
        params = {'keyword': keyword}
        r = self.post_request(url, params, timeout=20)#,verify=False
        return r.text

    def get_validate_image_save_path(self):
        return os.path.join(sys.path[0], '../temp/' + str(random.random())[2:] + '.png')

    def get_validate_file_path(self):
        return os.path.join(sys.path[0], '../temp/' + str(random.random())[2:] + '.txt')
    
    def recognize_yzm(self,validate_path,validate_result_path):
        cmd = self.plugin_path + " " + validate_path+ " " + validate_result_path
        # print cmd
        p=subprocess.Popen(cmd.encode('gbk','ignore'), stdout=subprocess.PIPE)
        p.communicate()
        fo = open(validate_result_path,'r')
        answer=fo.readline().strip()
        fo.close()
        print 'answer: '+answer.decode('gbk', 'ignore')
        os.remove(validate_path)
        os.remove(validate_result_path)
        return answer.decode('gbk', 'ignore')

    def get_yzm(self):
        params = {'ra': '%.15f' % random.random(), 'preset:': ''}  # 与网站中有和关系？
        image_url = 'http://wsgs.fjaic.gov.cn/creditpub/captcha'
        r = self.get_request(image_url, params, timeout=20)#, verify=False
        # print r.headers
        yzm_path = self.get_validate_image_save_path()
        with open(yzm_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    f.flush()
            f.close()
        yzm_file_path =self.get_validate_file_path()
        yzm = self.recognize_yzm(yzm_path,yzm_file_path) 
        return yzm 

    def get_session_token(self):
        r = self.get_request('http://wsgs.fjaic.gov.cn/creditpub/home', timeout=20)#,verify=False
        # print r.text
        idx_1 = r.text.index('session.token": "') + len('session.token": "')
        idx_2 = r.text.index('"', idx_1)
        self.session_token = r.text[idx_1:idx_2]

    def get_tag_a_from_page(self, keyword):
        tag_a = None
        for t in range(10):
            self.get_verify_keyword(keyword)
#           self.today = str(datetime.date.today()).replace('-', '')
            yzm = self.get_yzm()
            url_1 = 'http://wsgs.fjaic.gov.cn/creditpub/security/verify_captcha'
            params_1 = {'captcha':yzm, 'session.token': self.session_token}
            r_1 = self.post_request(url=url_1, params=params_1, timeout=20) #, verify=False
            # print r_1, r_1.text
            if r_1.text != '0':
                url_2 = 'http://wsgs.fjaic.gov.cn/creditpub/search/ent_info_list'
                params_2 = {'captcha': yzm, 'condition.keyword': keyword, 'searchType': '1', 'session.token': self.session_token}
                r_2 = self.post_request(url=url_2, params=params_2, timeout=20) #, verify=False
                r_2.encoding = 'utf-8'
                if u'您搜索的条件无查询结果' not in r_2.text:
                    soup = BeautifulSoup(r_2.text, 'lxml')
                    content=soup.find(class_='list-info')
                    corp=content.find(class_='list-item')
                    self.cur_mc = corp.find(class_='link').get_text().strip().replace('(', u'（').replace(')', u'）')
                    if keyword == self.cur_mc:
                        self.cur_code = corp.find(class_='profile').span.get_text().strip()
                        tag_a = corp.find(class_='link').a['href']
                break
        return tag_a

    def get_search_args(self, tag_a, keyword):
        if tag_a:
            return [tag_a]
        else:
            return []

    def parse_detail(self, args):
        page = args[0]                 # arg 首页的import 从gs.searcher中引入的
        r2 = self.post_request(page, timeout=20)     #page 即是tag_a
        if u'该市场主体不在公示范围' not in r2.text:
            resdetail = BeautifulSoup(r2.text, 'lxml')
            print 'self.save_tag_a'
            print self.save_tag_a
            if not self.save_tag_a:
                li_list = resdetail.select('html body.layout div.main div.notice ul li')       #详情页 上标
                mc = li_list[0].text
                code = li_list[1].text
                # title_bar = resdetail.find(class_='title-bar clearfix')
                # if not title_bar:
                #     print '************************************'
                #     print r2.text
                # mc=title_bar.find('li')
                # code=mc.find_next('li')
                self.cur_mc=mc.strip()
                self.cur_code=code.strip()[13:]  # 前13个为 【注册号/统一社会信用代码：】
                print self.cur_mc,self.cur_code
            div_element_list = resdetail.find_all(class_='hide') #(style="display: none;") # 灰色的也能查看？打印确认
            for div_element in div_element_list:
                table_element_list = div_element.find_all('table')
                for table_element in table_element_list:
                    row_cnt=len(table_element.find_all("tr"))
    #                 print 'row_cnt',row_cnt
                    table_desc = table_element.find("th").get_text().strip().split('\n')[0]
                    if table_desc in self.load_func_dict:
                        if table_desc == u'清算信息':
                            self.load_func_dict[table_desc](table_element)
                        elif row_cnt > 3:
                            self.load_func_dict[table_desc](table_element)
                    else:
                        raise Exception("unknown table!")
        else:
            print u'该市场主体不在公示范围'

    def load_jiben(self,table_element):
        jsonarray = []
        tr_element_list = table_element.find_all("tr")
        values = {}
        for tr_element in tr_element_list[1:]:
            th_element_list = tr_element.find_all('th')
            td_element_list = tr_element.find_all('td')
            if len(th_element_list) == len(td_element_list):
                col_nums = len(th_element_list)
                for i in range(col_nums):
                    col_dec = th_element_list[i].get_text().strip().replace('\n','')
                    col=jiben_column_dict[col_dec]
                    val = td_element_list[i].get_text().strip().replace('\n','')
                    if col != u'':
                        values[col] = val
                        if col == 'Registered_Info:registrationno':
                            if len(val) == 18:
                                values['Registered_Info:tyshxy_code'] = val
                            else:
                                values['Registered_Info:zch'] = val
#                     print col,val
        values['Registered_Info:province']=self.province
        values['rowkey']=self.cur_mc+'_01_'+self.cur_code+'_'
        jsonarray.append(values)
        self.json_result['Registered_Info']=jsonarray             #什么意思呢？
#         json_jiben=json.dumps(jsonarray,ensure_ascii=False)
#         print 'json_jiben',json_jiben
        
        
    def load_gudong(self, table_element):
        tr_element_list = table_element.find_all(class_="page-item")
        th_element_list = table_element.find_all('th')[1:-1]
        jsonarray = []
        values = {}
        id=1
        for tr_element in tr_element_list:    
            td_element_list = tr_element.find_all('td')
            col_nums = len(th_element_list)
            for i in range(col_nums):
                col_dec = th_element_list[i].get_text().strip().replace('\n','')
                col=gudong_column_dict[col_dec]
                td = td_element_list[i]
                val = td.get_text().strip()
                if val == u'详情':
                    link=td.a['href']
                    detail_th_list = ['Shareholder_Info:subscripted_capital','Shareholder_Info:actualpaid_capital',
                                      'Shareholder_Info:subscripted_method','Shareholder_Info:subscripted_amount',
                                      'Shareholder_Info:subscripted_time','Shareholder_Info:actualpaid_method',
                                      'Shareholder_Info:actualpaid_amount','Shareholder_Info:actualpaid_time']
                    r2 = self.get_request(link)
                    resdetail = r2.text
                    htmldetail = BeautifulSoup(resdetail,'html.parser')  # 为啥能加载js？原因是？
                    detail_content = htmldetail.find(class_="info m-bottom m-top")
                    detail_tr_list = detail_content.find_all('tr')
                    if len(detail_tr_list)>3:
                        for tr_ele in detail_tr_list[3:]:
                            td_ele_list = tr_ele.find_all('td')[1:]
                            detail_col_nums = len(td_ele_list)                       
                            for m in range(detail_col_nums):
                                col = detail_th_list[m]
                                td=td_ele_list[m]
                                val = td.text.strip()
                                values[col] = val
#                             print col,val
                    values[col] = link
                else:
                    values[col] = val
            values['Shareholder_Info:registrationno']=self.cur_code
            values['Shareholder_Info:enterprisename']=self.cur_mc
            values['Shareholder_Info:id']=str(id)
            values['rowkey']=self.cur_mc+'_04_'+self.cur_code+'_'+self.time+str(id)
            jsonarray.append(values)
            values = {}
            id+=1                 #如何映射？    通过上面的values['Shareholder_Info:id']=str(id) 来映射
        self.json_result['Shareholder_Info']=jsonarray
#         json_gudong=json.dumps(jsonarray,ensure_ascii=False)
#         print 'json_gudong',json_gudong
                                                                   
 
    def load_touziren(self,table_element):
        tr_element_list = table_element.find_all(class_="page-item")
        th_element_list = table_element.find_all('th')[1:-1]
        jsonarray = []
        values = {}
        id=1
        for tr_element in tr_element_list:                      
            td_element_list = tr_element.find_all('td')
            col_nums = len(th_element_list)
            for i in range(col_nums):
                col_dec = th_element_list[i].get_text().strip().replace('\n','')
                col=touziren_column_dict[col_dec]
                td = td_element_list[i]
                val = td.get_text().strip()
                values[col] = val
#                 print col,val
            values['Investor_Info:registrationno']=self.cur_code
            values['Investor_Info:enterprisename']=self.cur_mc
            values['Investor_Info:id']=str(id)
            values['rowkey']=self.cur_mc+'_02_'+self.cur_code+'_'+self.time+str(id)
            jsonarray.append(values)
            values = {}
            id+=1
        self.json_result['Investor_Info']=jsonarray
#         json_touziren=json.dumps(jsonarray,ensure_ascii=False)
#         print 'json_touziren',json_touziren  
                              

    def load_hehuoren(self,table_element):
        tr_element_list = table_element.find_all(class_="page-item")
        th_element_list = table_element.find_all('th')[1:-1]
        jsonarray = []
        values = {}
        id=1
        for tr_element in tr_element_list:                      
            td_element_list = tr_element.find_all('td')
            col_nums = len(th_element_list)
            for i in range(col_nums):
                col_dec = th_element_list[i].get_text().strip().replace('\n','')
                col=hehuoren_column_dict[col_dec]
                td = td_element_list[i]
                val = td.get_text().strip()
                values[col] = val
#                 print col,val
            values['Partner_Info:registrationno']=self.cur_code
            values['Partner_Info:enterprisename']=self.cur_mc
            values['Partner_Info:id']=str(id)
            values['rowkey']=self.cur_mc+'_03_'+self.cur_code+'_'+self.time+str(id)
            jsonarray.append(values)
            values = {}
            id+=1
        self.json_result['Partner_Info']=jsonarray
#         json_hehuoren=json.dumps(jsonarray,ensure_ascii=False)
#         print 'json_hehuoren',json_hehuoren 
            
            
    def load_DICInfo(self, table_element):
        tr_element_list = table_element.find_all(class_="page-item")
        th_element_list = table_element.find_all('th')[1:-1]
        jsonarray = []
        values = {}
        id=1
        for tr_element in tr_element_list:                     
            td_element_list = tr_element.find_all('td')
            col_nums = len(th_element_list)
            for i in range(col_nums):
                col_dec = th_element_list[i].get_text().strip().replace('\n','')
                col=DICInfo_column_dict[col_dec]
                td = td_element_list[i]
                val = td.get_text().strip()
                values[col] = val
#                 print col,val
            values['DIC_Info:registrationno']=self.cur_code
            values['DIC_Info:enterprisename']=self.cur_mc
            values['DIC_Info:id']=str(id)
            jsonarray.append(values)
            values = {} 
            id+=1
        # self.json_result['DIC_Info']=jsonarray
#         json_DICInfo=json.dumps(jsonarray,ensure_ascii=False)
#         print 'json_DICInfo',json_DICInfo   
        

    def load_biangeng(self, table_element):
        tr_element_list = table_element.find_all(class_="page-item")
        th_element_list = table_element.find_all('th')[1:-1]
        jsonarray = []
        values = {}
        id=1
        for tr_element in tr_element_list:                    
            td_element_list = tr_element.find_all('td')
            col_nums = len(th_element_list)
            for i in range(col_nums):
                col_dec = th_element_list[i].text.strip().replace('\n','')
                col=biangeng_column_dict[col_dec]
                td = td_element_list[i]
                val = td.get_text().strip()
                if val.endswith(u'收起更多'):
                    valmore=td.find(id='allWords').get_text().strip().replace('\n','')
                    values[col] = valmore
                else:
                    values[col] = val
#                 print col,val
            values['Changed_Announcement:registrationno']=self.cur_code
            values['Changed_Announcement:enterprisename']=self.cur_mc
            values['Changed_Announcement:id']=str(id)
            values['rowkey']=self.cur_mc+'_05_'+self.cur_code+'_'+self.time+str(id)
            jsonarray.append(values)
            values = {} 
            id+=1
        self.json_result['Changed_Announcement']=jsonarray
#         json_biangeng=json.dumps(jsonarray,ensure_ascii=False)
#         print 'json_biangeng',json_biangeng
        
                    
    def load_chexiao(self, table_element):
        pass


    def load_zhuyaorenyuan(self, table_element):
        tr_element_list = table_element.find_all(class_="page-item")
        th_element_list = table_element.find_all('th')[1:-1]
        jsonarray = []
        values = {}
        id=1
        for tr_element in tr_element_list:                      
            td_element_list = tr_element.find_all('td')
            for i in range(6):
                col_dec = th_element_list[i].text.strip().replace('\n','')
                col=zhuyaorenyuan_column_dict[col_dec]
                td = td_element_list[i]
                val = td.get_text().strip()
                values[col] = val
#                 print th,val
                if len(values) ==3:
                    if values['KeyPerson_Info:keyperson_name'] == '':
                        continue
                    else:
                        values['KeyPerson_Info:registrationno'] = self.cur_code
                        values['KeyPerson_Info:enterprisename'] = self.cur_mc
                        values['KeyPerson_Info:id'] = str(id)
                        values['rowkey']=self.cur_mc+'_06_'+self.cur_code+'_'+self.time+str(id)
                        jsonarray.append(values)
                    values = {}
                    id+=1
        self.json_result['KeyPerson_Info']=jsonarray
#         json_zhuyaorenyuan=json.dumps(jsonarray,ensure_ascii=False)
#         print 'json_zhuyaorenyuan',json_zhuyaorenyuan
        
     
    def load_jiatingchengyuan(self, table_element):
        tr_element_list = table_element.find_all(class_="page-item")
        th_element_list = table_element.find_all('th')[1:-1]
        jsonarray = []
        values = {}
        id=1
        for tr_element in tr_element_list:                      
            td_element_list = tr_element.find_all('td')
            for i in range(4):
                col_dec = th_element_list[i].text.strip().replace('\n','')
                col=jiatingchengyuan_column_dict[col_dec]
                td = td_element_list[i]
                val = td.get_text().strip()
                values[col] = val
#                 print th,val
                if len(values) ==2:
                    values['Family_Info:registrationno']=self.cur_code
                    values['Family_Info:enterprisename']=self.cur_mc
                    values['Family_Info:id'] = str(id)
                    values['rowkey']=self.cur_mc+'_07_'+self.cur_code+'_'+self.time+str(id)
                    jsonarray.append(values)
                    values = {}
                    id+=1
        self.json_result['Family_Info']=jsonarray
#         json_jiatingchengyuan=json.dumps(jsonarray,ensure_ascii=False)
#         print 'json_jiatingchengyuan',json_jiatingchengyuan
        
  
    def load_chengyuanmingce(self, table_element):
        tr_element_list = table_element.find_all(class_="page-item")
        th_element_list = table_element.find_all('th')[1:-1]
        jsonarray = []
        values = {}
        for tr_element in tr_element_list:                      
            td_element_list = tr_element.find_all('td')
            for i in range(4):
                col_dec = th_element_list[i].text.strip().replace('\n','')
                col=chengyuanmingce_column_dict[col_dec]
                td = td_element_list[i]
                val = td.get_text().strip()
                values[col] = val
#                 print th,val
                if len(values) ==2:
                    values['Members_Info:registrationno']=self.cur_code
                    values['Members_Info:enterprisename']=self.cur_mc
                    values['Members_Info:id'] = str(id)
                    jsonarray.append(values)
                    values = {}
        # self.json_result['Members_Info']=jsonarray
#         json_jiatingchengyuan=json.dumps(jsonarray,ensure_ascii=False)
#         print 'json_jiatingchengyuan',json_jiatingchengyuan
        

    def load_fenzhijigou(self, table_element):
        tr_element_list = table_element.find_all(class_="page-item")
        th_element_list = table_element.find_all('th')[1:-1]
        jsonarray = []
        values = {}
        id=1
        for tr_element in tr_element_list:                     
            td_element_list = tr_element.find_all('td')
            col_nums = len(th_element_list)
            for i in range(col_nums):
                col_dec = th_element_list[i].text.strip().replace('\n','')
                col=fenzhijigou_column_dict[col_dec]
                td = td_element_list[i]
                val = td.get_text().strip()
                values[col] = val
#                 print col,val
            values['Branches:registrationno']=self.cur_code
            values['Branches:enterprisename']=self.cur_mc
            values['Branches:id'] = str(id)
            values['rowkey']=self.cur_mc+'_08_'+self.cur_code+'_'+self.time+str(id)
            jsonarray.append(values)
            values = {}
            id+=1
        self.json_result['Branches']=jsonarray
#         json_fenzhijigou=json.dumps(jsonarray,ensure_ascii=False)
#         print 'json_fenzhijigou',json_fenzhijigou
        
 
    # 加载清算信息
    def load_qingsuan(self, table_element):
        tr_element_list = table_element.find_all('tr')[1:]
        # th_element_list = table_element.find_all('th')[1:-1]
        jsonarray = []
        values = {}
        for tr_element in tr_element_list:
            col_desc = tr_element.find('th').get_text().strip()
            col = qing_suan_dict[col_desc]
            td_list = tr_element.find_all('td')
            td_va = []
            for td in td_list:
                va = td.get_text().strip()
                td_va.append(va)
            val = ','.join(td_va)
            values[col] = val
        values['liquidation_Information:registrationno']=self.cur_code
        values['liquidation_Information:enterprisename']=self.cur_mc
        values['rowkey']=self.cur_mc+'_09_'+self.cur_code+'_'
        jsonarray.append(values)
        values = {}
        self.json_result['liquidation_Information']=jsonarray
#         json_fenzhijigou=json.dumps(jsonarray,ensure_ascii=False)
#         print 'json_fenzhijigou',json_fenzhijigou


    def load_dongchandiyadengji(self, table_element):  
        tr_element_list = table_element.find_all(class_="page-item")
        th_element_list = table_element.find_all('th')[1:-1]
        jsonarray = []
        values = {}
        id=1
        for tr_element in tr_element_list:    
            td_element_list = tr_element.find_all('td')
            col_nums = len(th_element_list)
            for i in range(col_nums):
                col_dec = th_element_list[i].text.strip().replace('\n','')
                col=dongchandiyadengji_column_dict[col_dec]
                td = td_element_list[i]
                val = td.get_text().strip()
                if val == u'详情':
                    link=td.a['href']
#                     print 'detail_link',self.detail_link
                    values[col] = link
                else:
                    values[col] = val
            values['Chattel_Mortgage:registrationno']=self.cur_code
            values['Chattel_Mortgage:enterprisename']=self.cur_mc
            values['Chattel_Mortgage:id'] = str(id)
            values['rowkey']=self.cur_mc+'_11_'+self.cur_code+'_'+self.time+str(id)
            jsonarray.append(values)
            values = {}
            id+=1
        self.json_result['Chattel_Mortgage']=jsonarray
#         json_dongchandiyadengji=json.dumps(jsonarray,ensure_ascii=False)
#         print 'json_dongchandiyadengji',json_dongchandiyadengji
        

    def load_guquanchuzhidengji(self, table_element):
        tr_element_list = table_element.find_all(class_="page-item")
        th_element_list = table_element.find_all('th')[1:-1]
        jsonarray = []
        values = {}
        id=1
        for tr_element in tr_element_list:    
            td_element_list = tr_element.find_all('td')
            col_nums = len(th_element_list)
            for i in range(col_nums):
                col_dec = th_element_list[i].text.strip().replace('\n','')
                previous= th_element_list[(i-1)].text.strip().replace('\n','')
                if col_dec==u'证照/证件号码' and previous==u'出质人':
                    col='Equity_Pledge:equitypledge_pledgorid'
                elif col_dec==u'证照/证件号码' and previous==u'质权人':
                    col='Equity_Pledge:equitypledge_pawneeid'
                else:
                    col=guquanchuzhidengji_column_dict[col_dec]
                td = td_element_list[i]
                val = td.get_text().strip()
                if val == u'详情':
                    link=td.a['href']
                    values[col] = link
                else:
                    values[col] = val
            values['Equity_Pledge:registrationno']=self.cur_code
            values['Equity_Pledge:enterprisename']=self.cur_mc
            values['Equity_Pledge:id'] = str(id)
            values['rowkey']=self.cur_mc+'_12_'+self.cur_code+'_'+self.time+str(id)
            jsonarray.append(values)
            values = {}
            id+=1
        self.json_result['Equity_Pledge']=jsonarray
#         json_guquanchuzhidengji=json.dumps(jsonarray,ensure_ascii=False)
#         print 'json_guquanchuzhidengji',json_guquanchuzhidengji
        
        
    def load_xingzhengchufa(self, table_element):
        tr_element_list = table_element.find_all(class_="page-item")
        th_element_list = table_element.find_all('th')[1:-1]
        jsonarray = []
        values = {}
        id=1
        for tr_element in tr_element_list:    
            td_element_list = tr_element.find_all('td')
            col_nums = len(th_element_list)
            for i in range(col_nums):
                col_dec = th_element_list[i].text.strip().replace('\n','')
                col=xingzhengchufa_column_dict[col_dec]
                td = td_element_list[i]
                val = td.get_text().strip()
                if val == u'详情':
                    link=td.a['href']
#                     print 'detail_link',self.detail_link
                    values[col] = link
                else:
                    values[col] = val
            values['Administrative_Penalty:registrationno']=self.cur_code
            values['Administrative_Penalty:enterprisename']=self.cur_mc
            values['Administrative_Penalty:id'] = str(id)
            values['rowkey']=self.cur_mc+'_13_'+self.cur_code+'_'+self.time+str(id)
            jsonarray.append(values)
            values = {}
            id+=1
        self.json_result['Administrative_Penalty']=jsonarray
#         json_xingzhengchufa=json.dumps(jsonarray,ensure_ascii=False)
#         print 'json_xingzhengchufa',json_xingzhengchufa
        
      
    def load_jingyingyichang(self, table_element):
        tr_element_list = table_element.find_all(class_="page-item")
        th_element_list = table_element.find_all('th')[1:-1]
        jsonarray = []
        values = {}
        id=1
        for tr_element in tr_element_list:                     
            td_element_list = tr_element.find_all('td')
            col_nums = len(th_element_list)
            for i in range(col_nums):
                col_dec = th_element_list[i].text.strip().replace('\n','')
                col=jingyingyichang_column_dict[col_dec]
                td = td_element_list[i]
                val = td.get_text().strip()
                values[col] = val
#                 print col,val
            values['Business_Abnormal:registrationno']=self.cur_code
            values['Business_Abnormal:enterprisename']=self.cur_mc
            values['Business_Abnormal:id'] = str(id)
            values['rowkey']=self.cur_mc+'_14_'+self.cur_code+'_'+self.time+str(id)
            jsonarray.append(values)
            values = {}
            id+=1
        self.json_result['Business_Abnormal']=jsonarray
#         json_jingyingyichang=json.dumps(jsonarray,ensure_ascii=False)
#         print 'json_jingyingyichang',json_jingyingyichang
        

    def load_yanzhongweifa(self, table_element):
        tr_element_list = table_element.find_all(class_="page-item")
        th_element_list = table_element.find_all('th')[1:-1]
        jsonarray = []
        values = {}
        id=1
        for tr_element in tr_element_list:                     
            td_element_list = tr_element.find_all('td')
            col_nums = len(th_element_list)
            for i in range(col_nums):
                col_dec = th_element_list[i].text.strip().replace('\n','')
                col=yanzhongweifa_column_dict[col_dec]
                td = td_element_list[i]
                val = td.get_text().strip()
                values[col] = val
#                 print col,val
            values['Serious_Violations:registrationno']=self.cur_code
            values['Serious_Violations:enterprisename']=self.cur_mc
            values['Serious_Violations:id'] = str(id)
            values['rowkey']=self.cur_mc+'_15_'+self.cur_code+'_'+self.time+str(id)
            jsonarray.append(values)
            values = {}
            id+=1
        self.json_result['Serious_Violations']=jsonarray
#         json_yanzhongweifa=json.dumps(jsonarray,ensure_ascii=False)
#         print 'json_yanzhongweifa',json_yanzhongweifa
            
 
    def load_chouchajiancha(self, table_element):
        tr_element_list = table_element.find_all(class_="page-item")
        th_element_list = table_element.find_all('th')[1:-1]
        jsonarray = []
        values = {}
        id=1
        for tr_element in tr_element_list:                     
            td_element_list = tr_element.find_all('td')
            col_nums = len(th_element_list)
            for i in range(col_nums):
                col_dec = th_element_list[i].text.strip().replace('\n','')
                col=chouchajiancha_column_dict[col_dec]
                td = td_element_list[i]
                val = td.get_text().strip()
                values[col] = val
#                 print col,val
            values['Spot_Check:registrationno']=self.cur_code
            values['Spot_Check:enterprisename']=self.cur_mc
            values['Spot_Check:id'] = str(id)
            values['rowkey']=self.cur_mc+'_16_'+self.cur_code+'_'+self.time+str(id)
            jsonarray.append(values)
            values = {}
            id+=1
        self.json_result['Spot_Check']=jsonarray
#         json_chouchajiancha=json.dumps(jsonarray,ensure_ascii=False)
#         print 'json_chouchajiancha',json_chouchajiancha

if __name__ == '__main__':
    args_dict = get_args()
    searcher = FuJianSearcher()
    # searcher.submit_search_request(u'宁化县旺鑫源园艺工程有限公司')
    searcher.submit_search_request(keyword=args_dict['companyName'], account_id=args_dict['accountId'], task_id=args_dict['taskId'])
