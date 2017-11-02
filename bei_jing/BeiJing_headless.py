# -*- coding=UTF-8 -*-
from template.FirefoxSearcher import FirefoxSearcher
from selenium import common
import template.SysConfig as SysConfig
from template.DataModel import DataModel
import sys
import os
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchFrameException
from selenium.common.exceptions import NoSuchElementException
from template.UnknownTableException import UnknownTableException
from template.UnknownColumnException import UnknownColumnException
from template.Tables import *
from template.Tables_dict import *
import time
from time import sleep
# from template.DBClient import *
from selenium import webdriver
from selenium.webdriver.remote.switch_to import SwitchTo
import traceback
import subprocess
from template.logger import *
import json
from PIL import Image
from bs4 import BeautifulSoup
from selenium.webdriver.common.action_chains import ActionChains


class BeiJingFirefoxSearcher(FirefoxSearcher):

    def __init__(self):
        super(BeiJingFirefoxSearcher, self).__init__()
        self.detail_page_handle=None
        #SysConfig.province=None
        self.search_model = None
        self.result_model = None
        

    def set_config(self):
        self.start_url = 'http://qyxy.baic.gov.cn/beijing'      
        self.code_input_box_xpath = ".//*[@id='keyword']"        
        self.code_submit_button_xpath = ".//*[@id='bjLoginForm']/div[2]/a"
        #self.validate_frame_xpath ='html/body/div[6]/div/iframe'     
        self.validate_image_xpath = ".//*[@id='MzImgExpPwd']"  
        self.validate_input_box_xpath = ".//*[@id='checkcodeAlt']"
        self.validate_submit_button_xpath = ".//*[@id='woaicss_con1']/ul/li[4]/a"
        self.change_one_image = ".//*[@id='suanshu2']/div[2]/a"
        self.tab_list_xpath = ".//*[@id='tabs']/ul/li"
        self.org_names_list = 'http://qyxy.baic.gov.cn/gjjbj/gjjQueryCreditAction!getBjQyList.dhtml#'
        self.plugin_pathzimu = os.path.join(sys.path[0], r'..\ocr\beijing\zimu\zimu.bat')
        self.plugin_pathjisuan = os.path.join(sys.path[0], r'..\ocr\beijing\jisuan\jisuan.bat')
        self.change_one_image_button = ".//*[@id='captcha']/div[1]/div[1]/div[2]/a"
        self.validate_tip_xpath="//*[@id='suanshu1']"
        self.province = u'北京市'
    
    
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
                    result_list = self.find_elements("//div[@class='list']/ul[1]")
                    row=1  
                    for result in result_list:
                        self.org_name = self.find_element("//div[@class='list']/ul[%d]/li[1]/a" %row).text
                        self.cur_code = self.find_element("//div[@class='list']/ul[%d]/li[2]/span[1]" %row).text
                        self.detail_page_url = result.find_element_by_xpath("ul/li[1]/a").get_attribute('onlcick')
#                         print self.org_name, self.cur_code
                        self.result_model = DataModel(self.org_name, self.province)
                        self.result_model.set_update_status(1)
                        self.find_element("//div[@class='list']/ul[%d]/li[1]/a" %row).click()
                        self.detail_page_handle = self.driver.window_handles[-1]
                        self.driver.switch_to.window(self.detail_page_handle)
                        try:
#                             self.parse_detail_page()
                            self.parse_lefttabs()
                        except (UnknownTableException, UnknownColumnException):
                            # 未知表名或列名，update_status：8
                            self.result_model.set_update_status(8)
                        row+=1   
                                        
        except Exception:
            # 未知异常，update_status：3
            traceback.print_exc()
            self.search_model.set_update_status(3)
#         self.switch_to_search_page()
        return self.search_model    


    def get_search_result(self):
        if not self.get_ip_status():
            return 4
        for handle in self.driver.window_handles:
            if handle != self.start_page_handle:
                self.driver.switch_to.window(handle) 
                self.search_result_handle=handle 
        search_result = self.find_element('//div [@class="list"]')
        result_text = search_result.text.strip()
#         print u'search result:'+result_text
        if result_text == '':
            logging.info(u'查询结果0条')
            self.search_model.set_update_status(0)
        else:
            self.search_model.set_update_status(1)
            
            
    def switch_to_search_page(self):
        for handle in self.driver.window_handles:
            if handle != self.start_page_handle:
                self.driver.switch_to.window(handle)
                self.driver.close()
                self.driver.switch_to.window(self.start_page_handle)

    def download_validate_image(self, image_element, save_path):
        self.driver.get_screenshot_as_file(save_path)
#         print self.screenshot_offset_y
#         print image_element.location['y']
        left = self.screenshot_offset_x + image_element.location['x']
        top = self.screenshot_offset_y+10 + image_element.location['y']
        right = self.screenshot_offset_x + image_element.location['x'] + image_element.size['width']
        bottom = self.screenshot_offset_y+10 + image_element.location['y'] + image_element.size['height']
#         print left,top,right,bottom
        image = Image.open(save_path)
        image = image.crop((int(left), int(top), int(right), int(bottom)))
        image.save(save_path)

            
    def submit_search_request(self):
        self.code_input_box = self.find_element(self.code_input_box_xpath)
        self.code_submit_button = self.find_element(self.code_submit_button_xpath)
        self.code_input_box.clear()  # 清空输入框
        self.code_input_box.send_keys(self.cur_name)  # 输入查询代码
        self.code_submit_button.click()
        validate_image_save_path = SysConfig.get_validate_image_save_path()  # 获取验证码保存路径
        for i in range(SysConfig.max_try_times):
            if "none" in self.find_element("//div [@id='zmdid']").get_attribute('style'):                    
                break
            validate_tip=self.find_element(self.validate_tip_xpath).text
            if u'请在查询框中正确输入你所看到的字符' in validate_tip:
                self.plugin_path=self.plugin_pathzimu
            if u'请根据下图中的算术题，在查询框中输入计算结果' in validate_tip:
                self.plugin_path=self.plugin_pathjisuan
            self.validate_image = self.find_element(self.validate_image_xpath)  # 定位验证码图片
            self.validate_input_box = self.find_element(self.validate_input_box_xpath)  # 定位验证码输入框
            self.validate_submit_button = self.find_element(self.validate_submit_button_xpath)  # 定位验证码提交按钮
            self.download_validate_image(self.validate_image, validate_image_save_path)  # 截图获取验证码
            validate_code = self.recognize_validate_code(validate_image_save_path)  # 识别验证码
            self.validate_input_box.clear()  # 清空验证码输入框
            self.validate_input_box.send_keys(validate_code)  # 输入验证码
            self.validate_submit_button.click()  # 点击搜索（验证码弹窗）
#             self.driver.save_screenshot('bj.png')
            

    # 判断IP是否被禁
    def get_ip_status(self):
        body_text = self.find_element("/html/body").text
        if body_text.startswith(u'您停留的时间过长'):
            return False
        else:
            return True
        
    def build_driver(self):
        build_result = 0
