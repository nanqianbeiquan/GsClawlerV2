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
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
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
    flag = True
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
        super(HeBei, self).__init__(use_proxy=True)
        self.headers = {'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Encoding':'gzip, deflate',
                        'Accept-Language':'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
                        'Content-Type':'application/x-www-form-urlencoded',
                        'Connection':'keep-alive',
                        'Host':'www.hebscztxyxx.gov.cn',
                        'Referer':'http://www.hebscztxyxx.gov.cn/notice/',
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
        self.load_func_dict[u'������Ѻ�Ǽ���Ϣ'] = self.load_dongchandiyadengji
        self.load_func_dict[u'������Ѻ��Ϣ'] = self.load_dongchandiyadengji
        self.load_func_dict[u'��Ȩ���ʵǼ���Ϣ'] = self.load_guquanchuzhidengji
        self.load_func_dict[u'����������Ϣ'] = self.load_xingzhengchufa
        self.load_func_dict[u'��Ӫ�쳣��Ϣ'] = self.load_jingyingyichang
        self.load_func_dict[u'����Υ����Ϣ'] = self.load_yanzhongweifa
        self.load_func_dict[u'����Υ��ʧ����Ϣ'] = self.load_yanzhongweifa
        self.load_func_dict[u'�������Ϣ'] = self.load_chouchajiancha
        self.load_func_dict[u'������Ϣ'] = self.load_jiben
        self.load_func_dict[u'�ɶ���Ϣ'] = self.load_gudong
        self.load_func_dict[u'��������Ϣ'] = self.load_gudong
        self.load_func_dict[u'�����Ϣ'] = self.load_biangeng
        self.load_func_dict[u'��Ҫ��Ա��Ϣ'] = self.load_zhuyaorenyuan
        self.load_func_dict[u'��֧������Ϣ'] = self.load_fenzhijigou
        self.load_func_dict[u'������Ϣ'] = self.load_qingsuan
        self.load_func_dict[u'�μӾ�Ӫ�ļ�ͥ��Ա����'] = self.load_jiatingchengyuan     # Modified by Jing
        self.load_func_dict[u'Ͷ������Ϣ'] = self.load_touziren     #Modified by Jing
        self.load_func_dict[u'�ϻ�����Ϣ'] = self.load_hehuoren     #Modified by Jing    
        self.load_func_dict[u'��Ա����'] = self.load_chengyuanmingce     #Modified by Jing
        self.load_func_dict[u'������Ϣ'] = self.load_chexiao     #Modified by Jing
        self.load_func_dict[u'���ܲ��ţ������ˣ���Ϣ'] = self.load_DICInfo     #Modified by Jing

    def set_config(self):
        self.plugin_path = os.path.join(sys.path[0], '../he_bei/ocr/type34.bat')
        self.group = 'Crawler'  # ��ʽ
        self.kafka = KafkaAPI("GSCrawlerResult")  # ��ʽ
        # self.group = 'CrawlerTest'  # ����
        # self.kafka = KafkaAPI("GSCrawlerTest")  # ����
        self.topic = 'GsSrc13'
        self.province = u'�ӱ�ʡ'
        self.kafka.init_producer()

    def get_verify_ip(self):
        url = 'http://www.hebscztxyxx.gov.cn/notice/security/verify_ip'
        r = self.post_request(url,verify=False)
        self.verify_ip = r.text
        # pass

    def get_verify_keyword(self, keyword):
        url = "http://www.hebscztxyxx.gov.cn/notice/security/verify_keyword"
        params = {'keyword': keyword}
        r = self.post_request(url, params,verify=False)
        # print '***', r.text
        return r.text
        # pass

    def get_challenge_code(self):
        url = 'http://www.hebscztxyxx.gov.cn/notice/pc-geetest/register?t='+get_cur_ts_mil()
        r = self.get_request(url=url)
        # print r.content
        soup = BeautifulSoup(r.text, 'html5lib')
        # print soup.text
        d = eval(soup.text)
        gtCode = d['gt']
        challengeCode = d['challenge']
        self.gtCode = gtCode
        self.challengeCode = challengeCode
        print 'gtCode:', gtCode, 'challengeCode:', challengeCode

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
        url2 = 'http://www.hebscztxyxx.gov.cn/notice/'  # yzm_page
        # url2 = 'http://www.hebscztxyxx.gov.cn/notice/search/popup_captcha?adfwkey=plp16'
        r = self.get_request(url=url2)
        bs = BeautifulSoup(r.text,'html5lib')
        sp = bs.select('script')[0].text.strip()
        # print '*******************',sp
        try:
            self.session_token = re.search(u'(?<=code:).*(?=,)',sp).group().strip().replace(' ','').replace('"','')
            print 'session)token',self.session_token
        except AttributeError as e:
            if t == 5:
                self.info(u'��ǰ��վʵ��̫�����ˣ���Ϣ'+time.ctime())
                raise e
            return self.get_session_token(t+1)

    def get_the_mc_or_code(self, keyword):
        if keyword:
            if len(keyword) == 15 or len(keyword) == 18:
                cnt = 0
                for i in keyword:
                    if i in 'abcdefghijklmnopqrstuvwxyz1234567890':
                        cnt += 1
                if cnt > 10:
                    return False
            else:
                return True
        else:
            self.info(u'����keyword����')
            return True

    def get_tag_a_from_page(self, keyword, flags=0):
        return self.get_tag_a_from_page0(keyword)

    def get_tag_a_from_page0(self, keyword):
        self.flag=self.get_the_mc_or_code(keyword)
        print self.flag
        url = 'http://www.hebscztxyxx.gov.cn/notice/home'
        driver = webdriver.Firefox()
        # driver = webdriver.Chrome()
        driver.set_window_size(1920,1080)
        driver.get(url)

        # keyword = u'��ɽ��½�������޹�˾'
        input_path = r".//*[@id='keyword']"
        submit_path = r".//*[@id='buttonSearch']"
        driver.find_element_by_xpath(input_path).clear()
        driver.find_element_by_xpath(input_path).send_keys(keyword)
        driver.find_element_by_xpath(submit_path).click()

        WebDriverWait(driver,30).until(lambda the_driver: the_driver.find_element_by_xpath(".//*[@class='gt_holder popup']"))

        time.sleep(2)

        print 'before:', time.ctime()
        fa = 0
        element=driver.find_element_by_xpath(".//*[@class='gt_slider_knob gt_show']")
        try:
            for i in range(10, 12):
                print '%d step1--click' % i
                ActionChains(driver).click_and_hold(on_element=element).perform()
                time.sleep(1)
                driver.get_screenshot_as_file('E:\\losg.jpg')
                time.sleep(1)
                img = Image.open('E:\\losg.jpg')
                # img.show()
                img_crop = img.crop((818, 419, 1078, 535))
                # img_crop.show()
                # img_path = os.path.join(sys.path[0], '../temp/' + str(random.random())[2:] + '.png')
                img_path = 'E:\\hebeijpg\\' + str(random.random())[2:] + '.png'
                # img_path = 'E:\\losk.jpg'
                ocr_path = os.path.join(sys.path[0], '../he_bei/slideocr/' + 'huadongjuli.exe')
                img_path1 = 'E:\\zfjpg300\\' + str(random.random())[2:] + '.png'
                # img_crop.save('E:\\losk.jpg')
                img_crop.save(img_path)
                if i == 11:
                    img_crop.save(img_path1)
                cmd = ocr_path + '  ' + img_path
                print 'cmd', cmd
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
                print 'alive'
                results = p.stdout.readlines()
                # print results[0].strip()
                offset = int(results[0].strip())
                print 'offset', offset
                print '%d step2--move' % i
                # ActionChains(driver).move_to_element_with_offset(to_element=element, xoffset=i*3, yoffset=10).perform()
                ActionChains(driver).move_to_element_with_offset(to_element=element, xoffset=offset+i*2, yoffset=10).perform()

                time.sleep(1)
                print '%d step3--release' % i
                ActionChains(driver).release(on_element=element).perform()
                time.sleep(2)
                try:
                    WebDriverWait(driver, 20).until(lambda the_driver: the_driver.find_element_by_xpath(".//*[@class='contentA']"))
                    # WebDriverWait(driver, 20).until(EC.presence_of_element_located(By.Class('contentA')))
                    print 'element_found'
                    break
                except Exception as e:
                    print 'yzm_exception', e
                    # continue
                fa += 1
            print '**m**', fa

        except:
            print 'geetest--pass--success!'
            driver.get_screenshot_as_file(r'E:\\hbgee.jpg')
        # if fa == 5:
        #     print 'zf'*500
        #     driver.quit()
        #     print 'once more'
        #     return self.get_tag_a_from_page0(self, keyword)

        print 'after:', time.ctime()

        # ���ҳ��
        try:
            # source = driver.find_element_by_xpath(".//*[@id='wrap1366']/div[3]/div")
            source = driver.find_element_by_xpath(".//*[@class='contentA']")
            html = source.get_attribute("innerHTML")
            driver.quit()
        except:
            driver.quit()
            return None

        soup = BeautifulSoup(html, 'html5lib')
        print 'soup:', soup

        results = soup.find_all(class_='tableContent')
        print 'results_lens', len(results)

        self.xydm_if = ''
        self.zch_if = ''

        cnt = 0
        company_list = []
        company_code = []
        company_tags = []

        if len(results) > 0:
            nn = ''
            for r in results:
                cnt += 1
                name_parts = r.find_all('span')
                # for p in name_parts:
                # 	print '**',p.text

                name = r.find('thead').text.strip()
                # print '--',name.split('\n')[0]
                name = name.split('\n')[0]
                code = r.find('tbody').find('th').find('em').text.strip()

                tagAs = r.get('onclick')
                # print tagAs
                tagA = re.search(u"(?<=[(']).*(?=[)'])",tagAs).group().replace(u"'","")
                print cnt, name, code, tagA
                company_list.append(name)
                company_code.append(code)
                company_tags.append(tagA)
        else:
            print '**'*100, u'��ѯ�޽��'
            self.info(u'��ѯ�޽��')
            driver.quit()
            return None
        if len(company_list) > 1:
            for name in company_list[1:]:
                self.save_company_name_to_db(name)
        self.cur_mc = company_list[0]
        self.cur_code = company_code[0]
        self.cur_zch = company_code[0]
        self.tagA = company_tags[0]
        if len(self.cur_code) == 18:
            self.xydm_if = self.cur_code
        else:
            self.zch_if = self.cur_code
        print 'name:', company_list[0], 'code:', company_code[0], 'tagA:', company_tags[0]
        # r = requests.get(company_tags[0])
        # print r.text,r.headers

        return company_tags[0]

    def get_search_args(self, tag_a, keyword):
        if tag_a:
            print 'tag_a', tag_a, 'self.mc:', self.cur_mc
            self.tagA = tag_a
            if self.flag:
                if self.cur_mc == keyword:
                    return 1
                else:
                    return 0
            else:
                self.info(self.cur_mc)
                return 1
        else:
            return 0

    def save_tag_a_to_db(self, tag_a):
        """
        ��ͨ���ύ��֤���ȡ����tag_a�洢�����ݿ���
        :param tag_a: ��ѯ�ؼ���
        :return:
        """
        # sql = "insert into GsSrc.dbo.tag_a values ('%s','%s',getdate(), '%s')" % (self.cur_mc, tag_a, self.province)
        # MSSQL.execute_update(sql)
        pass

    def parse_detail(self):
        page = self.tagA
        print 'parse_page:', page
        r2 = self.get_request(url=page)
        resdetail = BeautifulSoup(r2.text, 'html5lib')
        lensoup = len(resdetail.find_all(class_='contentB'))
        # print 'self.save_tag_a', lensoup, resdetail.find(class_='contentB')
        print '*'*1000
        resdetail = resdetail.find(class_='contentB')
        div_element_list = resdetail.find_all(class_='content1') #(style="display: none;")
        print 'dvns', len(div_element_list)
        for div_element in div_element_list:
            print 'ff'*100
            table_title = div_element.find(class_='titleTop').text.strip()
            table_body = div_element.find_next('table')
            # print '*pip*', table_title#, table_body
            if table_title == u'Ӫҵִ����Ϣ':
                self.load_jiben(table_body)
            elif u'�ɶ���������Ϣ' in table_title:
                self.load_gudong(table_body)
            elif table_title == u'��Ҫ��Ա��Ϣ':
                self.load_zhuyaorenyuan(table_body)
            elif table_title == u'��֧������Ϣ':
                self.load_fenzhijigou(table_body)
            elif table_title == u'������Ϣ':
                self.load_qingsuan(table_body)
            elif table_title == u'��Ȩ���ʵǼ���Ϣ':
                self.load_guquanchuzhidengji(table_body)
            elif table_title == u'������Ѻ�Ǽ���Ϣ':
                self.load_dongchandiyadengji(table_body)
            elif table_title == u'����������Ϣ':
                self.load_xingzhengchufa(table_body)
            elif table_title == u'���뾭Ӫ�쳣��¼��Ϣ':
                self.load_jingyingyichang(table_body)
            elif table_title == u'����Υ��ʧ����ҵ����������������Ϣ':
                self.load_yanzhongweifa(table_body)
            elif table_title == u'���������Ϣ':
                self.load_chouchajiancha(table_body)
#             for table_element in table_element_list:
#                 row_cnt=len(table_element.find_all("tr"))
# #                 print 'row_cnt',row_cnt
#                 table_desc = div_element.find("th").get_text().strip().split('\n')[0]
#                 if table_desc == u'���ܷ�����Ϣ':
#                     continue
#                 elif table_desc in self.load_func_dict:
#                     if row_cnt > 3:
#                         self.load_func_dict[table_desc](table_element)
#                 else:
#                     print table_desc
#                     raise Exception("unknown table!")
#         self.load_nianbao()
        print '*_*'*100
        page2 = self.tagA.replace('=01', '=02')
        print 'parse_page:', page2
        r2 = self.get_request(url=page2)
        resdetail = BeautifulSoup(r2.text, 'html5lib')
        # print 'self.save_tag_a', resdetail
        # print self.save_tag_a
        # if not self.save_tag_a:
        #     li_list = resdetail.select('html body.layout div.main div.notice ul li')
        #     mc = li_list[0].text
        #     code = li_list[1].text
        #     title_bar = resdetail.find(class_='title-bar clearfix')
        #     # if not title_bar:
        #     #     print '************************************'
        #     #     print r2.text
        #     # mc=title_bar.find('li')
        #     # code=mc.find_next('li')
        #     self.cur_mc=mc.strip()
        #     self.cur_code=code.strip()[13:]
            # print '**', self.cur_mc,self.cur_code
        div_element_list = resdetail.find_all(class_='content1') #(style="display: none;")
        for div_element in div_element_list:
            table_title = div_element.find(class_='titleTop').text.strip()
            table_body = div_element.find('table')
            # print 'pip2', table_title#, table_body.text
            if table_title == u'��ҵ�걨��Ϣ':
                self.load_nianbao(table_body)

        json_result = json.dumps(self.json_result,ensure_ascii=False)
        print u'json_result���', time.ctime(), json_result

    def load_jiben(self, table_element):
        family = 'Registered_Info'
        table_id = '01'
        json_list = []
        values = {}

        tr_element_list = table_element.find_all("tr")
        for tr_element in tr_element_list:
            # th_element_list = tr_element.find_all('th')
            td_element_list = tr_element.find_all('td')
            for td in td_element_list:
                if td.text.strip():
                    td_list = td.text.replace(u'��', '').replace(u'?', '').strip().replace(u' ', '').split(u'��',1)
                    col = td_list[0].strip()
                    val = td_list[1].strip()
                    # print col, val
                    col = jiben_column_dict[col]
                    values[col] = val

        values['rowkey'] = '%s_%s_%s_' % (self.cur_mc, table_id, self.cur_zch)
        values[family + ':registrationno'] = self.cur_zch
        values[family + ':enterprisename'] = self.cur_mc
        values[family + ':tyshxy_code'] = self.xydm_if
        values[family + ':zch'] = self.zch_if
        values[family + ':lastupdatetime'] = get_cur_time()
        values[family + ':province'] = u'�ӱ�ʡ'
        json_list.append(values)
        self.json_result['Registered_Info'] = json_list
        json_jiben = json.dumps(json_list, ensure_ascii=False)
        print 'json_jiben', json_jiben
        
        
    def load_gudong(self, table_element):
        family = 'Shareholder_Info'
        table_id = '04'

        tr_element_list = table_element.find_all(class_="page-item")
        th_element_list = table_element.find_all('th')
        jsonarray = []
        values = {}
        id=1
        for tr_element in tr_element_list:    
            td_element_list = tr_element.find_all('td')
            col_nums = len(th_element_list)
            for i in range(col_nums):
                col_dec = th_element_list[i].get_text().strip().replace('\n','')
                col = gudong_column_dict[col_dec]
                td = td_element_list[i]
                val = td.get_text().strip()
                # print '--gdval--', val
                if val == u'�鿴':
                    # print 'Q'*20
                    link = td.a.get('onclick')
                    tid = re.search(u"(?<=[(']).*(?=[)'])", link).group().replace(u"'", "")
                    # print 'tid', tid
                    link = 'http://www.hebscztxyxx.gov.cn/notice/notice/view_investor?uuid=' + tid
                    values[col] = link
                    self.get_gu_dong_detail(link,values)
                else:
                    values[col] = val
            values['Shareholder_Info:registrationno']=self.cur_code
            values['Shareholder_Info:enterprisename']=self.cur_mc
            values['Shareholder_Info:id']=str(id)
            values['rowkey']=self.cur_mc+'_04_'+self.cur_code+'_'+self.time+str(id)
            jsonarray.append(values)
            values = {}
            id += 1
        if jsonarray:
            self.json_result['Shareholder_Info']=jsonarray
            json_gudong=json.dumps(jsonarray,ensure_ascii=False)
            print 'json_gudong',json_gudong
                                                                   
    def get_gu_dong_detail(self, url, values):
        """
        ��ѯ�ɶ�����
        """

        # print 'gudong_detail_url',url
        r = self.get_request(url=url, params={})
        # r.encoding = 'gbk'

        resdetail = r.text
        htmldetail = BeautifulSoup(resdetail, 'html5lib')
        # jsbody = htmldetail.find(class_='detail_content')
        # print '***a*', htmldetail
        # print 'jsbody', jsbody
        detail_content = htmldetail.find(class_='detail_content')
        detail_div_list = detail_content.find_all(class_='content2')        # �ɶ����Ͻɣ�ʵ�ɷ�Ϊ3��div

        n = 0
        for div_ele in detail_div_list:
            div_title = div_ele.find('div').text.strip()
            div_table = div_ele.find('table')
            # print u'��ʼ����%s��' % div_title
            tr_ele_list = div_table.find_all('tr')
            if n == 0:
                for tr in tr_ele_list[1:]:
                    col = tr.th.text.strip()
                    val = tr.td.text.strip()
                    # print 'gddetails', col, val
                    values[gudong_column_dict[col]] = val
            else:
                th_list = tr_ele_list[0].find_all('th')
                if len(tr_ele_list) == 1:
                    for c in range(len(th_list)):
                        col = th_list[c].text.strip()
                        val = u''
                        values[gudong_column_dict[col]] = val
                elif len(tr_ele_list) == 2:
                    for tr in tr_ele_list[1:]:
                        td_list = tr.find_all('td')
                        if len(td_list) == 3:
                            for c in range(len(th_list)):
                                col = th_list[c].text.strip()
                                val = td_list[c].text.strip()
                                # print col,val
                                values[gudong_column_dict[col]] = val
                        else:
                            for c in range(len(th_list)):
                                col = th_list[c].text.strip()
                                val = ''
                                # print col,val
                                values[gudong_column_dict[col]] = val

                elif len(tr_ele_list) > 2:
                    self.info(u'�ɶ������Ͻ�ʵ�ɳ��ֶ�����')
                    for tr in tr_ele_list[1:]:
                        td_list = tr.find_all('td')
                        if len(td_list) == 3:
                            for c in range(len(th_list)):
                                col = th_list[c].text.strip()
                                val = td_list[c].text.strip()
                                # print col,val
                                values[gudong_column_dict[col]] = val
                        else:
                            for c in range(len(th_list)):
                                col = th_list[c].text.strip()
                                val = ''
                                # print col,val
                                values[gudong_column_dict[col]] = val
            n += 1

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
                if val.endswith(u'�������'):
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
        if jsonarray:
            self.json_result['Changed_Announcement']=jsonarray
#         json_biangeng=json.dumps(jsonarray,ensure_ascii=False)
#         print 'json_biangeng',json_biangeng
        
                    
    def load_chexiao(self, table_element):
        pass


    def load_zhuyaorenyuan(self, table_element):
        # print 'zhuyaorenyuan', table_element

        family = 'KeyPerson_Info'
        table_id = '06'
        json_list = []
        values = {}

        try:
            tr_num = len(table_element.find_all('ul'))
        except:
            tr_num = 0

        ul_list = table_element.find_all('ul')

        if tr_num > 0:
            cnt = 1
            for t in range(tr_num):
                pson = ul_list[t].find_all('li')
                if len(pson):
                    name = pson[0].text.strip()
                    posn = pson[1].text.strip()
                    # print '******', t, 'name:', name, 'position:', posn
                    values[zhuyaorenyuan_column_dict[u'����']] = name
                    values[zhuyaorenyuan_column_dict[u'ְ��']] = posn
                    values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, cnt)
                    values[family + ':registrationno'] = self.cur_zch
                    values[family + ':enterprisename'] = self.cur_mc
                    values[family + ':id'] = str(cnt)
                    json_list.append(values)
                    values = {}
                    cnt += 1
            if json_list:
                print 'zhuyaorenyuan_jsonlist:', json_list
                self.json_result[family] = json_list
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
                if len(values) == 2:
                    values['Members_Info:registrationno']=self.cur_code
                    values['Members_Info:enterprisename']=self.cur_mc
                    values['Members_Info:id'] = str(id)
                    jsonarray.append(values)
                    values = {}
        # self.json_result['Members_Info']=jsonarray
