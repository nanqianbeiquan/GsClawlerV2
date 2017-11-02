# coding=gbk
import PackageTool
import requests
import os
from PIL import Image
from bs4 import BeautifulSoup
import json
import re
from HeBeiConfig import *
import datetime
from requests.exceptions import RequestException
import sys
import uuid
import time
from gs import MSSQL
import random
import subprocess
# from Tables_dict import *
from gs.Searcher import Searcher
from gs.Searcher import get_args
from gs.KafkaAPI import KafkaAPI
from gs.TimeUtils import *
import requests
requests.packages.urllib3.disable_warnings()


class HeBei(Searcher):
    search_result_json = None
    pattern = re.compile("\s")
    cur_mc = ''
    cur_code = ''
    json_result_data = []
    tagA = ''
    today = None
    # kafka = KafkaAPI("GSCrawlerTest")
    session_token = None
    cur_time = None
    verify_ip = None
    # save_tag_a = None
    load_func_dict = {}

    def __init__(self):
        super(HeBei, self).__init__(use_proxy=False)
        self.headers = {'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Encoding':'gzip, deflate',
                        'Accept-Language':'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
                        'Content-Type':'application/x-www-form-urlencoded',
                        'Connection':'keep-alive',
                        'Host':'www.hebscztxyxx.gov.cn',
                        'Referer':'http://www.hebscztxyxx.gov.cn/notice/home',
                        'User-Agent':'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0'
                        }
        # self.cur_time = '%d' % (time.time() * 1000)
        # self.get_session_token()
        # self.get_verify_ip()
        # self.json_result = {}
        self.set_config()
        self.log_name = self.topic + "_" + str(uuid.uuid1())
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
        self.plugin_path = os.path.join(sys.path[0], '../he_bei/ocr/type34.bat')
        self.group = 'Crawler'  # 正式
        self.kafka = KafkaAPI("GSCrawlerResult")  # 正式
        # self.group = 'CrawlerTest'  # 测试
        # self.kafka = KafkaAPI("GSCrawlerTest")  # 测试
        self.topic = 'GsSrc13'
        self.province = u'河北省'
        self.kafka.init_producer()

    def get_verify_ip(self):
        # url = 'http://www.hebscztxyxx.gov.cn/notice/security/verify_ip'
        # r = self.post_request(url,verify=False)
        # self.verify_ip = r.text
        pass

    def get_verify_keyword(self, keyword):
        # url = "http://www.hebscztxyxx.gov.cn/notice/security/verify_keyword"
        # params = {'keyword': keyword}
        # r = self.post_request(url, params,verify=False)
        # return r.text
        pass

    def get_validate_image_save_path(self):
        return os.path.join(sys.path[0], '../temp/' + str(random.random())[2:] + '.png')

    def get_validate_file_path(self):
        return os.path.join(sys.path[0], '../temp/' + str(random.random())[2:] + '.txt')
    
    def recognize_yzm(self,validate_path,validate_result_path):
        cmd = self.plugin_path + " " + validate_path+ " " + validate_result_path
        # print cmd
        os.path.join(cmd)
        p=subprocess.Popen(cmd.encode('gbk','ignore'), stdout=subprocess.PIPE)
        p.communicate()
        fo = open(validate_result_path,'r')
        answer=fo.readline().strip()
        fo.close()
        # print 'answer: '+answer.decode('gbk', 'ignore')
        os.remove(validate_path)
        os.remove(validate_result_path)
        return answer.decode('gbk', 'ignore')

    def get_yzm(self):
        image_url = 'http://www.hebscztxyxx.gov.cn/notice/captcha?preset=&ra='
        r = self.get_request(url=image_url)
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

    def get_session_token(self, t=0):
        url2 = 'http://www.hebscztxyxx.gov.cn/notice/search/popup_captcha'  # yzm_page
        # url2 = 'http://www.hebscztxyxx.gov.cn/notice/search/popup_captcha?adfwkey=plp16'
        r = self.get_request(url=url2)
        bs = BeautifulSoup(r.text,'html5lib')
        sp = bs.select('script')[0].text.strip()
        # print '*******************',sp
        try:
            self.session_token = re.search(u'(?<=code:).*(?=,)',sp).group().strip().replace(' ','').replace('"','')
            # print 'session)token',self.session_token
        except AttributeError as e:
            if t == 5:
                self.info(u'当前网站实在太累了了，休息'+time.ctime())
                raise e
            return self.get_session_token(t+1)


    def get_tag_a_from_page(self, keyword):
        tag_a = None
        self.get_session_token()
        for t in range(10):
            # self.get_verify_keyword(keyword)
            # print u'验证码识别中...第%s次' %(t+1)
            self.info(u'验证码识别中...第%s次' %(t+1))
            yzm = self.get_yzm()
            # print 'yzm',yzm
            url_2 = 'http://www.hebscztxyxx.gov.cn/notice/search/ent_info_list'
            params_2 = {'captcha': yzm, 'condition.keyword': keyword, 'searchType': 1, 'session.token': self.session_token}
            # print 'params: ', params_2
            # print 'gogogo'
            r_2 = self.post_request(url=url_2, data=params_2)
            # print 'gogofoo'
            r_2.encoding = 'utf-8'
            # print r_2.text
            soup = BeautifulSoup(r_2.text,'html5lib')
            # print 'soup', soup
            if u'您搜索的条件无查询结果'  in soup.text:
                # print u'您搜索的条件无查询结果'
                self.info(u'您搜索的条件无查询结果')
                break
            if soup.find(class_='list-item'):
                # print 'r.headers', r.headers
                # print u'**********验证码识别通过***he_bei*********'  #, soup.find(class_='list')
                self.info(u'**********验证码识别通过***he_bei*********')
                if soup.find(class_='list-item').text.strip() != '':
                    list_item = soup.find(class_='list-item')
                    list_stat = soup.find(class_='list-stat')
                    tagA = list_item.find('a').get('href')
                    # print 'tagA',tagA
                    self.cur_mc = list_item.find('a').text
                    self.cur_code = list_item.find('span').text
                    self.tagA = tagA
                    # print 'list_item:', list_item, 'list_stat', list_stat, 'tagA', tagA
                    if len(self.cur_code) == 18:
                        self.xydm = self.cur_code
                    else:
                        self.zch = self.cur_code
                    tag_a = tagA
                    return tag_a
                break
        return tag_a

    def get_search_args(self, tag_a, keyword):
        if tag_a:
            # print 'tag_a',tag_a,'self.mc:', self.cur_mc
            self.tagA = tag_a

        if self.cur_mc == keyword:
            return 1
        else:
            return 0

    def save_tag_a_to_db(self, tag_a):
        """
        将通过提交验证码获取到的tag_a存储到数据库中
        :param tag_a: 查询关键词
        :return:
        """
        # sql = "insert into GsSrc.dbo.tag_a values ('%s','%s',getdate())" % (self.cur_mc, tag_a)
        # MSSQL.execute_update(sql)
        pass

    def parse_detail(self):
        page = self.tagA
        # print 'parse_page:', page
        r2 = self.get_request(url=page)
        resdetail = BeautifulSoup(r2.text, 'lxml')
        # print 'self.save_tag_a', resdetail
        # print self.save_tag_a
        if not self.save_tag_a:
            li_list = resdetail.select('html body.layout div.main div.notice ul li')
            mc = li_list[0].text
            code = li_list[1].text
            title_bar = resdetail.find(class_='title-bar clearfix')
            # if not title_bar:
            #     print '************************************'
            #     print r2.text
            # mc=title_bar.find('li')
            # code=mc.find_next('li')
            self.cur_mc=mc.strip()
            self.cur_code=code.strip()[13:]
            # print '**', self.cur_mc,self.cur_code
        div_element_list = resdetail.find_all(class_='hide') #(style="display: none;")
        for div_element in div_element_list:
            table_element_list = div_element.find_all('table')
            for table_element in table_element_list:
                row_cnt=len(table_element.find_all("tr"))