#         self.driver=webdriver.Firefox()
        self.driver = webdriver.PhantomJS()
        self.driver.set_window_size(1024, 768)
        self.set_timeout_config()
        for i in xrange(SysConfig.max_try_times):
            if self.wait_for_load_start_url():
                break
            else:
                if i == SysConfig.max_try_times:
                    build_result = 1
        return build_result


    # 判断搜索起始页是否加载成功 {0:成功, 1:失败}
    def wait_for_load_start_url(self):
        load_result = True
        try:
            self.driver.get(self.start_url)
            try:
                WebDriverWait(self.driver, 30).until(
                        EC.presence_of_element_located((By.XPATH, "//*[@id='float_icon']/div/img"))
                ).click()
#                 self.driver.save_screenshot('piaochuang.png')
            except common.exceptions.TimeoutException:
                pass
            self.start_page_handle = self.driver.current_window_handle
        except common.exceptions.TimeoutException:
            pass
        try:
            self.code_input_box = self.find_element(self.code_input_box_xpath)
            self.code_submit_button = self.find_element(self.code_submit_button_xpath)
        except common.exceptions.NoSuchElementException:
            load_result = False
        return load_result


    def parse_lefttabs(self):
        for i in range(2):
            tab_element = self.find_element("//*[@id='leftTabs']/ul/li[%d]" % (i+1))
            tab_desc = tab_element.text.strip().replace('\n','')
#             print tab_desc
            if tab_element.get_attribute('class') != 'current':
                tab_element.click()
            if tab_desc==u'工商公示信息':
                self.parse_detail_page()
            elif tab_desc==u'企业公示信息':
                self.load_qiyegongshi()


    def parse_detail_page(self):
        try:
            t=self.find_element("/html/body/p").text
            if t.find(u'您停留的时间过长')!=-1:
                print u'您停留的时间过长'
                while True:
                    self.driver.back()
                    sleep(0.5)
                    self.driver.current_url
                    if self.driver.current_url==self.org_names_list:
                        self.driver.delete_all_cookies()
                        break
                return 999
        except:
            pass
        tab_list_length = len(self.find_elements(self.tab_list_xpath))
        print tab_list_length
        for i in range(tab_list_length):
            tab=WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH,".//*[@id='tabs']/ul/li[%d]" % (i+1)))
                        )
            tab_text = tab.text
            if tab.get_attribute('class') != 'current':
                sleep(1)
                tab.click()
            self.load_func_dict[tab_text]()

    def load_qiyegongshi(self):
        WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, "//div [@id='qynbDiv']//iframe"))
            )
        iframe_element = self.find_element("//div [@id='qynbDiv']//iframe")                                                                                                                                                                                                                                           
        self.driver.switch_to.frame(iframe_element)
        self.ARList_hadle=self.driver.window_handles[-1]
        report_tr_list = self.find_elements("//*[@id='qiyenianbao']/table/tbody/tr")
        if len(report_tr_list)>2:
            i=1
            for tr_element in report_tr_list[2:]:
                td_element_list=self.find_elements("//*[@id='qiyenianbao']/table/tbody/tr[%d]/td" %(i+2))
                values = []
                j=1
                for td in td_element_list:
                    val = self.find_element("//*[@id='qiyenianbao']/table/tbody/tr[%d]/td[%d]" %((i+2),j)).text.strip()
#                     print val
                    if u'年度' in val:
                        values.append(val)
                        values.append(self.find_element("//*[@id='qiyenianbao']/table/tbody/tr[%d]/td[%d]/a" %((i+2),j)).get_attribute('href'))
                        self.nianbaotitle=val
                        self.find_element("//*[@id='qiyenianbao']/table/tbody/tr[%d]/td[%d]/a" %((i+2),j)).click()
                        time.sleep(5)
                        self.driver.switch_to.window(self.driver.window_handles[-1])
                        self.load_nianbaodetail()
                        self.driver.close()
                        self.driver.switch_to.window(self.ARList_hadle)
                        self.driver.switch_to.default_content()
                        self.driver.switch_to.frame(iframe_element)
                    else:
                        values.append(val)  
                    j+=1
                json_nianbaosum=json.dumps(values,ensure_ascii=False)
                print 'json_nianbaosum',json_nianbaosum
                i+=1


    def load_nianbaodetail(self):  
#         print 'AR detail successfully accessed '     
        table_list = self.driver.find_elements_by_xpath("//table[@class='detailsList']" )
        row=1
        for table_element in table_list:
            row_cnt = len(table_element.find_elements_by_xpath("//table[@class='detailsList'][%d]//tr" %row))
            table_desc_element = table_element.find_element_by_xpath("//table[@class='detailsList'][%d]//tr/th" %row)
            if row==1:
                table_desc = u'企业基本信息'
            else:
                table_desc = table_desc_element.text.split('\n')[0].strip()
            logging.info(u"解析%s ..." % table_desc)
            if row_cnt >3:           
                if table_desc in self.load_func_dict:
#                     print 'pre-loading',table_desc
                    self.load_func_dict[table_desc](table_element)
                else:
#                     print 'unkonw table',table_desc
                    raise UnknownTableException(self.cur_code, table_desc)
            row+=1
            logging.info(u"解析%s成功" % table_desc) 
        iframe_list = self.find_elements("//div [@id='qufenkuang']//iframe")
        for table_iframe in iframe_list:
            self.driver.switch_to.frame(table_iframe)
            table_element_list = self.driver.find_elements_by_xpath("/html/body//table")
            table_element = table_element_list[0]
            table_desc_element = table_element.find_element_by_xpath("tbody/tr/th")
            table_desc = table_desc_element.text.split('\n')[0].strip()
#             print 'table_desc',table_desc
            row_cnts=len(table_element.find_elements_by_xpath("tbody/tr"))
            if row_cnts>3:
                if table_desc in self.load_func_dict:
#                     print 'pre-loading',table_desc
                    self.load_func_dict[table_desc](table_element)
                else:
