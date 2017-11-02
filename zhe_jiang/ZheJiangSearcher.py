# coding=utf-8
import PackageTool
from gs.Searcher import Searcher
from gs.Searcher import get_args
from gs import MSSQL
import requests
from PIL import Image
import os
import sys
import re
import random
import subprocess
from bs4 import BeautifulSoup
from TableConfig import *
from gs.KafkaAPI import KafkaAPI
from gs.TimeUtils import get_cur_time
import json
from requests.exceptions import RequestException
import traceback
import urllib
import uuid


class ZheJiangSearcher(Searcher):
    load_func_dict = {}
    corpid = None
    regno = None

    def __init__(self):
        super(ZheJiangSearcher, self).__init__(use_proxy=True)
        self.load_func_dict[u'登记信息'] = self.get_deng_ji
        self.load_func_dict[u'基本信息'] = self.get_ji_ben
        self.load_func_dict[u'股东信息'] = self.get_gu_dong
        self.load_func_dict[u'变更信息'] = self.get_bian_geng
        self.load_func_dict[u'备案信息'] = self.get_bei_an
        self.load_func_dict[u'主要人员信息'] = self.get_zhu_yao_ren_yuan
        self.load_func_dict[u'分支机构信息'] = self.get_fen_zhi_ji_gou
        self.load_func_dict[u'清算信息'] = self.get_qing_suan
        self.load_func_dict[u'投资人信息'] = self.get_tou_zi_ren
        # self.load_func_dict[u'主管部门（出资人）信息'] = self.get_zhu_guan_bu_men     #Modified by Jing
        # self.load_func_dict[u'参加经营的家庭成员姓名'] = self.load_jiatingchengyuan     # Modified by Jing
        # self.load_func_dict[u'合伙人信息'] = self.load_hehuoren     #Modified by Jing
        # self.load_func_dict[u'成员名册'] = self.load_chengyuanmingce     #Modified by Jing
        # self.load_func_dict[u'撤销信息'] = self.load_chexiao     #Modified by Jing
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:45.0) Gecko/20100101 Firefox/45.0",
                        "Host": "gsxt.zjaic.gov.cn",
                        "Accept": "*/*",
                        "Accept-Encoding": "gzip, deflate",
                        "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
                        "Referer": "http://gsxt.zjaic.gov.cn/search/doGetAppSearchResult.do",
                        "Connection": "keep-alive"
                        }
        self.set_config()
        self.log_name = self.topic + "_" + str(uuid.uuid1())

    def set_config(self):
        self.plugin_path = os.path.join(sys.path[0], '../zhe_jiang/ocr/jisuan/zhejiang.bat')
        self.group = 'Crawler'  # 正式
        self.kafka = KafkaAPI("GSCrawlerResult")  # 正式
        # self.group = 'CrawlerTest'  # 测试
        # self.kafka = KafkaAPI("GSCrawlerTest")  # 测试
        self.topic = 'GsSrc33'
        self.province = u'浙江省'
        self.kafka.init_producer()
        self.set_request_timeout(20)
    # def recognize_yzm(self, yzm_path):
    #     image = Image.open(yzm_path)
    #     image.show()
    #     print '请输入验证码:'
    #     yzm = raw_input()
    #     image.close()
    #     return yzm

    def recognize_yzm(self, yzm_path):
        """
        识别验证码
        :param yzm_path: 验证码保存路径
        :return: 验证码识别结果
        """
        cmd = self.plugin_path + " " + yzm_path
        # print cmd
        process = subprocess.Popen(cmd.encode('GBK', 'ignore'), stdout=subprocess.PIPE)
        process_out = process.stdout.read()
        process_out = process_out.strip()
        answer = process_out.split('\r\n')[-1].strip()
        if answer.endswith(yzm_path):
            answer = u''
        # print 'answer: ' + answer.decode('gbk', 'ignore')
        return answer.decode('gbk', 'ignore')

    def download_yzm(self):
        # print 'lock_id -> %s' % self.lock_id
        image_url = 'http://gsxt.zjaic.gov.cn/common/captcha/doReadKaptcha.do'
        r = self.get_request(image_url)
        # print 1, r.headers
        yzm_path = self.get_yzm_path().replace('/', '\\')
        with open(yzm_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    f.flush()
            f.close()
        return yzm_path

    def save_tag_a_to_db(self, tag_a):
        pass

    def get_tag_a_from_db(self, keyword):
        return None

    def get_tag_a_from_page(self, keyword, flags=True):
        url = 'http://gsxt.zjaic.gov.cn/search/doGetAppSearchResult.do'
        for t in range(20):
            self.get_lock_id()
            yzm = self.get_yzm()
            if not str.isdigit(yzm.encode('utf-8')):
                print u'非数字验证码'
                self.release_lock_id()
                continue
            # if len(yzm) == 0:
            #     self.info(u'非数字、成语验证码...')
            #     self.session = requests.session()
            #     self.session.proxies = self.proxy_config.get_proxy()
            #     self.release_lock_id()
            #     continue
            params = {'clickType': '1', 'name': keyword.encode('utf-8'), 'verifyCode': yzm.encode('utf-8')}
            self.info(u'提交验证码...')
            r = self.post_request(url=url, data=params)
            # print 2, r.headers
            # self.release_lock_id()
            # print r.text
            if u'验证码输入错误' in r.text:
                self.info(u'验证码输入错误')
                self.session = requests.session()
                self.session.proxies = self.proxy_config.get_proxy()
                self.release_lock_id()
                continue
            elif u'您搜索的条件无查询结果' in r.text:
                # print r.text
                return None
            else:
                search_result_json = {}
                soup = BeautifulSoup(r.text, 'lxml')
                search_result_text = soup.select('html body div div dl dt a')[0].attrs['href']
                if search_result_text != u'':
                    self.cur_mc = soup.select('html body div div dl dt a')[0].text.strip()
                    search_result_json['entname'] = self.cur_mc
                    if flags:
                        if keyword == self.cur_mc :
                            self.cur_zch = soup.select('html body div div dl dt span')[0].text.strip()
                            search_result_json['regno'] = self.cur_zch
                            search_result_json['corpid'] = search_result_text.split("=")[1]
                    else:
                        self.cur_zch = soup.select('html body div div dl dt span')[0].text.strip()
                        search_result_json['regno'] = self.cur_zch
                        search_result_json['corpid'] = search_result_text.split("=")[1]
                    # search_result_json['corpid']=search_result_text[search_result_text.index('corpid=')+len('corpid='):len('search_result_text')]
                    tag_a = json.dumps(search_result_json, ensure_ascii=False)
                    return tag_a

    def get_search_args(self, tag_a, keyword):
        self.corpid = None
        search_result_json = json.loads(tag_a)
        if search_result_json.get('entname', None) == keyword:
            self.corpid = search_result_json['corpid']
            self.cur_mc = search_result_json['entname'].replace('(', u'（').replace(')', u'）')  # 公司名称括号统一转成全角
            self.cur_zch = search_result_json['regno']
            return 1
        else:
            return 0

    def parse_detail(self):
        """
        解析公司详情信息
        :param kwargs:
        :return:
        """
        self.info(u'获取公司注册号...')
        self.get_regno()
        self.info(u'解析基本信息...')
        self.info(u'解析登记信息...')
        self.get_deng_ji()
        self.info(u'解析备案信息...')
        self.get_bei_an()
        self.info(u'解析动产抵押信息...')
        self.get_dong_chan_di_ya()
        self.info(u'解析股权出质信息...')
        self.get_gu_quan_chu_zhi()
        self.info(u'解析行政处罚信息...')
        self.get_xing_zheng_chu_fa()
        self.info(u'解析经营异常信息...')
        self.get_jing_ying_yi_chang()
        self.info(u'解析严重违法信息...')
        # self.get_yan_zhong_wei_fa()
        self.info(u'解析抽查检查信息...')
        self.get_chou_cha_jian_cha()

    def get_regno(self):
        url = 'http://gsxt.zjaic.gov.cn/appbasicinfo/doViewAppBasicInfo.do'
        params = {'corpid': self.corpid}
        r = self.get_request(url=url, params=params)
        soup = BeautifulSoup(r.text, 'lxml')
        h_element = soup.find_all('h2')[0].text
        regno_info = h_element.split('\n')[2].replace(u'注册号：','')
        self.regno = regno_info.strip()

    def get_deng_ji(self):
        for i in range(5):
            url = 'http://gsxt.zjaic.gov.cn/appbasicinfo/doReadAppBasicInfo.do'
            params = {'corpid': self.corpid}
            r = self.get_request(url=url, params=params)
            if u'系统警告' in r.text and i < 4:
                continue
            elif u'系统警告' in r.text and i == 4:
                break
            else:
                soup = BeautifulSoup(r.text, 'lxml')
                table_elements = soup.find_all("table")
                for table_element in table_elements:
                    table_name = table_element.find("th").get_text().strip()  # 表格名称
                    if u'股东信息' in table_name:
                        self.get_gu_dong(table_element)
                    elif table_name in self.load_func_dict:
                        self.load_func_dict[table_name](table_element)
                    else:
                        self.info(u'未知表名')

    def get_ji_ben(self, table_element):
        """
        查询基本信息
        :return: 基本信息结果
        """
        family = 'Registered_Info'
        table_id = '01'
        self.json_result[family] = []
        td_list = table_element.select('tr > td')
        th_list = table_element.select('tr > th')[1:]
        result_json = [{}]
        for i in range(len(td_list)):
            th = th_list[i]
            td = td_list[i]
            desc = self.pattern.sub('', th.text)
            val = self.pattern.sub('', td.text)
            # print desc,val
            if len(desc) > 0:
                if desc == u'统一社会信用代码/注册号' and len(val) == 18:
                    result_json[0][u'社会信用代码'] = val
                    result_json[0][u'注册号码'] = ''
                if desc == u'统一社会信用代码/注册号' and len(val) != 18:
                    result_json[0][u'社会信用代码'] = ''
                    result_json[0][u'注册号码'] = val
                result_json[0][desc] = val
        for j in result_json:
            self.json_result[family].append({})
            for k in j:
                col = jiben_column_dict[k]
                val = j[k]
                self.json_result[family][-1][col] = val
        self.json_result[family][-1]['rowkey'] = '%s_%s_%s_' % (self.cur_mc, table_id, self.cur_zch)
        self.json_result[family][-1][family + ':registrationno'] = self.cur_zch
        self.json_result[family][-1][family + ':enterprisename'] = self.cur_mc
        self.json_result[family][-1][family + ':province'] = self.province
        self.json_result[family][-1][family + ':lastupdatetime'] = get_cur_time()
        # print json.dumps(self.json_result[family], ensure_ascii=False)

    def get_gu_dong(self, table_element):
        """
        查询股东信息
        :param param_corpid:
        :param table_element:
        :return:
        """
        family = 'Shareholder_Info'
        table_id = '04'
        self.json_result[family] = []
        if u'下一页' in table_element.text:
            th_element_list = table_element.select('th')[1:-1]
            tr_element_list = table_element.select('tr')[2:-1]
            pages = self.pattern.sub('', table_element.select('th')[-1].text.strip())
            page_nums = pages[1:pages.index(u'页')]
        else:
            th_element_list = table_element.select('th')[1:]
            tr_element_list = table_element.select('tr')[2:]
            page_nums = 1
        for i in range(int(page_nums)):
            if i > 0:
                url = 'http://gsxt.zjaic.gov.cn/appbasicinfo/doReadAppBasicInfo.do'
                params = {'corpid': self.corpid, 'entInvestorPagination.currentPage': '%s' % (i+1), 'entInvestorPagination.pageSize': '5'}
                r = self.get_request(url = url, params = params)
                soup = BeautifulSoup(r.text, 'lxml')
                table_element = soup.select('table')[1]
                th_element_list = table_element.select('th')[1:-1]
                tr_element_list = table_element.select('tr')[2:-1]
            for tr_element in tr_element_list:
                td_element_list = tr_element.select('td')
                col_nums = len(th_element_list)
                self.json_result[family].append({})
                for j in range(col_nums):
                    col_dec = th_element_list[j].text.strip().replace('\n', '')
                    col = gudong_column_dict[col_dec]
                    td = td_element_list[j]
                    val = td.text.strip()
                    self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
        # print json.dumps(self.json_result[family], ensure_ascii=False)

    def get_tou_zi_ren(self, table_element):
        pass

    def get_bian_geng(self, table_element):
        """
        查询变更信息
        :return:变更信息
        """
        family = 'Changed_Announcement'
        table_id = '05'
        self.json_result[family] = []
        if u'下一页' in table_element.text:
            th_element_list = table_element.select('th')[1:-1]
            tr_element_list = table_element.select('tr')[2:-1]
            pages = self.pattern.sub('', table_element.select('th')[-1].text.strip())
            page_nums = pages[1:pages.index(u'页')]
        else:
            th_element_list = table_element.select('th')[1:]
            tr_element_list = table_element.select('tr')[2:]
            page_nums = 1
        for i in range(int(page_nums)):
            if i > 0:
                url = 'http://gsxt.zjaic.gov.cn/appbasicinfo/doReadAppBasicInfo.do'
                params = {'corpid': self.corpid, 'checkAlterPagination.currentPage': '%s' % (i+1), 'checkAlterPagination.pageSize': '5'}
                r = self.get_request(url=url, params=params)
                soup = BeautifulSoup(r.text, 'lxml')
                table_element = soup.select('table')[-1]
                th_element_list = table_element.select('th')[1:-1]
                tr_element_list = table_element.select('tr')[2:-1]
            # print table_element
            for tr_element in tr_element_list:
                td_element_list = tr_element.select('td')
                col_nums = len(th_element_list)
                self.json_result[family].append({})
                for j in range(col_nums):
                    col_dec = th_element_list[j].text.strip().replace('\n', '')
                    col = biangeng_column_dict[col_dec]
                    td = td_element_list[j]
                    val = self.pattern.sub('', td.text)
                    if val.endswith(u'更多'):
                        val = val[val.index(u'更多')+2:val.index(u'收起更多')]
                    self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family][i], ensure_ascii=False)

    def get_bei_an(self):
        for i in range(5):
            url = 'http://gsxt.zjaic.gov.cn/filinginfo/doViewFilingInfo.do'
            params = {'corpid': self.corpid}
            r = self.get_request(url=url, params=params)
            if u'系统警告' in r.text and i < 4:
                continue
            elif u'系统警告' in r.text and i == 4:
                break
            else:
                soup = BeautifulSoup(r.text, 'lxml')
                table_elements = soup.find_all("table")
                for table_element in table_elements:
                    table_name = table_element.find("th").get_text().strip()  # 表格名称
                    if table_name in self.load_func_dict:
                        self.load_func_dict[table_name](table_element)
                    else:
                        self.info(u'未知表名')
                break

    def get_zhu_yao_ren_yuan(self, table_element):
        """
        查询主要人员信息
        :param table_element:
        :return:
        """
        family = 'KeyPerson_Info'
        table_id = '06'
        self.json_result[family] = []
        if u'下一页' in table_element.text:
            th_element_list = table_element.select('th')[1:]
            tr_element_list = table_element.select('tr')[2:-1]
            pages = self.pattern.sub('', table_element.select('th')[-1].text.strip())
            page_nums = pages[1:pages.index(u'页')]
        else:
            th_element_list = table_element.select('th')[1:]
            tr_element_list = table_element.select('tr')[2:]
            page_nums = 1
        for i in range(int(page_nums)):
            if i > 0:
                url = 'http://gsxt.zjaic.gov.cn/filinginfo/doViewFilingInfo.do'
                params = {'corpid': self.corpid, 'entMemberPagination.currentPage': '%s' % (i+1), 'entMemberPagination.pageSize': '10'}
                r = self.get_request(url=url, params=params)
                soup = BeautifulSoup(r.text, 'lxml')
                table_element = soup.select('table')[0]
                th_element_list = table_element.select('th')[1:]
                tr_element_list = table_element.select('tr')[2:-1]
            for tr_element in tr_element_list:
                td_element_list = tr_element.select('td')
                list_length = len(td_element_list)
                fixed_length = list_length - list_length % 3
                self.json_result[family].append({})
                for j in range(fixed_length):
                    col_dec = th_element_list[j].text.strip().replace('\n', '')
                    col = zhuyaorenyuan_column_dict[col_dec]
                    td = td_element_list[j]
                    val = self.pattern.sub('', td.text)
                    self.json_result[family][-1][col] = val
                    if j == 2 and fixed_length == 6:
                        self.json_result[family].append({})
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1

    def get_fen_zhi_ji_gou(self, table_element):
        """
        查询分支机构信息
        :param table_element:
        :return:
        """
        family = 'Branches'
        table_id = '08'
        self.json_result[family] = []
        th_element_list = table_element.select('th')[1:]
        tr_element_list = table_element.select('tr')[2:]
        for tr_element in tr_element_list:
            td_element_list = tr_element.select('td')
            col_nums = len(th_element_list)
            self.json_result[family].append({})
            for j in range(col_nums):
                col_dec = th_element_list[j].text.strip().replace('\n', '')
                col = fenzhijigou_column_dict[col_dec]
                td = td_element_list[j]
                val = self.pattern.sub('', td.text)
                self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family], ensure_ascii=False)

    def get_qing_suan(self, table_element):
        """
        查询清算信息
        :param table_element:
        :return:
        """
        family = 'liquidation_Information'
        table_id = '09'
        self.json_result[family] = []
        tr_element_list = table_element.select('tr')[1:]
        # self.json_result[family].append({})
        for tr_element in tr_element_list:
            td_element = tr_element.select('td')
            th_element = tr_element.select('th')
            col_dec = th_element[0].text.strip()
            col = qingsuan_column_dict[col_dec]
            val = self.pattern.sub('', td_element[0].text)
            # self.json_result[family][-1][col] = val
            if col_dec == u'清算组负责人':
                cheng_yuan = val
            else:
                fu_ze_ren = val
        # print cheng_yuan, fu_ze_ren
        result_json = []
        if cheng_yuan != '' and fu_ze_ren != '':
            result_json.append({'rowkey': '%s_%s_%s_' % (self.cur_mc, table_id, self.cur_zch),
                                family + ':' + 'liquidation_member': 'cheng_yuan',
                                family + ':' + 'liquidation_pic': 'fu_ze_ren',
                                family + ':registrationno': self.cur_zch,
                                family + ':enterprisename': self.cur_mc
                                })
            self.json_result[family].extend(result_json)
            # print json.dumps(self.json_result[family], ensure_ascii=False)

    def get_dong_chan_di_ya(self):
        """
        查询动产抵押信息
        :return:动产抵押信息
        """
        family = 'Chattel_Mortgage'
        table_id = '11'
        self.json_result[family] = []
        values = {}
        url = 'http://gsxt.zjaic.gov.cn/dcdyapplyinfo/doReadDcdyApplyinfoList.do?regNo=%s&uniSCID=%s' % (self.regno, self.cur_zch)
        params = {'corpid': self.corpid}
        r = self.get_request(url=url)
        if u'系统警告' not in r.text:
            soup = BeautifulSoup(r.text, 'lxml')
            table_element = soup.find("table")
            if u'此企业暂无动产抵押登记信息' not in table_element.text:
                th_element_list = table_element.select('th')[1:]
                tr_element_list = table_element.select('tr')[2:]
                for tr_element in tr_element_list:
                    td_element_list = tr_element.select('td')
                    col_nums = len(th_element_list)
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n', '')
                        col = dongchandiyadengji_column_dict[col_dec]
                        td = td_element_list[j]
                        val = self.pattern.sub('', td.text)
                        if col_dec == u'详情':
                            link = td.select('a')[0].attrs['href']
                            val =  'http://gsxt.zjaic.gov.cn' + link
                            values[col] = val
                            diya_detail = self.get_diya_detail(link)
                            values.update(diya_detail)
                        else:
                            values[col] = val
                    self.json_result[family].append(values)
                    values = {}
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family][i], ensure_ascii=False)

    def get_diya_detail(self, link):
        values = {}
        """动产抵押登记信息"""
        dcdydj = list()
        dcdydj_table_id = '63'
        dcdydj_dict = dict()
        family = 'dcdydj'
        url = 'http://gsxt.zjaic.gov.cn' + link
        r_1 = self.get_request(url, verify=False)
        soup = BeautifulSoup(r_1.text, 'lxml')
        table_element = soup.find_all(class_='detailsList')
        dcdydj_table = table_element[0]
        dcdydj_tr_list = dcdydj_table.find_all('tr')
        for tr_element in dcdydj_tr_list[1:]:
            th_element_list = tr_element.find_all('th')
            td_element_list = tr_element.find_all('td')
            col_nums = len(td_element_list)
            for i in range(col_nums):
                col_dec = th_element_list[i].get_text().strip().replace('\n', '')
                if col_dec <> u'':
                    col = dcdydj_column_dict[col_dec]
                    val = td_element_list[i].get_text().strip().replace('\n', '').replace('\t', '').replace('\r', '')
                    dcdydj_dict[col] = val
        mot_no = dcdydj_dict['dcdyzx:dcdy_djbh']
        mot_date = dcdydj_dict['dcdyzx:dcdy_djrq']
        dcdydj_dict['rowkey'] = '%s_%s_%s_%s' % (self.cur_mc, mot_no,mot_date, dcdydj_table_id)
        dcdydj_dict[family + ':registrationno'] = self.cur_zch
        dcdydj_dict[family + ':enterprisename'] = self.cur_mc
        dcdydj.append(dcdydj_dict)
        values['Chattel_Mortgage:dcdydj'] = dcdydj # 动产抵押登记信息

        """抵押权人概况"""
        family = 'dyqrgk'
        dyqrgk = []
        dyqrgk_values = []
        dyqrgk_table_id = '55' # 抵押权人概况表格
        dyqrgk_table = table_element[1]
        dyqrgk_tr_list = dyqrgk_table.find_all('tr')
        th_element_list = dyqrgk_table.find_all('th')[1:]
        for tr_element in dyqrgk_tr_list[2:]:
            td_element_list = tr_element.find_all('td')
            col_nums = len(th_element_list)
            dyqrgk_values.append({})
            for i in range(col_nums):
                col_dec = th_element_list[i].get_text().strip().replace('\n', '')
                col = dyqrgk_column_dict[col_dec]
                val = td_element_list[i].get_text().strip().replace('\n', '')
                dyqrgk_values[-1][col] = val
        for i in range(len(dyqrgk_values)):
            dyqrgk_values[i]['rowkey'] = '%s_%s_%s_%s_%d' % (self.cur_mc, mot_no,mot_date, dyqrgk_table_id, i+1)
            dyqrgk_values[i][family + ':registrationno'] = self.cur_zch
            dyqrgk_values[i][family + ':enterprisename'] = self.cur_mc
            dyqrgk_values[i][family + ':id'] = i+1
            # print json.dumps(dyqrgk_values[i], ensure_ascii=False)
            dyqrgk.append(dyqrgk_values)
            values['Chattel_Mortgage:dyqrgk'] = dyqrgk # 抵押权人概况

        """被担保债券概况"""
        family = 'bdbzqgk'
        bdbzqgk = list()
        bdbzqgk_table_id = '56'
        bdbzqgk_dict = dict()
        bdbzqgk_table = table_element[2]
        bdbzqgk_tr_list = bdbzqgk_table.find_all('tr')
        for tr_element in bdbzqgk_tr_list[1:]:
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
        dywgk_values = []
        s = 1
        pnum = 1
        dywgk_table = table_element[3]
        dywgk_tr_list = dywgk_table.find_all('tr')
        dywgk_th_list = dywgk_table.find_all('th')[1:]
        tr_element_list = dywgk_tr_list[2:]
        if len(dywgk_th_list)==6:
            page_num = dywgk_table.find_all('th')[-1].text.split('\n')[1].strip()
            pnum = page_num[1:-1]
        for u in range(int(pnum)):
            if len(dywgk_th_list) == 6:
                for s in range(5):
                    url1 = 'http://gsxt.zjaic.gov.cn' + link
                    params = {'dcdyPawnPagination.currentPage':u,'cdyPawnPagination.pageSize':'5'}
                    r1 = self.post_request(url, params = params, verify=False)
                    soup = BeautifulSoup(r1.text, 'lxml')
                    if u'系统警告，累了' in r1.text:
                        continue
                    table_element = soup.find_all(class_='detailsList')
                    dcdydj_table = table_element[-1]
                    dywgk_th_list = dywgk_table.find_all('th')[1:-1]
                    dywgk_tr_list = dywgk_table.find_all('tr')
                    tr_element_list = dywgk_tr_list[2:-1]
                    break
            if s == 4 and u > 0:
                break
            else:
                tr_element_list = dywgk_tr_list[2:]
            for tr_element in tr_element_list:
                td_element_list = tr_element.find_all('td')
                col_nums = len(td_element_list)
                dywgk_values.append({})
                for i in range(col_nums):
                    col_dec = dywgk_th_list[i].get_text().strip().replace('\n', '')
                    col = dywgk_column_dict[col_dec]
                    val = td_element_list[i].get_text().strip().replace('\n', '').replace(' ', '')
                    dywgk_values[-1][col] = val
            if len(dywgk_th_list) == 6:
                dywgk_values.remove({})
                break
        for i in range(len(dywgk_values)):
            dywgk_values[i]['rowkey'] = '%s_%s_%s_%s_%d' % (self.cur_mc, mot_no,mot_date, dywgk_table_id, i+1)
            dywgk_values[i][family + ':registrationno'] = self.cur_zch
            dywgk_values[i][family + ':enterprisename'] = self.cur_mc
            dywgk_values[i][family + ':id'] = i+1
        dywgk.append(dywgk_values)
        values['Chattel_Mortgage:dywgk'] = dywgk # 抵押物概况
        return values

    def get_gu_quan_chu_zhi(self):
        """
        查询动产抵押信息
        :return:动产抵押信息
        """
        family = 'Equity_Pledge'
        table_id = '13'
        self.json_result[family] = []
        values = {}
        url = 'http://gsxt.zjaic.gov.cn/equityall/doReadEquityAllListFromPV.do'
        params = {'corpid': self.corpid}
        r = self.get_request(url=url, params=params)
        if u'系统警告' not in r.text:
            soup = BeautifulSoup(r.text, 'lxml')
            table_element = soup.find("table")
            if u'此企业暂无股权出质信息' not in table_element.text:
                th_element_list = table_element.select('th')[1:]
                tr_element_list = table_element.select('tr')[2:]
                for tr_element in tr_element_list:
                    td_element_list = tr_element.select('td')
                    col_nums = len(th_element_list)
                    # self.json_result[family].append({})
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n', '')
                        col = guquanchuzhidengji_column_dict[col_dec]
                        td = td_element_list[j]
                        val = self.pattern.sub('', td.text)
                        self.czrq = td_element_list[7].get_text().strip()
                        self.djbh = td_element_list[0].get_text().strip()
                        if val == u'详情':
                            link = td.select('a')[0].attrs['href']
                            val =  'http://gsxt.zjaic.gov.cn' + link
                            values[col] = val
                            pledge_detail = self.get_pledge_detail(link)
                            values.update(pledge_detail)
                        else:
                            values[col] = val
                    self.json_result[family].append(values)
                    values = {}
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1

    def get_pledge_detail(self, link):
        family = 'gqczzx'
        table_id = '60'
        values = {}
        pledge = []
        pledge_values = []
        url = 'http://gsxt.zjaic.gov.cn' + link
        r = self.get_request(url, verify=False)
        if u'暂无变更信息' not in r.text:
            soup = BeautifulSoup(r.text, 'lxml')
            table  = soup.find(class_='detailsList')
            dyqrgk_th_list = table.find_all('th')[1:]
            gqcz_tr_list = table.find_all('tr')[2:]
            for tr_element in gqcz_tr_list:
                td_element_list = tr_element.find_all('td')
                col_nums = len(td_element_list)
                pledge_values.append({})
                for i in range(col_nums):
                    col_dec = dyqrgk_th_list[i].get_text().strip().replace('\n', '')
                    col = gqczzx_biangeng_dict[col_dec]
                    val = td_element_list[i].get_text().strip().replace('\n', '')
                    pledge_values[-1][col] = val
            equity_date = self.czrq.replace(u'年', '-').replace(u'月', '-').replace(u'日', '')
        for i in range(len(pledge_values)):
            equity_no = self.djbh
            pledge_values[i]['rowkey'] = '%s_%s_%s_%s' % (self.cur_mc,equity_no,equity_date, table_id)
            pledge_values[i][family + ':registrationno'] = self.cur_zch
            pledge_values[i][family + ':enterprisename'] = self.cur_mc
            pledge_values[i][family + ':id'] = i+1
        pledge.append(pledge_values)
        values['Equity_Pledge:gqczzx'] = pledge # 抵押物概况
        return values


    def get_xing_zheng_chu_fa(self):
        """
        查询行政处罚信息
        :return:
        """
        family = 'Administrative_Penalty'
        table_id = '13'
        self.json_result[family] = []
        url = 'http://gsxt.zjaic.gov.cn/punishment/doViewPunishmentFromPV.do'
        params = {'corpid': self.corpid}
        r = self.get_request(url=url, params=params)
        if u'系统警告' not in r.text:
            soup = BeautifulSoup(r.text, 'lxml')
            table_element = soup.find("table")
            if u'此企业暂无行政处罚信息' not in table_element.text:
                th_element_list = table_element.select('th')[1:]
                tr_element_list = table_element.select('tr')[2:]
                for tr_element in tr_element_list:
                    td_element_list = tr_element.select('td')
                    col_nums = len(th_element_list)
                    self.json_result[family].append({})
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n', '')
                        col = xingzhengchufa_column_dict[col_dec]
                        td = td_element_list[j]
                        val = self.pattern.sub('', td.text)
                        self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family][i], ensure_ascii=False)

    def get_jing_ying_yi_chang(self):
        """
        查询经营异常信息
        :return:
        """
        family = 'Business_Abnormal'
        table_id = '14'
        self.json_result[family] = []
        url = 'http://gsxt.zjaic.gov.cn/catalogapply/doReadCatalogApplyList.do'
        params = {'corpid': self.corpid}
        r = self.get_request(url=url, params=params)
        if u'系统警告' not in r.text:
            soup = BeautifulSoup(r.text, 'lxml')
            table_element = soup.find("table")
            if u'暂无经营异常信息' not in table_element.text:
                th_element_list = table_element.select('th')[1:]
                tr_element_list = table_element.select('tr')[2:]
                for tr_element in tr_element_list:
                    td_element_list = tr_element.select('td')
                    col_nums = len(th_element_list)
                    self.json_result[family].append({})
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n', '')
                        col =jingyingyichang_column_dict[col_dec]
                        td = td_element_list[j]
                        val = self.pattern.sub('', td.text)
                        self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps( self.json_result[family], ensure_ascii=False)

    def get_yan_zhong_wei_fa(self):
        """
        查询严重违法信息
        :return:严重违法信息
        """
        family = 'Serious_Violations'
        table_id = '15'
        self.json_result[family] = []
        url = 'http://gsxt.zjaic.gov.cn/blacklist/doViewBlackListInfo.do'
        params = {'corpid': self.corpid}
        r = self.get_request(url=url, params=params)
        if u'系统警告' not in r.text:
            soup = BeautifulSoup(r.text, 'lxml')
            table_element = soup.find("table")
            if u'此企业暂无严重违法信息' not in table_element.text:
                th_element_list = table_element.select('th')[1:]
                tr_element_list = table_element.select('tr')[2:]
                for tr_element in tr_element_list:
                    td_element_list = tr_element.select('td')
                    col_nums = len(th_element_list)
                    self.json_result[family].append({})
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n', '')
                        col = yanzhongweifa_column_dict[col_dec]
                        td = td_element_list[j]
                        val = self.pattern.sub('', td.text)
                        self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family], ensure_ascii=False)

    def get_chou_cha_jian_cha(self):
        """
        查询抽查检查信息
        :return:抽查检查信息
        """
        family = 'Spot_Check'
        table_id = '16'
        self.json_result[family] = []
        url = 'http://gsxt.zjaic.gov.cn/pubcheckresult/doViewPubCheckResultList.do'
        params = {'corpid': self.corpid}
        r = self.get_request(url=url, params=params)
        if u'系统警告' not in r.text:
            soup = BeautifulSoup(r.text, 'lxml')
            table_element = soup.find("table")
            if u'此企业无抽查检查信息' not in table_element.text:
                th_element_list = table_element.select('th')[1:]
                tr_element_list = table_element.select('tr')[2:]
                for tr_element in tr_element_list:
                    td_element_list = tr_element.select('td')
                    col_nums = len(th_element_list)
                    self.json_result[family].append({})
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n', '')
                        col = chouchajiancha_column_dict[col_dec]
                        td = td_element_list[j]
                        val = self.pattern.sub('', td.text)
                        self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family], ensure_ascii=False)

if __name__ == '__main__':
    args_dict = get_args()
    # args_dict = {'companyName': u'浙江朗诗德健康饮水设备股份有限公司', 'accountId': '123', 'taskId': '456'}
    searcher = ZheJiangSearcher()
    searcher.submit_search_request(u'岱山县鼎点理发店')
    searcher.info(json.dumps(searcher.json_result, ensure_ascii=False))
    # for i in range(10):
    #     try:
    #         searcher.submit_search_request(keyword=args_dict['companyName'], flags=True,account_id=args_dict['accountId'], task_id=args_dict['taskId'])
    #     except Exception, e:
    #         traceback.print_exc(e)

