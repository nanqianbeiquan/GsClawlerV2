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
import uuid


class HaiNanSearcher(Searcher):
    load_func_dict = {}
    lock_id = 0
    cid = None
    doc_soup = None

    def __init__(self):
        super(HaiNanSearcher, self).__init__(use_proxy=False)
        self.load_func_dict[u'基本信息'] = self.get_ji_ben
        self.load_func_dict[u'股东信息'] = self.get_gu_dong
        self.load_func_dict[u'变更信息'] = self.get_bian_geng
        self.load_func_dict[u'主要人员信息'] = self.get_zhu_yao_ren_yuan
        self.load_func_dict[u'分支机构信息'] = self.get_fen_zhi_ji_gou
        self.load_func_dict[u'清算信息'] = self.get_qing_suan
        self.load_func_dict[u'投资人信息'] = self.get_tou_zi_ren
        self.load_func_dict[u'动产抵押登记信息'] = self.get_dong_chan_di_ya
        self.load_func_dict[u'股权出质登记信息'] = self.get_gu_quan_chu_zhi
        self.load_func_dict[u'行政处罚信息'] = self.get_xing_zheng_chu_fa
        self.load_func_dict[u'经营异常信息'] = self.get_jing_ying_yi_chang
        self.load_func_dict[u'严重违法信息'] = self.get_yan_zhong_wei_fa
        self.load_func_dict[u'严重违法失信信息'] = self.get_yan_zhong_wei_fa
        self.load_func_dict[u'抽查检查信息'] = self.get_chou_cha_jian_cha
        # self.load_func_dict[u'主管部门（出资人）信息'] = self.get_zhu_guan_bu_men     #Modified by Jing
        # self.load_func_dict[u'参加经营的家庭成员姓名'] = self.load_jiatingchengyuan     # Modified by Jing
        # self.load_func_dict[u'合伙人信息'] = self.load_hehuoren     #Modified by Jing
        # self.load_func_dict[u'成员名册'] = self.load_chengyuanmingce     # Modified by Jing
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:45.0) Gecko/20100101 Firefox/45.0",
                        "Host": "aic.hainan.gov.cn:1888",
                        "Accept": "*/*",
                        "Accept-Encoding": "gzip, deflate",
                        "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
                        "Referer": "http://aic.hainan.gov.cn:1888/search.jspx",
                        "Connection": "keep-alive"
                        }
        self.set_config()
        self.log_name = self.topic + "_" + str(uuid.uuid1())

    def set_config(self):
        self.plugin_path = os.path.join(sys.path[0], '../hai_nan/ocr/hainan/hainan.bat')
        self.list_path = os.path.join(sys.path[0], '../hai_nan/IllegalCharacterList/list.txt')
        self.group = 'Crawler'  # 正式
        self.kafka = KafkaAPI("GSCrawlerResult")  # 正式
        # self.group = 'CrawlerTest'  # 测试
        # self.kafka = KafkaAPI("GSCrawlerTest")  # 测试
        self.topic = 'GsSrc46'
        self.province = u'海南省'
        self.kafka.init_producer()

    def download_yzm(self):
        image_url = 'http://aic.hainan.gov.cn:1888/validateCode.jspx?type=0'
        r = self.get_request(image_url)
        yzm_path = self.get_yzm_path()
        with open(yzm_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    f.flush()
            f.close()
        return yzm_path

    def get_tag_a_from_page(self, keyword, flags=True):
        url = 'http://aic.hainan.gov.cn:1888/searchList.jspx'
        for t in range(50):
            yzm = self.get_yzm()
            params = {'entName': keyword, 'checkNo': yzm}
            r = self.post_request(url=url, params=params)
            soup = BeautifulSoup(r.text, 'lxml')
            body_text = soup.select('html > body')[0].text.strip()
            if u'验证码不正确或已失效' in body_text:
                continue
            elif u'您搜索的条件无查询结果' in body_text:
                return None
            elif u'查询条件中含有非法字符' in body_text:
                self.info(u'存在非法字符')
                list_path = self.list_path
                f = open(list_path, 'a')
                f.write(keyword.encode('gbk'))
                f.write('\n')
                f.flush()
                f.close()
                break
            else:
                search_result_json = {}
                # print '*** %d' % r.status_code
                search_result_text = soup.select('html body div div div div ul li a')[0].attrs['href']
                if search_result_text != u'':
                    self.cur_mc = soup.select('html body div div div div ul li a')[0].text.strip()
                    if flags:
                        if keyword == self.cur_mc :
                            self.cur_zch = soup.select('html body div div div div ul li span')[0].text.strip()
                            search_result_json['entname'] = self.cur_mc
                            search_result_json['regno'] = self.cur_zch
                            search_result_json['id'] = search_result_text.split("=")[1]
                            tag_a = json.dumps(search_result_json, ensure_ascii=False)
                    else:
                        self.cur_zch = soup.select('html body div div div div ul li span')[0].text.strip()
                        search_result_json['entname'] = self.cur_mc
                        search_result_json['regno'] = self.cur_zch
                        search_result_json['id'] = search_result_text.split("=")[1]
                        tag_a = json.dumps(search_result_json, ensure_ascii=False)
                    return tag_a

    def get_search_args(self, tag_a, keyword):
        self.cid = None
        search_result_json = json.loads(tag_a)
        if search_result_json.get('entname', None) == keyword:
            self.cid = search_result_json['id']
            self.cur_mc = search_result_json['entname'].replace('(', u'（').replace(')', u'）')  # 公司名称括号统一转成全角
            self.cur_zch = search_result_json['regno']
            return [id, keyword]
        else:
            return []

    def parse_detail(self):
        """
        解析公司详情信息
        :param kwargs:
        :return:
        """
        self.get_detail_info()

    def get_detail_info(self):
        url = 'http://aic.hainan.gov.cn:1888/businessPublicity.jspx'
        params = {'id': self.cid,'ad_check':'1'}
        r = self.get_request(url=url, params=params)
        self.doc_soup = BeautifulSoup(r.text, 'lxml')
        table_elements = self.doc_soup.select("html > body > div > div > div > div > table")
        for table_element in table_elements:
            table_name = table_element.find("th").text.strip().split('\n')[0]  # 表格名称
            table_name=table_name.replace(u'股东（发起人）信息',u'股东信息')
            table_name=self.pattern.sub('',table_name)
            if u'<<' in table_name:
                continue
            elif table_name in self.load_func_dict:
                self.load_func_dict[table_name](table_element)
            else:
                self.info(u'未知表名...')

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
                if u'统一社会信用代码' in desc and len(val) == 18:
                    result_json[0][u'社会信用代码'] = val
                    result_json[0][u'注册号码'] = ''
                if u'统一社会信用代码' in desc and len(val) != 18:
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
        :param param_id:
        :param table_element:
        :return:
        """
        family = 'Shareholder_Info'
        table_id = '04'
        self.json_result[family] = []
        th_element_list = table_element.select('th')[1:]
        # urll = 'http://aic.hainan.gov.cn:1888/businessPublicity.jspx'
        # para = {'id': self.cid,'ad_check':'1'}
        # r = self.get_request(url=urll, params=para)
        # bsoup = BeautifulSoup(r.text, 'lxml')
        pages=self.doc_soup.select('div#invDiv + *')[0].text.strip()
        page_nums=re.findall(r'\d',pages)
        for i in range(len(page_nums)):
            url = 'http://aic.hainan.gov.cn:1888/QueryInvList.jspx'
            params = {'mainId': self.cid, 'pno': '%s' % (i+1)}
            r = self.get_request(url = url, params = params)
            soup = BeautifulSoup(r.text, 'lxml')
            table_element = soup.find('table')
            tr_element_list = table_element.select('tr')
            for tr_element in tr_element_list:
                td_element_list = tr_element.select('td')
                col_nums = len(th_element_list)
                self.json_result[family].append({})
                for j in range(col_nums):
                    col_dec = th_element_list[j].text.strip().replace('\n', '')
                    col = gudong_column_dict[col_dec]
                    td = td_element_list[j]
                    val = td.text.strip()
                    if val==u'详情':
                        id=td.select('a')[0].attrs['onclick'].split('=')[1].replace('\')','')
                        detail_list = self.get_gu_dong_detail(id, table_element)
                        for detail_json in detail_list:
                            for k in detail_json:
                                col = k
                                val = detail_json[k]
                                self.json_result[family][-1][col] = val
                    else:
                        self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family][i], ensure_ascii=False)

    def get_gu_dong_detail(self, id,table_element):
        detail_dict_list = []
        url = 'http://aic.hainan.gov.cn:1888/queryInvDetailAction.jspx'
        params = {'id': id, 'ad_cheak': '1'}
        r = self.get_request(url = url, params = params)
        soup = BeautifulSoup(r.text, 'lxml')
        table_element=soup.find('table')
        th_element_list=table_element.select('th')[2:]
        tr_element_list=table_element.select('tr')[3:4]
        for tr_element in tr_element_list:
            # detail_dict_list.append({})
            td_element_list = tr_element.select('td')[1:]
            col_nums = len(th_element_list)
            detail_dict_list.append({})
            for j in range(col_nums):
                col_dec = th_element_list[j].text.strip().replace('\n', '')
                if u'明细' in col_dec:
                    continue
                if j > 3:
                    j = j-2
                col = gudong_column_dict[col_dec]
                td = td_element_list[j]
                val = td.text.strip()
                detail_dict_list[-1][col] = val
        # print 'detail_dict_list:',detail_dict_list
        return detail_dict_list

    def get_tou_zi_ren(self, table_element):
        pass

    def get_bian_geng(self, table_element):
        """
        查询变更信息
        :param param_id:
        :param table_element:
        :return:
        """
        family = 'Changed_Announcement'
        table_id = '05'
        self.json_result[family] = []
        th_element_list = table_element.select('th')[1:]
        # urll = 'http://aic.hainan.gov.cn:1888/businessPublicity.jspx'
        # para = {'id': self.cid,'ad_check':'1'}
        # r = self.get_request(url=urll, params=para)
        # bsoup = BeautifulSoup(r.text, 'lxml')
        if self.doc_soup.select('div#altDiv > table')[0].text.strip() !=u'':
            pages=self.doc_soup.select('div#altDiv + *')[0].text.strip()
            page_nums=re.findall(r'\d',pages)
            for i in range(len(page_nums)):
                url = 'http://aic.hainan.gov.cn:1888/QueryAltList.jspx'
                params = {'mainId': self.cid, 'pno': '%s' % (i+1)}
                r = self.get_request(url = url, params = params)
                soup = BeautifulSoup(r.text, 'lxml')
                table_element = soup.find('table')
                tr_element_list = table_element.select('tr')
                for tr_element in tr_element_list:
                    td_element_list = tr_element.select('td')
                    col_nums = len(th_element_list)
                    self.json_result[family].append({})
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n', '')
                        col = biangeng_column_dict[col_dec]
                        td = td_element_list[j]
                        val = self.pattern.sub('', td.text)
                        # val = td.text.strip().replace('\n','').replace('\t','').replace('\t','')
                        if val.endswith(u'更多'):
                            val = val[val.index(u'更多')+2:val.index(u'收起更多')]
                        self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family][i], ensure_ascii=False)

    def get_zhu_yao_ren_yuan(self, table_element):
        """
        查询主要人员信息
        :param param_id:
        :param table_element:
        :return:
        """
        family = 'KeyPerson_Info'
        table_id = '06'
        self.json_result[family] = []
        th_element_list = table_element.select('th')[1:]
        # urll = 'http://aic.hainan.gov.cn:1888/businessPublicity.jspx'
        # para = {'id': self.cid,'ad_check':'1'}
        # r = self.get_request(url=urll, params=para)
        # bsoup = BeautifulSoup(r.text, 'lxml')
        pages=self.doc_soup.select('div#memDiv + *')[0].text.strip()
        page_nums=re.findall(r'\d',pages)
        for i in range(len(page_nums)):
            url = 'http://aic.hainan.gov.cn:1888/QueryMemList.jspx'
            params = {'mainId': self.cid, 'pno': '%s' % (i+1)}
            r = self.get_request(url = url, params = params)
            soup = BeautifulSoup(r.text, 'lxml')
            table_element = soup.find('table')
            tr_element_list = table_element.select('tr')
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
                    if col_dec == u'序号' and val == u'':
                        self.json_result[family].remove({})
                        break
                    self.json_result[family][-1][col] = val
                    if j == 2 and fixed_length == 6:
                        self.json_result[family].append({})
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family][i], ensure_ascii=False)

    def get_fen_zhi_ji_gou(self, table_element):
        """
        查询分支机构信息
        :param param_id:
        :param table_element:
        :return:
        """
        family = 'Branches'
        table_id = '08'
        self.json_result[family] = []
        th_element_list = table_element.select('th')[1:]
        # urll = 'http://aic.hainan.gov.cn:1888/businessPublicity.jspx'
        # para = {'id': self.cid,'ad_check':'1'}
        # r = self.get_request(url=urll, params=para)
        # bsoup = BeautifulSoup(r.text, 'lxml')
        if self.doc_soup.select('div#childDiv > table')[0].text.strip() !=u'':
            pages=self.doc_soup.select('div#childDiv + *')[0].text.strip()
            page_nums=re.findall(r'\d',pages)
            for i in range(len(page_nums)):
                url = 'http://aic.hainan.gov.cn:1888/QueryChildList.jspx'
                params = {'mainId': self.cid, 'pno': '%s' % (i+1)}
                r = self.get_request(url = url, params = params)
                soup = BeautifulSoup(r.text, 'lxml')
                table_element = soup.find('table')
                tr_element_list = table_element.select('tr')
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
            # print json.dumps(self.json_result[family][i], ensure_ascii=False)

    def get_qing_suan(self, table_element):
        """
        查询清算信息
        :param param_corpid:
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
        # print cheng_yuan,fu_ze_ren
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

    def get_dong_chan_di_ya(self, table_element):
        """
        查询动产抵押信息
        :param param_corpid:
        :param table_element:
        :return:
        """
        family = 'Chattel_Mortgage'
        table_id = '11'
        self.json_result[family] = []
        th_element_list = table_element.select('th')[1:]
        # urll = 'http://aic.hainan.gov.cn:1888/businessPublicity.jspx'
        # para = {'id':self.cid,'ad_check':'1'}
        # r = self.get_request(url=urll, params=para)
        # bsoup = BeautifulSoup(r.text, 'lxml')
        if self.doc_soup.select('div#mortDiv > table')[0].text.strip() !=u'':
            pages=self.doc_soup.select('div#mortDiv + *')[0].text.strip()
            page_nums=re.findall(r'\d',pages)
            for i in range(len(page_nums)):
                url = 'http://aic.hainan.gov.cn:1888/QueryMortList.jspx'
                params = {'mainId': self.cid, 'pno': '%s' % (i+1)}
                r = self.get_request(url = url, params = params)
                soup = BeautifulSoup(r.text, 'lxml')
                table_element = soup.find('table')
                tr_element_list = table_element.select('tr')
                for tr_element in tr_element_list:
                    td_element_list = tr_element.select('td')
                    col_nums = len(th_element_list)
                    self.json_result[family].append({})
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n', '')
                        col = dongchandiyadengji_column_dict[col_dec]
                        td = td_element_list[j]
                        val = self.pattern.sub('', td.text)
                        self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family], ensure_ascii=False)

    def get_gu_quan_chu_zhi(self, table_element):
        """
        查询动产抵押信息
        :param param_corpid:
        :param table_element:
        :return:
        """
        family = 'Equity_Pledge'
        table_id = '13'
        self.json_result[family] = []
        th_element_list = table_element.select('th')[1:]
        # urll = 'http://aic.hainan.gov.cn:1888/businessPublicity.jspx'
        # para = {'id': self.cid,'ad_check':'1'}
        # r = self.get_request(url=urll, params=para)
        # bsoup = BeautifulSoup(r.text, 'lxml')
        if self.doc_soup.select('div#pledgeDiv > table')[0].text.strip() !=u'':
            pages=self.doc_soup.select('div#pledgeDiv + *')[0].text.strip()
            page_nums=re.findall(r'\d',pages)
            for i in range(len(page_nums)):
                url = 'http://aic.hainan.gov.cn:1888/QueryPledgeList.jspx'
                params = {'mainId': self.cid, 'pno': '%s' % (i+1)}
                r = self.get_request(url = url, params = params)
                soup = BeautifulSoup(r.text, 'lxml')
                table_element = soup.find('table')
                tr_element_list = table_element.select('tr')
                for tr_element in tr_element_list:
                    td_element_list = tr_element.select('td')
                    col_nums = len(th_element_list)
                    self.json_result[family].append({})
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n', '')
                        col = guquanchuzhidengji_column_dict[col_dec]
                        td = td_element_list[j]
                        val = self.pattern.sub('', td.text)
                        self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family], ensure_ascii=False)

    def get_xing_zheng_chu_fa(self, table_element):
        """
        查询行政处罚信息
        :param param_corpid:
        :param table_element:
        :return:
        """
        family = 'Administrative_Penalty'
        table_id = '13'
        self.json_result[family] = []
        th_element_list = table_element.select('th')[1:]
        # urll = 'http://aic.hainan.gov.cn:1888/businessPublicity.jspx'
        # para = {'id': self.cid,'ad_check':'1'}
        # r = self.get_request(url=urll, params=para)
        # bsoup = BeautifulSoup(r.text, 'lxml')
        if self.doc_soup.select('div#punDiv > table')[0].text.strip() !=u'':
            pages=self.doc_soup.select('div#punDiv + *')[0].text.strip()
            page_nums=re.findall(r'\d',pages)
            for i in range(len(page_nums)):
                url = 'http://aic.hainan.gov.cn:1888/QueryPunList.jspx'
                params = {'mainId': self.cid, 'pno': '%s' % (i+1)}
                r = self.get_request(url = url, params = params)
                soup = BeautifulSoup(r.text, 'lxml')
                table_element = soup.find('table')
                tr_element_list = table_element.select('tr')
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
            # print json.dumps(self.json_result[family], ensure_ascii=False)

    def get_jing_ying_yi_chang(self, table_element):
        """
        查询经营异常信息
        :param table_element:
        :return:
        """
        family = 'Business_Abnormal'
        table_id = '14'
        self.json_result[family] = []
        th_element_list = table_element.select('th')[1:]
        # urll = 'http://aic.hainan.gov.cn:1888/businessPublicity.jspx'
        # para = {'id': self.cid,'ad_check':'1'}
        # r = self.get_request(url=urll, params=para)
        # bsoup = BeautifulSoup(r.text, 'lxml')
        if self.doc_soup.select('div#excDiv > table')[0].text.strip() !=u'':
            pages=self.doc_soup.select('div#excDiv + *')[0].text.strip()
            page_nums=re.findall(r'\d',pages)
            for i in range(len(page_nums)):
                url = 'http://aic.hainan.gov.cn:1888/QueryExcList.jspx'
                params = {'mainId': self.cid, 'pno': '%s' % (i+1)}
                r = self.get_request(url = url, params = params)
                soup = BeautifulSoup(r.text, 'lxml')
                table_element = soup.find('table')
                tr_element_list = table_element.select('tr')
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
            # print json.dumps( self.json_result[family][i], ensure_ascii=False)

    def get_yan_zhong_wei_fa(self, table_element):
        """
        查询严重违法信息
        :param param_corpid:
        :param table_element:
        :return:
        """
        family = 'Serious_Violations'
        table_id = '15'
        self.json_result[family] = []
        th_element_list = table_element.select('th')[1:]
        # urll = 'http://aic.hainan.gov.cn:1888/businessPublicity.jspx'
        # para = {'id': self.cid,'ad_check':'1'}
        # r = self.get_request(url=urll, params=para)
        # bsoup = BeautifulSoup(r.text, 'lxml')
        if self.doc_soup.select('div#serillDiv > table')[0].text.strip() !=u'':
            pages=self.doc_soup.select('div#serillDiv + *')[0].text.strip()
            page_nums=re.findall(r'\d',pages)
            for i in range(len(page_nums)):
                url = 'http://aic.hainan.gov.cn:1888/QuerySerillList.jspx'
                params = {'mainId': self.cid, 'pno': '%s' % (i+1)}
                r = self.get_request(url = url, params = params)
                soup = BeautifulSoup(r.text, 'lxml')
                table_element = soup.find('table')
                tr_element_list = table_element.select('tr')
                for tr_element in tr_element_list:
                    td_element_list = tr_element.select('td')
                    col_nums = len(th_element_list)
                    self.json_result[family].append({})
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n', '')
                        col =yanzhongweifa_column_dict[col_dec]
                        td = td_element_list[j]
                        val = self.pattern.sub('', td.text)
                        self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family], ensure_ascii=False)

    def get_chou_cha_jian_cha(self, table_element):
        """
        查询抽查检查信息
        :param param_corpid:
        :param table_element:
        :return:
        """
        family = 'Spot_Check'
        table_id = '16'
        self.json_result[family] = []
        th_element_list = table_element.select('th')[1:]
        # urll = 'http://aic.hainan.gov.cn:1888/businessPublicity.jspx'
        # para = {'id': self.cid,'ad_check':'1'}
        # r = self.get_request(url=urll, params=para)
        # bsoup = BeautifulSoup(r.text, 'lxml')
        if self.doc_soup.select('div#spotCheckDiv > table')[0].text.strip() !=u'':
            pages=self.doc_soup.select('div#spotCheckDiv + *')[0].text.strip()
            page_nums=re.findall(r'\d',pages)
            for i in range(len(page_nums)):
                url = 'http://aic.hainan.gov.cn:1888/QuerySpotCheckList.jspx'
                params = {'mainId': self.cid, 'pno': '%s' % (i+1)}
                r = self.get_request(url = url, params = params)
                soup = BeautifulSoup(r.text, 'lxml')
                table_element = soup.find('table')
                tr_element_list = table_element.select('tr')
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
            # print json.dumps(self.json_result[family][i], ensure_ascii=False)

if __name__ == '__main__':
    args_dict = get_args()
    args_dict = {'companyName': u'白沙海汽出租车有限公司', 'accountId': '123', 'taskId': '456'}
    searcher = HaiNanSearcher()
    searcher.submit_search_request(u'白沙海汽出租车有限公司')
    # searcher.submit_search_request(keyword=args_dict['companyName'], flags = True, account_id=args_dict['accountId'], task_id=args_dict['taskId'])
    searcher.info(json.dumps(searcher.json_result, ensure_ascii=False))