# coding=gbk
from template.FirefoxSearcher import FirefoxSearcher
from selenium import common
import template.SysConfig as SysConfig
import sys
import os
import re
from template.UnknownColumnException import UnknownColumnException
from template.UnknownTableException import UnknownTableException
from selenium.common.exceptions import NoSuchElementException
from template.Tables import *
from template.Tables_dict import *
import time
from selenium import webdriver
import requests
from template.DataModel import DataModel
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from template.logger import *
from template.DBClient import *
from template.logger import *
import traceback
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from pip._vendor.colorama.win32 import handles
import subprocess
import json
from json.decoder import  JSONArray

print sys.getdefaultencoding()

class AnhuiFirefoxSearcher(FirefoxSearcher):

    def __init__(self):
        super(AnhuiFirefoxSearcher, self).__init__()
        # 四川抽查检查信息没有备注列
        chouchajiancha_template.column_list.pop()
        # gudong_template.column_list.remove('Shareholder_Details')
        self.load_func_dict[u'投资人信息'] = self.load_touziren     #Modified by Jing
#         self.load_func_dict[u'合伙人信息'] = self.load_hehuoren     #Modified by Jing    
        self.load_func_dict[u'成员名册'] = self.load_chengyuanmingce     #Modified by Jing
        self.detail_page_handle=None
        self.search_model = None
        self.result_model = None
        gudong_template.column_list = ['Shareholder_Type','Shareholder_Name', 'Shareholder_CertificationType', 'Shareholder_CertificationNo',  'Shareholder_Details',
                               'Subscripted_Capital', 'ActualPaid_Capital', 'Subscripted_Method', 'Subscripted_Amount', 'Subscripted_Time', 'ActualPaid_Method',
                               'ActualPaid_Amount', 'ActualPaid_Time']
        
    def authCode(self):
        appkey = "83179618"
        secret = "eade15d3fe68d5d665e42ad13cc04073"
        paraMap = {
           "app_key": appkey,
           "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        keys = paraMap.keys()
        keys.sort()
        codes = "%s%s%s" % (secret, str().join('%s%s' % (key, paraMap[key]) for key in keys), secret)
        sign = hashlib.md5(codes).hexdigest().upper()
        paraMap['sign'] = sign
        keys = paraMap.keys()
        authHeader = "MYH-AUTH-MD5 " + str('&').join("%s=%s" % (key, paraMap[key]) for key in keys)
        return authHeader        

    # 查询名称
    def search(self, name):
        self.cur_name = name
        self.search_model = DataModel(name, self.province)
        namo = []
        codo = []
        kong = []
        try:
            if not self.get_ip_status():
                # IP被禁，update_status：4
                self.search_model.set_update_status(4)                
            else:
                self.submit_search_request()
                self.get_search_result()
                if self.search_model.update_status == 1:
                    self.get_search_result()
                    result_list = self.driver.find_elements_by_xpath("html/body/div[1]/div/div[2]/div[@class='list']")
#                         row=len(self.driver.find_elements_by_xpath("html/body/div[1]/div/div[2]/div[@class='list']"))
                    row=1
                    for result in result_list:
                        org_name = result.find_element_by_xpath("ul/li/a").text
                        cur_code = result.find_element_by_xpath("ul/li[2]/span[1]").text
                        tagA = result.find_element_by_xpath("ul/li/a").get_attribute('href')
                        namo.append(org_name)
                        codo.append(cur_code)
                        kong.append(tagA)
                    for r in range(len(kong)):
                        if len(kong)>1:
                            print row
                        # result=self.driver.find_element_by_xpath("html/body/div[1]/div/div[2]/div[@class='list']["+str(row)+"]")
                        # org_name = result.find_element_by_xpath("ul/li/a").text
                        org_name = namo[r]
                        self.org_name = org_name
                        self.cur_code = codo[r]
                        self.tagA = kong[r]
                        try:
                            print 'result_page_get',org_name, self.cur_code,self.tagA
                        except:
                            print 'illegal coding'
                        self.result_model = DataModel(org_name, self.province)
                        sql_1 = "select EnterpriseName from Registered_Info where RegistrationNo='%s'" % org_name
                        database_client_cursor.execute(sql_1)
                        res_1 = database_client_cursor.fetchone()
                        if res_1:
                            print u'%s已更新' % org_name
                        else:
                            self.result_model.set_update_status(1)
                            self.result_model.set_code(self.cur_code)
                            self.result_model.set_tagA(self.tagA)
                            self.result_model.set_codeS(self.cur_code)
                            # result.find_element_by_xpath("ul/li/a").click()
                            # print self.driver.window_handles
                            self.driver.get(kong[r])
                            # time.sleep(3)
                            # print self.driver.window_handles
                            self.detail_page_handle = self.driver.window_handles[-1]
                            self.driver.switch_to.window(self.detail_page_handle)
                            try:
                                # self.parse_lefttabs()
                                self.parse_detail_page()
                            except (UnknownTableException, UnknownColumnException):
                                # 未知表名或列名，update_status：8
                                self.result_model.set_update_status(8)
                            print "*******************************************"+self.driver.current_window_handle
                            self.driver.back()
                            self.driver.switch_to.window(self.search_result_handle)
                            if self.search_model.name == self.result_model.name:
                                self.search_model.set_code(self.cur_code)
                                self.search_model.set_update_status(self.result_model.update_status)
                                self.search_model.set_tagA(self.tagA)
                                self.search_model.set_codeS(self.cur_code)
                            else:

                                sql_2 = "update GsSrc_34_3 set %s where mc='%s'" % (self.result_model, self.result_model.name)
                                database_client_newcursor.execute(sql_2)
                                sql_3 = "select @@rowcount"
                                database_client_newcursor.execute(sql_3)
                                res_3 = database_client_newcursor.fetchone()
                                if int(res_3[0]) == 0:
                                    sql_4 = "insert into GsSrc_34_3(%s) values(%s)" % (self.result_model.get_cols(), self.result_model.get_vals())
                                    database_client_newcursor.execute(sql_4)
                        row+=1
                            
        except Exception:
            # 未知异常，update_status：3
            traceback.print_exc()
            self.search_model.set_update_status(3)
        self.switch_to_search_page()
        return self.search_model


        
    def build_driver(self):
        build_result = 0
#         profile = webdriver.FirefoxProfile(SysConfig.get_firefox_profile_path())
#         self.driver = webdriver.Firefox(firefox_profile=profile)
#         self.driver = webdriver.Firefox()
#         auth = self.authCode()
#         dcap = dict(webdriver.DesiredCapabilities.PHANTOMJS)
#         dcap["phantomjs.page.settings.userAgent"] = ('Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36')
#         dcap["phantomjs.page.customHeaders.Proxy-Authorization"] = (auth)
#         args = ['--load-images=false', '--disk-cache=true', '--proxy=123.56.251.212:8123']
#         self.driver = webdriver.PhantomJS(service_args=args, desired_capabilities=dcap)
        self.driver = webdriver.PhantomJS()#'D:\program\python27\Scripts\phantomjs.exe'
        self.driver.set_window_size(1920, 1080)
#         self.driver = webdriver.PhantomJS()
#         self.driver.set_window_size(1024, 768)
        self.set_timeout_config()
        for i in xrange(SysConfig.max_try_times):
            if self.wait_for_load_start_url():
                break
            else:
                if i == SysConfig.max_try_times:
                    build_result = 1
        return build_result

    def switch_to_search_page(self):
        for handle in self.driver.window_handles:
            if handle != self.start_page_handle:
                self.driver.switch_to.window(handle)
                self.driver.close()
                self.driver.switch_to.window(self.start_page_handle)


    def get_search_result(self):
        if not self.get_ip_status():
            return 4
        time.sleep(2)
        for handle in self.driver.window_handles:
            if handle != self.start_page_handle:
                self.driver.switch_to.window(handle) 
                self.search_result_handle=handle
        # self.driver.get_screenshot_as_file('E:\\anhuibck.png')
        search_result = self.driver.find_element_by_xpath('html/body/div[1]/div/div[2]/div')
        result_text = search_result.text.strip()
        if result_text == u'>> 您搜索的条件无查询结果。 <<':
            logging.info(u'查询结果0条')
            self.search_model.set_update_status(0)
        else:
            self.search_model.set_update_status(1)


    def submit_search_request(self):
        self.code_input_box = self.driver.find_element_by_xpath(self.code_input_box_xpath)
        self.code_submit_button = self.driver.find_element_by_xpath(self.code_submit_button_xpath)
        self.code_input_box.clear()  # 清空输入框
        print 'before',self.cur_name.encode('gbk','ignore')
        self.cur_name = self.cur_name.replace(u'(',u'（').replace(u')', u'）').replace(u':', u'').replace(u'：','').replace(u'[', '').replace(u'?', '')\
            .replace(u'、','').replace(u'—','').replace(u'·','').replace(u'-', '').replace(u'/','').replace(u' ','').replace(u'.','').replace(u'“','')\
            .replace(u'”','').replace(u'&','').replace(u'_','').replace(u'+','').replace(u']', '').replace(u'。','').replace(u'，','').replace(u'#','')\
        .replace(u';', '').replace(u'》','').replace(u'《','').replace(u'〈','').replace(u'〉','').replace(u',','')
        if self.cur_name.count(u'（')>=2 or self.cur_name.count(u'）')>=2 :
            print 'shhhht'
            self.cur_name = self.cur_name.replace(u'（',u'').replace(u'）', u'')
        print 'after',self.cur_name.encode('gbk','ignore')
        self.code_input_box.send_keys(self.cur_name)  # 输入查询代码
        self.code_submit_button.click()
        validate_image_save_path = SysConfig.get_validate_image_save_path()  # 获取验证码保存路径
        # self.driver.get_screenshot_as_file('E:\\ooo.png')
        for i in range(SysConfig.max_try_times):
            # print 'len',len(self.driver.window_handles)
            if "none" in self.find_element("//div [@id='zmdid']").get_attribute('style') and len(self.driver.window_handles)>1:
                break 
            validate_tip=self.driver.find_element_by_xpath(self.validate_tip_xpath).text
            if validate_tip!=u'请根据下图中的汉字，在查询框中输入首字母。':
                self.driver.execute_script("changeVal()")
                continue
            self.validate_image = self.find_element(self.validate_image_xpath)  # 定位验证码图片
            self.validate_input_box = self.find_element("//*[@id='checkNoShow']")  # 定位验证码输入框
            self.validate_submit_button = self.find_element(self.validate_submit_button_xpath)  # 定位验证码提交按钮
            self.download_validate_image(self.validate_image, validate_image_save_path)
            validate_code = self.recognize_validate_code(validate_image_save_path)  # 识别验证码
            self.validate_input_box.clear()  # 清空验证码输入框
            self.validate_input_box.send_keys(validate_code)  # 输入验证码
            self.driver.execute_script("doQuery();")  # 点击搜索（验证码弹窗）
            time.sleep(5)  
        
    # 判断IP是否被禁
    def get_ip_status(self):
        body_text = self.driver.find_element_by_xpath("/html/body").text
        if body_text.startswith(u'您的访问过于频繁'):
            return False
        else:
            return True

    def set_config(self):
        self.start_url = 'http://www.ahcredit.gov.cn/search.jspx'
        self.code_input_box_xpath = "//*[@id='entName']"
        self.code_submit_button_xpath = "//*[@onclick='queryCheck()']/img"
        self.validate_image_xpath = "//*[@id='valCode']"
        self.validate_input_box_xpath = "//*[@id='checkNoShow']"
        self.validate_submit_button_xpath = "//*[@id='woaicss_con1']/ul/li[4]/a"
        self.tab_list_xpath = "//*[@id='tabs']/ul/li"
        self.validate_tip_xpath ="//*[@id='valCodeTip']"
        self.plugin_path = os.path.join(sys.path[0], r'..\ocr\pinyin\pinyin.bat')
        self.province = u'安徽省'

    # 判断搜索起始页是否加载成功 {0:成功, 1:失败}
    def wait_for_load_start_url(self):
        load_result = True
        try:
            self.driver.get(self.start_url)
            self.driver.save_screenshot('screen.png')
#             print self.driver.page_source
            self.start_page_handle = self.driver.current_window_handle
        except common.exceptions.TimeoutException:
            pass
        return load_result

    # 进入详情页 返回int型 {0：查询无结果，1：查询有结果，进入成功，9：进入失败}
    def enter_detail_page(self):
        res = 9
        if not self.get_ip_status():
            return 4
        for handle in self.driver.window_handles:
            if handle != self.start_page_handle:
                self.driver.switch_to.window(handle)  
        search_result = self.driver.find_element_by_xpath('html/body/div[1]/div/div[2]/div')
        result_text = search_result.text.strip()
        logging.info(result_text)
        if result_text == u'>> 您搜索的条件无查询结果。 <<':
            logging.info(u'查询结果0条')
            res = 0
        else:
            info_list = result_text.split('\n')
            company_name = info_list[0]
            company_abstract = info_list[1]
            self.cur_code = self.driver.find_element_by_xpath('html/body/div[1]/div/div[2]/div/ul/li[2]/span[1]').text.strip()
            print 'cur_code:'+self.cur_code
            print 'company_name:'+company_name
            print 'company_abstract:'+company_abstract
            detail_link = self.driver.find_element_by_xpath('html/body/div[1]/div/div[2]/div/ul/li[1]/a')
            detail_link.click()
            for handle in self.driver.window_handles:
                if handle == self.driver.current_window_handle:
                    continue
                else:
                    self.driver.switch_to.window(handle)
                    self.detail_page_handle=handle
                    res = 1
                    logging.info(u"进入详情页成功")
        return res

    def parse_lefttabs(self):
        for i in range(2):
            tab_element = self.find_element("//*[@id='leftTabs']/ul/li[%d]" % (i+1))
            tab_desc = tab_element.text.strip().replace('\n','')
            print tab_desc
            if tab_element.get_attribute('class') != 'current':
                tab_element.click()
            if tab_desc==u'工商公示信息':
                self.parse_detail_page()
            elif tab_desc==u'企业公示信息':
                # print u'pass enterprise info'
                self.load_qiyegongshi()

    def parse_detail_page(self):
        tab_list_length = len(self.driver.find_elements_by_xpath(self.tab_list_xpath))
        for i in range(tab_list_length):
            tab = self.driver.find_element_by_xpath("//*[@id='tabs']/ul/li[%d]" % (i+1))
            tab_text = tab.text
            if tab.get_attribute('class') != 'current':
                tab.click()
            self.load_func_dict[tab_text]()

    def load_qiyegongshi(self):
        time.sleep(3)

        jsonarray=[]
        report_tr_list = self.find_elements(".//*[@id='qiyenianbao']/table/tbody/tr")
        if len(report_tr_list)>2:
            i=1
            self.nowhandles=self.driver.current_window_handle
            for tr_element in report_tr_list[2:]:
                td_element_list=self.find_elements(".//*[@id='qiyenianbao']/table/tbody/tr[%d]/td" %(i+2))
                values = []
                json_dict = {}
                j=1
                for td in td_element_list:
                    val = self.find_element(".//*[@id='qiyenianbao']/table/tbody/tr[%d]/td[%d]" %((i+2),j)).text.strip()
#                     print val
                    if u'报告' in val:
                        values.append(val)
                        values.append(self.find_element(".//*[@id='qiyenianbao']/table/tbody/tr[%d]/td[%d]/a" %((i+2),j)).get_attribute('href'))
                        self.nianbaotitle=val
                        self.find_element(".//*[@id='qiyenianbao']/table/tbody/tr[%d]/td[%d]/a" %((i+2),j)).click()
                        time.sleep(5)
                        self.driver.switch_to.window(self.driver.window_handles[-1])
                        self.load_nianbaodetail()
                        self.driver.close()
                        self.driver.switch_to.window(self.nowhandles)
                        # self.driver.switch_to.default_content()

                    else:
                        values.append(val)
                    j += 1
                i += 1
                json_dict[qiyenianbao_column_list[u'序号']]=values[0]
                json_dict[qiyenianbao_column_list[u'报送年度']]=values[1]
                json_dict[qiyenianbao_column_list[u'链接地址']]=values[2]
                json_dict[qiyenianbao_column_list[u'发布日期']]=values[3]
                jsonarray.append(json_dict)


            json_nianbaosum=json.dumps(jsonarray,ensure_ascii=False)
            print '***json_nianbaosum***',json_nianbaosum

    def load_nianbaodetail(self):
        print '******AnnualReportLoading******'
        html_text = self.driver.find_element_by_xpath(".//*[@id='sifapanding']").get_attribute('innerHTML')   #get_attribute定位xpath后提取片段html结构，可用bs处理
        # print html_text.text
        bs = BeautifulSoup(html_text, 'html5lib')#.prettify()
        tableList = bs.find_all(id = 'qufenkuang')[0].find_all(class_='detailsList')

        self.load_nianbaojiben(bs)
        funcMap = {}
        for i in range(1, len(tableList)):
            title_text = tableList[i].find_all('tr')[0].th.text.strip()
            funcMap[title_text] = i
            # print i, title_text
        for key in funcMap.keys():
            if key == u'网站或网店信息':
                self.load_nianbaoweb(funcMap[key])
            elif key == u'股东及出资信息' or key == u'股东（发起人）及出资信息':
                self.load_nianbaogudong(funcMap[key])
            elif key == u'对外投资信息':
                self.load_nianbaoduiwaitouzi(funcMap[key])
            elif key == u'企业资产状况信息':
                self.load_nianbaozichan(funcMap[key])
            elif key == u'对外提供保证担保信息':
                self.load_nianbaodanbao(funcMap[key])
            elif key == u'股权变更信息':
                self.load_nianbaoguquanbiangeng(funcMap[key])
            elif u'生产经营情况' == key:
                self.load_nianbaozichan(funcMap[key])
            else:
                print u'---看看出现了什么:', key

        self.load_nianbaoxiugai(bs)
        # self.load_nianbaoweb(bs)
        # self.load_nianbaogudong(bs)
        # self.load_nianbaoduiwaitouzi(bs)
        # self.load_nianbaozichan(bs)
        # self.load_nianbaodanbao(bs)
        # self.load_nianbaoguquanbiangeng(bs)
        # self.load_nianbaoxiugai(bs)

        # print bs
        # pass

    def load_dengji(self):
        table_list = self.driver.find_elements_by_xpath("/html/body/div[2]/div[2]/div/div[2]/table")
        for table_element in table_list:
            row_cnt = len(table_element.find_elements_by_xpath("tbody/tr"))
            table_desc_element = table_element.find_element_by_xpath("tbody/tr/th")
            table_desc = table_desc_element.text.split('\n')[0].strip() 
            if table_desc==u'股东（发起人）信息': 
                table_desc=u'股东信息'
            logging.info(u"解析%s ..." % table_desc)
            if row_cnt > 1:
                if table_desc == u'基本信息':
                    self.load_func_dict[table_desc](table_element)            
                elif table_desc in self.load_func_dict:
                            self.load_func_dict[table_desc](table_element)
#                             print table_desc
                else:
                    raise UnknownTableException(self.cur_code, self.org_name,table_desc)
            self.driver.switch_to.default_content()
            logging.info(u"解析%s成功" % table_desc)
                       

    def load_jiben(self,table_element):
        jiben_template.delete_from_database(self.cur_code,self.org_name)
        tr_element_list = self.driver.find_elements_by_xpath("//*[@id='jibenxinxi']/table[1]/tbody/tr")
        jsonarray=[]
        values = {}

        for tr_element in tr_element_list[1:]:
            th_element_list = tr_element.find_elements_by_xpath('th')
            td_element_list = tr_element.find_elements_by_xpath('td')
            if len(th_element_list) == len(td_element_list):
                col_nums = len(th_element_list)
                for i in range(col_nums):
                    col = th_element_list[i].text.strip().replace('\n','')
                    val = td_element_list[i].text.strip().replace("'","''")
                    if col != u'':
                        # coleng = jiben_column_dict[col]
                        # values[coleng] = val
                        values[col] = val
        # values[jiben_column_dict[u'省份']]=self.province
        values[u'省份']=self.province

        # jsonarray.append(values)
        # json_jiben = json.dumps(values,ensure_ascii=False)
        # print 'json_jiben',json_jiben
        jiben_template.insert_into_database(self.cur_code, self.org_name,values)


    def load_gudong(self,table_element):
        gudong_template.delete_from_database(self.cur_code,self.org_name)
        jsonarray=[]
        values = {}
        if "invPagination" in self.driver.find_element_by_xpath('/html/body/div[2]/div[2]/div/div[2]/div[2]').get_attribute("id"):
            p_index_table1 = self.driver.find_element_by_xpath('.//div[@id="invPagination"]/table')
            if p_index_table1.find_element_by_xpath('tbody/tr/th/a[last()]').get_attribute('href').startswith('javascript:slipFive'):
                slip_five=True
            else:
                slip_five=False
            index_element=None
            i=0
            while True:
                if i>0:
                    index_element=self.driver.find_element_by_xpath('.//div[@id="invPagination"]/table/tbody/tr/th/a[%d]' % (i+1))
                    index_element.click()
                i+=1
                time.sleep(0.5)
                tr_element_list = self.driver.find_elements_by_xpath("//*[@id='invDiv']//tbody/tr")
                th_element_list = self.driver.find_element_by_xpath(".//*[@id='touziren']/tbody/tr[2]").find_elements_by_xpath('th')

                for tr_element in tr_element_list:
                    td_element_list = tr_element.find_elements_by_xpath('td')
                    values_list=[]
                    for tdn in range(len(td_element_list)):
                        col_text = th_element_list[tdn].text.strip().replace('\n','')
                        # print col_text
                        col = gudong_column_dict[col_text]

                        val = td_element_list[tdn].text.strip()
                        if val == u'详情':
                            link_text = td_element_list[tdn].find_element_by_xpath('a').get_attribute('onclick')
                            link_t = re.search(r"(?<=').*(?=')",link_text).group()
                            link_href = 'http://www.ahcredit.gov.cn'+link_t
                            values[u'详情']=link_href
                            values_list.append(link_href)
                            # print self.driver.window_handles
                            ActionChains(self.driver).key_down(Keys.SHIFT).perform()
                            td_element_list[tdn].find_element_by_xpath('a').click()
                            ActionChains(self.driver).key_up(Keys.SHIFT).perform()
                            # print self.driver.window_handles
                            for handle in self.driver.window_handles:
                                if handle != self.start_page_handle and handle!=self.detail_page_handle:
                                    self.driver.switch_to.window(handle)
                            # print self.driver.current_window_handle
                            tr_detail_list = self.driver.find_elements_by_xpath("/html/body/div[2]/table/tbody/tr")
                            th_detail_list = self.driver.find_element_by_xpath("/html/body/div[2]/table/tbody/tr[3]").find_elements_by_xpath('th')
                            for tr_ele in tr_detail_list[3:4]:
                                td_ele_list = tr_ele.find_elements_by_xpath('td')
                                for tdc in range(1,len(td_ele_list)):
                                    if tdc ==1:
                                        col_va = self.driver.find_element_by_xpath("/html/body/div[2]/table/tbody/tr[2]").find_elements_by_xpath('th')[1].text.strip()

                                    elif tdc==2:
                                        col_va = self.driver.find_element_by_xpath("/html/body/div[2]/table/tbody/tr[2]").find_elements_by_xpath('th')[2].text.strip()

                                    else:
                                        col_va = th_detail_list[tdc-3].text.strip()
                                    # col_va = th_detail_list[tdc].text.strip()
                                    col = gudong_column_dict[col_va]

                                    va = td_ele_list[tdc].text.strip()
                                    values[col]= va
                                    values_list.append(va)
                                    # jsonarray.append(va)
                            self.driver.close()
                            self.driver.switch_to.window(self.driver.window_handles[-1])
                        else:
                            values[col] = val
                            values_list.append(val)
                    jsonarray.append(values)
                    values={}
                    if len(values_list)<6:
                        print 'len',len(values_list)
                        values_list.extend(['','','','','','',''])

                    # print values_list
                    gudong_template.insert_into_database(self.cur_code,self.org_name, values_list)
                if i==len(self.driver.find_elements_by_xpath('.//div[@id="invPagination"]/table/tbody/tr/th/a[@id]')):
                    if slip_five:
                        self.driver.find_element_by_xpath(".//div[@id='invPagination']/table/tbody/tr/th/a[last()]").click()
                        slip_five=False
                        i=0
                    else:
                        break
            json_gudong = json.dumps(jsonarray,ensure_ascii=False)
            # print 'json_gudong',json_gudong
        else:
            table_element = self.driver.find_element_by_xpath("//*[@id='invDiv']/table")
            if len(table_element.find_elements_by_xpath("tbody/tr")) > 0:
                last_index_element = self.driver.find_element_by_xpath("//*[@id='jibenxinxi']/table[3]/tbody/tr/th/a[last()]")
                index_element_list_length = int(last_index_element.text.strip())
                for i in range(index_element_list_length):
                    if i > 0:
                        index_element = self.driver.find_element_by_xpath("//*[@id='jibenxinxi']/table[3]/tbody/tr/th/a[%d]" % (i+1))
                        index_element.click()
                        time.sleep(0.5)
                        table_element = self.driver.find_element_by_xpath("//*[@id='invDiv']/table")
                    tr_element_list = table_element.find_elements_by_xpath('tbody/tr')
                    th_element_list = self.driver.find_element_by_xpath(".//*[@id='touziren']/tbody/tr[2]").find_elements_by_xpath('th')
                    for tr_element in tr_element_list:
                        td_element_list = tr_element.find_elements_by_xpath('td')
                        # print len(td_element_list),td_element_list
                        values_list=[]
                        for tdn in range(len(td_element_list)):
                            col_text = th_element_list[tdn].text.strip().replace('\n','')
                            # print col_text
                            col = gudong_column_dict[col_text]
                            # print col

                            val = td_element_list[tdn].text.strip().replace("'", "''")
                            if val == u'详情':
                                link_text = td_element_list[tdn].find_element_by_xpath('a').get_attribute('onclick')
                                link_t = re.search(r"(?<=').*(?=')",link_text).group()
                                link_href = 'http://www.ahcredit.gov.cn'+link_t
                                # print 'detaillink','http://www.ahcredit.gov.cn'+link_t
                                values[u'详情']=link_href
                                values_list.append(link_href)
                                td_element_list[tdn].find_element_by_xpath('a').click()
                                for handle in self.driver.window_handles:
                                    if handle != self.start_page_handle and handle!=self.detail_page_handle:
                                        self.driver.switch_to.window(handle)
                                tr_detail_list = self.driver.find_elements_by_xpath("/html/body/div[2]/table/tbody/tr")
                                th_detail_list = self.driver.find_element_by_xpath("/html/body/div[2]/table/tbody/tr[3]").find_elements_by_xpath('th')
                                for tr_ele in tr_detail_list[3:4]:
                                    td_ele_list = tr_ele.find_elements_by_xpath('td')
                                    # print 'lenTD',len(td_ele_list)
                                    for tdc in range(1,len(td_ele_list)):

                                        if tdc ==1:
                                            col_va = self.driver.find_element_by_xpath("/html/body/div[2]/table/tbody/tr[2]").find_elements_by_xpath('th')[1].text.strip()
                                            # print col_va,'111'
                                        elif tdc==2:
                                            col_va = self.driver.find_element_by_xpath("/html/body/div[2]/table/tbody/tr[2]").find_elements_by_xpath('th')[2].text.strip()
                                            # print col_va,'222'
                                        else:
                                            col_va = th_detail_list[tdc-3].text.strip()
                                            # print col_va,'else'
                                        col = gudong_column_dict[col_va]

                                        va = td_ele_list[tdc].text.strip()
                                        values[col]= va
                                        values_list.append(va)
                                        # jsonarray.append(va)
                                self.driver.close()
                                self.driver.switch_to.window(self.driver.window_handles[-1])
                            else:
                                values[col] = val
                                values_list.append(val)
                        jsonarray.append(values)
                        values={}
                        if len(values_list)<6:
                            print len(values_list)
                            values_list.extend(['','','','','','',''])
                        # print values_list
                # json_gudong = json.dumps(jsonarray,ensure_ascii=False)
                # print 'json_dudong',json_gudong
                        gudong_template.insert_into_database(self.cur_code, self.org_name,values_list)


    def load_touziren(self,table_element):
        touziren_template = TableTemplate('Investor_Info', u'投资人信息')
        touziren_template.column_list = ['Investor_Name', 'investment_Method']
        # touziren_template.delete_from_database(self.cur_code)
        jsonarray =[]
        table_text = self.driver.find_element_by_xpath("//*[@id='invDiv']/table").text.strip()
        if table_text !='':
            if "javascript:slipFive" in self.driver.find_elements_by_xpath('//*[@id="jibenxinxi"]/table[3]'):
                slip_five=True
            else:
                slip_five=False
                index_element=None
                i=0
            while True:
                if i>0:
                    index_element=self.driver.find_element_by_xpath('.//*[@id="jibenxinxi"]/table[3]/tbody/tr/th/a[%d]' % (i+1))
                    index_element.click()
                i+=1
                time.sleep(0.5)
                tr_element_list = self.driver.find_elements_by_xpath("//*[@id='invDiv']//tbody/tr")
                for tr_element in tr_element_list:
                    td_element_list = tr_element.find_elements_by_xpath('td')
                    values = []
                    json_dict = {}
                    for td in td_element_list:
                        val = td.text.strip()
                        values.append(val)
                    json_dict[touziren_column_dict[u'投资人']] = values[0]
                    json_dict[touziren_column_dict[u'出资方式']] = values[1]
                    jsonarray.append(json_dict)


                    # touziren_template.insert_into_database(self.cur_code, values)
                if i==len(self.driver.find_elements_by_xpath('.//*[@id="jibenxinxi"]/table[3]/tbody/tr/th/a[@id]')):
                        if slip_five:
                            self.driver.find_element_by_xpath(".//*[@id='jibenxinxi']/table[3]/tbody/tr/th/a[last()]").click()
                            slip_five=False
                            i=0
                        else:
                            break
            json_touziren = json.dumps(jsonarray,ensure_ascii=False)
            print 'json_touziren',json_touziren

#
#     def load_hehuoren(self,table_element):
#         hehuoren_template.delete_from_database(self.cur_code)
#         tr_element_list = self.driver.find_elements_by_xpath("//*[@id='table_fr']/tbody/tr[position()<last()]")
#
#             td_element_list = tr_element.find_elements_by_xpath('td')
#             values = []
#             for td in td_element_list:
#                 val = td.text.strip()
#                 values.append(val)
#             hehuoren_template.insert_into_database(self.cur_code, values)


    def load_biangeng(self, table_element):
        biangeng_template.delete_from_database(self.cur_code,self.org_name)
        table_text = self.driver.find_element_by_xpath("//*[@id='altTab']").text.strip()
        jsonarray=[]

        if table_text !='':
            if "javascript:slipFive" in self.driver.find_elements_by_xpath('//*[@id="jibenxinxi"]/table[last()]'):
                slip_five=True
            else:
                slip_five=False
                index_element=None
                i=0
            while True:
                if i>0:
                    index_element=self.driver.find_element_by_xpath('.//*[@id="jibenxinxi"]/table[last()]/tbody/tr/th/a[%d]' % (i+1))
                    index_element.click()
                i+=1
                time.sleep(0.5)
                row=0
                tr_element_list = self.driver.find_elements_by_xpath("//*[@id='altTab']//tbody/tr")
                th_element_list = self.driver.find_elements_by_xpath("//*[@id='altDiv']/preceding-sibling::*")[-1].find_elements_by_xpath('tbody/tr[2]/th')
                # print 'th_last_element','aa',th_element_list.text,type(th_element_list)
                for tr_element in tr_element_list:
                    values_list = []
                    td_element_list = tr_element.find_elements_by_xpath('td')
                    # biangeng_column_dict[u'注册号']=self.cur_code
                    values = {}
                    col=0
                    for n,td in enumerate(td_element_list):
                        col_text = th_element_list[n].text
                        col_t = biangeng_column_dict[col_text]

                        col+=1
                        if col==2: position='before'
                        elif col==3: position='after'
                        else: position='none'
                        val = td.text.strip().replace('\n','')
                        if val.endswith(u'更多'):
                            self.driver.execute_script("doShow('%s','%s')" %(row,position))
                            val = td.text.strip().replace('\n','')
                            values[col_t] = val[:-4].strip()
                            values_list.append(val[:-4].strip())
                            # values.append(val[:-4].strip())
                        else:
                            values[col_t] = val.strip()
                            values_list.append(val.strip())
                            # values.append(val.strip())
                    row+=1
                    values[u'RegistrationNo']=self.cur_code   #加入注册号字段
                    jsonarray.append(values)
                    values = {}

                    biangeng_template.insert_into_database(self.cur_code, self.org_name,values_list)
                if i==len(self.driver.find_elements_by_xpath('.//*[@id="jibenxinxi"]/table[last()]/tbody/tr/th/a[@id]')):
                        if slip_five:
                            self.driver.find_element_by_xpath(".//*[@id='jibenxinxi']/table[last()]/tbody/tr/th/a[last()]").click()
                            slip_five=False
                            i=0
                        else:
                            break
            json_biangeng = json.dumps(jsonarray,ensure_ascii=False)
            # print 'json_biangeng',json_biangeng


    def load_beian(self):
        table_list = self.driver.find_elements_by_xpath("/html/body/div[2]/div[2]/div/div[3]/table")
        for table_element in table_list:
            row_cnt = len(table_element.find_elements_by_xpath("tbody/tr"))
            table_desc_element = table_element.find_element_by_xpath("tbody/tr/th")
            table_desc = table_desc_element.text.split('\n')[0].strip()
            if row_cnt > 1:
                if table_desc not in self.load_func_dict:
                    raise UnknownTableException(self.cur_code, table_desc)
                logging.info(u"解析%s ..." % table_desc)
                self.load_func_dict[table_desc](table_element)
                self.driver.switch_to.default_content()
                logging.info(u"解析%s成功" % table_desc)

    def load_DICInfo(self,table_element):
        pass

    def load_zhuyaorenyuan(self, table_element):
        zhuyaorenyuan_template.delete_from_database(self.cur_code,self.org_name)
        table_text = self.driver.find_element_by_xpath("//*[@id='memDiv']/table").text.strip()
        # zhuyaorenyuan_column_dict
        jsonarray = []
        persons = {}
        if table_text !='':
            if "javascript:slipFive" in self.driver.find_elements_by_xpath('//*[@id="beian"]/table[2]'):
                slip_five=True
            else:
                slip_five=False
                index_element=None
                i=0
            while True:
                if i>0:
                    index_element=self.driver.find_element_by_xpath('.//*[@id="beian"]/table[2]/tbody/tr/th/a[%d]' % (i+1))
                    index_element.click()
                i+=1
                time.sleep(0.5)
                table_element = self.driver.find_element_by_xpath("//*[@id='memDiv']//tbody/tr")
                tr_element_list = table_element.find_elements_by_xpath("//*[@id='memDiv']//tbody/tr")
                for tr_element in tr_element_list:
                    values = []
                    td_element_list = tr_element.find_elements_by_xpath('td')
                    list_length = len(td_element_list)
                    fixed_length = list_length - list_length % 3
                    for j in range(fixed_length):
                        val = td_element_list[j].text.strip().replace(u"'",u"''")
                        values.append(val)
                        if len(values) == 3 and values[1]!=u'':
                            # zhuyaorenyuan_column_dict
                            persons[zhuyaorenyuan_column_dict[u'序号']]=values[0]
                            persons[zhuyaorenyuan_column_dict[u'姓名']]=values[1]
                            persons[zhuyaorenyuan_column_dict[u'职务']]=values[2]
                            jsonarray.append(persons)
                            zhuyaorenyuan_template.insert_into_database(self.cur_code,self.org_name, values)
                            values = []
                            persons={}

                if i==len(self.driver.find_elements_by_xpath('.//*[@id="beian"]/table[2]/tbody/tr/th/a[@id]')):
                    if slip_five:
                        self.driver.find_element_by_xpath(".//*[@id='beian']/table[2]/tbody/tr/th/a[last()]").click()
                        slip_five=False
                        i=0
                    else:
                        break
            json_zhuyaorenyuan = json.dumps(jsonarray,ensure_ascii=False)
            # print 'json_zhuyaorenyuan',json_zhuyaorenyuan


#     def load_jiatingchengyuan(self, table_element):
#         jiatingchengyuan_template.delete_from_database(self.cur_code)
#         table_element = self.driver.find_element_by_xpath("//*[@id='memDiv']/tbody/tr")
#         tr_element_list = table_element.find_elements_by_xpath("//*[@id='memDiv']/tbody/tr")
#         for tr_element in tr_element_list:
#             values = []
#             td_element_list = tr_element.find_elements_by_xpath('td')
#             list_length = len(td_element_list)
#             fixed_length = list_length - list_length % 3
#             for i in range(fixed_length):
#                 val = td_element_list[i].text.strip()
#                 values.append(val)
#                 if len(values) == 3:
#                     zhuyaorenyuan_template.insert_into_database(self.cur_code, values)
#                     values = []
#
    def load_chengyuanmingce(self, table_element):
        zhuyaorenyuan_template.delete_from_database(self.cur_code,self.org_name)
        table_text = self.driver.find_element_by_xpath("//*[@id='countryDiv']/table").text.strip()
        jsonarray = []
        if table_text !='':
            try:
                if "javascript:slipFive" in self.driver.find_elements_by_xpath('//*[@id="beian"]/table[2]'):
                    slip_five=True
                else:
                    slip_five=False
                    index_element=None
                    i=0
                while True:
                    if i>0:
                        index_element=self.driver.find_element_by_xpath('.//*[@id="beian"]/table[2]/tbody/tr/th/a[%d]' % (i+1))
                        index_element.click()
                    i+=1
                    time.sleep(0.5)
                    table_element = self.driver.find_element_by_xpath("//*[@id='countryDiv']//tbody/tr")
                    tr_element_list = table_element.find_elements_by_xpath("//*[@id='countryDiv']//tbody/tr")
                    for tr_element in tr_element_list:
                        values = []
                        persons = {}
                        td_element_list = tr_element.find_elements_by_xpath('td')
                        list_length = len(td_element_list)
                        fixed_length = list_length - list_length % 2
                        for j in range(fixed_length):
                            val = td_element_list[j].text.strip()
                            values.append(val)
                            if len(values) == 2 and values[1] != u'':
                                values.append('')
                                zhuyaorenyuan_template.insert_into_database(self.cur_code, self.org_name,values)
                                persons[zhuyaorenyuan_column_dict[u'序号']]=values[0]
                                persons[zhuyaorenyuan_column_dict[u'姓名']]=values[1]
                                persons[zhuyaorenyuan_column_dict[u'职务']]=values[2]
                                jsonarray.append(persons)
                                values = []
                                persons = {}

                    if i==len(self.driver.find_elements_by_xpath('.//*[@id="beian"]/table[2]/tbody/tr/th/a[@id]')):
                        if slip_five:
                            self.driver.find_element_by_xpath(".//*[@id='beian']/table[2]/tbody/tr/th/a[last()]").click()
                            slip_five=False
                            i=0
                        else:
                            break
                json_chengyuanmingce = json.dumps(jsonarray,ensure_ascii=False)
                # print 'json_chengyuanmingce',json_chengyuanmingce
            except:
                if "javascript:slipFive" in self.driver.find_elements_by_xpath('//*[@id="beian"]/div[2]'):
                    slip_five=True
                else:
                    slip_five=False
                    index_element=None
                    i=0
                while True:
                    if i>0:
                        index_element=self.driver.find_element_by_xpath('.//*[@id="beian"]/div[2]/table/tbody/tr/th/a[%d]' % (i+1))
                        index_element.click()
                    i+=1
                    time.sleep(0.5)
                    table_element = self.driver.find_element_by_xpath("//*[@id='countryDiv']//tbody/tr")
                    tr_element_list = table_element.find_elements_by_xpath("//*[@id='countryDiv']//tbody/tr")
                    for tr_element in tr_element_list:
                        values = []
                        persons = {}
                        td_element_list = tr_element.find_elements_by_xpath('td')
                        list_length = len(td_element_list)
                        fixed_length = list_length - list_length % 2
                        for j in range(fixed_length):
                            val = td_element_list[j].text.strip()
                            values.append(val)
                            if len(values) == 2 and values[1] != u'':
                                values.append('')
                                zhuyaorenyuan_template.insert_into_database(self.cur_code, self.org_name,values)
                                persons[zhuyaorenyuan_column_dict[u'序号']]=values[0]
                                persons[zhuyaorenyuan_column_dict[u'姓名']]=values[1]
                                persons[zhuyaorenyuan_column_dict[u'职务']]=values[2]
                                jsonarray.append(persons)
                                values = []
                                persons = {}

                    if i==len(self.driver.find_elements_by_xpath('.//*[@id="beian"]/div[2]/table/tbody/tr/th/a[@id]')):
                        if slip_five:
                            self.driver.find_element_by_xpath(".//*[@id='beian']/div[2]/table/tbody/tr/th/a[last()]").click()
                            slip_five=False
                            i=0
                        else:
                            break
                json_chengyuanmingce = json.dumps(jsonarray,ensure_ascii=False)
                # print 'json_chengyuanmingce',json_chengyuanmingce

    def load_fenzhijigou(self, table_element):
        fenzhijigou_template.delete_from_database(self.cur_code,self.org_name)
        table_text = self.driver.find_element_by_xpath("//*[@id='childDiv']/table").text.strip()
        jsonarray = []
        if table_text !='':
            if "javascript:slipFive" in self.driver.find_elements_by_xpath('//*[@id="beian"]/table[4]'):
                slip_five=True
            else:
                slip_five=False
                index_element=None
                i=0
                while True:
                    if i>0:
                        index_element=self.driver.find_element_by_xpath('.//*[@id="beian"]/table[4]/tbody/tr/th/a[%d]' % (i+1))
                        index_element.click()
                    i+=1
                    time.sleep(0.5)
                    tr_element_list = table_element.find_elements_by_xpath("//*[@id='childDiv']/table/tbody/tr")
                    for tr_element in tr_element_list:
                        td_element_list = tr_element.find_elements_by_xpath('td')
                        values = []
                        json_dict = {}
                        for td in td_element_list:
                            val = td.text.strip()
                            values.append(val)
                        json_dict[fenzhijigou_column_dict[u'序号']]=values[0]
                        json_dict[fenzhijigou_column_dict[u'注册号/统一社会信用代码']]=values[1]
                        json_dict[fenzhijigou_column_dict[u'名称']]=values[2]
                        json_dict[fenzhijigou_column_dict[u'登记机关']]=values[3]
                        jsonarray.append(json_dict)

                        fenzhijigou_template.insert_into_database(self.cur_code, self.org_name, values)
                    if i==len(self.driver.find_elements_by_xpath('.//*[@id="beian"]/table[4]/tbody/tr/th/a[@id]')):
                        if slip_five:
                            self.driver.find_element_by_xpath(".//*[@id='beian']/table[4]/tbody/tr/th/a[last()]").click()
                            slip_five=False
                            i=0
                        else:
                            break
                json_fenzhijigou = json.dumps(jsonarray,ensure_ascii=False)
                # print 'json_fenzhijigou',json_fenzhijigou


    def load_qingsuan(self, table_element):
        pass


    def load_dongchandiyadengji(self):
        dongchandiyadengji_template.delete_from_database(self.cur_code,self.org_name)
        table_text = self.driver.find_element_by_xpath("//*[@id='mortDiv']/table").text.strip()
        jsonarray = []
        if table_text !='':
            if "javascript:slipFive" in self.driver.find_elements_by_xpath("//*[@id='dongchandiya']/table[2]"):
                slip_five=True
            else:
                slip_five=False
                index_element=None
                i=0
            while True:
                if i>0:
                    index_element=self.driver.find_element_by_xpath("//*[@id='dongchandiya']/table[2]/tbody/tr/th/a[%d]" % (i+1))
                    index_element.click()
                i+=1
                time.sleep(0.5)
                tr_element_list = self.driver.find_elements_by_xpath("//*[@id='mortDiv']/table/tbody/tr")
                for tr_element in tr_element_list:
                    td_element_list = tr_element.find_elements_by_xpath('td')
                    values = []
                    values_dict = {}
                    for td in td_element_list:
                        val = td.text.strip()
                        if val == u'详情':
                            link=td.find_element_by_xpath('a').get_attribute('onclick')
                            xiangqing_link ="http://www.ahcredit.gov.cn"+link[13:-2]
                            print u'xiangqing_link:'+xiangqing_link
                            values.append(xiangqing_link)
                        else:
                            values.append(val)
                    values_dict[dongchandiyadengji_column_dict[u'序号']] = values[0]
                    values_dict[dongchandiyadengji_column_dict[u'登记编号']] = values[1]
                    values_dict[dongchandiyadengji_column_dict[u'登记日期']] = values[2]
                    values_dict[dongchandiyadengji_column_dict[u'登记机关']] = values[3]
                    values_dict[dongchandiyadengji_column_dict[u'被担保债权数额']] = values[4]
                    values_dict[dongchandiyadengji_column_dict[u'状态']] = values[5]
                    values_dict[dongchandiyadengji_column_dict[u'公示日期']] = values[6]
                    values_dict[dongchandiyadengji_column_dict[u'详情']] = values[7]
                    jsonarray.append(values_dict)


                    dongchandiyadengji_template.insert_into_database(self.cur_code, self.org_name, values)
                if i==len(self.driver.find_elements_by_xpath('.//*[@id="dongchandiya"]/table[2]/tbody/tr/th/a[@id]')):
                    if slip_five:
                        self.driver.find_element_by_xpath(".//*[@id='dongchandiya']/table[2]/tbody/tr/th/a[last()]").click()
                        slip_five=False
                        i=0
                    else:
                        break
            json_dongchandiya = json.dumps(jsonarray,ensure_ascii=False)
            # print 'json_dongchandiya',json_dongchandiya

    def load_guquanchuzhidengji(self):
        guquanchuzhidengji_template.delete_from_database(self.cur_code,self.org_name)
        table_text = self.driver.find_element_by_xpath("//*[@id='pledgeDiv']/table").text.strip()
        jsonarray = []
        if table_text !='':
            if "javascript:slipFive" in self.driver.find_elements_by_xpath("//*[@id='guquanchuzhi']/table[2]"):
                slip_five=True
            else:
                slip_five=False
                index_element=None
                i=0
            while True:
                if i>0:
                    index_element=self.driver.find_element_by_xpath("//*[@id='guquanchuzhi']/table[2]/tbody/tr/th/a[%d]" % (i+1))
                    index_element.click()
                i+=1
                time.sleep(0.5)
                tr_element_list = self.driver.find_elements_by_xpath("//*[@id='pledgeDiv']/table/tbody/tr")
                th_element_list =  self.driver.find_elements_by_xpath("//*[@id='pledgeDiv']/preceding-sibling::*")[-1].find_elements_by_xpath("tbody/tr[2]/th")
                for tr_element in tr_element_list:
                    td_element_list = tr_element.find_elements_by_xpath('td')
                    values = []
                    json_dict = {}
                    for n,td in enumerate(td_element_list):
                        col_text = th_element_list[n].text.strip()
                        col = guquanchuzhidengji_column_dict[col_text]
                        val = td.text.strip()
                        if val.endswith(u'详情'):
                            link=td.find_element_by_xpath('a').get_attribute('onclick')
                            xiangqing_link ="http://www.ahcredit.gov.cn"+link[13:-2]
                            print u'xiangqing_link:'+xiangqing_link
                            json_dict[guquanchuzhidengji_column_dict[u'变化情况']]=xiangqing_link
                            values.append(xiangqing_link)
                        else:
                            json_dict[col]=val
                            values.append(val)
                    jsonarray.append(json_dict)

                    guquanchuzhidengji_template.insert_into_database(self.cur_code,self.org_name, values)
                if i==len(self.driver.find_elements_by_xpath('.//*[@id="guquanchuzhi"]/table[2]/tbody/tr/th/a[@id]')):
                    if slip_five:
                        self.driver.find_element_by_xpath(".//*[@id='guquanchuzhi']/table[2]/tbody/tr/th/a[last()]").click()
                        slip_five=False
                        i=0
                    else:
                        break
            json_guquanchuzhidengji = json.dumps(jsonarray,ensure_ascii=False)
            # print 'json_guquanchuzhidengji',json_guquanchuzhidengji


    def load_xingzhengchufa(self):
        xingzhengchufa_template.column_list = ['Penalty_No', 'Penalty_Code', 'Penalty_IllegalType', 'Penalty_DecisionContent',
                                       'Penalty_DecisionInsititution', 'Penalty_DecisionDate', 'Penalty_AnnouncedDate','Penalty_Details']
        xingzhengchufa_template.delete_from_database(self.cur_code,self.org_name)
        table_text = self.driver.find_element_by_xpath("//*[@id='punDiv']/table").text.strip()
        jsonarray = []
        if table_text !='':
            if "javascript:slipFive" in self.driver.find_elements_by_xpath("//*[@id='xingzhengchufa']/table[2]"):
                slip_five=True
            else:
                slip_five=False
                index_element=None
                i=0
            while True:
                if i>0:
                    index_element=self.driver.find_element_by_xpath("//*[@id='xingzhengchufa']/table[2]/tbody/tr/th/a[%d]" % (i+1))
                    index_element.click()
                i+=1
                time.sleep(0.5)
                tr_element_list = self.driver.find_elements_by_xpath("//*[@id='punTab']/tbody/tr")
                for tr_element in tr_element_list:
                    td_element_list = tr_element.find_elements_by_xpath('td')
                    values = []
                    values_dict = {}
                    for td in td_element_list[:8]:
                        val = td.text.strip()
                        print val
                        if val.endswith(u'更多'):
                            td.find_element_by_xpath('a').click()
                            val = td.text.strip()
                            values.append(val[:-4].strip())
                        elif val == u'详情':
#                         values.append(td.find_element_by_xpath('a').get_attribute('href'))
                            link=td.find_element_by_xpath('a').get_attribute('onclick')
                            xiangqing_link ="http://www.ahcredit.gov.cn"+link[13:-2]
                            print u'xiangqing_link:'+xiangqing_link
                            values.append(xiangqing_link)
                        else:
                            values.append(val)
                    # values_dict[xingzhengchufa_column_dict[u'序号']]=values[0]
                    # values_dict[xingzhengchufa_column_dict[u'行政处罚决定书文号']]=values[1]
                    # values_dict[xingzhengchufa_column_dict[u'违法行为类型']]=values[2]
                    # values_dict[xingzhengchufa_column_dict[u'行政处罚内容']]=values[3]
                    # values_dict[xingzhengchufa_column_dict[u'作出行政处罚决定机关名称']]=values[4]
                    # values_dict[xingzhengchufa_column_dict[u'作出行政处罚决定日期']]=values[5]
                    # values_dict[xingzhengchufa_column_dict[u'公示日期']]=values[6]
                    # values_dict[xingzhengchufa_column_dict[u'详情']]=values[7]
                    # jsonarray.append(values_dict)


                    xingzhengchufa_template.insert_into_database(self.cur_code, self.org_name,values)
                if i==len(self.driver.find_elements_by_xpath('.//*[@id="xingzhengchufa"]/table[2]/tbody/tr/th/a[@id]')):
                    if slip_five:
                        self.driver.find_element_by_xpath(".//*[@id='xingzhengchufa']/table[2]/tbody/tr/th/a[last()]").click()
                        slip_five=False
                        i=0
                    else:
                        break
            json_xingzhengchufa = json.dumps(jsonarray,ensure_ascii=False)
            # print 'json_xingzhengchufa',json_xingzhengchufa


    def load_jingyingyichang(self):
        jingyingyichang_template.delete_from_database(self.cur_code,self.org_name)
        table_text = self.driver.find_element_by_xpath("//*[@id='excTab']").text.strip()
        jsonarray = []
        if table_text !='':
            if "javascript:slipFive" in self.driver.find_elements_by_xpath("//*[@id='jingyingyichangminglu']/table[2]"):
                slip_five=True
            else:
                slip_five=False
                index_element=None
                i=0
                while True:
                    if i>0:
                        index_element=self.driver.find_element_by_xpath('.//*[@id="jingyingyichangminglu"]/table[2]/tbody/tr/th/a[%d]' % (i+1))
                        index_element.click()
                    i+=1
                    time.sleep(1)
                    tr_list = self.driver.find_elements_by_xpath("//*[@id='excTab']//tbody/tr")
                    if tr_list:
                        for tr_element in tr_list:
                            values = []
                            json_dict = {}
                            td_element_list = tr_element.find_elements_by_xpath('td')
                            for td in td_element_list:
                                val = td.text.strip()
                                if val.endswith(u'更多'):
                                    td.find_element_by_xpath('a').click()
                                    val = td.text.strip()
                                    values.append(val[:-4].strip())
                                else:
                                    values.append(val.strip())
                            json_dict[jingyingyichang_column_dict[u'序号']]=values[0]
                            json_dict[jingyingyichang_column_dict[u'列入经营异常名录原因']]=values[1]
                            json_dict[jingyingyichang_column_dict[u'列入日期']]=values[2]
                            json_dict[jingyingyichang_column_dict[u'移出经营异常名录原因']]=values[3]
                            json_dict[jingyingyichang_column_dict[u'移出日期']]=values[4]
                            json_dict[jingyingyichang_column_dict[u'作出决定机关']]=values[5]
                            jsonarray.append(json_dict)

                            jingyingyichang_template.insert_into_database(self.cur_code, self.org_name,values)
                    # print str(len(self.driver.find_elements_by_xpath('.//*[@id="jingyingyichangminglu"]/table[2]/tbody/tr/th/a[@id]')))
                    if i==len(self.driver.find_elements_by_xpath('.//*[@id="jingyingyichangminglu"]/table[2]/tbody/tr/th/a[@id]')):
                        if slip_five:
                            self.driver.find_element_by_xpath(".//*[@id='jingyingyichangminglu']/table[2]/tbody/tr/th/a[last()]").click()
                            slip_five=False
                            i=0
                        else:
                            break
                json_jingyingyichang = json.dumps(jsonarray,ensure_ascii=False)
                # print 'json_jingyingyichang',json_jingyingyichang

    def load_yanzhongweifa(self):
        pass

    def load_chouchajiancha(self):
        chouchajiancha_template.delete_from_database(self.cur_code,self.org_name)
        jsonarray = []
        table_text = self.driver.find_element_by_xpath("//*[@id='spotCheckDiv']/table").text.strip()
        if table_text !='':
            if "javascript:slipFive" in self.driver.find_elements_by_xpath("//*[@id='chouchaxinxi']/table[2]"):
                slip_five=True
            else:
                slip_five=False
                index_element=None
                i=0
                while True:
                    if i>0:
                        index_element=self.driver.find_element_by_xpath('.//*[@id="chouchaxinxi"]/table[last()]/tbody/tr/th/a[%d]' % (i+1))
                        index_element.click()
                    i+=1
                    time.sleep(1)
                    tr_element_list = self.driver.find_elements_by_xpath("//div[@id='spotCheckDiv']//tbody/tr")
                    for tr_element in tr_element_list:
                        td_element_list = tr_element.find_elements_by_xpath('td')
                        values = []
                        json_dict = {}
                        for td in td_element_list:
                            val = td.text.strip()
                            values.append(val)
                        json_dict[chouchajiancha_column_dict[u'序号']]=values[0]
                        json_dict[chouchajiancha_column_dict[u'检查实施机关']]=values[1]
                        json_dict[chouchajiancha_column_dict[u'类型']]=values[2]
                        json_dict[chouchajiancha_column_dict[u'日期']]=values[3]
                        json_dict[chouchajiancha_column_dict[u'结果']]=values[4]
                        jsonarray.append(json_dict)

                        chouchajiancha_template.insert_into_database(self.cur_code, self.org_name,values)
                    if i==len(self.driver.find_elements_by_xpath('.//*[@id="chouchaxinxi"]/table[last()]/tbody/tr/th/a[@id]')):
                        if slip_five:
                            self.driver.find_element_by_xpath(".//*[@id='chouchaxinxi']/table[last()]/tbody/tr/th/a[last()]").click()
                            slip_five=False
                            i=0
                        else:
                            break
                json_chouchajiancha = json.dumps(jsonarray,ensure_ascii=False)
                # print 'json_chouchajiancha',json_chouchajiancha

    def load_nianbaojiben(self,table_element):
#         nianbaojiben_template = TableTemplate('AR_Registered_Info', u'企业基本信息')
#         nianbaojiben_template.column_dict = {
#             u'统一社会信用代码/注册号': 'RegistrationNo',
#             u'注册号/统一社会信用代码': 'RegistrationNo',             # Modified by Jing
#             u'注册号': 'RegistrationNo',                        # Modified by Jing
#             u'企业名称': 'AR_EnterpriseName',
#             u'企业联系电话':'AR_PhoneNum',
#             u'邮政编码':'AR_PostCode',
#             u'企业通信地址':'AR_MailAddress',
#             u'电子邮箱':'AR_Email',
#             u'企业是否有投资信息或购买其他公司股权':'AR_tzgmgq',
#             u'企业经营状态':'AR_Status',
#             u'是否有网站或网点':'AR_WebsiteExist',
#             u'从业人数':'AR_EmployeeCnt'
#         }
        source= self.driver.find_elements_by_id("qufenkuang")[0]
        html=source.get_attribute('outerHTML')
        Soup = BeautifulSoup(html,'html.parser')
        table_element=Soup.find_all('table')[0]
        tr_element_list = table_element.find_all("tr")
        values = {}
        for tr_element in tr_element_list[2:]:
            th_element_list = tr_element.find_all('th')
            td_element_list = tr_element.find_all('td')
            if len(th_element_list) == len(td_element_list):
                col_nums = len(th_element_list)
                for i in range(col_nums):
                    col = th_element_list[i].get_text().strip().replace('\n','')
                    val = td_element_list[i].get_text().strip().replace('\n','')
                    if col != u'':
                        values[col] = val
#                     print col,val
        values[u'省份']=self.province
        values[u'报送年度']=self.nianbaotitle
        json_nianbaojiben=json.dumps(values,ensure_ascii=False)
        print '-.-json_nianbaojiben',json_nianbaojiben

    def load_nianbaoweb (self,table_element):
        table_num = table_element
        source= self.driver.find_elements_by_id("qufenkuang")[0]
        html=source.get_attribute('outerHTML')
        Soup = BeautifulSoup(html,'html.parser')
#             print Soup

        table_detail=Soup.find_all('table')[table_num]
        if table_detail.find_all("tr")[2].text.strip() != '':
            th_element_list = table_detail.find_all("tr")[1].find_all("th")
            tr_element_list = table_detail.find_all("tr")[2:-1]
            jsonarray = []
            values = {}
            for tr_element in tr_element_list:
                if tr_element.text.strip() !='':
                    td_element_list = tr_element.find_all('td')
                    col_nums = len(th_element_list)
                    for i in range(col_nums):
                        th = th_element_list[i].text.strip().replace('\n','')
                        td = td_element_list[i]
                        val = td.text.strip()
                        values[th] = val
        #                     print th,val
                    values[u'注册号']=self.cur_code
                    values[u'企业名称']=self.org_name
                    values[u'报送年度']=self.nianbaotitle
                    jsonarray.append(values)
                    values = {}

            json_nianbaoweb=json.dumps(jsonarray,ensure_ascii=False)
            print '-.-json_nianbaoweb',json_nianbaoweb

    def load_nianbaogudong (self,table_element):
        table_num = table_element
        source= self.driver.find_elements_by_id("qufenkuang")[0]
        html=source.get_attribute('outerHTML')
        Soup = BeautifulSoup(html,'html.parser')
#             print Soup
        table_detail=Soup.find_all('table')[table_num]

        th_element_list = table_detail.find_all("tr")[1].find_all("th")
        tr_element_list = table_detail.find_all("tr")[2:-1]
        if table_detail.find_all("tr")[2].text.strip() !='':
            jsonarray = []
            values = {}
            for tr_element in tr_element_list:
                if tr_element.text.strip()!='':
                    td_element_list = tr_element.find_all('td')
                    col_nums = len(th_element_list)
                    for i in range(col_nums):
                        th = th_element_list[i].text.strip().replace('\n','')
                        td = td_element_list[i]
                        val = td.text.strip()
                        values[th] = val
        #                     print th,val
                    values[u'注册号']=self.cur_code
                    values[u'企业名称']=self.org_name
                    values[u'报送年度']=self.nianbaotitle
                    jsonarray.append(values)
                    values = {}

            json_nianbaogudong=json.dumps(jsonarray,ensure_ascii=False)
            print '-.-json_nianbaogudong',json_nianbaogudong
        
    def load_nianbaoduiwaitouzi(self,table_element):
        table_num = table_element
        source= self.driver.find_elements_by_id("qufenkuang")[0]
        html=source.get_attribute('outerHTML')
        Soup = BeautifulSoup(html,'html.parser')
#             print Soup
        table_detail=Soup.find_all('table')[table_num]

        th_element_list = table_detail.find_all("tr")[1].find_all("th")
        tr_element_list = table_detail.find_all("tr")[2:-1]
        if table_detail.find_all("tr")[2].text.strip() !='':
            jsonarray = []
            values = {}
            for tr_element in tr_element_list:
                if tr_element.text.strip()!='':
                    td_element_list = tr_element.find_all('td')
                    col_nums = len(th_element_list)
                    for i in range(col_nums):
                        th = th_element_list[i].text.strip().replace('\n','')
                        td = td_element_list[i]
                        val = td.text.strip()
                        values[th] = val
        #                     print th,val
                    values[u'注册号']=self.cur_code
                    values[u'企业名称']=self.org_name
                    values[u'报送年度']=self.nianbaotitle
                    jsonarray.append(values)
                    values = {}

            json_nianbaoduiwaitouzi=json.dumps(jsonarray,ensure_ascii=False)
            print '-.-json_nianbaoduiwaitouzi',json_nianbaoduiwaitouzi

    def load_nianbaozichan(self,table_element):
        table_num = table_element
#         nianbaozichan_template = TableTemplate('AR_Asset', u'企业资产状况信息')
#         nianbaozichan_template.column_dict = {
#             u'注册号': 'RegistrationNo',
#             u'资产总额': 'AR_TotalAsset',
#             u'营业总收入': 'AR_Revenue',
#             u'营业总收入中主营业务收入':'AR_PrimeOperatingRevenue',
#             u'纳税总额':'AR_TotalTax',
#             u'所有者权益合计':'AR_Equity',
#             u'利润总额':'AR_TotalProfit',
#             u'净利润':'AR_NetProfit',
#             u'负债总额':'AR_ GrossLiabilities'
#         }
        source= self.driver.find_elements_by_id("qufenkuang")[0]
        html=source.get_attribute('outerHTML')
        Soup = BeautifulSoup(html,'html.parser')
        table_detail=Soup.find_all('table')[table_num]
        tr_element_list = table_detail.find_all("tr")[1:]
        values = {}
        for tr_element in tr_element_list:
            th_element_list = tr_element.find_all('th')
            td_element_list = tr_element.find_all('td')
            if len(th_element_list) == len(td_element_list):
                col_nums = len(th_element_list)
                for i in range(col_nums):
                    col = th_element_list[i].get_text().strip().replace('\n','')
                    val = td_element_list[i].get_text().strip().replace('\n','')
                    if col != u'':
                        values[col] = val
#                     print col,val
        values[u'注册号']=self.cur_code
        values[u'省份']=self.province
        values[u'报送年度']=self.nianbaotitle
        json_nianbaozichan=json.dumps(values,ensure_ascii=False)
        print '-.-json_nianbaozichan',json_nianbaozichan

    def load_nianbaodanbao(self,table_element):
        table_num = table_element
        source= self.driver.find_elements_by_id("qufenkuang")[0]
        html=source.get_attribute('outerHTML')
        Soup = BeautifulSoup(html,'html.parser')
#             print Soup
        table_detail=Soup.find_all('table')[table_num]

        th_element_list = table_detail.find_all("tr")[1].find_all("th")
        tr_element_list = table_detail.find_all("tr")[2:-1]
        if table_detail.find_all("tr")[2].text.strip() !='':

            jsonarray = []
            values = {}
            for tr_element in tr_element_list:
                if tr_element.text.strip()!='':
                    td_element_list = tr_element.find_all('td')
                    col_nums = len(th_element_list)
                    for i in range(col_nums):
                        th = th_element_list[i].text.strip().replace('\n','')
                        td = td_element_list[i]
                        val = td.text.strip()
                        values[th] = val
        #                     print th,val
                    values[u'注册号']=self.cur_code
                    values[u'企业名称']=self.org_name
                    values[u'报送年度']=self.nianbaotitle
                    jsonarray.append(values)
                    values = {}

            json_nianbaodanbao=json.dumps(jsonarray,ensure_ascii=False)
            print '-.-json_nianbaodanbao',json_nianbaodanbao

    def load_nianbaoguquanbiangeng (self,table_element):
        table_num = table_element
        source= self.driver.find_elements_by_id("qufenkuang")[0]
        html=source.get_attribute('outerHTML')
        Soup = BeautifulSoup(html,'html.parser')
#             print Soup
        table_detail=Soup.find_all('table')[table_num]

        th_element_list = table_detail.find_all("tr")[1].find_all("th")
        tr_element_list = table_detail.find_all("tr")[2:-1]
        if table_detail.find_all("tr")[2].text.strip() !='':
            jsonarray = []
            values = {}
            for tr_element in tr_element_list:
                if tr_element.text.strip()!='':
                    td_element_list = tr_element.find_all('td')
                    col_nums = len(th_element_list)
                    for i in range(col_nums):
                        th = th_element_list[i].text.strip().replace('\n','')
                        td = td_element_list[i]
                        val = td.text.strip()
                        values[th] = val
        #                     print th,val
                    values[u'注册号']=self.cur_code
                    values[u'企业名称']=self.org_name
                    values[u'报送年度']=self.nianbaotitle
                    jsonarray.append(values)
                    values = {}

            json_nianbaoguquanbiangeng=json.dumps(jsonarray,ensure_ascii=False)
            print '-.-json_nianbaoguquanbiangeng',json_nianbaoguquanbiangeng

    def load_nianbaoxiugai(self,table_element):
        if self.driver.find_element_by_xpath(".//*[@id='altYearExamineTab']/tbody/tr[3]").text.strip()!='':
            try:
                for tro in self.driver.find_elements_by_xpath(".//*[@id='altYearExamineTab']/tbody/tr")[2:-1]:
                    for tda in tro.find_elements_by_xpath('td'):
                        if u'更多' in tda.text.strip():
                            tda.find_element_by_xpath('a').click()
            except:
                pass

        source= self.driver.find_elements_by_id("qufenkuang")[1]
        html=source.get_attribute('outerHTML')
        Soup = BeautifulSoup(html,'html.parser')
#             print Soup
        table_detail=Soup.find_all('table')[0]

        th_element_list = table_detail.find_all("tr")[1].find_all("th")
        tr_element_list = table_detail.find_all("tr")[2:-1]
        if table_detail.find_all("tr")[2].text.strip() !='':
            jsonarray = []
            values = {}
            for tr_element in tr_element_list:
                if tr_element.text.strip()!='':
                    td_element_list = tr_element.find_all('td')
                    col_nums = len(th_element_list)
                    for i in range(col_nums):
                        th = th_element_list[i].text.strip().replace('\n','')
                        td = td_element_list[i]
                        val = td.text.strip().strip(u'收起更多')
                        values[th] = val
        #                     print th,val
                    values[u'注册号']=self.cur_code
                    values[u'企业名称']=self.org_name
                    values[u'报送年度']=self.nianbaotitle
                    jsonarray.append(values)
                    values = {}

            json_nianbaoxiugai=json.dumps(jsonarray,ensure_ascii=False)
            print '-.-json_nianbaoxiugai',json_nianbaoxiugai
    def driverclose(self):
        self.driver.close()


if __name__ == '__main__':

    code_list = [u'安徽湧崟电子科技有限公司']#合肥圣泰房地产开发有限公司']#淮南矿务局大华商贸公司供销经理部']#合肥圣泰房地产开发有限公司 #东方富海（芜湖）股权投资基金（有限合伙）']#皖西银河房地产开发有限责任公司']#合肥伟晖乐贸易有限责任公司']#六安市晖润新材料有限公司'] #中国石化销售安庆公司']#u"云道股份有限公司",u'京仪股份有限公司']
    # code_list = [u'马鞍山威泰机电有限公司']
    searcher = AnhuiFirefoxSearcher()
    searcher.set_config()

    if searcher.build_driver() == 0:
        for name in code_list:
            searcher.search(name)
            # break
        # searcher.driverclose()