#                     print 'unkonw table',table_desc
                    raise UnknownTableException(self.cur_code, table_desc)
            self.driver.switch_to.default_content()
            
            
    def load_nianbaojiben(self,table_element):
        source= self.driver.find_element_by_id("qufenkuang")
        html=source.get_attribute('outerHTML')
        Soup = BeautifulSoup(html,'html.parser')
        table_element=Soup.find('table')
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
        print 'json_nianbaojiben',json_nianbaojiben
             
                          
    def load_nianbaoweb (self,table_element):          
        jsonarray=[]   
        values = {}  
        row=1                        
        while True:
            tr_element_list = self.find_elements("//*[@id='touziren']/tbody/tr[position()<last()]")
            th_element_list = self.find_elements("//*[@id='touziren']/tbody/tr[2]/th")
            i=3
            for tr_element in tr_element_list[2:]:       
                td_element_list = self.find_elements("//*[@id='touziren']/tbody/tr[%d]/td" %i)
                col_nums = len(th_element_list)
                for j in range(col_nums):
                    col = th_element_list[j].text.strip().replace('\n','')
                    td=td_element_list[j]
                    val = td.text.strip()
                    values[col] = val
                values[u'注册号']=self.cur_code
                values[u'省份']=self.province
                values[u'报送年度']=self.nianbaotitle
                jsonarray.append(values)
                values = {}                                                            
                i+=1
            if len(self.find_elements("//*[@id='touziren']/tbody/tr[last()]/th/a"))>2:
                index_element = self.find_element(".//*[@id='touziren']/tbody/tr[last()]/th/font/following-sibling::a[1]")
                if index_element.get_attribute('onclick').startswith('jumppage') and index_element.text.strip()==u'>>': #and index_element.text()!=u'>>':
                    break
                else:
                    index_element.click()   
            else:
                break                           
        json_nianbaoweb=json.dumps(jsonarray,ensure_ascii=False)
        print 'json_nianbaoweb',json_nianbaoweb   

        
            
    def load_nianbaogudong (self,table_element):
        jsonarray=[]   
        values = {}  
        row=1                        
        while True:
            tr_element_list = self.find_elements("//*[@id='touziren']/tbody/tr[position()<last()]")
            th_element_list = self.find_elements("//*[@id='touziren']/tbody/tr[2]/th")
            i=3
            for tr_element in tr_element_list[2:]:       
                td_element_list = self.find_elements("//*[@id='touziren']/tbody/tr[%d]/td" %i)
                col_nums = len(th_element_list)
                for j in range(col_nums):
                    col = th_element_list[j].text.strip().replace('\n','')
                    td=td_element_list[j]
                    val = td.text.strip()
                    values[col] = val
                values[u'注册号']=self.cur_code
                values[u'省份']=self.province
                values[u'报送年度']=self.nianbaotitle
                jsonarray.append(values)
                values = {}                                                            
                i+=1
            if len(self.find_elements("//*[@id='touziren']/tbody/tr[last()]/th/a"))>2:
                index_element = self.find_element(".//*[@id='touziren']/tbody/tr[last()]/th/font/following-sibling::a[1]")
                if index_element.get_attribute('onclick').startswith('jumppage') and index_element.text.strip()==u'>>': #and index_element.text()!=u'>>':
                    break
                else:
                    index_element.click()   
            else:
                break                           
        json_nianbaogudong=json.dumps(jsonarray,ensure_ascii=False)
        print 'json_nianbaogudong',json_nianbaogudong   


    def load_nianbaoduiwaitouzi(self,table_element):
        jsonarray = []
        values = {}
        while True:
            tr_element_list = self.find_elements("//*[@id='touziren']/tbody/tr[position()<last()]")
            th_element_list = self.find_elements("//*[@id='touziren']/tbody/tr[2]/th")
            i=3
            for tr_element in tr_element_list[2:]:       
                td_element_list = self.find_elements("//*[@id='touziren']/tbody/tr[%d]/td" %i)
                col_nums = len(th_element_list)
                for j in range(col_nums):
                    col = th_element_list[j].text.strip().replace('\n','')
                    td=td_element_list[j]
                    val = td.text.strip()
                    values[col] = val
                values[u'注册号']=self.cur_code
                values[u'省份']=self.province
                values[u'报送年度']=self.nianbaotitle
                jsonarray.append(values)
                values = {}                                                            
                i+=1
            if len(self.find_elements("//*[@id='touziren']/tbody/tr[last()]/th/a"))>2:
                index_element = self.find_element(".//*[@id='touziren']/tbody/tr[last()]/th/font/following-sibling::a[1]")
                if index_element.get_attribute('onclick').startswith('jumppage') and index_element.text.strip()==u'>>': #and index_element.text()!=u'>>':
                    break
                else:
                    index_element.click()    
            else:
                break                         
        json_nianbaoduiwaitouzi=json.dumps(jsonarray,ensure_ascii=False)
        print 'json_nianbaoduiwaitouzi',json_nianbaoduiwaitouzi
    
    
    def load_nianbaozichan(self,table_element):
        source= self.driver.find_element_by_id("qufenkuang")
        html=source.get_attribute('outerHTML')
        Soup = BeautifulSoup(html,'html.parser')
        title=Soup.find(text=u'企业资产状况信息')
        tr_element_list = title.find_all_next("tr")
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
        print 'json_nianbaozichan',json_nianbaozichan
        
        
    def load_nianbaodanbao(self,table_element):
        jsonarray = []
        values = {}
        while True:
            tr_element_list = self.find_elements("//*[@id='touziren']/tbody/tr[position()<last()]")
            th_element_list = self.find_elements("//*[@id='touziren']/tbody/tr[2]/th")
            i=3
            for tr_element in tr_element_list[2:]:       
                td_element_list = self.find_elements("//*[@id='touziren']/tbody/tr[%d]/td" %i)
                col_nums = len(th_element_list)
                for j in range(col_nums):
                    col = th_element_list[j].text.strip().replace('\n','')
                    td=td_element_list[j]
                    val = td.text.strip()
                    values[col] = val
                values[u'注册号']=self.cur_code
                values[u'省份']=self.province
                values[u'报送年度']=self.nianbaotitle
                jsonarray.append(values)
                values = {}                                                            
                i+=1
            if len(self.find_elements("//*[@id='touziren']/tbody/tr[last()]/th/a"))>2:
                index_element = self.find_element(".//*[@id='touziren']/tbody/tr[last()]/th/font/following-sibling::a[1]")
                if index_element.get_attribute('onclick').startswith('jumppage') and index_element.text.strip()==u'>>': #and index_element.text()!=u'>>':
                    break
                else:
                    index_element.click()    
            else:
                break                     
        json_nianbaodanbao=json.dumps(jsonarray,ensure_ascii=False)
        print 'json_nianbaodanbao',json_nianbaodanbao
        
        
    def load_nianbaoguquanbiangeng (self,table_element):
        jsonarray = []
        values = {}
        while True:
            tr_element_list = self.find_elements("//*[@id='touziren']/tbody/tr[position()<last()]")
            th_element_list = self.find_elements("//*[@id='touziren']/tbody/tr[2]/th")
            i=3
            for tr_element in tr_element_list[2:]:       
                td_element_list = self.find_elements("//*[@id='touziren']/tbody/tr[%d]/td" %i)
                col_nums = len(th_element_list)
                for j in range(col_nums):
                    col = th_element_list[j].text.strip().replace('\n','')
                    td=td_element_list[j]
                    val = td.text.strip()
                    values[col] = val
                values[u'注册号']=self.cur_code
                values[u'省份']=self.province
                values[u'报送年度']=self.nianbaotitle
                jsonarray.append(values)
                values = {}                                                            
                i+=1
            if len(self.find_elements("//*[@id='touziren']/tbody/tr[last()]/th/a"))>2:
                index_element = self.find_element(".//*[@id='touziren']/tbody/tr[last()]/th/font/following-sibling::a[1]")
                if index_element.get_attribute('onclick').startswith('jumppage') and index_element.text.strip()==u'>>': #and index_element.text()!=u'>>':
                    break
                else:
                    index_element.click()   
            else:
                break                      
        json_nianbaoguquanbiangeng=json.dumps(jsonarray,ensure_ascii=False)
        print 'json_nianbaoguquanbiangeng',json_nianbaoguquanbiangeng
        
        
    def load_nianbaoxiugai(self):
        jsonarray = []
        values = {}
        while True:
            tr_element_list = self.find_elements("//*[@id='touziren']/tbody/tr[position()<last()]")
            th_element_list = self.find_elements("//*[@id='touziren']/tbody/tr[2]/th")
            i=3
            for tr_element in tr_element_list[2:]:       
                td_element_list = self.find_elements("//*[@id='touziren']/tbody/tr[%d]/td" %i)
                col_nums = len(th_element_list)
                for j in range(col_nums):
                    col = th_element_list[j].text.strip().replace('\n','')
                    td=td_element_list[j]
                    val = td.text.strip()
                    values[col] = val
                values[u'注册号']=self.cur_code
                values[u'省份']=self.province
                values[u'报送年度']=self.nianbaotitle
                jsonarray.append(values)
                values = {}                                                            
                i+=1
            if len(self.find_elements("//*[@id='touziren']/tbody/tr[last()]/th/a"))>2:
                index_element = self.find_element(".//*[@id='touziren']/tbody/tr[last()]/th/font/following-sibling::a[1]")
                if index_element.get_attribute('onclick').startswith('jumppage') and index_element.text.strip()==u'>>': #and index_element.text()!=u'>>':
                    break
                else:
                    index_element.click()        
            else:
                break                 
        json_nianbaoxiugai=json.dumps(jsonarray,ensure_ascii=False)
        print 'json_nianbaoxiugai',json_nianbaoxiugai

              
    def load_dengji(self):
        table_list = self.find_elements("html/body/div[2]/div[2]/div[1]/div[2]/div/table")
        for table_element in table_list:
