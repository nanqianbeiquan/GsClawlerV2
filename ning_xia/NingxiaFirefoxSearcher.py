# coding=gbk
from template.DBClient import database_client_cursor
from template.DBClient import database_client_newcursor
from template.FirefoxSearcher import FirefoxSearcher
from selenium import common
import template.SysConfig as SysConfig
import sys
import os
import re
import hashlib
import requests
from template.UnknownTableException import UnknownTableException
from template.UnknownColumnException import UnknownColumnException
from template.Tables import *
from template.Tables_dict import  *
from template.DataModel import DataModel
from bs4 import BeautifulSoup
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from template.logger import *
import traceback
from selenium import webdriver
import json
from json.decoder import JSONArray


class NingXiaFirefoxSearcher(FirefoxSearcher):

    def __init__(self):
        super(NingXiaFirefoxSearcher, self).__init__()
        # 宁夏抽查检查信息缺少备注列
        chouchajiancha_template.column_list.pop()
        self.start_page_handle_bak = None
        self.detail_page_handle = None
        self.search_model = None
        self.result_model = None
        self.headers = {
            # 'Accept-Encoding':'gzip, deflate',
            'User-Agent':'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0'
            }

    # 配置页面元素xpath与浏览器插件
    def set_config(self):
        self.start_url = 'http://gsxt.ngsh.gov.cn/ECPS/index.jsp'
        self.code_input_box_xpath = ".//input[@id='selectValue']"
        self.code_submit_button_xpath = '/html/body/form/div[3]/div/div[2]/div/div[2]/div[2]/a'
        self.validate_image_xpath = ".//img[@id='verificationCode1']"
        self.validate_input_box_xpath = '/html/body/div[2]/div/div/ul/li[3]/div[2]/input'
        self.validate_submit_button_xpath = '/html/body/div[2]/div/div/ul/li[4]/a'
        self.tab_list_xpath = '/html/body/div[2]/div[2]/div/div[1]/ul/li'
        self.plugin_path = os.path.join(sys.path[0], r'..\ocr\ningxia.bat')
        self.province = u'宁夏回族自治区'

    def authCode(self):
        appkey = "40743729"
        secret = "c1aeb971a2379d5123c8b3392fcb69c6"
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

    def build_driver(self):
        build_result = 0
        driveraddress=os.path.join("C:\Python27\Scripts\phantomjs.exe")#os.getcwd()+\\phantomjs\\bin\\phantomjs.exe')
        print 'address**',driveraddress
        auth = self.authCode()
        dcap = dict(webdriver.DesiredCapabilities.PHANTOMJS)
        dcap["phantomjs.page.settings.userAgent"] = ('Mozilla/5.0 (Windows NT 6.3; WOW64; rv:43.0) Gecko/20100101 Firefox/43.0')
        dcap["phantomjs.page.customHeaders.Proxy-Authorization"] = (auth)
        args = ['--proxy=123.56.251.212:8123']#'--load-images=false', '--disk-cache=true',
        self.driver = webdriver.PhantomJS(executable_path=driveraddress, service_args=args, desired_capabilities=dcap)
        # profile = webdriver.FirefoxProfile(SysConfig.get_firefox_profile_path())
        # self.driver = webdriver.Firefox(firefox_profile=profile)
        # self.driver = webdriver.PhantomJS()
        self.driver.set_window_size(1920,1080)
        self.set_timeout_config()
        for i in xrange(SysConfig.max_try_times):
            if self.wait_for_load_start_url():
                break
            else:
                if i == SysConfig.max_try_times:
                    build_result = 1
        return build_result

    # 查询名称
    def search(self, name):
        self.cur_name = name
        self.search_model = DataModel(name, self.province)
        try:
            if not self.get_ip_status():
                # IP被禁，update_status：4
                self.search_model.set_update_status(4)
            else:
                self.submit_search_request()
                self.get_search_result()
                if self.search_model.update_status == 1:
                    result_list = self.driver.find_elements_by_xpath("/html/body/form/div/div/dl/div")
                    for result in result_list:
                        self.driver.execute_script("arguments[0].style=''", result)
                        org_name = result.find_element_by_xpath("dt/a").text
                        self.org_name = org_name
                        self.tagA = result.find_element_by_xpath("dt/a").get_attribute('href')
                        self.cur_code = result.find_element_by_xpath("dd/span").text
                        self.title = result.find_element_by_xpath("dt/a").get_attribute('outerHTML')
                        try:
                            print org_name, self.cur_code,self.tagA,self.title
                        except:
                            print u'公司名称编码异常'
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
                            result.find_element_by_xpath("dt/a").click()
                            self.detail_page_handle = self.driver.window_handles[-1]
                            self.driver.switch_to.window(self.detail_page_handle)
                            try:
                                # self.parse_detail_page()
                                self.parse_lefttabs()
                            except (UnknownTableException, UnknownColumnException):
                                # 未知表名或列名，update_status：8
                                self.result_model.set_update_status(8)
                            print "*******************************************"+self.driver.current_window_handle
                            self.driver.close()

                            self.driver.switch_to.window(self.start_page_handle)
                            if self.search_model.name == self.result_model.name:
                                self.search_model.set_code(self.cur_code)
                                self.search_model.set_tagA(self.tagA)
                                self.search_model.set_codeS(self.cur_code)
                            else:
                                sql_2 = "update GsSrc_64_3 set %s where mc='%s'" % (self.result_model, self.result_model.name)
                                database_client_newcursor.execute(sql_2)
                                sql_3 = "select @@rowcount"
                                database_client_newcursor.execute(sql_3)
                                res_3 = database_client_newcursor.fetchone()
                                if int(res_3[0]) == 0:
                                    sql_4 = "insert into GsSrc_64_3(%s) values(%s)" % (self.result_model.get_cols(), self.result_model.get_vals())
                                    database_client_newcursor.execute(sql_4)
        except Exception:
            # 未知异常，update_status：3
            traceback.print_exc()
            self.search_model.set_update_status(3)
        self.switch_to_search_page()
        return self.search_model

    def switch_to_search_page(self):
        for handle in self.driver.window_handles:
            if handle != self.start_page_handle_bak:
                self.driver.switch_to.window(handle)
                self.driver.close()
        if self.start_page_handle_bak:
            self.driver.switch_to.window(self.start_page_handle_bak)
            self.start_page_handle = self.start_page_handle_bak
        else:
            self.build_driver()

    def switch_to_result_page(self):
        pass

    def parse_detail_page(self):
        self.tab_list = self.driver.find_elements_by_xpath(self.tab_list_xpath)
        for tab in self.tab_list:
            tab_text = tab.text
            # print 'tab_text',tab_text
            logging.info(u"解析%s ..." % tab_text)
            if tab.get_attribute('class') != 'current':
                tab.click()
                # time.sleep(2)
            self.load_func_dict[tab_text]()
            logging.info(u"解析%s成功" % tab_text)
            self.driver.switch_to.default_content()

    def get_search_result(self):
        if not self.get_ip_status():
            return 4
        search_result = self.driver.find_element_by_xpath('/html/body/form/div/div/dl')
        result_text = search_result.text.strip()
        if result_text == '':
            logging.info(u'查询结果0条')
            self.search_model.set_update_status(0)
        else:
            self.search_model.set_update_status(1)

    # 提交查询请求
    def submit_search_request(self):
        i = 0
        self.start_page_handle_bak = None
        print 'round','***'
        # if i>0:
        #     # self.driver.back()
        #     # self.driver.get(self.start_url)
        #     self.driver.find_element_by_xpath(".//*[@id='initQyxyxxMain']/div/div/div[1]/div/a[2]").click()
        #     time.sleep(1)
        # i+=1
        self.code_input_box = self.driver.find_element_by_xpath(self.code_input_box_xpath)
        time.sleep(1)
        try:
            self.code_submit_button = self.driver.find_element_by_xpath(self.code_submit_button_xpath)
        except:
            self.driver.find_element_by_xpath(".//*[@id='initQyxyxxMain']/div/div/div[1]/div/a[2]").click()
            time.sleep(1)
            self.code_input_box = self.driver.find_element_by_xpath(self.code_input_box_xpath)
            self.code_submit_button = self.driver.find_element_by_xpath(self.code_submit_button_xpath)
        self.code_input_box.clear()  # 清空输入框
        print 'before',self.cur_name
        self.code_input_box.send_keys(self.cur_name)  # 输入查询代码
        ActionChains(self.driver).key_down(Keys.SHIFT).perform()
        self.code_submit_button.click()
        ActionChains(self.driver).key_up(Keys.SHIFT).perform()
        time.sleep(1)
        self.start_page_handle_bak = self.driver.window_handles[-1]
        self.validate_image = self.driver.find_element_by_xpath(self.validate_image_xpath)  # 定位验证码图片
        self.validate_input_box = self.driver.find_element_by_xpath(self.validate_input_box_xpath)  # 定位验证码输入框
        self.validate_submit_button = self.driver.find_element_by_xpath(self.validate_submit_button_xpath)  # 定位验证码提交按钮
        validate_image_save_path = SysConfig.get_validate_image_save_path()  # 获取验证码保存路径
        for i in range(SysConfig.max_try_times):
            try:
                self.validate_image = self.driver.find_element_by_xpath(self.validate_image_xpath)  # 定位验证码图片
                self.download_validate_image(self.validate_image, validate_image_save_path)  # 截图获取验证码
                validate_code = self.recognize_validate_code(validate_image_save_path)  # 识别验证码
                self.validate_input_box.clear()  # 清空验证码输入框
                self.validate_input_box.send_keys(validate_code)  # 输入验证码
                self.validate_submit_button.click()  # 点击搜索（验证码弹窗）
                # self.driver.switch_to.alert.accept()
                if "none" in self.find_element("//div [@id='zmdid']").get_attribute('style'):
                    break
                time.sleep(1)
            except:
                pass
        logging.info(u"提交查询请求成功")


    # 判断IP是否被禁
    def get_ip_status(self):
        body_text = self.driver.find_element_by_xpath("/html/body").text
        if body_text.startswith(u'您的访问过于频繁'):
            return False
        else:
            return True

    # 判断搜索起始页是否加载成功 {0:成功, 1:失败}
    def wait_for_load_start_url(self):
        load_result = True
        try:
            self.driver.get(self.start_url)
            self.start_page_handle = self.driver.current_window_handle
        except common.exceptions.TimeoutException:
            pass
        return load_result

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
                # self.load_qiyegongshi()
                pass

    def load_qiyegongshi(self):
        time.sleep(3)

        jsonarray=[]
        iframe = self.driver.find_element_by_xpath(".//*[@id='qynb']/iframe")
        self.driver.switch_to.frame(iframe)
        report_tr_list = self.find_elements("html/body/table/tbody/tr")
        # for i in report_tr_list:
        #     print '******qynb******',i.text
        if len(report_tr_list)>2:
            i=1
            self.nowhandles=self.driver.current_window_handle
            for tr_element in report_tr_list[2:]:
                td_element_list=tr_element.find_elements_by_xpath("td")
                # for l in td_element_list:
                #     print 'l',l.text
                values = []
                json_dict = {}
                j=1
                for td in td_element_list:
                    val = td.text.strip()
                    print 'val', val
                    if u'报告' in val:
                        values.append(val)
                        values.append(td.find_element_by_xpath("a").get_attribute('href'))
                        nianbao_href = td.find_element_by_xpath("a").get_attribute('href')
                        # print 'nianbao_href',nianbao_href
                        self.nianbaotitle=val

                        ActionChains(self.driver).key_down(Keys.SHIFT).perform()
                        td.find_element_by_xpath("a").click()
                        ActionChains(self.driver).key_up(Keys.SHIFT).perform()
                        time.sleep(5)
                        # print '11111',self.driver.window_handles
                        self.driver.switch_to.window(self.driver.window_handles[-1])
                        self.load_nianbaodetail()
                        self.driver.close()
                        # print '22222',self.driver.window_handles
                        self.driver.switch_to.window(self.nowhandles)
                        # self.driver.switch_to.default_content()
                        self.driver.switch_to.frame(iframe)

                    else:
                        values.append(val)
                    # print 'valuelens',len(values)
                    j += 1
                i += 1
                json_dict[qiyenianbao_column_list[u'序号']]=values[0]
                json_dict[qiyenianbao_column_list[u'报送年度']]=values[1]
                json_dict[qiyenianbao_column_list[u'链接地址']]=values[2]
                json_dict[qiyenianbao_column_list[u'发布日期']]=values[3]
                jsonarray.append(json_dict)
            json_nianbao = json.dumps(jsonarray,ensure_ascii=False)
            print 'json_nianbao',json_nianbao

    def load_nianbaodetail(self):
        table_iframe_list = self.driver.find_element_by_xpath(".//*[@id='jibenxinxi']/iframe")
        table_iframe_list1 = self.driver.find_elements_by_xpath(".//*[@id='jibenxinxi']/following-sibling::*")
        table_iframe_list2 = self.driver.find_element_by_xpath(".//*[@id='xiugaijilu']/iframe")

        jiben_href = table_iframe_list.get_attribute('src')
        print 'nianbaosrc',table_iframe_list.get_attribute('src')
        jibengo = self.quest_getout(jiben_href,self.headers)
        jibengobs = self.beaut_souping(jibengo)
        self.load_nianbaojiben(jibengobs)

        for i in table_iframe_list1:
            details_id = i.get_attribute('id')
            details_href = i.find_element_by_xpath('iframe').get_attribute('src')
            # print 'nianbao1src',i.find_element_by_xpath('iframe').get_attribute('src')
            # print 'details_id**',details_id
            if details_id == 'wanzhanxinxi':
                jibengo = self.quest_getout(details_href,self.headers)
                jibengobs = self.beaut_souping(jibengo)
                self.load_nianbaoweb(jibengobs)
            elif details_id == 'touzirenxinxi':
                jibengo = self.quest_getout(details_href,self.headers)
                jibengobs = self.beaut_souping(jibengo)
                self.load_nianbaogudong(jibengobs)
            elif details_id == 'duiwaixinxi':
                jibengo = self.quest_getout(details_href,self.headers)
                jibengobs = self.beaut_souping(jibengo)
                self.load_nianbaoduiwaitouzi(jibengobs)
            elif details_id == 'qiyezichanxinxi':
                jibengo = self.quest_getout(details_href,self.headers)
                jibengobs = self.beaut_souping(jibengo)
                self.load_nianbaozichan(jibengobs)
            elif details_id == 'danbaoxinxi':
                jibengo = self.quest_getout(details_href,self.headers)
                jibengobs = self.beaut_souping(jibengo)
                self.load_nianbaodanbao(jibengobs)
            elif details_id == 'guquanxinxi':
                jibengo = self.quest_getout(details_href,self.headers)
                jibengobs = self.beaut_souping(jibengo)
                self.load_nianbaoguquanbiangeng(jibengobs)
            else:
                print 'LETs SEE WHAT COME OUT',details_id
        xiugai_href = table_iframe_list2.get_attribute('src')
        print 'nianbao2src',table_iframe_list2.get_attribute('src')
        jibengo = self.quest_getout(xiugai_href,self.headers)
        jibengobs = self.beaut_souping(jibengo)
        self.load_nianbaoxiugai(jibengobs)

    # 加载登记信息
    def load_dengji(self):
        table_iframe_list = self.driver.find_elements_by_xpath(".//div[@id='jibenxinxi']/iframe")
        for table_iframe in table_iframe_list:
            self.driver.switch_to.frame(table_iframe)
            table_element_list = self.driver.find_elements_by_xpath("/html/body/table")
            table_element = table_element_list[0]
            table_desc_element = table_element.find_element_by_xpath("tbody/tr/th")
            table_desc = table_desc_element.text.split('\n')[0].strip()
            if table_desc not in self.load_func_dict:
                raise UnknownTableException(self.cur_code,self.org_name, table_desc)
            logging.info(u"解析%s ..." % table_desc)
            self.load_func_dict[table_desc](table_iframe)
            self.driver.switch_to.default_content()
            logging.info(u"解析%s成功" % table_desc)

    # 加载基本信息
    def load_jiben(self, table_iframe):
        jiben_template.delete_from_database(self.cur_code,self.org_name)
        table_element = self.driver.find_element_by_xpath("/html/body/table[1]")
        tr_element_list = table_element.find_elements_by_xpath('tbody/tr')
        values = {}
        for tr_element in tr_element_list[1:]:
            th_element_list = tr_element.find_elements_by_xpath('th')
            td_element_list = tr_element.find_elements_by_xpath('td')
            if len(th_element_list) == len(td_element_list):
                col_nums = len(th_element_list)
                for i in range(col_nums):
                    col = th_element_list[i].text.strip()
                    val = td_element_list[i].text.strip()
                    if col != u'':
                        values[col] = val
        json_jiben = json.dumps(values,ensure_ascii=False)
        # print 'json_jiben',json_jiben
        jiben_template.insert_into_database(self.cur_code,self.org_name, values)

    # 加载股东信息
    def load_gudong(self, table_iframe):

        gudong_template.column_list = [ 'Shareholder_Type', 'Shareholder_Name','Shareholder_CertificationType', 'Shareholder_CertificationNo', 'Shareholder_Details',
                               'Subscripted_Capital', 'ActualPaid_Capital', 'Subscripted_Method', 'Subscripted_Amount', 'Subscripted_Time', 'ActualPaid_Method',
                               'ActualPaid_Amount', 'ActualPaid_Time']
        jsonarray = []
        table_element = self.driver.find_element_by_xpath("/html/body/table[1]")
        gudong_template.delete_from_database(self.cur_code,self.org_name)
        if len(table_element.find_elements_by_xpath("tbody/tr")) > 2:
            last_index_element = self.driver.find_element_by_xpath('/html/body/table[2]/tbody/tr/th/a[last()-1]')
            index_element_list_length = int(last_index_element.text.strip())
            for i in range(index_element_list_length):
                if i > 0:
                    index_element = self.driver.find_element_by_xpath('/html/body/table[2]/tbody/tr/th/a[%d]' % (i+1))
                    index_element.click()
                    table_element = self.driver.find_element_by_xpath("/html/body/table[1]")
                tr_element_list = table_element.find_elements_by_xpath('tbody/tr')
                for tr_element in tr_element_list[2:]:
                    td_element_list = tr_element.find_elements_by_xpath('td')
                    values = []
                    json_dict = {}
                    for td in td_element_list:
                        val = td.text.strip()
                        if val == u'详情':
                            values.append(td.find_element_by_xpath('a').get_attribute('href'))
                            td.find_element_by_xpath('a').click()
                            values.extend(self.load_gudong_detail())
                            self.driver.switch_to.frame(table_iframe)
                        else:
                            values.append(val)
                    values.extend((len(gudong_template.column_list) - len(values))*[''])
                    for n,th in enumerate(gudong_template.column_list):
                        json_dict[th] = values[n]
                    jsonarray.append(json_dict)
            # json_gudong = json.dumps(jsonarray,ensure_ascii=False)
            # print 'json_gudong',json_gudong

                    gudong_template.insert_into_database(self.cur_code, self.org_name, values)

    def load_gudong_detail(self):
        self.driver.switch_to.window(self.driver.window_handles[-1])
        td_element_list = self.driver.find_elements_by_xpath("/html/body/div[2]/div/table/tbody/tr[4]/td")
        values = []
        for td in td_element_list[1:]:
            values.append(td.text.strip())
        self.driver.close()
        self.driver.switch_to.window(self.detail_page_handle)
        return values

    # 加载变更信息
    def load_biangeng(self, table_iframe):
        biangeng_template.delete_from_database(self.cur_code,self.org_name)
        table_element = self.driver.find_element_by_xpath("/html/body/table[1]")
        jsonarray = []
        if len(table_element.find_elements_by_xpath("tbody/tr")) > 2:
            last_index_element = self.driver.find_element_by_xpath('/html/body/table[2]/tbody/tr/th/a[last()-1]')
            index_element_list_length = int(last_index_element.text.strip())
            for i in range(index_element_list_length):
                if i > 0:
                    index_element = self.driver.find_element_by_xpath('/html/body/table[2]/tbody/tr/th/a[%d]' % (i+1))
                    index_element.click()
                    table_element = self.driver.find_element_by_xpath("/html/body/table[1]")
                tr_element_list = table_element.find_elements_by_xpath('tbody/tr')
                for tr_element in tr_element_list[2:]:
                    td_element_list = tr_element.find_elements_by_xpath('td')
                    values = []
                    json_dict = {}
                    for td in td_element_list:
                        val = td.text.strip()
                        if val.endswith(u'更多'):
                            td.find_element_by_xpath('div/a').click()
                        val = td.text.strip()
                        values.append(val[:-4].strip())
                    for n,th in enumerate(biangeng_template.column_list):
                        json_dict[th]=values[n]
                    jsonarray.append(json_dict)
            # json_biangeng = json.dumps(jsonarray,ensure_ascii=False)
            # print 'json_biangeng',json_biangeng

                    biangeng_template.insert_into_database(self.cur_code, self.org_name,values)
        self.driver.switch_to.default_content()

    def quest_getout(self,url,headers): #requests,可接headers
        # print url
        r = requests.get(url,headers=headers)
        # r = requests.get(url,headers)
        # print r.encoding
        # r.encoding = 'gbk'  #u'乱码情况使用'
        return r.text

    def beaut_souping(self,thn):  # Beautifulsoup处理网页文本,有乱码情况
        mat = thn
        bs = BeautifulSoup(mat,'html5lib')
        return bs

    # 加载变更信息
    def load_beian(self):
        # table_iframe_list = self.driver.find_elements_by_xpath(".//div[@id='beian']/iframe")
        # # print 'HTML',table_iframe_list[0].get_attribute('outerHTML')
        # table_iframe1 = self.driver.find_elements_by_xpath(".//div[@id='beian']/iframe")
        self.driver.get_screenshot_as_file('E:\\ningxiaswb.png')
        for table_iframe in self.driver.find_elements_by_xpath(".//div[@id='beian']/iframe"):#table_iframe_list:
            block_href = table_iframe.get_attribute('src')
            # print u'备案信息href',table_iframe.get_attribute('src')#table_iframe.text,table_iframe.get_attribute('id')
            block = self.quest_getout(block_href,self.headers)
            blockbs = self.beaut_souping(block)#.decode('utf-8').encode('gbk')
            # print 'blockbs',blockbs.decode('utf-8').encode('gbk')
            trIF = blockbs.find_all('table')[0].find_all('tr')
            if len(trIF)>2:
                table_desc = trIF[0].th.text.split('\n')[0].strip()
                if table_desc != u'清算信息':
                    print '**table_desc**',table_desc
                    self.load_func_dict[table_desc](blockbs)

            # time.sleep(3)
            # self.driver.execute_async_script()
            # self.driver.switch_to.frame(table_iframe)
            # # self.driver.switch_to_active_element()
            # table_element_list = self.driver.find_elements_by_xpath("/html/body/table")
            # table_element = table_element_list[0]
            # table_desc_element = table_element.find_element_by_xpath("tbody/tr/th")
            # table_desc = table_desc_element.text.split('\n')[0].strip()
            # print '**table_beian_desc**',table_desc
            # if table_desc not in self.load_func_dict:
            #     raise UnknownTableException(self.cur_code, table_desc)
            # logging.info(u"解析%s ..." % table_desc)
            # self.load_func_dict[table_desc](table_iframe)
            # self.driver.switch_to.default_content()
            # logging.info(u"解析%s成功" % table_desc)

    def load_touziren(self):
        pass

    # 加载主要人员信息
    def load_zhuyaorenyuan(self, blockbs):
        zhuyaorenyuan_template.delete_from_database(self.cur_code,self.org_name)
        # table_element = self.driver.find_element_by_xpath("/html/body/table[1]")
        jsonarray = []
        tr_element_list = blockbs.find_all('table')[0].find_all('tr')
        # if len(table_element.find_elements_by_xpath("tbody/tr")) > 2:
        #     last_index_element = self.driver.find_element_by_xpath('/html/body/table[2]/tbody/tr/th/a[last()-1]')
            # index_element_list_length = int(last_index_element.text.strip())
            # for i in range(index_element_list_length):
            #     if i > 0:
            #         index_element = self.driver.find_element_by_xpath('/html/body/table[2]/tbody/tr/th/a[%d]' % (i+1))
            #         index_element.click()
            #         table_element = self.driver.find_element_by_xpath("/html/body/table[1]")
            #     tr_element_list = table_element.find_elements_by_xpath('tbody/tr')
        for tr_element in tr_element_list[2:]:
            values = []
            json_dict = {}
            td_element_list = tr_element.find_all('td')
            list_length = len(td_element_list)
            fixed_length = list_length - list_length % 3
            for i in range(fixed_length):
                val = td_element_list[i].text.strip()
                values.append(val)
                if len(values) == 3:
                    json_dict[zhuyaorenyuan_template.column_list[0]] = values[0]
                    json_dict[zhuyaorenyuan_template.column_list[1]] = values[1]
                    json_dict[zhuyaorenyuan_template.column_list[2]] = values[2]
                    zhuyaorenyuan_template.insert_into_database(self.cur_code, self.org_name, values)
                    jsonarray.append(json_dict)
                    values = []
                    json_dict = {}
        json_zhuyaorenyuan = json.dumps(jsonarray,ensure_ascii=False)
        # print 'json_zhuyaorenyuan',json_zhuyaorenyuan

    # 加载分支机构信息
    def load_fenzhijigou(self, blockbs):
        fenzhijigou_template.delete_from_database(self.cur_code,self.org_name)
        # table_element = self.driver.find_element_by_xpath("/html/body/table[1]")
        # if len(table_element.find_elements_by_xpath("tbody/tr")) > 2:
        #     last_index_element = self.driver.find_element_by_xpath('/html/body/table[2]/tbody/tr/th/a[last()-1]')
        #     index_element_list_length = int(last_index_element.text.strip())
        #     for i in range(index_element_list_length):
        #         if i > 0:
        #             index_element = self.driver.find_element_by_xpath('/html/body/table[2]/tbody/tr/th/a[%d]' % (i+1))
        #             index_element.click()
        #             table_element = self.driver.find_element_by_xpath("/html/body/table[1]")
        jsonarray = []
        tr_element_list = blockbs.find_all('table')[0].find_all('tr')
        # tr_element_list = table_element.find_elements_by_xpath('tbody/tr')
        for tr_element in tr_element_list[2:]:
            td_element_list = tr_element.find_all('td')
            values = []
            json_dict = {}
            for td in td_element_list:
                val = td.text.strip()
                values.append(val)
            fenzhijigou_template.insert_into_database(self.cur_code,self.org_name,values)
            for n,th in enumerate(fenzhijigou_template.column_list):
                json_dict[th] = values[n]
            jsonarray.append(json_dict)
        json_fenzhijigou = json.dumps(jsonarray,ensure_ascii=False)
        # print 'json_fenzhijigou',json_fenzhijigou


    # 加载清算信息
    def load_qingsuan(self, table_iframe):
        # table_element = self.driver.find_element_by_xpath("/html/body/table[1]")
        # val_1 = table_element.find_element_by_xpath('tbody/tr[2]/td').text.strip()
        # val_2 = table_element.find_element_by_xpath('tbody/tr[3]/td').text.strip()
        # values = [val_1, val_2]
        # if len(values[0]) != 0 or len(values[1]) != 0:
        #     qingsuan_template.delete_from_database(self.cur_code)
        #     qingsuan_template.insert_into_database(self.cur_code, values)
        pass

    # 加载动产抵押信息
    def load_dongchandiyadengji(self):

        # print 'dfasdfsadfasdf',self.driver.page_source
        # print 'ffffddd',self.driver.find_element_by_xpath('/html/body/table[2]').text
        table_iframe = self.driver.find_element_by_xpath(".//div[@id='dcdy']/iframe[@id='dcdyxx']")
        table_iframe_list = self.driver.find_elements_by_xpath(".//div[@id='dcdy']/iframe")
        for table_iframe in table_iframe_list:
            block_href = table_iframe.get_attribute('src')
            # print u'动产抵押href',table_iframe.get_attribute('src')
            block = self.quest_getout(block_href,self.headers)
            blockbs = self.beaut_souping(block)#.decode('utf-8').encode('gbk')
            trIF = blockbs.find_all('table')[0].find_all('tr')
            if len(trIF)>2:
                dongchandiyadengji_template.delete_from_database(self.cur_code,self.org_name)
                jsonarray = []
                tr_element_list = blockbs.find_all('table')[0].find_all('tr')
        # self.driver.switch_to.frame(table_iframe)
        # time.sleep(5)
        #
        # table_element_list = self.driver.find_elements_by_xpath("/html/body/table")
        # for t in table_element_list:
        #     print 'tableelement',t.text
        # table_element = table_element_list[0]
        # row_cnt = len(table_element.find_elements_by_xpath("tbody/tr"))
        # for i in table_element.find_elements_by_xpath("tbody/tr"):
        #     print '969696',i.text
        # print 'row_cnt' , row_cnt
        # if row_cnt > 2:
        #     print self.driver.current_window_handle
        #     self.driver.get_screenshot_as_file('E:\\ningxiasb.png')
        #     last_index_element = self.driver.find_element_by_xpath('/html/body/table[2]/tbody/tr/th/a[last()-1]')
        #     index_element_list_length = int(last_index_element.text.strip())
        #     for i in range(index_element_list_length):
        #         if i > 0:
        #             index_element = self.driver.find_element_by_xpath('/html/body/table[2]/tbody/tr/th/a[%d]' % (i+1))
        #             index_element.click()
        #             table_element = self.driver.find_element_by_xpath("/html/body/table[1]")
        #         tr_element_list = table_element.find_elements_by_xpath('tbody/tr')
                for tr_element in tr_element_list[2:]:
                    td_element_list = tr_element.find_all('td')
                    values = []
                    json_dict = {}
                    for td in td_element_list:
                        val = td.text.strip()
                        if val == u'详情':
                            values.append(td.find('a').get('href'))
                        else:
                            values.append(val)
                    for n,th in enumerate(dongchandiyadengji_template.column_list):
                        json_dict[th]=values[n]
                    jsonarray.append(json_dict)
                # json_dongchandiya = json.dumps(jsonarray,ensure_ascii=False)
                # print 'json_dongchandiya',json_dongchandiya
                    dongchandiyadengji_template.insert_into_database(self.cur_code,self.org_name, values)
        # self.driver.switch_to.default_content()

    # 加载股权出质登记信息
    def load_guquanchuzhidengji(self):

        table_iframe = self.driver.find_element_by_xpath(".//div[@id='guquanchuzhi']/iframe")
        table_iframe_list = self.driver.find_elements_by_xpath(".//div[@id='guquanchuzhi']/iframe")
        for table_iframe in table_iframe_list:
            block_href = table_iframe.get_attribute('src')
            # print u'股权出质href',table_iframe.get_attribute('src')
            block = self.quest_getout(block_href,self.headers)
            blockbs = self.beaut_souping(block)#.decode('utf-8').encode('gbk')
            trIF = blockbs.find_all('table')[0].find_all('tr')
            if len(trIF)>2:
                guquanchuzhidengji_template.delete_from_database(self.cur_code,self.org_name)
                jsonarray = []
                tr_element_list = blockbs.find_all('table')[0].find_all('tr')
        # self.driver.switch_to.frame(table_iframe)
        # table_element_list = self.driver.find_elements_by_xpath("/html/body/table")
        # table_element = table_element_list[0]
        # row_cnt = len(table_element.find_elements_by_xpath("tbody/tr"))
        # if row_cnt > 2:
        #     last_index_element = self.driver.find_element_by_xpath('/html/body/table[2]/tbody/tr/th/a[last()-1]')
        #     index_element_list_length = int(last_index_element.text.strip())
        #     for i in range(index_element_list_length):
        #         if i > 0:
        #             index_element = self.driver.find_element_by_xpath('/html/body/table[2]/tbody/tr/th/a[%d]' % (i+1))
        #             index_element.click()
        #             table_element = self.driver.find_element_by_xpath("/html/body/table[1]")
        #         tr_element_list = table_element.find_elements_by_xpath('tbody/tr')
                for tr_element in tr_element_list[2:]:
                    td_element_list = tr_element.find_all('td')
                    values = []
                    json_dict = {}
                    for td in td_element_list:
                        val = td.text.strip()
                        values.append(val)
                    for n,th in enumerate(guquanchuzhidengji_template.column_list):
                        json_dict[th] = values[n]
                    jsonarray.append(json_dict)
                # json_guquanchuzhi = json.dumps(jsonarray,ensure_ascii=False)
                # print 'json_guquanchuzhi',json_guquanchuzhi
                    guquanchuzhidengji_template.insert_into_database(self.cur_code,self.org_name, values)
        # self.driver.switch_to.default_content()

    # 加载行政处罚信息
    def load_xingzhengchufa(self):
        xingzhengchufa_template.column_list = ['Penalty_No', 'Penalty_Code', 'Penalty_IllegalType', 'Penalty_DecisionContent',
                                       'Penalty_DecisionInsititution', 'Penalty_DecisionDate','Penalty_PublicationDate', 'Penalty_Details']

        table_iframe = self.driver.find_element_by_xpath(".//div[@id='xingzhengchufa']/iframe")
        table_iframe_list = self.driver.find_elements_by_xpath(".//div[@id='xingzhengchufa']/iframe")
        for table_iframe in table_iframe_list:
            block_href = table_iframe.get_attribute('src')
            # print u'行政处罚href',table_iframe.get_attribute('src')
            block = self.quest_getout(block_href,self.headers)
            blockbs = self.beaut_souping(block)#.decode('utf-8').encode('gbk')
            trIF = blockbs.find_all('table')[0].find_all('tr')
            if len(trIF)>2:
                xingzhengchufa_template.delete_from_database(self.cur_code,self.org_name)
                jsonarray = []
                tr_element_list = blockbs.find_all('table')[0].find_all('tr')
        # self.driver.switch_to.frame(table_iframe)
        # table_element_list = self.driver.find_elements_by_xpath("/html/body/table")
        # table_element = table_element_list[0]
        # row_cnt = len(table_element.find_elements_by_xpath("tbody/tr"))
        # if row_cnt > 2:
        #     last_index_element = self.driver.find_element_by_xpath('/html/body/table[2]/tbody/tr/th/a[last()-1]')
        #     index_element_list_length = int(last_index_element.text.strip())
        #     for i in range(index_element_list_length):
        #         if i > 0:
        #             index_element = self.driver.find_element_by_xpath('/html/body/table[2]/tbody/tr/th/a[%d]' % (i+1))
        #             index_element.click()
        #             table_element = self.driver.find_element_by_xpath("/html/body/table[1]")
        #         tr_element_list = table_element.find_elements_by_xpath('tbody/tr')
                for tr_element in tr_element_list[2:]:
                    td_element_list = tr_element.find_all('td')
                    values = []
                    json_dict = {}
                    for td in td_element_list:
                        val = td.text.strip()
                        values.append(val)
                    for n,th in enumerate(xingzhengchufa_template.column_list):
                        json_dict[th] = values[n]
                    jsonarray.append(json_dict)
                # json_xingzhengchufa = json.dumps(jsonarray,ensure_ascii=False)
                # print 'json_xingzhengchufa',json_xingzhengchufa
                    xingzhengchufa_template.insert_into_database(self.cur_code,self.org_name, values)
        # self.driver.switch_to.default_content()

    # 加载经营异常信息
    def load_jingyingyichang(self):

        table_iframe = self.driver.find_element_by_xpath(".//div[@id='jyyc']/iframe")
        table_iframe_list = self.driver.find_elements_by_xpath(".//div[@id='jyyc']/iframe")
        for table_iframe in table_iframe_list:
            block_href = table_iframe.get_attribute('src')
            # print u'经营异常href',table_iframe.get_attribute('src')
            block = self.quest_getout(block_href,self.headers)
            blockbs = self.beaut_souping(block)#.decode('utf-8').encode('gbk')
            trIF = blockbs.find_all('table')[0].find_all('tr')
            if len(trIF)>2:
                jingyingyichang_template.delete_from_database(self.cur_code,self.org_name)
                jsonarray = []
                tr_element_list = blockbs.find_all('table')[0].find_all('tr')
        # self.driver.switch_to.frame(table_iframe)
        # table_element_list = self.driver.find_elements_by_xpath("/html/body/table")
        # table_element = table_element_list[0]
        # row_cnt = len(table_element.find_elements_by_xpath("tbody/tr"))
        # if row_cnt > 2:
        #     last_index_element = self.driver.find_element_by_xpath('/html/body/table[2]/tbody/tr/th/a[last()-1]')
        #     index_element_list_length = int(last_index_element.text.strip())
        #     for i in range(index_element_list_length):
        #         if i > 0:
        #             index_element = self.driver.find_element_by_xpath('/html/body/table[2]/tbody/tr/th/a[%d]' % (i+1))
        #             index_element.click()
        #             table_element = self.driver.find_element_by_xpath("/html/body/table[1]")
        #         tr_element_list = table_element.find_elements_by_xpath('tbody/tr')
                for tr_element in tr_element_list[2:]:
                    td_element_list = tr_element.find_all('td')
                    values = []
                    json_dict = {}
                    for td in td_element_list:
                        val = td.text.strip()
                        values.append(val)
                    for n,th in enumerate(jingyingyichang_template.column_list):
                        json_dict[th] = values[n]
                    jsonarray.append(json_dict)
                # json_jingyingyichang = json.dumps(jsonarray,ensure_ascii=False)
                # print 'json_jingyingyichang', json_jingyingyichang
                    jingyingyichang_template.insert_into_database(self.cur_code,self.org_name, values)
        # self.driver.switch_to.default_content()

    # 加载严重违法信息
    def load_yanzhongweifa(self):

        table_iframe = self.driver.find_element_by_xpath(".//div[@id='yzwf']/iframe")
        table_iframe_list = self.driver.find_elements_by_xpath(".//div[@id='yzwf']/iframe")
        for table_iframe in table_iframe_list:
            block_href = table_iframe.get_attribute('src')
            # print u'严重违法href',table_iframe.get_attribute('src')
            block = self.quest_getout(block_href,self.headers)
            blockbs = self.beaut_souping(block)#.decode('utf-8').encode('gbk')
            trIF = blockbs.find_all('table')[0].find_all('tr')
            if len(trIF)>2:
                yanzhongweifa_template.delete_from_database(self.cur_code,self.org_name)
                jsonarray = []
                tr_element_list = blockbs.find_all('table')[0].find_all('tr')
        # self.driver.switch_to.frame(table_iframe)
        # table_element_list = self.driver.find_elements_by_xpath("/html/body/table")
        # table_element = table_element_list[0]
        # row_cnt = len(table_element.find_elements_by_xpath("tbody/tr"))
        # if row_cnt > 2:
        #     last_index_element = self.driver.find_element_by_xpath('/html/body/table[2]/tbody/tr/th/a[last()-1]')
        #     index_element_list_length = int(last_index_element.text.strip())
        #     for i in range(index_element_list_length):
        #         if i > 0:
        #             index_element = self.driver.find_element_by_xpath('/html/body/table[2]/tbody/tr/th/a[%d]' % (i+1))
        #             index_element.click()
        #             table_element = self.driver.find_element_by_xpath("/html/body/table[1]")
        #         tr_element_list = table_element.find_elements_by_xpath('tbody/tr')
                for tr_element in tr_element_list[2:]:
                    td_element_list = tr_element.find_all('td')
                    values = []
                    json_dict = {}
                    for td in td_element_list:
                        val = td.text.strip()
                        values.append(val)
                    for n,th in enumerate(yanzhongweifa_template.column_list):
                        json_dict[th] = values[n]
                    jsonarray.append(json_dict)
                # json_yanzhongweifa = json.dumps(jsonarray,ensure_ascii=False)
                # print 'json_yanzhongweifa',json_yanzhongweifa
                    yanzhongweifa_template.insert_into_database(self.cur_code, self.org_name,values)
        # self.driver.switch_to.default_content()

    # 加载抽查检查信息
    def load_chouchajiancha(self):

        table_iframe = self.driver.find_element_by_xpath(".//div[@id='ccjc']/iframe")
        table_iframe_list = self.driver.find_elements_by_xpath(".//div[@id='ccjc']/iframe")
        for table_iframe in table_iframe_list:
            block_href = table_iframe.get_attribute('src')
            # print u'抽查检查href',table_iframe.get_attribute('src')
            block = self.quest_getout(block_href,self.headers)
            blockbs = self.beaut_souping(block)#.decode('utf-8').encode('gbk')
            trIF = blockbs.find_all('table')[0].find_all('tr')
            if len(trIF)>2:
                chouchajiancha_template.delete_from_database(self.cur_code,self.org_name)
                jsonarray = []
                tr_element_list = blockbs.find_all('table')[0].find_all('tr')
        # self.driver.switch_to.frame(table_iframe)
        # table_element_list = self.driver.find_elements_by_xpath("/html/body/table")
        # table_element = table_element_list[0]
        # row_cnt = len(table_element.find_elements_by_xpath("tbody/tr"))
        # if row_cnt > 2:
        #     last_index_element = self.driver.find_element_by_xpath('/html/body/table[2]/tbody/tr/th/a[last()-1]')
        #     index_element_list_length = int(last_index_element.text.strip())
        #     for i in range(index_element_list_length):
        #         if i > 0:
        #             index_element = self.driver.find_element_by_xpath('/html/body/table[2]/tbody/tr/th/a[%d]' % (i+1))
        #             index_element.click()
        #             table_element = self.driver.find_element_by_xpath("/html/body/table[1]")
        #         tr_element_list = table_element.find_elements_by_xpath('tbody/tr')
                for tr_element in tr_element_list[2:]:
                    td_element_list = tr_element.find_all('td')
                    values = []
                    json_dict = {}
                    for td in td_element_list:
                        val = td.text.strip()
                        values.append(val)
                    for n,th in enumerate(chouchajiancha_template.column_list):
                        json_dict[th]=values[n]
                    jsonarray.append(json_dict)
                # json_chouchajiancha = json.dumps(jsonarray,ensure_ascii=False)
                # print 'json_chouchajiancha',json_chouchajiancha
                    chouchajiancha_template.insert_into_database(self.cur_code,self.org_name, values)
        # self.driver.switch_to.default_content()

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
#         source= self.driver.find_elements_by_id("qufenkuang")[0]
#         html=source.get_attribute('outerHTML')
#         Soup = BeautifulSoup(html,'html.parser')
#         table_element=Soup.find_all('table')[0]
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
        # table_num = table_element
        # source= self.driver.find_elements_by_id("qufenkuang")[0]
        # html=source.get_attribute('outerHTML')
        # Soup = BeautifulSoup(html,'html.parser')