#         json_jiatingchengyuan=json.dumps(jsonarray,ensure_ascii=False)
#         print 'json_jiatingchengyuan',json_jiatingchengyuan
        
    def load_fenzhijigou(self, table_element):
        print 'fenzhijigou', table_element
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
        if jsonarray:
            self.json_result['Branches']=jsonarray
#         json_fenzhijigou=json.dumps(jsonarray,ensure_ascii=False)
#         print 'json_fenzhijigou',json_fenzhijigou

    # ����������Ϣ
    def load_qingsuan(self, table_element):
        family = 'liquidation_Information'
        table_id = '09'

        # print 'qingsuan', table_element
        tr_element_list = table_element.find_all('tr')[1:]
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
            values[qingsuan_column_dict[col]] = val
        if values.values()[0] or values.values()[1]:        # ����������ʱ����
            values['liquidation_Information:registrationno']=self.cur_code
            values['liquidation_Information:enterprisename']=self.cur_mc
            values['rowkey']=self.cur_mc+'_09_'+self.cur_code+'_'
            jsonarray.append(values)
            values = {}
            # print jsonarray
            self.json_result['liquidation_Information'] = jsonarray


    def load_dongchandiyadengji(self, table_element):
        # print 'dongchandiya', table_element
        tr_element_list = table_element.find_all(class_="page-item")
        th_element_list = table_element.find_all('th')
        jsonarray = []
        values = {}
        id=1
        for tr_element in tr_element_list:    
            td_element_list = tr_element.find_all('td')
            col_nums = len(th_element_list)
            for i in range(col_nums):
                col_dec = th_element_list[i].text.strip().replace('\n','')
                col = dongchandiyadengji_column_dict[col_dec]
                td = td_element_list[i]
                val = td.get_text().strip()
                if val == u'�鿴':
                    link = td.a.get('onclick')
                    tid = re.search(u"(?<=[(']).*(?=[)'])", link).group().replace(u"'", "")
                    # print 'tid', tid
                    link = 'http://www.hebscztxyxx.gov.cn/notice/notice/view_mortage?uuid=' + tid
                    # print 'dcdy', link
                    values[col] = link
                else:
                    values[col] = val
            values['Chattel_Mortgage:registrationno']=self.cur_code
            values['Chattel_Mortgage:enterprisename']=self.cur_mc
            values['Chattel_Mortgage:id'] = str(id)
            values['rowkey'] = self.cur_mc+'_11_'+self.cur_code+'_'+self.time+str(id)
            jsonarray.append(values)
            values = {}
            id += 1
        if jsonarray:
            self.json_result['Chattel_Mortgage']=jsonarray
            json_dongchandiyadengji = json.dumps(jsonarray,ensure_ascii=False)
            print 'json_dongchandiyadengji',json_dongchandiyadengji
        
    def load_guquanchuzhidengji(self, table_element):
        # print 'guquanchuzhi', table_element
        tr_element_list = table_element.find_all(class_="page-item")
        th_element_list = table_element.find_all('th')
        jsonarray = []
        values = {}
        id=1
        for tr_element in tr_element_list:    
            td_element_list = tr_element.find_all('td')
            col_nums = len(th_element_list)
            for i in range(col_nums):
                col_dec = th_element_list[i].text.strip().replace('\n','')
                previous = th_element_list[(i-1)].text.strip().replace('\n','')
                if col_dec == u'֤��/֤������' and previous == u'������':
                    col = 'Equity_Pledge:equitypledge_pledgorid'
                elif col_dec == u'֤��/֤������' and previous == u'��Ȩ��':
                    col = 'Equity_Pledge:equitypledge_pawneeid'
                else:
                    col = guquanchuzhidengji_column_dict[col_dec]
                td = td_element_list[i]
                val = td.get_text().strip()
                if val == u'�鿴':
                    link = td.a.get('onclick')
                    tid = re.search(u"(?<=[(']).*(?=[)'])", link).group().replace(u"'", "")
                    # print 'tid', tid
                    link = 'http://www.hebscztxyxx.gov.cn/notice/notice/view_pledge?uuid=' + tid
                    # print 'gqcz', link
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
        if jsonarray:
            self.json_result['Equity_Pledge']=jsonarray
            json_guquanchuzhidengji=json.dumps(jsonarray,ensure_ascii=False)
            print 'json_guquanchuzhidengji',json_guquanchuzhidengji
        
    def load_xingzhengchufa(self, table_element):
        # print 'xingzhengchufa', table_element
        tr_element_list = table_element.find_all(class_="page-item")
        th_element_list = table_element.find_all('th')
        jsonarray = []
        values = {}
        id=1
        switchs = len(th_element_list)
        # print 'xzcf_switchs', switchs
        for tr_element in tr_element_list:    
            td_element_list = tr_element.find_all('td')
            col_nums = len(th_element_list)
            for i in range(col_nums):
                col_dec = th_element_list[i].text.strip().replace('\n','')
                col = xingzhengchufa_column_dict[col_dec]
                td = td_element_list[i]
                val = td.get_text().strip()
                if val == u'�鿴':
                    link = td.a.get('onclick')
                    tid = re.search(u"(?<=[(']).*(?=[)'])", link).group().replace(u"'", "")
                    # print 'tid', tid
                    link = 'http://www.hebscztxyxx.gov.cn/notice/notice/view_punish?uuid=' + tid
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
        if jsonarray:
            self.json_result['Administrative_Penalty']=jsonarray