#             row_cnt = len(table_element.find_elements_by_xpath("tbody/tr"))
            table_desc_element = table_element.find_element_by_xpath("tbody/tr/th")
            table_desc = table_desc_element.text.split('\n')[0].strip()
#             print table_desc
            logging.info(u"解析%s ..." % table_desc)
            if table_desc == u'基本信息':
                self.load_func_dict[table_desc](table_element)
            else:
                raise UnknownTableException(self.cur_code, table_desc)
            #self.driver.switch_to.default_content()
            logging.info(u"解析%s成功" % table_desc)
        # 股东、合伙人、投资人表单
        table1_iframe = self.find_element("html/body/div[2]/div[2]/div[1]/div[2]/div[2]/iframe")
        self.driver.switch_to.frame(table1_iframe)
        table1_desc = self.find_element(".//*[@id='touziren']/tbody[1]/tr/th").text.split('\n')[0].strip()
        if table1_desc==u'股东信息':
            self.load_func_dict[table1_desc](table1_iframe)
        elif table1_desc==u'发起人':
            table1_desc=u'股东信息'
            self.load_func_dict[table1_desc](table1_iframe)
        elif table1_desc not in self.load_func_dict:
            raise UnknownTableException(self.cur_code, table1_desc)
        logging.info(u"解析%s ..." % table1_desc)
        self.driver.switch_to.default_content()
        
        # 变更信息
        table2_iframe = self.find_element("html/body/div[2]/div[2]/div[1]/div[2]/div[@id='bgxx']/iframe")
        self.driver.switch_to.frame(table2_iframe)
        table2_desc = self.find_element(".//*[@id='table2']/tr[1]/th").text.strip()
        if table2_desc==u'变更信息':
            self.load_func_dict[table2_desc](table2_iframe)
        if table2_desc not in self.load_func_dict:
            raise UnknownTableException(self.cur_code, table2_desc)
        logging.info(u"解析%s ..." % table2_desc)
        self.driver.switch_to.default_content()
        
    def load_jiben(self, table_desc):
        jsonarray=[]
        tr_element_list = self.find_elements(".//*[@id='jbxx']/table/tbody/tr")        
        values = {}
        for tr_element in tr_element_list[1:]:
            th_element_list = tr_element.find_elements_by_xpath('th')            
            td_element_list = tr_element.find_elements_by_xpath('td')            
            if len(th_element_list) == len(td_element_list):
                col_nums = len(th_element_list)
                for i in range(col_nums):
                    col_dec = th_element_list[i].text.strip()
                    val = td_element_list[i].text.strip()
                    if col_dec != u'':
                        col=jiben_column_dict[col_dec]
                        values[col] = val
        values['Province']=self.province
        values['rowkey']=self.company_name+'_01_'+self.cur_code+'_'
        jsonarray.append(values)
        self.json_dict['Registered_Info']=jsonarray
        json_jiben=json.dumps(values,ensure_ascii=False)
        print 'json_jiben',json_jiben
     
    def load_gudong(self,table_desc):
        jsonarray=[]
        index_element_list = self.find_elements(".//*[@id='table2']/tr[last()]/th/a")
        print "gd-->:",len(index_element_list)
        if len(index_element_list)==2:       
            tr_element_list = self.find_elements(".//*[@id='touziren']/tbody[2]/tr[position()<last()]")
            th_element_list = self.find_elements(".//*[@id='touziren']/tbody[2]/tr[1]/th")
            id=1
            for tr in tr_element_list[1:]:  
                td_element_list = tr.find_elements_by_xpath('td')
                col_nums = len(th_element_list)
                values = {}
                for j in range(col_nums):
                    col_dec = th_element_list[j].text.strip().replace('\n','')
                    col=gudong_column_dict[col_dec]
                    td=td_element_list[j]
                    val = td.text.strip()
                    if val==u'详情':
                        td.find_element_by_xpath('a').click()
                        self.driver.switch_to_window(self.driver.window_handles[-1])
                        detail_tr_list = self.find_elements(".//*[@id='sifapanding']/table/tbody/tr[position()<last()]")
                        detail_th_list = ['Subscripted_Capital','ActualPaid_Capital','Subscripted_Method','Subscripted_Amount','Subscripted_Time','ActualPaid_Method','ActualPaid_Amount','ActualPaid_Time']
                        for tr_ele in detail_tr_list[3:]:
                            td_ele_list = tr_ele.find_elements_by_xpath('td')[1:]
                            detail_col_nums = len(td_ele_list) 
#                             print detail_col_nums                      
                            for m in range(detail_col_nums):
                                col = detail_th_list[m]
                                td=td_ele_list[m]
                                val = td.text.strip()
                                values[col] = val
                        self.driver.close()
                        self.driver.switch_to_window(self.driver.window_handles[0])
                        table1_iframe = self.find_element("html/body/div[2]/div[2]/div[1]/div[2]/div[2]/iframe")
                        self.driver.switch_to.frame(table1_iframe)
                    else:
                        values[col] = val                                                               
                values['RegistrationNo']=self.cur_code
                values['EnterpriseName']=self.org_name
                values['rowkey'] = values['EnterpriseName']+'_04_'+ values['RegistrationNo']+'_'+str(id)
                json_gudong=json.dumps(values,ensure_ascii=False)
                print 'json_gudong',json_gudong
