# coding=gbk
import PackageTool
import requests
import os
from PIL import Image
from bs4 import BeautifulSoup
import json
import re
import uuid
from FuJianConfig import *
import datetime
from requests.exceptions import RequestException
import sys
import time
from gs import MSSQL
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
import random
import subprocess
from gs.Searcher import Searcher
from gs.GeetestDistance import GeetestDistance
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
    tag_a = ''
    # save_tag_a = None
    load_func_dict = {}

    def __init__(self):
        super(FuJianSearcher, self).__init__(use_proxy=True)
        self.headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:47.0) Gecko/20100101 Firefox/47.0",
                        "Host": "fj.gsxt.gov.cn",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Encoding": "gzip, deflate",
                        "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
                        "Connection": "keep-alive",
                        "Referer": "http://fj.gsxt.gov.cn/notice/search/ent_info_list",
                        # "Upgrade-Insecure-Requests": "1",
                        "Content-type": "application/json"
                        }
        # self.cur_time = '%d' % (time.time() * 1000)
        # self.get_verify_ip()
        # self.json_result = {}
        self.set_config()
        self.log_name = self.topic + "_" + str(uuid.uuid1())
        time = datetime.datetime.now()
        self.time = time.strftime('%Y%m%d')
        self.load_func_dict[u'动产抵押登记信息'] = self.load_dongchandiyadengji
        self.load_func_dict[u'股权出质登记信息'] = self.load_guquanchuzhidengji
        self.load_func_dict[u'行政处罚信息'] = self.load_xingzhengchufa
        self.load_func_dict[u'经营异常信息'] = self.load_jingyingyichang
        self.load_func_dict[u'纳入经营异常名录信息'] = self.load_jingyingyichang
        self.load_func_dict[u'严重违法信息'] = self.load_yanzhongweifa
        self.load_func_dict[u'严重违法失信信息'] = self.load_yanzhongweifa
        self.load_func_dict[u'严重违法失信企业名单（黑名单）信息'] = self.load_yanzhongweifa
        self.load_func_dict[u'抽查检查信息'] = self.load_chouchajiancha
        self.load_func_dict[u'抽查检查结果信息'] = self.load_chouchajiancha
        self.load_func_dict[u'营业执照信息'] = self.load_jiben
        self.load_func_dict[u'股东及出资信息'] = self.load_gudong
        self.load_func_dict[u'发起人及出资信息'] = self.load_gudong
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
        self.plugin_path = os.path.join(sys.path[0], '../shanghai/ocr/type34.bat')
        self.group = 'Crawler'  # 正式
        self.kafka = KafkaAPI("GSCrawlerResult")  # 正式
        # self.group = 'CrawlerTest'  # 测试
        # self.kafka = KafkaAPI("GSCrawlerTest")  # 测试
        self.topic = 'GsSrc35'
        self.province = u'福建省'
        self.kafka.init_producer()

    def get_validate_image_save_path(self):
        return os.path.join(sys.path[0], '../temp/' + str(random.random())[2:] + '.png')

    def get_validate_file_path(self):
        return os.path.join(sys.path[0], '../temp/' + str(random.random())[2:] + '.txt')

    def recognize_yzm(self, validate_path, validate_result_path):
        cmd = self.plugin_path + " " + validate_path+ " " + validate_result_path
        # print 'validate_result_path', validate_result_path
        p = subprocess.Popen(cmd.encode('gbk', 'ignore'), stdout=subprocess.PIPE)
        p.communicate()
        fo = open(validate_result_path, 'r')
        answer = fo.readline().strip()
        fo.close()
        # print 'answer: '+answer.decode('gbk', 'ignore')
        os.remove(validate_path)
        os.remove(validate_result_path)
        return answer.decode('gbk', 'ignore')

    def get_yzm(self):
        params = {'ra': '%.15f' % random.random(), 'preset:': ''}
        image_url = 'http://www.sgs.gov.cn/notice/captcha'
        r = self.get_request(image_url, params=params, verify=False)
        # print r.headers
        yzm_path = self.get_validate_image_save_path()
        with open(yzm_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    f.flush()
            f.close()
        yzm_file_path = self.get_validate_file_path()
        yzm = self.recognize_yzm(yzm_path,yzm_file_path)
        return yzm

    def get_session_token(self):
        r = self.get_request('http://www.sgs.gov.cn/notice/home', verify=False)
        idx_1 = r.text.index('session.token": "') + len('session.token": "')
        idx_2 = r.text.index('"', idx_1)
        self.session_token = r.text[idx_1:idx_2]

    def get_tag_a_from_page(self, keyword, flags=0):
        return self.get_tag_a_from_page0(keyword)

    def get_tag_a_from_page0(self, keyword):
        # self.flag = self.get_the_mc_or_code(keyword)
        # print self.flag
        url = 'http://fj.gsxt.gov.cn/notice/home'
        driver = webdriver.Firefox()
        # driver = webdriver.Chrome()
        driver.set_window_size(1920, 1080)
        driver.get(url)
        input_path = r".//*[@id='keyword']"
        submit_path = r".//*[@id='buttonSearch']"
        driver.find_element_by_xpath(input_path).clear()
        driver.find_element_by_xpath(input_path).send_keys(keyword)
        time.sleep(3)
        driver.find_element_by_xpath(submit_path).click()
        WebDriverWait(driver, 10).until(lambda the_driver: the_driver.find_element_by_xpath(".//*[@class='gt_slider_knob gt_show']"))
        time.sleep(1)
        # print 'before:', time.ctime()
        fa = 0
        element = driver.find_element_by_xpath(".//*[@class='gt_slider_knob gt_show']")
        try:
            for i in range(1, 15):
                # print '%d step1--click' % i
                ActionChains(driver).click_and_hold(on_element=element).perform()
                time.sleep(1)
                driver.get_screenshot_as_file('D:\\losg.jpg')
                time.sleep(1)
                img = Image.open('D:\\losg.jpg')
                # img.show()
                img_crop = img.crop((818, 419, 1078, 535))
                # img_crop.show()
                # img_path = os.path.join(sys.path[0], '../temp/' + str(random.random())[2:] + '.png')
                img_path = 'D:\\hebeijpg\\' + str(random.random())[2:] + '.png'
                # print 'img_path', img_path
                # img_path = 'E:\\losk.jpg'
                ocr_path = os.path.join(sys.path[0], '../shanghai/slideocr/' + 'huadongjuli.exe')
                # print "ocr_path:", ocr_path
                img_path1 = 'D:\\zfjpg300\\' + str(random.random())[2:] + '.png'
                # print 'img_path1', img_path1
                # img_crop.save('E:\\losk.jpg')
                img_crop.save(img_path)
                if i == 11:
                    img_crop.save(img_path1)
                cmd = ocr_path + '  ' + img_path
                print 'cmd', cmd
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
                # print 'alive'
                results = p.stdout.readlines()
                # print results[0].strip()
                offset = int(results[0].strip())
                # print 'offset', offset
                # print '%d step2--move' % i
                # ActionChains(driver).move_to_element_with_offset(to_element=element, xoffset=i*3, yoffset=10).perform()
                ActionChains(driver).move_to_element_with_offset(to_element=element, xoffset=offset+i*2, yoffset=10).perform()
                time.sleep(1)
                # print '%d step3--release' % i
                ActionChains(driver).release(on_element=element).perform()
                time.sleep(2)
                try:
                    WebDriverWait(driver, 20).until(lambda the_driver: the_driver.find_element_by_xpath(".//*[@class='contentA']"))
                    # WebDriverWait(driver, 20).until(EC.presence_of_element_located(By.Class('contentA')))
                    # print 'element_found'
                    break
                except Exception as e:
                    print 'yzm_exception', e
                    # continue
                fa += 1
            # print '**m**', fa
        except:
            # print 'geetest--pass--success!'
            driver.get_screenshot_as_file(r'D:\\hbgee.jpg')
        # print 'after:', time.ctime()
        # 结果页面
        try:
            # source = driver.find_element_by_xpath(".//*[@id='wrap1366']/div[3]/div")
            source = driver.find_element_by_xpath(".//*[@class='contentA']")
            html = source.get_attribute("innerHTML")
            driver.quit()
        except:
            driver.quit()
            return None

        soup = BeautifulSoup(html, 'html5lib')
        # print 'soup:', soup
        results = soup.find_all(class_='tableContent')
        # print 'results_lens', len(results)
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
                # print cnt, name, code, tagA
                company_list.append(name)
                company_code.append(code)
                company_tags.append(tagA)
        else:
            # print '**'*100, u'查询无结果'
            self.info(u'查询无结果')
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
        # print 'name:', company_list[0], 'code:', company_code[0], 'tagA:', company_tags[0]
        # r = requests.get(company_tags[0])
        # print r.text,r.headers
        return company_tags[0]

    def get_image(self, driver, div):
        #找到图片所在的div
        print div
        background_images=driver.find_elements_by_xpath(div)
        location_list=[]
        imageurl=''
        #图片是被CSS按照位移的方式打乱的,我们需要找出这些位移,为后续还原做好准备
        for background_image in background_images:
            imageurl=re.findall("background-image: url\(\"(.*)\"\); background-position: (.*)px (.*)px;",background_image.get_attribute('style'))[0][0]
        imageurl=re.findall("background-image: url(\"(.*)\")", background_image.get_attribute('style'))
        print imageurl
        #替换图片的后缀,获得图片的URL
        imageurl=imageurl.replace("webp","jpg")
        #获得图片的名字
        imageName = imageurl.split('/')[-1]
        # session = requests.session()
        r = self.get_request(imageurl, headers=self.headers, verify=False)
        with open(imageName, 'wb') as f:
            f.write(r.content)
            f.close()
        return imageName

    def get_search_args(self, tag_a, keyword):
        self.tag_a = tag_a
        if tag_a:
            return 1
        else:
            return 0

    def parse_detail(self):
        uuid = self.tag_a.split('uuid=')[1].split('&tab')[0]
        tab = self.tag_a.split('=', 2)[2]
        params = {"tabPanel": tab, "uuid": uuid}
        r2 = self.post_request(self.tag_a, data=params, headers=self.headers, verify=False)
        # print r2.text
        if u'该市场主体不在公示范围' not in r2.text:
            resdetail = BeautifulSoup(r2.text, 'lxml')
            if not self.save_tag_a:
                li_list = resdetail.find(id='boxShadow1').find(class_='tableResult fL').find_all('li')
                mc = li_list[0].contents[0].text
                code = li_list[1].contents[1].text
                # print 'mc:', mc
                # print 'code:', code
                self.cur_mc = mc
                self.cur_code = code
            div_element_list2 = resdetail.find(id='sub_tab_01')
            # print 'div_element_list2:', div_element_list2
            div_element_list = resdetail.find(id='sub_tab_01').find_all(class_='content1')
            for div_element in div_element_list:
                table_element_list = div_element.find_all('table')
                table_desc = div_element.find(class_="titleTop").find('h1').contents[0].strip().split('\n')[0]
                # print 'table_desc', table_desc
                for table_element in table_element_list:
                    row_cnt = len(table_element.find_all("tr"))
                    # if table_desc in self.load_func_dict:
                    #     if table_desc in (u'知识产权出质登记信息',u'商标注册信息'):
                    #         continue
                        # if table_desc in(u'营业执照信息',u'股东及出资信息'):
                        #     self.load_func_dict[table_desc](table_element)
                        # else:
                        #     self.load_func_dict[table_desc](table_element)
                        # elif row_cnt > 2:
                    if row_cnt:
                        if table_desc in (u'知识产权出质登记信息',u'商标注册信息'):
                             continue
                        else:
                            self.load_func_dict[table_desc](table_element)
                    elif table_desc in (u'参加经营的家庭成员姓名'):
                        self.load_func_dict[table_desc](table_element)
                    else:
                        raise Exception("unknown table!")
            self.load_jingyingyichang(self.tag_a)
            self.load_xingzhengchufa(self.tag_a)
        else:
            print u'该市场主体不在公示范围'

    def load_jiben(self, table_element):
        self.info(u'解析基本信息...')
        jsonarray = []
        tr_element_list = table_element.find_all("tr")
        values = {}
        for tr_element in tr_element_list:
            td_element_list = tr_element.find_all('td')
            col_nums = len(td_element_list)
            for i in range(col_nums):
                # col_dec = td_element_list[i].contents[0].strip().split('\n')[0]
                col_dec_1 = td_element_list[i].contents
                if col_dec_1:
                    col_dec_2 = td_element_list[i].contents[0].strip().split('\n')[0]
                    col_dec_2.encode('utf-8')
                    col_dec = col_dec_2.replace(u'·', '').replace(u'：', '').strip().replace('', '')
                    col = jiben_column_dict[col_dec]
                    val = td_element_list[i].contents[1].text
                    if col != u'':
                        values[col] = val
                        if col == 'Registered_Info:registrationno':
                            if len(val) == 18:
                                values['Registered_Info:tyshxy_code'] = val
                            else:
                                values['Registered_Info:zch'] = val
                            self.cur_zch = val
        values['Registered_Info:province'] = self.province
        values['rowkey'] = self.cur_mc+'_01_'+self.cur_code+'_'
        jsonarray.append(values)
        self.json_result['Registered_Info'] = jsonarray
        # json_jiben =json.dumps(jsonarray, ensure_ascii=False)
        # print 'json_jiben', json_jiben

    def load_gudong(self, table_element):
        self.info(u'解析股东信息...')
        tr_element_list = table_element.find_all("tr")
        th_element_list = table_element.find_all('th')[1:]
        id = 1
        values = {}
        values_before = {}
        jsonarray = []
        self.json_result['Shareholder_Info'] = []
        for tr_element in tr_element_list[1:-1]:
            td_element_list = tr_element.find_all('td')[1:]
            col_nums = len(th_element_list)
            # self.json_result['Shareholder_Info'].append({})
            for i in range(col_nums):
                col_dec = th_element_list[i].get_text().strip().replace('\n', '')
                col = gudong_column_dict[col_dec]
                td = td_element_list[i]
                val = td.get_text().strip()
                values_before[col] = val
            # print 'values_before:', values_before
            # print "td_element_list[4].text.strip()", td_element_list[4].text.strip()
            if td_element_list[4].text.strip() == u'查看' or td_element_list[4].text.strip() == u'详情':
                link_1 = td_element_list[4].a['onclick']
                link = link_1.split("('")[1].split("')")[0]
                # self.json_result['Shareholder_Info:shareholder_details'] = link
                # print 'link:', link
                detail_list = self.get_gu_dong_detail(link)
                # print 'detail_list:', detail_list
                values_before['Shareholder_Info:shareholder_details'] = link
                for detail_json in detail_list:
                    for k in detail_json:
                        if k == 'Shareholder_Info:subscripted_capital':
                            values_before['Shareholder_Info:subscripted_capital'] = detail_json[k]
                        elif k == 'Shareholder_Info:actualpaid_capital':
                            values_before['Shareholder_Info:actualpaid_capital'] = detail_json[k]
                # print "values_before",values_before
                # print "self.row_len", self.row_len, self.len_renjiao_tr,self.len_shijiao_tr
                if self.len_renjiao_tr < self.len_shijiao_tr:
                    detail_list.insert(1, {})
                elif self.len_renjiao_tr > self.len_shijiao_tr:
                    detail_list.insert(self.len_renjiao_tr+1, {})
                # print "detail_list_renjiao:", detail_list
                for i in range(self.row_len):
                    if self.len_renjiao_tr == self.len_shijiao_tr:
                        values = values_before.copy()
                        values.update(detail_list[i+1])
                        values.update(detail_list[i+self.len_renjiao_tr+1])
                        self.json_result['Shareholder_Info'].append(values)
                    elif self.len_renjiao_tr > self.len_shijiao_tr:
                        values = values_before.copy()
                        values.update(detail_list[i+1])
                        values.update(detail_list[i+self.len_renjiao_tr+1])
                        self.json_result['Shareholder_Info'].append(values)
                    elif self.len_renjiao_tr < self.len_shijiao_tr:
                        values = values_before.copy()
                        values.update(detail_list[i+1])
                        values.update(detail_list[i+self.len_renjiao_tr+2])
                        self.json_result['Shareholder_Info'].append(values)
                # print "self.json_result['Shareholder_Info']", self.json_result['Shareholder_Info']
            else:
                self.json_result['Shareholder_Info'].append({})
                # self.json_result['Shareholder_Info'].append(values_before)
                self.json_result['Shareholder_Info'][-1] = values_before
                values_before = {}
            for i in range(len(self.json_result['Shareholder_Info'])):
                self.json_result['Shareholder_Info'][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc,  '04', self.cur_zch, self.today, i+1)
                self.json_result['Shareholder_Info'][i]['Shareholder_Info' + ':registrationno'] = self.cur_zch
                self.json_result['Shareholder_Info'][i]['Shareholder_Info' + ':enterprisename'] = self.cur_mc
                self.json_result['Shareholder_Info'][i]['Shareholder_Info' + ':id'] = i+1
            # print "self.json_result['Shareholder_Info']", self.json_result['Shareholder_Info']

    def get_gu_dong_detail(self, link):
        """
        查询股东详情信息
        :param id:
        :return:
        """
        detail_dict_list = []
        url = 'http://sh.gsxt.gov.cn/notice/notice/view_investor?uuid='+link
        params = {'uuid': link}
        r = self.get_request(url, params=params)
        soup = BeautifulSoup(r.text, 'html5lib')
        gudong_text = r.text
        gudong_table = soup.find_all(class_='content2')[0]
        # print 'gudong_text:', gudong_text
        gudong_tr_element_list = gudong_table.find_all('tr')
        if len(gudong_tr_element_list) == 3:
            detail_dict_list.append({})
            detail_dict_list[-1]['Shareholder_Info:shareholder_name'] = gudong_tr_element_list[0].find('td').text.strip()
            sub_content = gudong_text[(gudong_text.index(u'认缴总额')):(gudong_text.index(u'实缴总额'))]
            # print 'sub_content', sub_content
            sub_content= sub_content.encode("utf-8")
            count_sub = sub_content.count('invtAll +=')
            if count_sub == 1:
                sub_content_1 = sub_content.split("at('", 1)[1].split("')", 1)[0]
                detail_dict_list[-1]['Shareholder_Info:subscripted_capital'] = str(sub_content_1)
            elif count_sub > 1:
                sub_content_total = 0
                for i in range(count_sub):
                    sub_content_1 = sub_content.split("at('", i+1)[i+1].split("')",1)[0]
                    sub_content_2 = float(sub_content_1.encode("utf-8"))
                    sub_content_total += sub_content_2
                detail_dict_list[-1]['Shareholder_Info:subscripted_capital'] = sub_content_total
            detail_dict_list[-1]['Shareholder_Info:subscripted_capital'] = \
                str(detail_dict_list[-1]['Shareholder_Info:subscripted_capital'])+u'万元'
            # print 'Shareholder_Info:subscripted_capital', detail_dict_list[-1]['Shareholder_Info:subscripted_capital']
            act_content = gudong_text[(gudong_text.index(u'实缴总额')):(gudong_text.index("$('#invtActlAll')"))]
            # print 'act_content', act_content
            count_act = act_content.count('invtActlAll +=')
            if count_act == 1:
                act_content_1 = act_content.split("at('", 1)[1].split("')", 1)[0]
                detail_dict_list[-1]['Shareholder_Info:actualpaid_capital'] = str(act_content_1)
            elif count_act > 1:
                act_content_2_total = 0
                for i in range(count_act):
                    act_content_1 = act_content.split("at('", i+1)[i+1].split("')", 1)[0]
                    act_content_2 = float(act_content_1.encode("utf-8"))
                    # print 'act_content_2', type(act_content_2), act_content_2
                    act_content_2_total += act_content_2
                detail_dict_list[-1]['Shareholder_Info:actualpaid_capital'] = act_content_2_total
            detail_dict_list[-1]['Shareholder_Info:actualpaid_capital'] = \
                str(detail_dict_list[-1]['Shareholder_Info:actualpaid_capital']) + u'万元'
            # print 'Shareholder_Info:actualpaid_capital',detail_dict_list[-1]['Shareholder_Info:actualpaid_capital']
        renjiao_table = soup.find_all(class_='content2')[1]
        renjiao_tr_element_list = renjiao_table.find_all('tr')[1:]
        renjiao_th_element_list = renjiao_table.find_all('th')
        for tr_element in renjiao_tr_element_list:
            detail_dict_list.append({})
            td_element_list = tr_element.find_all('td')
            col_nums = len(td_element_list)
            for j in range(col_nums):
                col_dec = renjiao_th_element_list[j].text.strip().replace('\n', '')
                col = gudong_column_dict[col_dec]
                val = td_element_list[j].text.strip().replace('\n', '')
                detail_dict_list[-1][col] = val
            detail_dict_list[-1]['Shareholder_Info:subscripted_amount']=\
                detail_dict_list[-1]['Shareholder_Info:subscripted_amount'] + u'万元'
        shijiao_table = soup.find_all(class_='content2')[2]
        shijiao_tr_element_list = shijiao_table.find_all('tr')[1:]
        shijiao_th_element_list = shijiao_table.find_all('th')
        for tr_element in shijiao_tr_element_list:
            detail_dict_list.append({})
            td_element_list = tr_element.find_all('td')
            col_nums = len(td_element_list)
            for j in range(col_nums):
                col_dec = shijiao_th_element_list[j].text.strip().replace('\n', '')
                col = gudong_column_dict[col_dec]
                val = td_element_list[j].text.strip().replace('\n', '')
                detail_dict_list[-1][col] = val
                # print "detail_dict_list[-1][col]_2:", col,  val
            # print u'实缴明细详情', detail_dict_list
            detail_dict_list[-1]['Shareholder_Info:actualpaid_amount']= \
                detail_dict_list[-1]['Shareholder_Info:actualpaid_amount'] + u'万元'
        self.len_renjiao_tr = len(renjiao_tr_element_list)
        self.len_shijiao_tr = len(shijiao_tr_element_list)
        self.row_len = max(self.len_renjiao_tr, self.len_shijiao_tr)
        return detail_dict_list

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
                col = hehuoren_column_dict[col_dec]
                td = td_element_list[i]
                val = td.get_text().strip()
                values[col] = val
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
        self.info(u'解析主管部门（出资人）信息...')
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
                col= DICInfo_column_dict[col_dec]
                td = td_element_list[i]
                val = td.get_text().strip()
                values[col] = val
#                 print col,val
            values['DIC_Info:registrationno']=self.cur_code
            values['DIC_Info:enterprisename']=self.cur_mc
            values['DIC_Info:id']=str(id)
            values['rowkey']=self.cur_mc+'_10_'+self.cur_code+'_'+self.time+str(id)
            jsonarray.append(values)
            values = {}
            id+=1
        self.json_result['DIC_Info']=jsonarray
#         json_DICInfo=json.dumps(jsonarray,ensure_ascii=False)
#         print 'json_DICInfo',json_DICInfo

    def load_biangeng(self, table_element):
        self.info(u'解析变更信息...')
        tr_element_list = table_element.find_all("tr")[1:-1]
        th_element_list = table_element.find_all('th')[1:]
        jsonarray = []
        values = {}
        id = 1
        for tr_element in tr_element_list:
            td_element_list = tr_element.find_all('td')[1:]
            col_nums = len(th_element_list)
            for i in range(col_nums):
                col_dec = th_element_list[i].text.strip().replace('\n', '')
                # print "col_dec:", col_dec
                col = biangeng_column_dict[col_dec]
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
        self.json_result['Changed_Announcement'] = jsonarray
#         json_biangeng=json.dumps(jsonarray,ensure_ascii=False)
#         print 'json_biangeng',json_biangeng

    def load_chexiao(self, table_element):
        pass

    def load_zhuyaorenyuan(self, table_element):
        self.info(u'解析主要人员信息...')
        tr_element_list = table_element.find_all("tr")[1:]
        # print 'tr_element', tr_element
        jsonarray = []
        values = {}
        id = 1
        # if tr_element:
        for tr_element in tr_element_list:
            td_element_list = tr_element.find_all('ul')
            for td_element in td_element_list:
                values['KeyPerson_Info:keyperson_name'] = td_element.find_all('li')[0].text.strip().replace('\n', '')
                values['KeyPerson_Info:keyperson_position'] = td_element.find_all('li')[1].text.strip().replace('\n', '')
                values['KeyPerson_Info:registrationno'] = self.cur_code
                values['KeyPerson_Info:enterprisename'] = self.cur_mc
                values['KeyPerson_Info:id'] = str(id)
                values['rowkey'] = self.cur_mc+'_06_'+self.cur_code+'_'+self.time+str(id)
                jsonarray.append(values)
                values = {}
                id += 1
        self.json_result['KeyPerson_Info']= jsonarray
        # json_zhuyaorenyuan=json.dumps(jsonarray,ensure_ascii=False)
        # print 'json_zhuyaorenyuan',json_zhuyaorenyuan

    def load_jiatingchengyuan(self, table_element):
        self.info(u'解析家庭成员信息...')
        tr_element_list = table_element.find_all("tr")
        th_element_list = table_element.find_all('th')[1:-1]
        jsonarray = []
        values = {}
        id=1
        # print 'tr_element_list',tr_element_list
        if tr_element_list:
            print 'youyouyou'
            raise Exception(u"家庭成员有信息了")
    #         for tr_element in tr_element_list:
    #             td_element_list = tr_element.find_all('td')
    #             for i in range(4):
    #                 col_dec = th_element_list[i].text.strip().replace('\n','')
    #                 col=jiatingchengyuan_column_dict[col_dec]
    #                 td = td_element_list[i]
    #                 val = td.get_text().strip()
    #                 values[col] = val
    # #                 print th,val
    #                 if len(values) ==2:
    #                     values['Family_Info:registrationno']=self.cur_code
    #                     values['Family_Info:enterprisename']=self.cur_mc
    #                     values['Family_Info:id'] = str(id)
    #                     values['rowkey'] = self.cur_mc+'_07_'+self.cur_code+'_'+self.time+str(id)
    #                     jsonarray.append(values)
    #                     values = {}
    #                     id+=1
    #         self.json_result['Family_Info']=jsonarray
        else:
            return None
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
        self.info(u'解析分支机构信息...')
        tr_elements = table_element.find_all("tr")[1:]
        jsonarray = []
        values = {}
        id = 1
        for tr_element in tr_elements:
            if tr_element.text.strip():
                td_element_list = tr_element.find_all('ul')
                for td_element in td_element_list:
                    values['Branches:branch_registrationno'] = td_element.find_all('li')[1].contents[1]
                    values['Branches:branch_registrationname'] = td_element.find(class_='padding1').text.strip().replace('\n', '')
                    institution_len = len(td_element.find_all('li')[2])
                    if institution_len == 1:
                        values['Branches:branch_registrationinstitution'] = ''
                    elif institution_len == 2:
                        values['Branches:branch_registrationinstitution'] = td_element.find_all('li')[2].contents[1]
                    values['Branches:registrationno'] = self.cur_code
                    values['Branches:enterprisename'] = self.cur_mc
                    values['Branches:id'] = str(id)
                    values['rowkey']=self.cur_mc+'_08_'+self.cur_code+'_'+self.time+str(id)
                    jsonarray.append(values)
                    values = {}
                    id += 1
                self.json_result['Branches'] = jsonarray
                # json_fenzhijigou = json.dumps(jsonarray, ensure_ascii=False)
                # print 'json_fenzhijigou', json_fenzhijigou

    # 加载清算信息
    def load_qingsuan(self, table_element):
        self.info(u'解析清算信息...')
        tr_element_list = table_element.find_all('tr')
        # th_element_list = table_element.find_all('th')[1:-1]
        jsonarray = []
        values = {}
        if len(tr_element_list)> 1:
            if tr_element_list[0].find('td'):
                col_1 = table_element.find_all('tr')[1].find('th').get_text().strip()
                col_1 = qingsuanxinxi_column_dict[col_1]
                td_1 = table_element.find_all('tr')[1].find('td').get_text().strip()
                values[col_1] = td_1
                col_2 = table_element.find_all('tr')[2].find('th').get_text().strip()
                col_2 = qingsuanxinxi_column_dict[col_2]
                td_va = []
                for tr_element in tr_element_list[1:]:
                    td_list = tr_element.find_all('td')
                    for td in td_list:
                        va = td.get_text().strip()
                        # print va
                        td_va.append(va)
                    val = ','.join(td_va)
                values[col_2] = val
                values['liquidation_Information:registrationno']=self.cur_code
                values['liquidation_Information:enterprisename']=self.cur_mc
                values['rowkey']=self.cur_mc+'_09_'+self.cur_code+'_'
                jsonarray.append(values)
        values = {}
        self.json_result['liquidation_Information']=jsonarray

    def load_dongchandiyadengji(self, table_element):
        self.info(u'解析动产抵押信息...')
        tr_element_list = table_element.find_all("tr")
        th_element_list = table_element.find_all('th')[1:]
        jsonarray = []
        values = {}
        id=1
        for tr_element in tr_element_list[1:-1]:
            td_element_list = tr_element.find_all('td')[1:]
            col_nums = len(th_element_list)
            for i in range(col_nums):
                col_dec = th_element_list[i].text.strip().replace('\n','')
                col = dongchandiyadengji_column_dict[col_dec]
                td = td_element_list[i]
                val = td.get_text().strip()
                # if td_element_list[5].get_text().strip() == u'详情' or td_element_list[5].get_text().strip() == u'查看' :
                if val == u'详情' or val == u'查看' :
                    link = td.a['onclick']
                    values[col] = link
                    # print "link:", link
                    diya_detail = self.get_diya_detail(link)
                    values.update(diya_detail)
                else:
                    values[col] = val
            values['Chattel_Mortgage:registrationno'] = self.cur_code
            values['Chattel_Mortgage:enterprisename'] = self.cur_mc
            values['Chattel_Mortgage:id'] = str(id)
            values['rowkey'] = self.cur_mc+'_11_'+self.cur_code+'_'+self.time+str(id)
            jsonarray.append(values)
            values = {}
            id += 1
        self.json_result['Chattel_Mortgage'] = jsonarray
#         json_dongchandiyadengji=json.dumps(jsonarray,ensure_ascii=False)
#         print 'json_dongchandiyadengji',json_dongchandiyadengji

    def get_diya_detail(self, link):
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:47.0) Gecko/20100101 Firefox/47.0",
                        "Host": "fj.gsxt.gov.cn",
                        "Accept": "*/*",
                        "Accept-Encoding": "gzip, deflate",
                        "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
                        "Connection": "keep-alive",
                        # "Referer": "http://sh.gsxt.gov.cn/notice/search/ent_info_list",
                        # "Upgrade-Insecure-Requests": "1",
                        # "Content-type": "application/json"
                        "X-Requested-With": "XMLHttpRequest",
                        }
        values = dict()
        """动产抵押登记信息"""
        dcdydj = list()
        dcdydj_table_id = '63'
        family = 'dcdydj'
        dcdydj_dict = dict()
        link_detail = link.split("('")[1].split("')")[0]
        params = {'uuid':  link_detail}
        url = 'http://fj.gsxt.gov.cn/notice/notice/view_mortage?uuid='+link_detail
        # r_1 = self.get_request(url, data=params, headers=headers)
        r_1 = self.get_request(url)
        # r_1 = requests.get(url, data=params)
        # print 'get_diya_detail', r_1.text
        soup = BeautifulSoup(r_1.text, 'lxml')
        table_element = soup.find_all(class_='tableG')
        dcdydj_table = table_element[0]
        # print 'dcdydj_table', dcdydj_table
        dcdydj_tr_list = dcdydj_table.find_all('tr')
        for tr_element in dcdydj_tr_list:
            th_element_list = tr_element.find_all('th')
            td_element_list = tr_element.find_all('td')
            col_nums = len(td_element_list)
            for i in range(col_nums):
                col_dec = th_element_list[i].get_text().strip().replace('\n', '')
                if col_dec:
                    col = dcdydj_column_dict[col_dec]
                    val = td_element_list[i].get_text().strip().replace('\n', '').replace('\t', '').replace('\r', '')
                    dcdydj_dict[col] = val
        mot_no = dcdydj_dict['dcdyzx:dcdy_djbh']
        mot_date = dcdydj_dict['dcdyzx:dcdy_djrq']
        dcdydj_dict['rowkey'] = '%s_%s_%s_%s' % (self.cur_mc, mot_no,mot_date, dcdydj_table_id)
        dcdydj_dict[family + ':registrationno'] = self.cur_zch
        dcdydj_dict[family + ':enterprisename'] = self.cur_mc
        dcdydj.append(dcdydj_dict)
        # print 'dcdydj', dcdydj
        values['Chattel_Mortgage:dcdydj'] = dcdydj # 动产抵押登记信息

        """抵押权人概况"""
        family = 'dyqrgk'
        dyqrgk = list()
        dyqrgk_values = dict()
        dyqrgk_table_id = '55' # 抵押权人概况表格
        k = 1
        dyqrgk_table = table_element[1]
        dyqrgk_tr_list = dyqrgk_table.find_all('tr')
        dyqrgk_th_list = dyqrgk_table.find_all('th')[1:-1]
        for tr_element in dyqrgk_tr_list[1:]:
            td_element_list = tr_element.find_all('td')[1:-1]
            col_nums = len(td_element_list)
            for i in range(col_nums):
                col_dec = dyqrgk_th_list[i].get_text().strip().replace('\n', '')
                col = dyqrgk_column_dict[col_dec]
                val = td_element_list[i].get_text().strip().replace('\n', '')
                dyqrgk_values[col] = val
        dyqrgk_values['rowkey'] = '%s_%s_%s_%s_%d' % (self.cur_mc, mot_no,mot_date, dyqrgk_table_id, k)
        dyqrgk_values[family + ':registrationno'] = self.cur_zch
        dyqrgk_values[family + ':enterprisename'] = self.cur_mc
        dyqrgk_values[family + ':id'] = k
        dyqrgk.append(dyqrgk_values)
        k += 1
        values['Chattel_Mortgage:dyqrgk'] = dyqrgk # 抵押权人概况

        """被担保债券概况"""
        family = 'bdbzqgk'
        bdbzqgk = list()
        bdbzqgk_table_id = '56'
        bdbzqgk_dict = dict()
        bdbzqgk_table = table_element[2]
        bdbzqgk_tr_list = bdbzqgk_table.find_all('tr')
        for tr_element in bdbzqgk_tr_list:
            th_element_list = tr_element.find_all('th')
            td_element_list = tr_element.find_all('td')
            col_nums = len(td_element_list)
            for i in range(col_nums):
                col_dec = th_element_list[i].get_text().strip().replace('\n', '')
                col = bdbzqgk_column_dict[col_dec]
                val = td_element_list[i].get_text().strip().replace('\n', '').replace('\t', '').replace('\r', '')
                bdbzqgk_dict[col] = val
        bdbzqgk_dict['rowkey'] = '%s_%s_%s_%s' % (self.cur_mc, mot_no,mot_date, bdbzqgk_table_id)
        bdbzqgk_dict[family + ':registrationno'] = self.cur_zch
        bdbzqgk_dict[family + ':enterprisename'] = self.cur_mc
        bdbzqgk.append(bdbzqgk_dict)
        values['Chattel_Mortgage:bdbzqgk'] = bdbzqgk # 被担保债券概况

        """抵押物概况"""
        family = 'dywgk'
        dywgk = list()
        dywgk_table_id = '57'
        dywgk_values = dict()
        k = 1
        dywgk_table = table_element[3]
        dywgk_tr_list = dywgk_table.find_all('tr')
        dywgk_th_list = dywgk_table.find_all('th')[1:]
        for tr_element in dywgk_tr_list[1:]:
            td_element_list = tr_element.find_all('td')[1:]
            col_nums = len(td_element_list)
            for i in range(col_nums):
                col_dec = dywgk_th_list[i].get_text().strip().replace('\n', '')
                col = dywgk_column_dict[col_dec]
                val = td_element_list[i].get_text().strip().replace('\n', '').replace(' ', '')
                dywgk_values[col] = val
        dywgk_values['rowkey'] = '%s_%s_%s_%s_%d' % (self.cur_mc, mot_no,mot_date, dywgk_table_id, k)
        dywgk_values[family + ':registrationno'] = self.cur_zch
        dywgk_values[family + ':enterprisename'] = self.cur_mc
        dywgk_values[family + ':id'] = k
        dywgk.append(dywgk_values)
        k += 1
        values['Chattel_Mortgage:dywgk'] = dywgk # 抵押物概况
        # print 'values', values
        return values

    def load_guquanchuzhidengji(self, table_element):
        self.info(u'解析股权出质信息...')
        tr_element_list = table_element.find_all("tr")
        th_element_list = table_element.find_all('th')
        jsonarray = []
        values = {}
        id=1
        for tr_element in tr_element_list[1:-1]:
            td_element_list = tr_element.find_all('td')
            col_nums = len(th_element_list)
            self.cur_zch = td_element_list[1].text.strip()
            if col_nums == 11:
                values['Equity_Pledge:equitypledge_no'] = td_element_list[0].text.strip()
                values['Equity_Pledge:equitypledge_registrationno'] = td_element_list[1].text.strip()
                values['Equity_Pledge:equitypledge_pledgor'] = td_element_list[2].text.strip()
                values['Equity_Pledge:equitypledge_pledgorid'] = td_element_list[3].text.strip()
                values['Equity_Pledge:equitypledge_amount'] = td_element_list[4].text.strip()
                values['Equity_Pledge:equitypledge_pawnee'] = td_element_list[5].text.strip()
                values['Equity_Pledge:equitypledge_pawneeid'] = td_element_list[6].text.strip()
                values['Equity_Pledge:equitypledge_registrationdate'] = td_element_list[7].text.strip()
                values['Equity_Pledge:equitypledge_status'] = td_element_list[8].text.strip()
                values['Equity_Pledge:equitypledge_announcedate'] = td_element_list[9].text.strip()
                # values['Equity_Pledge:equitypledge_detail'] = td_element_list[10].text.strip()
                # if col_dec ==u'证照/证件号码' and previous==u'出质人':
                #     col='Equity_Pledge:equitypledge_pledgorid'
                # elif col_dec==u'证照/证件号码' and previous==u'质权人':
                #     col='Equity_Pledge:equitypledge_pawneeid'
                # else:
                #     col=guquanchuzhidengji_column_dict[col_dec]
                # td = td_element_list[i]
                # val = td.get_text().strip()
                if td_element_list[10].text.strip() == u'查看' or td_element_list[10].text.strip() == u'详情':
                    equity_no = td_element_list[1].text.strip()
                    equity_date = td_element_list[7].text.strip()
                    link = td_element_list[10].a['onclick']
                    values['Equity_Pledge:equitypledge_detail'] = link
                    # print 'link:', link
                    pledge_detail = self.get_pledge_detail(link, equity_no, equity_date)
                    # print 'pledge_detail', pledge_detail
                    values.update(pledge_detail)
                else:
                    values['Equity_Pledge:equitypledge_detail'] = td_element_list[10].text.strip()
            values['Equity_Pledge:registrationno'] = self.cur_code
            values['Equity_Pledge:enterprisename'] = self.cur_mc
            values['Equity_Pledge:id'] = str(id)
            values['rowkey'] = self.cur_mc+'_12_'+self.cur_code+'_'+self.time+str(id)
            jsonarray.append(values)
            values = {}
            id += 1
        self.json_result['Equity_Pledge']=jsonarray