#             print Soup
        lenif = table_element.find_all('table')[0].find_all('tr')
        table_detail = table_element.find_all('table')[0]
        # print '***lenif***',len(lenif)
        if len(lenif) >2:
            th_element_list = table_detail.find_all("tr")[1].find_all("th")
            tr_element_list = table_detail.find_all("tr")[2:]
            jsonarray = []
            values = {}
            for tr_element in tr_element_list:
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
        # table_num = table_element
        # source= self.driver.find_elements_by_id("qufenkuang")[0]
        # html=source.get_attribute('outerHTML')
        # Soup = BeautifulSoup(html,'html.parser')
#             print Soup
        table_detail=table_element.find_all('table')[0]
        lenif = table_element.find_all('table')[0].find_all('tr')
        if len(lenif) > 2:
            th_element_list = table_detail.find_all("tr")[1].find_all("th")
            tr_element_list = table_detail.find_all("tr")[2:]
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
        # table_num = table_element
        # source= self.driver.find_elements_by_id("qufenkuang")[0]
        # html=source.get_attribute('outerHTML')
        # Soup = BeautifulSoup(html,'html.parser')
#             print Soup
        table_detail=table_element.find_all('table')[0]
        lenif = table_element.find_all('table')[0].find_all('tr')
        if len(lenif)>2:
            th_element_list = table_detail.find_all("tr")[1].find_all("th")
            tr_element_list = table_detail.find_all("tr")[2:]
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
        # table_num = table_element
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
#         source= self.driver.find_elements_by_id("qufenkuang")[0]
#         html=source.get_attribute('outerHTML')
#         Soup = BeautifulSoup(html,'html.parser')
        table_detail=table_element.find_all('table')[0]
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
        # table_num = table_element
        # source= self.driver.find_elements_by_id("qufenkuang")[0]
        # html=source.get_attribute('outerHTML')
        # Soup = BeautifulSoup(html,'html.parser')