#         json_xingzhengchufa=json.dumps(jsonarray,ensure_ascii=False)
#         print 'json_xingzhengchufa',json_xingzhengchufa

    def load_jingyingyichang(self, table_element):
        # print 'jingyingyichang', table_element
        tr_element_list = table_element.find_all(class_="page-item")
        th_element_list = table_element.find_all('th')
        jsonarray = []
        values = {}
        id=1
        for tr_element in tr_element_list:                     
            td_element_list = tr_element.find_all('td')
            col_nums = len(th_element_list)
            for i in range(col_nums):
                col_dec = th_element_list[i].text.strip().replace('\n','')
                col = jingyingyichang_column_dict[col_dec]
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
            id += 1
        if jsonarray:
            self.json_result['Business_Abnormal']=jsonarray
#         json_jingyingyichang=json.dumps(jsonarray,ensure_ascii=False)
#         print 'json_jingyingyichang',json_jingyingyichang
        
    def load_yanzhongweifa(self, table_element):
        # print 'yanzhongweifa', table_element
        tr_element_list = table_element.find_all(class_="page-item")
        th_element_list = table_element.find_all('th')
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
            id += 1
        if jsonarray:
            self.json_result['Serious_Violations']=jsonarray
#         json_yanzhongweifa=json.dumps(jsonarray,ensure_ascii=False)
#         print 'json_yanzhongweifa',json_yanzhongweifa
            
    def load_chouchajiancha(self, table_element):
        # print 'chouchajiancha',table_element
        tr_element_list = table_element.find_all(class_="page-item")
        th_element_list = table_element.find_all('th')
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
        if jsonarray:
            self.json_result['Spot_Check'] = jsonarray