#                 jsonarray.append(values) 
                id+=1
        else:
            while (100):
                index_element = self.find_element(".//*[@id='table2']/tr[last()]/th/font/following-sibling::a[1]")
                print index_element.text.strip()
                if index_element.get_attribute('onclick').startswith('jumppage') :
                    tr_element_list = self.find_elements(".//*[@id='touziren']/tbody[2]/tr[position()<last()]")
                    th_element_list = self.find_elements("//*[@id='touziren']/tbody[2]/tr[1]/th")
                    id=1
                    for tr in tr_element_list:  
                        td_element_list = tr.find_elements_by_xpath('.//td')
                        col_nums = len(th_element_list)
                        values = {}
                        for j in range(col_nums):
                            col_dec = th_element_list[j].text.strip().replace('\n','')
                            col=gudong_column_dict[col_dec]
                            td=td_element_list[j]
                            val = td.text.strip()
                            if val==u'详情':
                                td.find_element_by_xpath('a').click()
                                self.driver.switch_to_window(self.driver.window_handles[-1])
                                detail_tr_list = self.find_elements(".//*[@id='sifapanding']/table/tbody/tr[position()<last()]")
                                detail_th_list = ['Subscripted_Capital','ActualPaid_Capital','Subscripted_Method','Subscripted_Amount','Subscripted_Time','ActualPaid_Method','ActualPaid_Amount','ActualPaid_Time']
                                for tr_ele in detail_tr_list[3:]:
                                    td_ele_list = tr_ele.find_elements_by_xpath('.//td')[1:]
                                    detail_col_nums = len(detail_th_list)                             
                                    for m in range(detail_col_nums):
                                        col = detail_th_list[m]
                                        td=td_ele_list[m]
                                        val = td.text.strip()
                                        values[col] = val
                                self.driver.close()
                                self.driver.switch_to_window(self.driver.window_handles[0])
                                table1_iframe = self.find_element("html/body/div[2]/div[2]/div[1]/div[2]/div[2]/iframe")
                                self.driver.switch_to.frame(table1_iframe)
                            else:
                                values[col] = val
                        values['RegistrationNo']=self.cur_code
                        values['EnterpriseName']=self.org_name
                        values['rowkey'] = values['EnterpriseName']+'_04_'+ values['RegistrationNo']+'_'+str(id)
                        json_gudong=json.dumps(values,ensure_ascii=False)
                        print 'json_gudong',json_gudong
                    if index_element.text.strip()!=u'>>':
                        index_element.click()
                    else: 
                        break
#         json_gudong=json.dumps(jsonarray,ensure_ascii=False)
#         print 'json_gudong',json_gudong
                                
    def load_biangeng(self,table_desc):
        jsonarray=[]
        table=WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, ".//*[@id='table2']"))
                    )
        trs=table.find_elements_by_xpath(".//tr")
        if len(trs)>2:
            index_element_list = self.find_elements(".//*[@id='table2']/tr[last()]/th/a")
            print "bg-->:",len(index_element_list)
            if len(index_element_list)==3:       
                tr_element_list = self.find_elements(".//*[@id='touziren']/tbody/tr[position()<last()]")   
                id=1      
                for tr in tr_element_list[2:]:  
                    th_element_list = self.find_elements(".//*[@id='touziren']/tbody/tr[2]/th")
                    td_element_list = tr.find_elements_by_xpath('td')
                    col_nums = len(th_element_list)
                    if col_nums==3:
                        th_element_list=['ChangedAnnouncement_Events','ChangedAnnouncement_details','ChangedAnnouncement_Date']
                    values = {}
                    for j in range(col_nums):
                        if col_nums==3:
                            col=th_element_list[j]
                        else:
                            col_dec = th_element_list[j].text.strip().replace('\n','')
                            col=biangeng_column_dict[col_dec]
                        td=td_element_list[j]
                        val = td.text.strip()
                        if val==u'详细':                        
                            self.get_detail()
                            values['ChangedAnnouncement_Before'] = self.bgq
                            values['ChangedAnnouncement_After'] = self.bgh
                        else:
                            values[col] = val                        
                    values['RegistrationNo']=self.cur_code
                    values['EnterpriseName']=self.org_name
                    values['rowkey'] = values['EnterpriseName']+'_05_'+ values['RegistrationNo']+'_'+str(id)
                    jsonarray.append(values)  
                    values = {}       
                    id+=1                                              
            else:
                while True:
                    id=1
                    tr_element_list = self.find_elements(".//*[@id='table2']/tr[position()<last()]")
                    for tr in tr_element_list[2:]:  
                        th_element_list = self.find_elements(".//*[@id='table2']/tr[2]/th")
                        td_element_list = tr.find_elements_by_xpath('td')
                        col_nums = len(td_element_list)
                        if col_nums==3:
                            th_element_list=['ChangedAnnouncement_Events','ChangedAnnouncement_details','ChangedAnnouncement_Date']
                        values = {}
                        for j in range(col_nums):
                            if col_nums==3:
                                col=th_element_list[j]
                            else:
                                col_dec = th_element_list[j].text.strip().replace('\n','')
                                col=biangeng_column_dict[col_dec]
                            td=td_element_list[j]
                            val = td.text.strip()
                            if val==u'详细':  
                                td.find_element_by_xpath('a').click()
                                self.driver.switch_to_window(self.driver.window_handles[1])
                                WebDriverWait(self.driver, 3).until(
                                EC.presence_of_element_located((By.XPATH,"//*[@id='tableIdStyle']/tbody/tr[1]/td")))                    
                                self.get_detail()
#                                 print 'bgq',self.bgq
#                                 print 'bgh',self.bgh
                                values['ChangedAnnouncement_Before'] = self.bgq
                                values['ChangedAnnouncement_After'] = self.bgh
                            else:
                                values[col] = val 
#                                 print col,val                                                       
                        values['RegistrationNo']=self.cur_code
                        values['EnterpriseName']=self.org_name
                        values['rowkey'] = values['EnterpriseName']+'_05_'+ values['RegistrationNo']+'_'+str(id)
                        jsonarray.append(values)
                        values = {}
                        id+=1
                    index_element = self.find_element(".//*[@id='table2']/tr[last()]/th/a[font]/following-sibling::a[1]")
                    if index_element.get_attribute('onclick').startswith('jumppage') and index_element.text.strip()==u'>>': #and index_element.text()!=u'>>':
                        break
                    else:
                        index_element.click()
            json_biangeng=json.dumps(jsonarray,ensure_ascii=False)
            print 'json_biangeng',json_biangeng


    def get_detail(self):
        row_data=[]    
        tables=self.driver.find_elements_by_xpath("//*[@id='tableIdStyle']/tbody")
        for t in tables:  
            time.sleep(1)
            trs=t.find_elements_by_xpath(".//tr")
            bt=trs[0].find_element_by_xpath(".//td").text
            ths=trs[1].find_elements_by_xpath(".//th")
            for tr in trs[2:]:
                tds=tr.find_elements_by_xpath(".//td")
                col_nums = len(ths)
                for j in range(col_nums):
                    col = ths[j].text.strip().replace('\n','')
                    td=tds[j]
                    val = td.text.strip()
                    row=col+u'：'+val