#         json_guquanchuzhidengji=json.dumps(jsonarray,ensure_ascii=False)
#         print 'json_guquanchuzhidengji',json_guquanchuzhidengji

    def get_pledge_detail(self, link, equity_no, equity_date):
        diya_detail_new = {'Equity_Pledge:gqczzx': [{'gqczzx:gqcz_bgrq': '', 'gqczzx:gqcz_bgnr': ''}]}
        result_values = dict()
        bg_list = list()
        zx_list = list()
        bg_values = dict()
        zx_values = dict()
        pripid = link.split("('")[1].split("')")[0]
        url = 'http://fj.gsxt.gov.cn/notice/notice/view_pledge?uuid=' + pripid
        # r = requests.get(url, data=params)
        r = self.get_request(url)
        # print 'get_pledge_detail:', r.text
        soup = BeautifulSoup(r.text, 'lxml')
        table_element_list = soup.find_all(class_='content2')
        table_num = len(table_element_list)
        if table_num == 1:
            # print '111'
            table_element = table_element_list[0]
            gqcz_tr_list = table_element.find('table').find_all("tr")
            table_des = table_element.find(class_='titleTop1').find('h1').text.strip()
            if table_des == u'股权出质变更信息':
                # print 'table_des', table_des
                family = 'gqczbg'
                table_id = '61'
                for tr_element in gqcz_tr_list[1:]:
                    td_element_list = tr_element.find_all('td')
                    col_nums = len(td_element_list)
                    if col_nums > 1:
                        bg_values['gqczbg:gqcz_bgrq'] = td_element_list[1].text.strip()
                        bg_values['gqczbg:gqcz_bgnr'] = td_element_list[2].text.strip()
                        bg_values['rowkey'] = '%s_%s_%s_%s' % (self.cur_mc,equity_no,equity_date, table_id)
                        bg_values[family + ':registrationno'] = self.cur_zch
                        bg_values[family + ':enterprisename'] = self.cur_mc
                    bg_list.append(bg_values)
                result_values['Equity_Pledge:gqczbg'] = bg_list
                return result_values
        elif table_num == 2:
            # print '222'
            table_des_1 = table_element_list[0].find(class_='titleTop1').find('h1').text.strip()
            # print 'table_des_1', table_des_1
            if table_des_1 == u'股权出质变更信息':
                family = 'gqczbg'
                table_id = '61'
                gqcz_tr_list = table_element_list[0].find('table').find_all("tr")
                for tr_element in gqcz_tr_list[1:]:
                    td_element_list = tr_element.find_all('td')
                    col_nums = len(td_element_list)
                    if col_nums > 1:
                        bg_values['gqczbg:gqcz_bgrq'] = td_element_list[1].text.strip()
                        bg_values['gqczbg:gqcz_bgnr'] = td_element_list[2].text.strip()
                        bg_values['rowkey'] = '%s_%s_%s_%s' % (self.cur_mc,equity_no,equity_date, table_id)
                        bg_values[family + ':registrationno'] = self.cur_zch
                        bg_values[family + ':enterprisename'] = self.cur_mc
                        bg_list.append(bg_values)
                result_values['Equity_Pledge:gqczbg'] = bg_list
            # print 'result_values_gqczbg', result_values['Equity_Pledge:gqczbg']
            table_des_2 = table_element_list[1].find(class_='titleTop1').find('h1').text.strip()
            if table_des_2 == u'股权出质注销信息':
                family = 'gqczzx'
                table_id = '60'
                zx_values['gqczzx:gqcz_zxrq'] = table_element_list[1].find('table').find_all("td")[0].text.strip()
                zx_values['gqczzx:gqcz_zxyy'] = table_element_list[1].find('table').find_all("td")[1].text.strip()
                zx_values['rowkey'] = '%s_%s_%s_%s' % (self.cur_mc,equity_no,equity_date, table_id)
                zx_values[family + ':registrationno'] = self.cur_zch
                zx_values[family + ':enterprisename'] = self.cur_mc
                zx_list.append(zx_values)
                # print 'pledge_list:', zx_list
                result_values['Equity_Pledge:gqczzx'] = zx_list
            # print 'result_values_gqczzx:', result_values
            return result_values
        else:
            return diya_detail_new

    def load_xingzhengchufa(self, tag_a):
        self.info(u'解析行政处罚信息...')
        url = tag_a.replace('=01', '=03')
        r = self.get_request(url)
        soup = BeautifulSoup(r.text, 'lxml')
        table_element = soup.find(class_='tableG')
        tr_element_list = table_element.find_all("tr")
        th_element_list = table_element.find_all('th')[1:]
        jsonarray = []
        values = {}
        id=1
        for tr_element in tr_element_list[1:-1]:
            td_element_list = tr_element.find_all('td')
            col_nums = len(th_element_list)
            if col_nums == 7:
                values['Administrative_Penalty:penalty_code'] = td_element_list[1].text.strip()
                values['Administrative_Penalty:penalty_illegaltype'] = td_element_list[2].text.strip()
                values['Administrative_Penalty:penalty_decisioncontent'] = td_element_list[3].text.strip()
                values['Administrative_Penalty:penalty_decisioninsititution'] = td_element_list[4].text.strip()
                values['Administrative_Penalty:penalty_decisiondate'] = td_element_list[5].text.strip()
                values['Administrative_Penalty:penalty_announcedate'] = td_element_list[6].text.strip()
                if td_element_list[7].text.strip() == u'详情' or td_element_list[7].text.strip() == u'查看':
                    link = td_element_list[7].a['href']
                    values['Administrative_Penalty:penalty_details'] = link
                else:
                    values['Administrative_Penalty:penalty_details'] = ''
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

    def load_jingyingyichang(self, tag_a):
        self.info(u'解析经营异常信息...')
        url = tag_a.split('==&')[0] + "==&tabPanel=04"
        r = self.get_request(url)
        soup = BeautifulSoup(r.text, 'html5lib')
        table_element = soup.find(class_='tableG')
        tr_element_list = table_element.find_all("tr")
        th_element_list = table_element.find_all('th')
        jsonarray = []
        values = {}
        id=1
        for tr_element in tr_element_list[1:-1]:
            td_element_list = tr_element.find_all('td')
            col_nums = len(th_element_list)
            if col_nums == 7:
                values['Business_Abnormal:abnormal_no'] = td_element_list[0].text.strip()
                values['Business_Abnormal:abnormal_events'] = td_element_list[1].text.strip()
                values['Business_Abnormal:abnormal_datesin'] = td_element_list[2].text.strip()
                values['Business_Abnormal:abnormal_decisioninstitution(in)'] = td_element_list[3].text.strip()
                values['Business_Abnormal:abnormal_moveoutreason'] = td_element_list[4].text.strip()
                values['Business_Abnormal:abnormal_datesout'] = td_element_list[5].text.strip()
                values['Business_Abnormal:abnormal_decisioninstitution(out)'] = td_element_list[6].text.strip()
                values['Business_Abnormal:registrationno']=self.cur_code
                values['Business_Abnormal:enterprisename']=self.cur_mc
                values['Business_Abnormal:id'] = str(id)
                values['rowkey']= self.cur_mc+'_14_'+self.cur_code+'_'+self.time+str(id)
                jsonarray.append(values)
                values = {}
                id += 1
        self.json_result['Business_Abnormal'] = jsonarray
        # json_jingyingyichang=json.dumps(jsonarray, ensure_ascii=False)
        # print 'json_jingyingyichang', json_jingyingyichang

    def load_yanzhongweifa(self, table_element):
        self.info(u'解析严重违法信息...')
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
                col = yanzhongweifa_column_dict[col_dec]
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
        self.info(u'解析抽查检查信息...')
        tr_element_list = table_element.find_all("tr")
        th_element_list = table_element.find_all('th')
        jsonarray = []
        values = {}
        id=1
        for tr_element in tr_element_list[1:-1]:
            td_element_list = tr_element.find_all('td')
            col_nums = len(th_element_list)
            for i in range(col_nums):
                col_dec = th_element_list[i].text.strip().replace('\n', '')
                col = chouchajiancha_column_dict[col_dec]
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

    def get_request(self, url, params={}, data={}, verify=True, t=0, release_lock_id=False):
        """
        发送get请求,包含添加代理,锁定ip与重试机制
        :param url: 请求的url
        :param params: 请求参数
        :param data: 请求数据
        :param verify: 忽略ssl
        :param t: 重试次数
        :param release_lock_id: 是否需要释放锁定的ip资源
        """
        try:
            if self.use_proxy:
                if not release_lock_id:
                    self.headers['Proxy-Authorization'] = self.proxy_config.get_auth_header(lock_id=self.lock_id)
                else:
                    self.headers['Proxy-Authorization'] = self.proxy_config.get_auth_header(lock_id=self.lock_id, release_id=self.lock_id)
            r = self.session.get(url=url, headers=self.headers, params=params, data=data, verify=verify)
            if r.status_code != 200:
                print u'错误的响应代码 -> %d' % r.status_code , url
                raise RequestException()
            return r
        except RequestException, e:
            if t == 15:
                raise e
            else:
                return self.get_request(url, params, data, verify, t+1, release_lock_id)

if __name__ == '__main__':
    args_dict = get_args()
    searcher = FuJianSearcher()
    # searcher.delete_tag_a_from_db(u'云南通海县通保缝纫有限公司')
    # searcher.submit_search_request(u'峰晓达包装印务（上海）有限公司')
    # searcher.submit_search_request('530103100023841')
    searcher.submit_search_request(u'南靖县农业技术服务部下戴炳聪门市')
    # searcher.submit_search_request(keyword=args_dict['companyName'], account_id=args_dict['accountId'], task_id=args_dict['taskId'])
    # print json.dumps(searcher.json_result, ensure_ascii=False)