#         json_chouchajiancha=json.dumps(jsonarray,ensure_ascii=False)
#         print 'json_chouchajiancha',json_chouchajiancha

    def load_nianbao(self, table_body):
        # print 'nianbao:', table_body
        family = 'annual_report'
        table_id = '39'

        json_list = []
        values = {}
        tr_ele_list = table_body.find_all('tr')
        th_ele_list = table_body.find_all('th')

        idn = 1
        year_list = []        # �����
        year_link = []        # ���������
        for tr_ele in tr_ele_list[1:-1]:                # ȥ����һ��th�������У���ȥ�����һ�У�ҳ���У�
            td_list = tr_ele.find_all('td')
            for i in range(len(th_ele_list)):
                col = th_ele_list[i].text.strip()
                val = td_list[i].text.strip()
                if col == u'�������':
                    y = val[:4]
                    year_list.append(y)
                if val == u'�鿴':
                    link = td_list[i].a.get('href')
                    values[qiyenianbao_column_dict[col]] = link
                    year_link.append(link)
                else:
                    values[qiyenianbao_column_dict[col]] = val
            values['rowkey'] = '%s_%s_%s_%d' %(self.cur_mc, y, table_id, idn)
            values[family + ':registrationno'] = self.cur_zch
            values[family + ':enterprisename'] = self.cur_mc
            values[family + ':id'] = str(idn)
            json_list.append(values)
            values = {}
            idn += 1
        if json_list:
            print 'nb', json_list
            self.json_result[family] = json_list

        #  ��ȡ�걨����ҳ��
        self.nbjb_list = []  # �걨������Ϣ
        self.nbzczk_list = []  # �걨�ʲ�״��

        self.nbdwdb_list = []
        self.nbgdcz_list = []
        self.nbgqbg_list = []
        self.nbwz_list = []
        self.nbxg_list = []
        self.nbdwtz_list = []

        if year_link:
            for i in range(len(year_link)):
                year = year_list[i]
                link = year_link[i]
                # print 'uiu', i, year, link
                self.y = year

                r = self.get_request(url=link)
                soup = BeautifulSoup(r.text, 'html5lib')
                # print 'Q'*1000
                # print 'nianbaoyesoup:', soup
                # print 'q'*1000
                soup = soup.find(class_='content3')
                div_element_list = soup.find_all(class_='content1')
                for div_element in div_element_list:
                    table_title = div_element.find(class_='titleTop').find('h1').text.strip()
                    table_body = div_element.find('table')
                    # print 'rqs', table_title#, table_body.text
                    # continue
                    if table_title == u'������Ϣ':
                        self.get_nianbaojiben(table_body)
                    elif table_title == u'��վ��������Ϣ':
                        self.get_nianbaowangzhan(table_body)
                    elif table_title == u'�ɶ���������Ϣ':
                        self.get_nianbaogudongchuzi(table_body)
                    elif table_title == u'����Ͷ����Ϣ':
                        self.get_nianbaoduiwaitouzi(table_body)
                    elif table_title == u'��ҵ�ʲ�״����Ϣ':
                        self.get_nianbaozichanzhuangkuang(table_body)
                    elif table_title == u'��Ȩ�����Ϣ':
                        self.get_nianbaoguquanbiangeng(table_body)
                    elif table_title == u'�����ṩ��֤������Ϣ':
                        self.get_nianbaoduiwaidanbao(table_body)
                    elif table_title == u'�޸���Ϣ':
                        self.get_nianbaoxiugai(table_body)
                    else:
                        self.info(u'������ʲô��'+table_title)

        if self.nbjb_list:
            self.json_result['report_base'] = self.nbjb_list  # �걨������Ϣ
        if self.nbzczk_list:
            self.json_result['industry_status'] = self.nbzczk_list  # �걨�ʲ�״��

        if self.nbdwdb_list:
            self.json_result['guarantee'] = self.nbdwdb_list
        if self.nbgdcz_list:
            self.json_result['enterprise_shareholder'] = self.nbgdcz_list
        if self.nbgqbg_list:
            self.json_result['equity_transfer'] = self.nbgqbg_list
        if self.nbwz_list:
            self.json_result['web_site'] = self.nbwz_list
        if self.nbxg_list:
            self.json_result['modify'] = self.nbxg_list
        if self.nbdwtz_list:
            self.json_result['investment'] = self.nbdwtz_list

    def get_nianbaojiben(self, soup):
        # print 'nbjb', soup
        family = 'report_base'
        table_id = '40'
        tr_element_list = soup.find_all('tr')#(".//*[@id='jbxx']/table/tbody/tr")
        values = {}
        json_list = []
        for tr_element in tr_element_list[1:]:
            # th_element_list = tr_element.find_all('th')
            td_element_list = tr_element.find_all('td')
            for td in td_element_list:
                if td.text.strip():
                    td_list = td.text.replace(u'��', '').replace(u'?', '').strip().replace(u' ', '').split(u'��',1)
                    col = td_list[0].strip()
                    val = td_list[1].strip()
                    # print col, val
                    col = qiyenianbaojiben_column_dict[col]
                    values[col] = val
        values['rowkey'] = '%s_%s_%s_' %(self.cur_mc, self.y, table_id)
        values[family + ':registrationno'] = self.cur_zch
        values[family + ':enterprisename'] = self.cur_mc
        json_list.append(values)
        # print 'jb', values
        self.nbjb_list.append(values)

    def get_nianbaowangzhan(self, soup):
        # print 'nbwz', soup
        family = 'web_site'
        table_id = '41'
        values = {}
        json_list = []
        tr_element_list = soup.find_all('tr')
        cnt = 1

        if len(tr_element_list):
            for tr_ele in tr_element_list:
                if tr_ele.text.strip():
                    li_lists = tr_ele.find_all('li')[1:]
                    for li in li_lists:
                        li_list = li.text.replace(u'��', '').replace(u'?', '').strip().replace(u' ', '').split(u'��',1)
                        col = li_list[0].strip()
                        val = li_list[1].strip()
                        values[qiyenianbaowangzhan_column_dict[col]] = val
                    values['rowkey'] = '%s_%s_%s_%d' %(self.cur_mc, self.y, table_id, cnt)
                    values[family + ':registrationno'] = self.cur_zch
                    values[family + ':enterprisename'] = self.cur_mc
                    values[family + ':id'] = str(cnt)
                    json_list.append(values)
                    self.nbwz_list.append(values)
                    values = {}
                    cnt += 1
            # if json_list:
            #     print 'wz',json_list

    def get_nianbaogudongchuzi(self, soup):
        # print 'nbgd', soup
        family = 'enterprise_shareholder'
        table_id = '42'
        values = {}
        json_list = []

        gd_th = soup.find_all('th')
        tr_element_list = soup.find_all('tr')[1:-1]
        iftr = tr_element_list

        cnt = 1
        for i in range(len(iftr)):
            if iftr[i].text.strip():
                gd_td = iftr[i].find_all('td')
                for j in range(len(gd_th)):
                    th = gd_th[j].text.strip()
                    td = gd_td[j].text.strip()
                    # print i,j,th,td
                    values[qiyenianbaogudong_column_dict[th]] = td
                values['rowkey'] = '%s_%s_%s_%d' %(self.cur_mc, self.y, table_id, cnt)
                values[family + ':registrationno'] = self.cur_zch
                values[family + ':enterprisename'] = self.cur_mc
                values[family + ':id'] = str(cnt)
                json_list.append(values)

                self.nbgdcz_list.append(values)
                values = {}
                cnt += 1
        # if json_list:
        #     print 'nbgdcz', json_list

    def get_nianbaoduiwaitouzi(self, soup):
        # print 'dwtz', soup
        family = 'investment'
        table_id = '47'
        values = {}
        json_list = []

        tr_element_list = soup.find_all('tr')
        cnt = 1
        if len(tr_element_list):
            for tr_ele in tr_element_list:
                if tr_ele.text.strip():
                    li_lists = tr_ele.find_all('li')

                    col = u'��˾����'
                    name = li_lists[0].text.strip()    # ��˾����
                    values[qiyenianbaoduiwaitouzi_column_dict[col]] = name

                    li_list = li_lists[1].text.replace(u'��', '').replace(u'?', '').strip().replace(u' ', '').split(u'��',1)
                    col = li_list[0].strip()
                    val = li_list[1].strip()
                    values[qiyenianbaoduiwaitouzi_column_dict[col]] = val
                    values['rowkey'] = '%s_%s_%s_%d' %(self.cur_mc, self.y, table_id, cnt)
                    values[family + ':id'] = str(cnt)
                    json_list.append(values)
                    self.nbdwtz_list.append(values)
                    values = {}
                    cnt += 1
            # if json_list:
            #     print 'nbdwtz', json_list

    def get_nianbaozichanzhuangkuang(self, soup):
        # print 'nbzczt', soup
        family = 'industry_status'
        table_id = '43'

        tr_element_list = soup.find_all("tr")
        values = {}
        json_list = []
        for tr_element in tr_element_list:
            th_element_list = tr_element.find_all('th')
            td_element_list = tr_element.find_all('td')
            if len(td_element_list) > 0:
                col_nums = len(td_element_list)
                for i in range(col_nums):
                    col = th_element_list[i].get_text().strip().replace('\n','')
                    val = td_element_list[i].get_text().strip().replace('\n','')
                    if col != u'':
                        values[qiyenianbaozichanzhuangkuang_column_dict[col]] = val