#                     print 'row',row
                    row_data.append(row)
            if u'变更前' in bt:
                self.bgq = u'；'.join(row_data)
#                 print 'bgq',self.bgq
            elif u'变更后' in bt:
                self.bgh = u'；'.join(row_data)
#                 print 'bgh',self.bgh
            row_data=[]
        self.driver.close()
        self.driver.switch_to_window(self.driver.window_handles[0])
        table2_iframe = self.driver.find_element_by_xpath("html/body/div[2]/div[2]/div[1]/div[2]/div[3]/iframe")
        self.driver.switch_to.frame(table2_iframe)  


    def load_beian(self):
        #主要人员#
        sleep(0.5)
        table_iframe_list = self.find_elements("//div [@id='bgxxDiv']/div/iframe")
        for iframe_element in table_iframe_list:
            self.driver.switch_to.frame(iframe_element)
#             table_zyry = self.find_element("html/body/form/table")        
            table_element = self.find_element("html/body/form/table")
            table_desc_element = table_element.find_element_by_xpath("tbody/tr/th")
            table_desc = table_desc_element.text.split('\n')[0].strip()
            if table_desc==u'主管部门（出资人）信息':
                table_desc=u'主要人员信息' 
            print table_desc
            if table_desc not in self.load_func_dict:
                raise UnknownTableException(self.cur_code, table_desc)
            logging.info(u"解析%s ..." % table_desc)
            self.load_func_dict[table_desc](table_element)
            logging.info(u"解析%s成功" % table_desc)
            self.driver.switch_to.default_content()
    
#     def load_zgbmczr(self,table_element):
#         gudong_template.delete_from_database(self.cur_code)
#         trs=self.find_elements(".//tr")
#         if len(trs)==2:
#             print "这里出现一个空表!"
#             return -1
#         for tr  in trs[2:]:
#             tds=tr.find_elements_by_xpath(".//td")
#             if len(tds)==5:
#                 values=[]
#                 values.append(tds[2].text)
#                 values.append(tds[3].text)
#                 values.append(tds[4].text)
#                 values.append(tds[1].text)
#                 for i in range(8):
#                     values.append('')
#                 gudong_template.insert_into_database(self.cur_code, values)
#             
    def load_zhuyaorenyuan(self, table_element):
        jsonarray=[]   
        values = {}
        zyry_tr_element = self.find_elements(".//*[@id='table2']/tr")
        if len(zyry_tr_element)>2:
            index_element_list = self.find_elements(".//*[@id='table2']/tr[last()]/th/a")
            if len(index_element_list)==2:
                tr_element_list = self.find_elements(".//*[@id='table2']/tr[position()<last()]")   
                th_element_list = self.find_elements(".//*[@id='table2']/tr[2]/th")      
                id=1                     
                for tr_element in tr_element_list[2:]:               
                    td_element_list = tr_element.find_elements_by_xpath('td')
                    list_length = len(td_element_list)
                    fixed_length = list_length - list_length % 3
                    for j in range(fixed_length):
                        col_dec = th_element_list[j].text.strip().replace('\n','')
                        col=zhuyaorenyuan_column_dict[col_dec]
                        td=td_element_list[j]
                        val = td.text.strip()
                        values[col] = val
                        if len(values) == 3:
                            values['RegistrationNo']=self.cur_code
                            values['EnterpriseName']=self.org_name
                            values['rowkey'] = values['EnterpriseName']+'_06_'+ values['RegistrationNo']+'_'+str(id)
                            json_zhuyaorenyuan=json.dumps(values,ensure_ascii=False)
                            print 'json_zhuyaorenyuan',json_zhuyaorenyuan
                            values = {}
                            id+=1
            else:
                while (100):
                    index_element = self.find_element(".//*[@id='table2']/tr[last()]/th/font/following-sibling::a[1]")
                    print index_element.text.strip()                
                    if index_element.get_attribute('onclick').startswith('jumppage'):
                        tr_element_list = self.find_elements(".//*[@id='table2']/tr[position()<last()]")  
                        th_element_list = self.find_elements(".//*[@id='table2']/tr[2]/th")         
                        id=1                   
                        for tr_element in tr_element_list[2:]:               
                            td_element_list = tr_element.find_elements_by_xpath('td')
                            list_length = len(td_element_list)
                            fixed_length = list_length - list_length % 3
                            for j in range(fixed_length):
                                col_dec = th_element_list[j].text.strip().replace('\n','')
                                col=zhuyaorenyuan_column_dict[col_dec]
                                td=td_element_list[j]
                                val = td.text.strip()
                                values[col] = val
                                if len(values) == 3:
                                    values['RegistrationNo']=self.cur_code
                                    values['EnterpriseName']=self.org_name
                                    values['rowkey'] = values['EnterpriseName']+'_06_'+ values['RegistrationNo']+'_'+str(id)
                                    json_zhuyaorenyuan=json.dumps(values,ensure_ascii=False)
                                    print 'json_zhuyaorenyuan',json_zhuyaorenyuan
                                    values = {}
                                    id+=1
                        if index_element.text.strip()!=u'>>':
                            index_element.click()
                        else: 
                            break
            
                        
    def load_hehuoren(self,table_desc):
        jsonarray=[]   
        values = {} 
        index_element_list = self.find_elements("html/body/form/table/tbody/tr[last()]/th/a")
        if len(index_element_list)==2:
            tr_element_list = self.find_elements("html/body/form/table/tbody/tr[position()<last()]")
            th_element_list = self.find_elements("html/body/form/table/tbody/tr[2]/th")
            for tr_element in tr_element_list[2:]:            
                td_element_list = tr_element.find_elements_by_xpath('td')
                col_nums = len(th_element_list)
                for j in range(col_nums):
                    col_dec = th_element_list[j].text.strip().replace('\n','')
                    col=touziren_column_dict[col_dec]
                    td=td_element_list[j]
                    val = td.text.strip()
                    values[col] = val
                values['RegistrationNo']=self.cur_code
                values['EnterpriseName']=self.org_name
                jsonarray.append(values)
                values = {}
            json_hehuoren=json.dumps(jsonarray,ensure_ascii=False)
            print 'json_hehuoren',json_hehuoren
        else:
            while (100):
                index_element = self.find_element("html/body/form/table/tbody/tr[last()]/th/font/following-sibling::a[1]")