#                 print 'row_cnt',row_cnt
                table_desc = div_element.find("th").get_text().strip().split('\n')[0]
                if table_desc == u'享受扶持信息':
                    continue
                elif table_desc in self.load_func_dict:
                    if row_cnt > 3:
                        self.load_func_dict[table_desc](table_element)
                else:
                    print table_desc
                    raise Exception("unknown table!")
        # self.load_nianbao()
        json_result = json.dumps(self.json_result,ensure_ascii=False)
        # print u'json_result结果', time.ctime(), json_result

    def load_jiben(self, table_element):
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
                    # print col,val
        values['Registered_Info:province']=self.province
        values['rowkey']=self.cur_mc+'_01_'+self.cur_code+'_'
        values['Registered_Info:lastupdatetime'] = get_cur_time()
        jsonarray.append(values)
        self.json_result['Registered_Info']=jsonarray
        # json_jiben=json.dumps(jsonarray,ensure_ascii=False)
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
                    htmldetail = BeautifulSoup(resdetail, 'html5lib')
                    jsbody = htmldetail.find(id='investor').find_next_sibling().text.strip().replace('\n', '').replace('	', '').replace(' ', '')
                    # print '****', htmldetail
                    # print 'jsbody', jsbody
                    detail_content = htmldetail.find(id='investor')
                    detail_tr_list = detail_content.find_all('tr')
                    a1 = re.search(r'(?<=invt.subConAm=).*?(?=;)', jsbody).group().strip().replace('"', '').replace("'", "")
                    a2 = re.search(r'(?<=invt.conDate=).*?(?=;)', jsbody).group().strip().replace('"', '').replace("'", "")
                    a3 = re.search(r'(?<=invt.conForm=).*?(?=;)', jsbody).group().strip().replace('"', '').replace("'", "")
                    # print 'aaaaaaaaaaaaaaaa11111', a1,'2', a2, '3', a3
                    b1 = re.search(r'(?<=invtActl.acConAm=).*?(?=;)', jsbody).group().strip().replace('"', '').replace("'", "")
                    b2 = re.search(r'(?<=invtActl.conDate=).*?(?=;)', jsbody).group().strip().replace('"', '').replace("'", "")
                    b3 = re.search(r'(?<=invtActl.conForm=).*?(?=;)', jsbody).group().strip().replace('"', '').replace("'", "")
                    # print 'bbbbbbbbbbbbbbbb11111', b1,'2', b2, '3', b3
                    values['Shareholder_Info:subscripted_capital'] = a1  # 认缴额
                    values['Shareholder_Info:subscripted_amount'] = a1
                    values['Shareholder_Info:subscripted_time'] = a2
                    values['Shareholder_Info:subscripted_method'] = a3

                    values['Shareholder_Info:actualpaid_capital'] = b1

                    values['Shareholder_Info:actualpaid_amount'] = b1
                    values['Shareholder_Info:actualpaid_time'] = b2
                    values['Shareholder_Info:actualpaid_method'] = b3
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
            id+=1
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
                values
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
            col = tr_element.find('th').get_text().strip()
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

    def load_nianbao(self):
        print 'nianbaotagA:', self.tagA
        tagB = self.tagA[:-1]+str(02)
        print 'nianbaotagB:', tagB
        r = self.get_request(url=tagB)
        soup = BeautifulSoup(r.text, 'html5lib')
        # print 'nianbaoyesoup:', soup
        tbody = soup.find_all('tbody')
        for tb in tbody:
            if u'报送年度' in tb.text and u'企业年报' in tb.text:
                soup = tb
        # print 'tbody:', soup
        self.get_nianbao(soup)
        # pass

    def get_nianbao(self, soup):
        family = 'annual_report'
        table_id = '39'

        nblist = soup.find_all('tr')
        json_list = []
        json_dict = {}
        link_list = []
        year_list = []
        cid_dict = {}
        if len(nblist) > 2:
            th_list = nblist[1].find_all('th')
            tr_list = nblist[2:]
            tr_recent = nblist[-1]

            for tr in tr_list:
                idn = 1
                if tr.text.strip():
                    td_list = tr.find_all('td')
                    for t in range(len(td_list)):
                        col_dec = th_list[t].text.strip()
                        col = qiyenianbao_column_dict[col_dec]
                        td = td_list[t].text.strip()
                        if col_dec == u'报送年度':
                            try:
                                href = td_list[t].a.get('href')
                            except AttributeError as e:
                                # print u'个体户年报不做处理', e
                                self.info(u'个体户年报不做处理')
                                return
                            # link = 'http://qyxy.baic.gov.cn' + href
                            link = href
                            print 'nianbao_link:', td, link
                            self.y = td[:4]
                            cid = re.search(r'(?<=uuid=).*', link).group()
                            # print '***cid***:', cid
                            cid_dict[td] = cid
                            year_list.append(td)
                            link_list.append(link)
                            json_dict[qiyenianbao_column_dict[u'详情']] = link
                        json_dict[col] = td
                    json_dict['rowkey'] = '%s_%s_%s_%d' %(self.cur_mc, self.y, table_id, idn)
                    json_dict[family + ':registrationno'] = self.cur_zch
                    json_dict[family + ':enterprisename'] = self.cur_mc
                    json_dict[family + ':id'] = str(idn)
                    json_list.append(json_dict)
                    json_dict = {}
                    idn += 1
            if json_list:
                print 'nianbaojson_list:', json_list
                # self.json_result[family] = json_list

            if link_list:
                print link_list
                for l in link_list:
                    r = self.get_request(url=l)
                    soup = BeautifulSoup(r.text, 'html5lib')
                    print '*'*50, soup
                    print '*'*100
                    table_list = soup.find_all(class_='detail-cont')[0].find_all('table')

                    for t in table_list:
                        te = t.find_all('tr')[0].text
                        print 'triger:', te

    # def get_request(self, url, params={}, data={}, verify=True, t=0, release_lock_id=False):
    #     """
    #     发送get请求,包含添加代理,锁定ip与重试机制
    #     :param url: 请求的url
    #     :param params: 请求参数
    #     :param data: 请求数据
    #     :param verify: 忽略ssl
    #     :param t: 重试次数
    #     :param release_lock_id: 是否需要释放锁定的ip资源
    #     """
    #     try:
    #         if self.use_proxy:
    #             if not release_lock_id:
    #                 self.headers['Proxy-Authorization'] = self.proxy_config.get_auth_header(lock_id=self.lock_id)
    #             else:
    #                 self.headers['Proxy-Authorization'] = self.proxy_config.get_auth_header(lock_id=self.lock_id, release_id=self.lock_id)
    #         r = self.session.get(url=url, headers=self.headers, params=params, data=data, verify=verify)
    #         if r.status_code != 200:
    #             print u'错误的响应代码 -> %d' % r.status_code , url
    #             raise RequestException()
    #         return r
    #     except RequestException, e:
    #         if t == 15:
    #             raise e
    #         else:
    #             return self.get_request(url, params, data, verify, t+1, release_lock_id)
    #
    # def post_request(self, url, params={}, data={}, verify=True, t=0, release_lock_id=False):
    #     """
    #     发送post请求,包含添加代理,锁定ip与重试机制
    #     :param url: 请求的url
    #     :param params: 请求参数
    #     :param data: 请求数据
    #     :param verify: 忽略ssl
    #     :param t: 重试次数
    #     :param release_lock_id: 是否需要释放锁定的ip资源
    #     :return:
    #     """
    #     try:
    #         if self.use_proxy:
    #             if not release_lock_id:
    #                 self.headers['Proxy-Authorization'] = self.proxy_config.get_auth_header(lock_id=self.lock_id)
    #             else:
    #                 self.headers['Proxy-Authorization'] = self.proxy_config.get_auth_header(lock_id=self.lock_id, release_id=self.lock_id)
    #         r = self.session.post(url=url, headers=self.headers, params=params, data=data, verify=verify)
    #         if r.status_code != 200:
    #             print u'错误的响应代码 -> %d' % r.status_code , url
    #             raise RequestException()
    #         return r
    #     except RequestException, e:
    #         if t == 15:
    #             raise e
    #         else:
    #             return self.post_request(url, params, data, verify, t+1, release_lock_id)

if __name__ == '__main__':
    args_dict = get_args()
    searcher = HeBei()
    searcher.submit_search_request(u'唐山港陆钢铁有限公司')#奇瑞')#清河县飘丝纺羊绒制品有限公司')
    # 上海益中亘泰物业管理有限公司廊坊分公司') #河北泰华实业集团有限公司')
    # searcher.submit_search_request(keyword=args_dict['companyName'], account_id=args_dict['accountId'], task_id=args_dict['taskId'])