#                     print col,val
        values['rowkey'] = '%s_%s_%s_' %(self.cur_mc, self.y, table_id)
        values[family + ':registrationno'] = self.cur_zch
        values[family + ':enterprisename'] = self.cur_mc
        json_list.append(values)
        self.nbzczk_list.append(values)
        # if json_list:
        #     print 'json_nianbaozichan', json_list

    def get_nianbaoguquanbiangeng(self, soup):
        # print 'nbgqbg', soup
        family = 'equity_transfer'
        table_id = '45'
        values = {}
        json_list = []

        gd_th = soup.find_all('th')
        tr_element_list = soup.find_all('tr')[1:-1]
        iftr = tr_element_list

        cnt = 1
        for i in range(len(iftr)):
            if iftr[i].text.strip():
                gd_td = iftr[i].find_all('td')
                for j in range(len(gd_th)):
                    th = gd_th[j].text.strip()
                    td = gd_td[j].text.strip()
                    # print i,j,th,td
                    values[qiyenianbaoguquanbiangeng_column_dict[th]] = td
                values['rowkey'] = '%s_%s_%s_%d' %(self.cur_mc, self.y, table_id, cnt)
                values[family + ':registrationno'] = self.cur_zch
                values[family + ':enterprisename'] = self.cur_mc
                values[family + ':id'] = str(cnt)
                json_list.append(values)
                self.nbgqbg_list.append(values)
                values = {}
                cnt += 1
        # if json_list:
        #     print 'nbgqbg', json_list

    def get_nianbaoduiwaidanbao(self, soup):
        # print 'nbdwdb', soup
        family = 'guarantee'
        table_id = '44'
        values = {}
        json_list = []

        gd_th = soup.find_all('th')
        tr_element_list = soup.find_all('tr')[1:-1]
        iftr = tr_element_list

        cnt = 1
        for i in range(len(iftr)):
            if iftr[i].text.strip():
                gd_td = iftr[i].find_all('td')
                for j in range(len(gd_th)):
                    th = gd_th[j].text.strip()
                    td = gd_td[j].text.strip()
                    # print i,j,th,td
                    values[qiyenianbaoduiwaidanbao_column_dict[th]] = td
                values['rowkey'] = '%s_%s_%s_%d' %(self.cur_mc, self.y, table_id, cnt)
                values[family + ':registrationno'] = self.cur_zch
                values[family + ':enterprisename'] = self.cur_mc
                values[family + ':id'] = str(cnt)
                json_list.append(values)
                self.nbdwdb_list.append(values)
                values = {}
                cnt += 1
        # if json_list:
        #     print 'nbdwdb', json_list

    def get_nianbaoxiugai(self, soup):
        # print 'nbxg', soup
        family = 'modify'
        table_id = '46'
        values = {}
        json_list = []

        gd_th = soup.find_all('th')
        tr_element_list = soup.find_all('tr')[1:-1]
        iftr = tr_element_list

        cnt = 1
        for i in range(len(iftr)):
            if iftr[i].text.strip():
                gd_td = iftr[i].find_all('td')
                for j in range(len(gd_th)):
                    th = gd_th[j].text.strip()
                    td = gd_td[j].text.strip()
                    # print i,j,th,td
                    values[qiyenianbaoxiugaijilu_column_dict[th]] = td
                values['rowkey'] = '%s_%s_%s_%d' %(self.cur_mc, self.y, table_id, cnt)
                values[family + ':registrationno'] = self.cur_zch
                values[family + ':enterprisename'] = self.cur_mc
                values[family + ':id'] = str(cnt)
                json_list.append(values)
                self.nbxg_list.append(values)
                values = {}
                cnt += 1
        # if json_list:
        #     print 'nbxg', json_list

    # def get_request(self, url, params={}, data={}, verify=True, t=0, release_lock_id=False):
    #     """
    #     ����get����,������Ӵ���,����ip�����Ի���
    #     :param url: �����url
    #     :param params: �������
    #     :param data: ��������
    #     :param verify: ����ssl
    #     :param t: ���Դ���
    #     :param release_lock_id: �Ƿ���Ҫ�ͷ�������ip��Դ
    #     """
    #     try:
    #         if self.use_proxy:
    #             if not release_lock_id:
    #                 self.headers['Proxy-Authorization'] = self.proxy_config.get_auth_header(lock_id=self.lock_id)
    #             else:
    #                 self.headers['Proxy-Authorization'] = self.proxy_config.get_auth_header(lock_id=self.lock_id, release_id=self.lock_id)
    #         r = self.session.get(url=url, headers=self.headers, params=params, data=data, verify=verify)
    #         if r.status_code != 200:
    #             print u'�������Ӧ���� -> %d' % r.status_code , url
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
    #     ����post����,������Ӵ���,����ip�����Ի���
    #     :param url: �����url
    #     :param params: �������
    #     :param data: ��������
    #     :param verify: ����ssl
    #     :param t: ���Դ���
    #     :param release_lock_id: �Ƿ���Ҫ�ͷ�������ip��Դ
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
    #             print u'�������Ӧ���� -> %d' % r.status_code , url
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
    searcher.submit_search_request(u'�����Ʈ˿��������Ʒ���޹�˾')#911302007356029939')#����')#�����Ʈ˿��������Ʒ���޹�˾')
    # �Ϻ�����ب̩��ҵ�������޹�˾�ȷ��ֹ�˾') #�ӱ�̩��ʵҵ�������޹�˾')
    # searcher.submit_search_request(keyword=args_dict['companyName'], account_id=args_dict['accountId'], task_id=args_dict['taskId'])
    print json.dumps(searcher.json_result, ensure_ascii=False)