#                 print index_element.text.strip() 
                if index_element.get_attribute('onclick').startswith('jumppage'):
                    tr_element_list = self.find_elements("html/body/form/table/tbody/tr[position()<last()]")
                    th_element_list = self.find_elements("html/body/form/table/tbody/tr[2]/th")
                    for tr_element in tr_element_list[2:]:            
                        td_element_list = tr_element.find_elements_by_xpath('td')
                        col_nums = len(th_element_list)
                        for j in range(col_nums):
                            col_dec = th_element_list[j].text.strip().replace('\n','')
                            col=touziren_column_dict[col_dec]
                            td=td_element_list[j]
                            val = td.text.strip()
                            values[col] = val
                        values['RegistrationNo']=self.cur_code
                        values['EnterpriseName']=self.org_name
                        jsonarray.append(values)
                        values = {}
                    if index_element.text.strip()!=u'>>':
                            index_element.click()
                    else: 
                        break   
                json_hehuoren=json.dumps(jsonarray,ensure_ascii=False)
                print 'json_hehuoren',json_hehuoren

                    
    def load_touziren(self, table_element):
        jsonarray=[]   
        values = {} 
        table_element = self.find_element(".//*[@id='touziren']")
        tr_element_list = table_element.find_elements_by_xpath("tbody/tr")
        th_element_list = table_element.find_elements_by_xpath("tbody/tr[2]/th")
        row_cnt=len(tr_element_list)
        if row_cnt>2:
            for tr_element in tr_element_list:
                td_element_list = tr_element.find_elements_by_xpath("td")
                col_nums = len(th_element_list)
                for j in range(col_nums):
                    col_dec = th_element_list[j].text.strip().replace('\n','')
                    col=touziren_column_dict[col_dec]
                    td=td_element_list[j]
                    val = td.text.strip()
                    values[col] = val
                values['RegistrationNo']=self.cur_code
                values['EnterpriseName']=self.org_name
                jsonarray.append(values)
                values = {}
            json_touziren=json.dumps(jsonarray,ensure_ascii=False)
            print 'json_touziren',json_touziren
                
                           
    def load_jiatingchengyuan(self, table_element):
        jsonarray=[]   
        values = {}
        table_element = self.find_element(".//*[@id='memberTable']")
        tr_element_list = table_element.find_elements_by_xpath("tbody/tr")
        th_element_list = table_element.find_elements_by_xpath("tbody/tr[2]/th")
        for tr_element in tr_element_list[2:]:
            td_element_list = tr_element.find_elements_by_xpath('td')
            list_length = len(td_element_list)
            fixed_length = list_length - list_length % 2
            for j in range(fixed_length):
                    col_dec = th_element_list[j].text.strip().replace('\n','')
                    col=jiatingchengyuan_column_dict[col_dec]
                    td=td_element_list[j]
                    val = td.text.strip()
                    values[col] = val
                    if len(values) == 2:
                        values['RegistrationNo']=self.cur_code
                        values['EnterpriseName']=self.org_name
                        jsonarray.append(values)
                        values = {}
        json_jiatingchengyuan=json.dumps(jsonarray,ensure_ascii=False)
        print 'json_jiatingchengyuan',json_jiatingchengyuan
                    
    def load_chengyuanmingce(self, table_element):
        jsonarray=[]   
        values = {}
        table_element = self.find_element(".//*[@id='memberTable']")
        tr_element_list = table_element.find_elements_by_xpath("tbody/tr")
        th_element_list = table_element.find_elements_by_xpath("tbody/tr[2]/th")
        for tr_element in tr_element_list[2:]:
            td_element_list = tr_element.find_elements_by_xpath('td')
            list_length = len(td_element_list)
            fixed_length = list_length - list_length % 3
            for j in range(fixed_length):
                    col_dec = th_element_list[j].text.strip().replace('\n','')
                    col=chengyuanmingce_column_dict[col_dec]
                    td=td_element_list[j]
                    val = td.text.strip()
                    values[col] = val
                    if len(values) == 2:
                        values['RegistrationNo']=self.cur_code
                        values['EnterpriseName']=self.org_name
                        jsonarray.append(values)
                        values = {}
        json_chengyuanmingce=json.dumps(jsonarray,ensure_ascii=False)
        print 'json_chengyuanmingce',json_chengyuanmingce
          
    def load_fenzhijigou(self,table_desc):
        jsonarray=[]   
        values = {}
        table_tr_elements=self.find_elements("//*[@id='table2']/tr")
        if len(table_tr_elements)>3:
            tr_element_list = self.find_elements("//*[@id='table2']/tr/td/parent::*")
            th_element_list = self.find_elements("//*[@id='table2']/tr[2]/th")
            id=1
            for tr_element in tr_element_list:
                td_element_list = tr_element.find_elements_by_xpath("td")
                col_nums = len(th_element_list)
                for j in range(col_nums):
                    col_dec = th_element_list[j].text.strip().replace('\n','')
                    col=fenzhijigou_column_dict[col_dec]
                    td=td_element_list[j]
                    val = td.text.strip()
                    values[col] = val
                values['RegistrationNo']=self.cur_code
                values['EnterpriseName']=self.org_name
                values['rowkey'] = values['EnterpriseName']+'_08_'+ values['RegistrationNo']+'_'+str(id)
                json_fenzhijigou=json.dumps(values,ensure_ascii=False)
                print 'json_fenzhijigou',json_fenzhijigou 
                values = {}    
                id+=1
                  
                

    def load_qingsuan(self, table):
        pass

    def load_dongchandiyadengji(self):
        jsonarray=[]   
        values = {}
        table_iframe_list = self.find_elements("//div [@id='dcdyDiv']/div/iframe")
        for iframe_element in table_iframe_list:
            self.driver.switch_to.frame(iframe_element)
#             table_zyry = self.find_element("html/body/form/table")        
            table_element = self.find_element("//*[@id='iframeFrame']/table")
            row_cnt = len(table_element.find_elements_by_xpath("tbody/tr"))
            if row_cnt > 3:
                tr_element_list = self.find_elements("//*[@id='iframeFrame']/table/tbody/tr[position()<last()]")
                th_element_list = self.find_elements("//*[@id='iframeFrame']/table/tbody/tr[2]/th")
                id=1
                for tr_element in tr_element_list[2:]:     
                    td_element_list = tr_element.find_elements_by_xpath('td')
                    col_nums = len(th_element_list)
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n','')
                        col=dongchandiyadengji_column_dict[col_dec]
                        td = td_element_list[j]
                        val = td.text.strip()
                        if val == u'详情':
                            link=td.find_element_by_xpath('a').get_attribute('href')
                            values[col]=link
                        else:
                            values[col]=val
                    values['RegistrationNo']=self.cur_code
                    values['EnterpriseName']=self.org_name
                    values['rowkey'] = values['EnterpriseName']+'_11_'+ values['RegistrationNo']+'_'+str(id)
                    json_dongchandiyadengji=json.dumps(values,ensure_ascii=False)
                    print 'json_dongchandiyadengji',json_dongchandiyadengji
                    values = {}
                    id+=1
        self.driver.switch_to.default_content()