#             print Soup
        table_detail=table_element.find_all('table')[0]
        lenif = table_element.find_all('table')[0].find_all('tr')
        if len(lenif)>2:
            th_element_list = table_detail.find_all("tr")[1].find_all("th")
            tr_element_list = table_detail.find_all("tr")[2:]

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
        # table_num = table_element
        # source= self.driver.find_elements_by_id("qufenkuang")[0]
        # html=source.get_attribute('outerHTML')
        # Soup = BeautifulSoup(html,'html.parser')
#             print Soup
        table_detail=table_element.find_all('table')[0]
        lenif = table_element.find_all('table')[0].find_all('tr')
        if len(lenif) > 2:
            th_element_list = table_detail.find_all("tr")[1].find_all("th")
            tr_element_list = table_detail.find_all("tr")[2:-1]

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
        sec = 0
        if '2' in table_element.find_all('table')[1].text:
            ling = table_element.find_all('table')[1].find('th').find_all_next('a')
            print 'lenling',len(ling),ling[2]
            other_href = 'http://gsxt.ngsh.gov.cn/ECPS/'+ling[2].get('href')
            print 'other_href',other_href
            sec = 1

        table_detail=table_element.find_all('table')[0].find_all('tr')
        if len(table_detail)>2:

            th_element_list = table_detail[1].find_all("th")
            tr_element_list = table_detail[2:]
            jsonarray = []
            values = {}
            for tr_element in tr_element_list:
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

            if sec==1:
                ott = self.quest_getout(other_href,headers=self.headers)
                obs = self.beaut_souping(ott)
                table_element = obs
                table_detail=table_element.find_all('table')[0].find_all('tr')
                if len(table_detail)>2:

                    th_element_list = table_detail[1].find_all("th")
                    tr_element_list = table_detail[2:]
                    jsonarray = []
                    values = {}
                    for tr_element in tr_element_list:
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


if __name__ == '__main__':

    code_list = ['640103200001999', '640100200099662', '640000100002816', '91640000715044058N',  '640221200010727',  '640103200001999', '640181200008860']
    searcher = NingXiaFirefoxSearcher()
    searcher.set_config()

    if searcher.build_driver() == 0:
        searcher.search(u"宁夏固海汽车贸易有限公司")#宁夏亨源薯制品有限公司")#银川塔木金商贸有限公司",)
#银川高新区正帝广告有限公司