# 
    def load_guquanchuzhidengji(self):
        jsonarray=[]   
        values = {}
        table_iframe_list = self.find_elements("//div [@id='gqczdjDiv']/div/iframe")
        for iframe_element in table_iframe_list:
            self.driver.switch_to.frame(iframe_element)
            table_element = self.find_element("//*[@id='gdczdjFrame']/table")
            row_cnt = len(table_element.find_elements_by_xpath("tbody/tr"))
            if row_cnt > 2:
                tr_element_list = self.find_elements("//*[@id='gdczdjFrame']/table/tbody/tr[position()<last()]")
                th_element_list = self.find_elements("//*[@id='gdczdjFrame']/table/tbody/tr[2]/th")
                id=1
                for tr_element in tr_element_list[2:]:        
                    td_element_list = tr_element.find_elements_by_xpath('td')
                    col_nums = len(th_element_list)
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n','')
                        col=guquanchuzhidengji_column_dict[col_dec]
                        td = td_element_list[j]
                        val = td.text.strip()
                        if val == u'详情':
                            link=td.find_element_by_xpath('a').get_attribute('href')
                            values[col]=link                    
                        else:
                            values[col]=val
                    values['RegistrationNo']=self.cur_code
                    values['EnterpriseName']=self.org_name
                    values['rowkey'] = values['EnterpriseName']+'_12_'+ values['RegistrationNo']+'_'+str(id)
                    json_guquanchuzhidengji=json.dumps(values,ensure_ascii=False)
                    print 'json_guquanchuzhidengji',json_guquanchuzhidengji
                    values = {}
                    id+=1
        self.driver.switch_to.default_content()
# 
    def load_xingzhengchufa(self):
        jsonarray=[]   
        values = {}
        table_iframe = self.find_element("//div [@id='xzcfDiv']/div/iframe")
        self.driver.switch_to.frame(table_iframe)
        table_element = self.find_element("//*[@id='xzcfForm']/table")
        row_cnt = len(table_element.find_elements_by_xpath("tbody/tr"))
        if row_cnt > 3:
            tr_element_list = self.find_elements("//*[@id='xzcfForm']/table/tbody/tr[pisition()<last()]")
            th_element_list = self.find_elements("//*[@id='xzcfForm']/table/tbody/tr[2]/th")
            id=1
            for tr_element in tr_element_list[2:]:        
                td_element_list = tr_element.find_elements_by_xpath('td')
                col_nums = len(th_element_list)
                for j in range(col_nums):
                    col_dec = th_element_list[j].text.strip().replace('\n','')
                    col=xingzhengchufa_column_dict[col_dec]
                    td = td_element_list[j]
                    val = td.text.strip()
                    values[col]=val
                values['RegistrationNo']=self.cur_code
                values['EnterpriseName']=self.org_name
                values['rowkey'] = values['EnterpriseName']+'_13_'+ values['RegistrationNo']+'_'+str(id)
                json_xingzhengchufa=json.dumps(values,ensure_ascii=False)
                print 'json_xingzhengchufa',json_xingzhengchufa
                values = {}
                id+=1
        self.driver.switch_to.default_content()

    def load_jingyingyichang(self):
        jsonarray=[]   
        values = {}
        table_iframe = self.find_element("//div [@id='jyycDiv']/div/iframe")
        self.driver.switch_to.frame(table_iframe)
        table_element = self.find_element("//*[@id='list_jyycxx']/table")
        row_cnt = len(table_element.find_elements_by_xpath("tbody/tr"))
        if row_cnt > 2:
            id=1
            tr_element_list = self.find_elements("//*[@id='list_jyycxx']/table/tbody/tr")
            th_element_list = self.find_elements("//*[@id='list_jyycxx']/table/tbody/tr[2]/th")
            for tr_element in tr_element_list[2:]:        
                td_element_list = tr_element.find_elements_by_xpath('td')
                col_nums = len(th_element_list)
                for j in range(col_nums):
                    col_dec = th_element_list[j].text.strip().replace('\n','')
                    col=jingyingyichang_column_dict[col_dec]
                    td = td_element_list[j]
                    val = td.text.strip()
                    values[col]=val
                values['RegistrationNo']=self.cur_code
                values['EnterpriseName']=self.org_name
                values['rowkey'] = values['EnterpriseName']+'_14_'+ values['RegistrationNo']+'_'+str(id)
                json_jingyingyichang=json.dumps(values,ensure_ascii=False)
                print 'json_jingyingyichang',json_jingyingyichang
                values = {}
                id+=1
        self.driver.switch_to.default_content()
# 
    def load_yanzhongweifa(self):
        jsonarray=[]   
        values = {}
        table_iframe = self.find_element("//div [@id='yzwfDiv']/div/iframe")
        self.driver.switch_to.frame(table_iframe)
        table_element = self.find_element("//*[@id='iframeFrame']/table")
        row_cnt = len(table_element.find_elements_by_xpath("tbody/tr"))
        if row_cnt > 3:
            tr_element_list = self.find_elements("//*[@id='iframeFrame']/table/tbody/tr[pisition()<last()]")
            th_element_list = self.find_elements("//*[@id='iframeFrame']/table/tbody/tr[2]/th")
            id=1
            for tr_element in tr_element_list[2:]:        
                td_element_list = tr_element.find_elements_by_xpath('td')
                col_nums = len(th_element_list)
                for j in range(col_nums):
                    col_dec = th_element_list[j].text.strip().replace('\n','')
                    col=yanzhongweifa_column_dict[col_dec]
                    td = td_element_list[j]
                    val = td.text.strip()
                    values[col]=val
                values['RegistrationNo']=self.cur_code
                values['EnterpriseName']=self.org_name
                values['rowkey'] = values['EnterpriseName']+'_15_'+ values['RegistrationNo']+'_'+str(id)
                json_yanzhongweifa=json.dumps(values,ensure_ascii=False)
                print 'json_yanzhongweifa',json_yanzhongweifa
                values = {}
                id+=1
        self.driver.switch_to.default_content()
# 
    def load_chouchajiancha(self):
        jsonarray=[]   
        values = {}
        table_iframe = self.find_element("//div [@id='ccycDiv']/div/iframe")
        self.driver.switch_to.frame(table_iframe)
        table_tr_element=self.find_elements("//div [@id='jyycxx']/form/table//tr")
        row_cnt = len(table_tr_element)
        print row_cnt
        if row_cnt > 3:
            tr_element_list = self.find_elements("//div [@id='jyycxx']/form/table//td/parent::*")
            th_element_list = self.find_elements("//div [@id='jyycxx']/form/table//tr[2]/th")
            id=1
            for tr_element in tr_element_list:        
                td_element_list = tr_element.find_elements_by_xpath('td')
                col_nums = len(th_element_list)
                for j in range(col_nums):
                    col_dec = th_element_list[j].text.strip().replace('\n','')
                    col=chouchajiancha_column_dict[col_dec]
                    td = td_element_list[j]
                    val = td.text.strip()
                    values[col]=val
                values['RegistrationNo']=self.cur_code
                values['EnterpriseName']=self.org_name
                values['rowkey'] = values['EnterpriseName']+'_16_'+ values['RegistrationNo']+'_'+str(id)
                json_chouchajiancha=json.dumps(values,ensure_ascii=False)
                print 'json_chouchajiancha',json_chouchajiancha
                values = {}
                id+=1
        self.driver.switch_to.default_content()

if __name__ == '__main__':
    name_list = [u'本草汇（北京）环境治理有限公司']#'430000000057587',,u'北京金顺蝶科技有限公司'
    searcher = BeiJingFirefoxSearcher()
    searcher.set_config()
    if searcher.build_driver() == 0:
        for name in name_list:
            print time.strftime('%Y-%m-%d %X', time.localtime())
            searcher.search(name)
            print time.strftime('%Y-%m-%d %X', time.localtime())
            # break
