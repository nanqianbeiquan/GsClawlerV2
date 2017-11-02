# coding=utf-8

import requests
import os
from bs4 import BeautifulSoup
import json
import re
import datetime
from requests.exceptions import RequestException
import sys
import time
import random
from lxml import html
from GuangdongConfig import *
import subprocess
from gs.ProxyConf import ProxyConf
from gs.ProxyConf import key1 as app_key
from gs.TimeUtils import get_cur_time
# from lxml import XMLSyntaxError
import traceback
from gs.Searcher import Searcher, save_dead_company

class GuangdongShenzhen(Searcher):

    search_result_json = None
    pattern = re.compile("\s")
    cur_mc = ''
    cur_zch = ''
    json_result_data = {}
    today = None
    credit_ticket = None
    cur_time = None
    plugin_path = os.path.join(sys.path[0], 'ocr/guangdong.bat')
    ent_url = ''
    params = dict()
    province = u'广东省'

    def __init__(self):
        super(GuangdongShenzhen, self).__init__(use_proxy=True)
        self.today = str(datetime.date.today()).replace('-', '')
        self.tree_1 = ''
        self.tree_2 = ''
        self.tree_3 = ''
        self.headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:47.0) Gecko/20100101 Firefox/47.0",
                        "Host": "gsxt.gdgs.gov.cn",
                        "Accept": "*/*",
                        "Accept-Encoding": "gzip, deflate",
                        "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1",
                        "Content-type": "application/json"
                        }

    def get_detail(self, ent_url):
        self.ent_url = ent_url
        headers = {
                    'Host': "www.szcredit.com.cn",
                    "Referer": "http://gsxt.gdgs.gov.cn/aiccips/CheckEntContext/showInfo.html",
                    "User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0",
        }
        r_1 = self.get_request(ent_url, headers=headers)  #
        """
        基本信息、投资人信息、主要人员信息、分支机构信息、清算信息、动产抵押登记信息、股权出质登记信息、异常名录信息、严重违法信息、抽查检查信息
        """
        r_1.encoding = 'gbk'
        self.tree_1 = html.fromstring(r_1.text)
        # self.tree_1 = html.fromstring(r_1.text)
        viewstate = self.tree_1.xpath('.//*[@id="__VIEWSTATE"]')[0].get('value')
        eventargument = self.tree_1.xpath('.//*[@id="__EVENTARGUMENT"]')[0].get('value')
        viewstategenerator = self.tree_1.xpath('.//*[@id="__VIEWSTATEGENERATOR"]')[0].get('value')

        params_1 = {"ScriptManager1": "xingzhengchufa|Timer1", "__ASYNCPOST": 'true', "__EVENTTARGET": 'Timer1', "__VIEWSTATEGENERATOR": viewstategenerator,
                    "__EVENTARGUMENT": eventargument, "__VIEWSTATE": viewstate}
        headers = {
                    'Host': "www.szcredit.com.cn",
                    "Referer": ent_url,
                    "User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0",
                    "X-Requested-With": "XMLHttpRequest",
                    "X-MicrosoftAjax": "Delta=true",
                    }
        r_2 = self.post_request(ent_url, data=params_1, headers=headers)  # 行政处罚信息
        r_2.encoding = 'gbk'
        self.tree_2 = html.fromstring(r_2.text)

        params_1["__VIEWSTATE"] = re.findall('VIEWSTATE\|(.*?)\|', r_2.text)[0]
        params_1["ScriptManager1"] = "biangengxinxi|Timer2"
        params_1["__EVENTTARGET"] = "Timer2"
        r_3 = self.post_request(ent_url, data=params_1, headers=headers)  # 变更信息
        r_3.encoding = 'gbk'
        # self.info('r_3', r_3.text
        self.tree_3 = html.fromstring(r_3.text)
    def parse_detail_shen_zhen(self, ent_url):
        self.get_detail(ent_url)
        self.get_ji_ben()
        # self.get_gu_dong()
        self.get_tou_zi_ren()
        self.get_bian_geng()
        self.get_zhu_yao_ren_yuan()
        self.get_fen_zhi_ji_gou()
        self.get_qing_suan()
        self.get_dong_chan_di_ya()
        self.get_gu_quan_chu_zhi()
        self.get_xing_zheng_chu_fa()
        self.get_jing_ying_yi_chang()
        self.get_yan_zhong_wei_fa()
        self.get_chou_cha_jian_cha()
        # self.get_nian_bao_link(

    def get_ji_ben(self):
        """
        查询基本信息
        :return: 基本信息结果
        """
        self.info(u'查询基本信息')
        family = 'Registered_Info'
        table_id = '01'
        th_list = self.tree_1.xpath(".//*[@id='jibenxinxi']/table[1]//th")[1:]
        td_list = self.tree_1.xpath(".//*[@id='jibenxinxi']/table[1]//td")
        result_values = {}
        for i in range(len(td_list)):
            th = th_list[i]
            td = td_list[i]
            desc = th.text
            if td.xpath("span"):
                val = td.xpath("span")[0].text
            else:
                val = td.text
            if desc:
                desc = desc.strip()
                if desc in ji_ben_dict:
                    desc = family + ':' + ji_ben_dict[desc]
                    if val:
                        val = val.strip().replace('\n', '')
                    result_values[desc] = val
        if self.tree_1.xpath(".//*[@id='RegInfo_SSDJCBuItem_labCBuItem']"):
            result_values[family + ':businessscope'] = self.tree_1.xpath(".//*[@id='RegInfo_SSDJCBuItem_labCBuItem']")[0].text
        assert len(result_values) > 1, 'tag_a in useless'
        if family + ":" + 'tyshxy_code' in result_values:
            if result_values[family + ":" + 'tyshxy_code']:
                self.cur_zch = result_values[family + ":" + 'tyshxy_code']
            else:
                self.cur_zch = result_values.get(family + ":" + 'zch', '')
        result_values['rowkey'] = '%s_%s_%s_' % (self.cur_mc, table_id, self.cur_zch)
        result_values[family + ':registrationno'] = self.cur_zch
        result_values[family + ':enterprisename'] = self.cur_mc
        result_values[family + ':lastupdatetime'] = get_cur_time()
        result_values[family + ':province'] = u'广东省'
        self.json_result_data["Registered_Info"] = [result_values]

    def get_tou_zi_ren(self):
        """
        查询投资人信息
        :return: 基本信息结果
        """
        self.info(u'查询投资人信息')
        family = 'Investor_Info'
        table_id = '02'
        result_list = []
        result_values = {}
        j = 1
        th_list = self.tree_1.xpath(".//*[@id='table2']//th")
        tr_list = self.tree_1.xpath(".//*[@id='table2']//tr")
        if tr_list and len(tr_list) > 1:
            for tr in tr_list[1:]:
                td_list = tr.xpath("td")
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.text
                    if td.xpath("a"):
                        # self.info(u'查看投资人详情'
                        val = "http://www.szcredit.com.cn/web/GSZJGSPT/" + td.xpath("a")[0].get("href")
                        tou_zi_detail = self.get_tou_zi_ren_detail(val)
                        for detail_key in tou_zi_detail:
                            result_values[family + ":" + tou_zi_ren_dict[detail_key]] = tou_zi_detail[detail_key]
                    else:
                        val = td.text
                    if desc in tou_zi_ren_dict:
                            result_values[family + ":" + tou_zi_ren_dict[desc]] = val
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
            self.json_result_data["Investor_Info"] = result_list
            # self.info(json.dumps(self.json_result_data, ensure_ascii=False)

    def get_tou_zi_ren_detail(self, url):
        headers = {
                    'Host': "www.szcredit.com.cn",
                    "Referer": self.ent_url,
                    "User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0",
                    }
        r = self.get_request(url, headers=headers)
        r.encoding = 'gbk'
        # self.info(len(r.text)
        tree = html.fromstring(r.text)
        colum_name_list = tree.xpath(".//table//th")[1:]
        td_element_list = tree.xpath(".//td")
        del colum_name_list[3:5]
        col_num = len(colum_name_list)
        values = {}
        for i in range(col_num):
            col = colum_name_list[i].text.strip().replace('\n', '')
            if td_element_list[i].xpath("span"):
                val = td_element_list[i].xpath("span")[0].text
            else:
                val = td_element_list[i].text
            if val:
                values[col] = val
        # self.info(json.dumps(values,ensure_ascii=False)
        return values

    def get_bian_geng(self):
        """
        查询变更信息
        :return: 基本信息结果
        """
        self.info(u'查询变更信息')
        family = 'Changed_Announcement'
        table_id = '05'
        result_list = []
        result_values = {}
        j = 1
        th_list = self.tree_3.xpath(".//*[@id='alterPanel']//tr[2]/th")
        tr_list = self.tree_3.xpath(".//*[@id='alterPanel']//tr")
        if tr_list and len(tr_list) > 4:
            for tr in tr_list[2:-2]:
                td_list = tr.xpath("td")
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.text.strip()
                    val = td.xpath('string(.)')
                    if desc in bian_geng_dict:
                        if val:
                            result_values[family + ":" + bian_geng_dict[desc]] = val
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
            self.json_result_data["Changed_Announcement"] = result_list
            # self.info(json.dumps(self.json_result_data, ensure_ascii=False)

    def get_zhu_yao_ren_yuan(self):
        """
        查询主要人员信息
        :return: 主要人员信息结果
        """
        self.info(u'主要人员信息')
        family = 'KeyPerson_Info'
        table_id = '06'
        result_list = []
        result_values = {}
        j = 1
        th_list = self.tree_1.xpath(".//table[@id='t30']//th")[1:]
        tr_list = self.tree_1.xpath(".//div[@id='beianPanel']/*[@id='t30']//tr")
        if tr_list and len(tr_list) > 2:
            for tr in tr_list[1:]:
                td_list = tr.xpath("td")
                for i in range(len(td_list)):
                    #self.info(i, len(th_list), len(tr_list)
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.text.strip()
                    val = td.text
                    if val:
                        result_values[family + ":" + zhu_yao_ren_yuan_dict[desc]] = val
                    if len(result_values) == 3:
                        result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                        result_values[family + ':registrationno'] = self.cur_zch
                        result_values[family + ':enterprisename'] = self.cur_mc
                        result_values[family + ':id'] = j
                        result_list.append(result_values)
                        result_values = {}
                        j += 1
            self.json_result_data["KeyPerson_Info"] = result_list
            # self.info(json.dumps(self.json_result_data, ensure_ascii=False)

    def get_fen_zhi_ji_gou(self):
        """
        查询分支机构信息
        :return:分支机构信息结果
        """
        self.info(u'分支机构信息')
        family = 'Branches'
        table_id = '08'
        result_list = []
        result_values = {}
        j = 1
        th_list = self.tree_1.xpath(".//*[@id='t31']/tbody/tr[2]/th")
        tr_list = self.tree_1.xpath(".//*[@id='t31']/tbody/tr")
        if tr_list and len(tr_list) > 2:
            for tr in tr_list[2:]:
                td_list = tr.xpath("td")
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.text.strip()
                    val = td.text
                    if val:
                        result_values[family + ":" + fen_zhi_ji_gou_dict[desc]] = val
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result_data["Branches"] = result_list
        # self.info(json.dumps(self.json_result_data, ensure_ascii=False)

    def get_qing_suan(self):
        pass

    def get_dong_chan_di_ya(self):
        """
        查询动产抵押信息
        :return: 动产抵押信息结果
        """
        family = 'Chattel_Mortgage'
        table_id = '11'
        result_list = []
        result_values = {}
        j = 1
        th_list = self.tree_1.xpath(".//*[@id='dongchandiyaPanel']//tr[2]/th")
        tr_list = self.tree_1.xpath(".//*[@id='dongchandiyaPanel']/table//tr")
        if tr_list and len(tr_list) > 2:
            self.info(u'查询动产抵押登记信息')
            for tr in tr_list[2:]:
                td_list = tr.xpath("td")
                if len(td_list) > 1:
                    for i in range(len(th_list)):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th.text
                        if td.xpath("a") and td.xpath("a")[0].text == u'详情':
                            val = "http://www.szcredit.com.cn/web/GSZJGSPT/" + td.xpath("a")[0].get('href')
                        else:
                            val = td.text
                        if val:
                            result_values[family + ":" + dong_chan_di_ya_dict[desc]] = val
                    result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                    result_values[family + ':registrationno'] = self.cur_zch
                    result_values[family + ':enterprisename'] = self.cur_mc
                    result_values[family + ':id'] = j
                    result_list.append(result_values)
                    result_values = {}
                    j += 1
        self.json_result_data["Chattel_Mortgage"] = result_list
        # self.info(json.dumps(self.json_result_data, ensure_ascii=False)

    def get_gu_quan_chu_zhi(self):
        """
        查询股权出质信息
        :return: 股权出质信息结果
        """
        family = 'Equity_Pledge'
        table_id = '12'
        result_list = []
        result_values = {}
        j = 1
        th_list = self.tree_1.xpath(".//*[@id='GQCZPanel']/table//tr[2]/th")
        tr_list = self.tree_1.xpath(".//*[@id='GQCZPanel']/table//tr")
        if tr_list and len(tr_list) > 3:
            self.info(u'查询股权出质信息')
            for tr in tr_list[2:-1]:
                td_list = tr.xpath("td")
                if len(td_list) > 1:
                    for i in range(len(th_list)):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th.text
                        if desc == u'证照/证件号码':
                            if i == 3:
                                desc = u'证照/证件号码(出质人)'
                            elif i == 6:
                                desc = u'证照/证件号码(质权人)'
                        if td.xpath("a") and td.xpath("a")[0].text == u'详情':
                            val = "http://www.szcredit.com.cn/web/GSZJGSPT/" + td.xpath("a")[0].get('href')
                            desc = u'备注'
                            val = self.get_gu_quan_chu_zhi_detail(val)
                        else:
                            val = td.text
                        if val:
                            result_values[family + ":" + gu_quan_chu_zhi_dict[desc]] = val.strip()
                    result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                    result_values[family + ':registrationno'] = self.cur_zch
                    result_values[family + ':enterprisename'] = self.cur_mc
                    result_values[family + ':id'] = j
                    result_list.append(result_values)
                    result_values = {}
                    j += 1
            self.json_result_data["Equity_Pledge"] = result_list
            # self.info(json.dumps(self.json_result_data, ensure_ascii=False)

    def get_gu_quan_chu_zhi_detail(self, url):
        """
        :param url: link
        :return: detail
        """
        headers = {
                    'Host': "www.szcredit.com.cn",
                    "Referer": self.ent_url,
                    "User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0",
                    }
        r = self.get_request(url, headers=headers)
        r.encoding = 'gbk'
        tree = html.fromstring(r.text)
        td_list = tree.xpath(".//*[@class='detailsList']//td")
        if td_list:
            val = td_list[-1].text
            return val


    def get_xing_zheng_chu_fa(self):
        """
        查询行政处罚信息
        :return: 行政处罚信息结果
        """
        family = 'Administrative_Penalty'
        table_id = '13'
        result_list = []
        result_values = {}
        j = 1
        th_list = self.tree_2.xpath(".//*[@id='XZCFPanel']/table//tr[2]/th")
        tr_list = self.tree_2.xpath(".//*[@id='XZCFPanel']/table//tr")
        if tr_list and len(tr_list) > 3:
            self.info(u'查询行政处罚信息')
            for tr in tr_list[2:-1]:
                td_list = tr.xpath("td")
                if len(td_list) > 1:
                    for i in range(len(th_list)):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th.xpath("string(.)").replace("\n", '').strip()
                        if td.xpath("a"):
                            val = "http://www.szcredit.com.cn/web/GSZJGSPT/" + td.xpath("a")[0].get('href')
                        else:
                            val = td.text
                        if val:
                            result_values[family + ":" + xing_zheng_chu_fa_dict[desc]] = val
                    result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                    result_values[family + ':registrationno'] = self.cur_zch
                    result_values[family + ':enterprisename'] = self.cur_mc
                    result_values[family + ':id'] = j
                    result_list.append(result_values)
                    result_values = {}
                    j += 1
            self.json_result_data["Administrative_Penalty"] = result_list
            # self.info(json.dumps(self.json_result_data, ensure_ascii=False)

    def get_jing_ying_yi_chang(self):
        """
        查询经营异常信息
        :return: 经营异常信息结果
        """
        family = 'Business_Abnormal'
        table_id = '14'
        result_list = []
        result_values = {}
        j = 1
        th_list = self.tree_1.xpath(".//*[@id='JYYCPanel']/table//tr[2]/th")
        tr_list = self.tree_1.xpath(".//*[@id='JYYCPanel']/table//tr")
        if tr_list and len(tr_list) > 3:
            self.info(u'查询经营异常信息')
            for tr in tr_list[2:-1]:
                td_list = tr.xpath("td")
                if len(td_list) > 1:
                    for i in range(len(th_list)):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th.text
                        if td.xpath("a") and td.xpath("a")[0].text == u'详情':
                            val = "http://www.szcredit.com.cn/web/GSZJGSPT/" + td.xpath("a")[0].get('href')
                        else:
                            val = td.text
                        if val:
                            result_values[family + ":" + jing_ying_yi_chang_dict[desc]] = val
                    result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                    result_values[family + ':registrationno'] = self.cur_zch
                    result_values[family + ':enterprisename'] = self.cur_mc
                    result_values[family + ':id'] = j
                    result_list.append(result_values)
                    result_values = {}
                    j += 1
            self.json_result_data["Business_Abnormal"] = result_list
            # self.info(json.dumps(self.json_result_data, ensure_ascii=False)

    def get_yan_zhong_wei_fa(self):
        """
        查询严重违法信息
        :return: 信息结果
        """
        family = 'Serious_Violations'
        table_id = '15'
        result_list = []
        result_values = {}
        j = 1
        th_list = self.tree_1.xpath(".//*[@id='YZWFPanel']/table//tr[2]/th")
        tr_list = self.tree_1.xpath(".//*[@id='YZWFPanel']/table//tr")
        if tr_list and len(tr_list) > 3:
            self.info(u'查询严重违法信息')
            for tr in tr_list[2:-1]:
                td_list = tr.xpath("td")
                if len(td_list) > 1:
                    for i in range(len(th_list)):
                        th = th_list[i].xpath("string(.)")
                        td = td_list[i]
                        desc = th.text.strip()
                        if td.xpath("a"):
                            val = "http://www.szcredit.com.cn/web/GSZJGSPT/" + td.xpath("a")[0].get('href')
                        else:
                            val = td.text
                        if val:
                            result_values[family + ":" + yan_zhong_wei_fa_dict[desc]] = val
                    result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                    result_values[family + ':registrationno'] = self.cur_zch
                    result_values[family + ':enterprisename'] = self.cur_mc
                    result_values[family + ':id'] = j
                    result_list.append(result_values)
                    result_values = {}
                    j += 1
            self.json_result_data["Serious_Violations"] = result_list
            # self.info(json.dumps(self.json_result_data, ensure_ascii=False)

    def get_chou_cha_jian_cha(self):
        """
        查询抽查检查信息
        :return: 抽查检查信息结果
        """
        family = 'Spot_Check'
        table_id = '16'
        result_list = []
        result_values = {}
        j = 1
        th_list = self.tree_1.xpath(".//*[@id='tableChoucha']/tr[1]/th")
        tr_list = self.tree_1.xpath(".//*[@id='tableChoucha']/tr")
        if tr_list and len(tr_list) > 2:
            self.info(u'查询抽查检查信息')
            for tr in tr_list[1:-1]:
                td_list = tr.xpath("td")
                if len(td_list) > 1:
                    for i in range(len(th_list)):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th.text
                        if td.xpath("a"):
                            val = "http://www.szcredit.com.cn/web/GSZJGSPT/" + td.xpath("a")[0].get('href')
                        else:
                            val = td.text
                        if val:
                            result_values[family + ":" + chou_cha_jian_cha_dict[desc]] = val
                    result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                    result_values[family + ':registrationno'] = self.cur_zch
                    result_values[family + ':enterprisename'] = self.cur_mc
                    result_values[family + ':id'] = j
                    result_list.append(result_values)
                    result_values = {}
                    j += 1
            self.json_result_data["Spot_Check"] = result_list
            # self.info(json.dumps(self.json_result_data, ensure_ascii=False)

def get_args():
    args = dict()
    for arg in sys.argv:
        kv = arg.split('=')
        if kv[0] == 'companyName':
            args['companyName'] = kv[1].decode(sys.stdin.encoding, 'ignore')
        elif kv[0] == 'taskId':
            args['taskId'] = kv[1].decode(sys.stdin.encoding, 'ignore')
            args['taskId'] = kv[1].decode(sys.stdin.encoding, 'ignore')
        elif kv[0] == 'accountId':
            args['accountId'] = kv[1].decode(sys.stdin.encoding, 'ignore')
    return args


if __name__ == '__main__':
    args_dict = get_args()
    searcher = GuangdongShenzhen()
    searcher.submit_search_request(u"怡安翰威特咨询（上海）有限公司深圳分公司")
    # searcher.get_credit_ticket()
    # self.info(searcher.credit_ticket

    # self.info(json.dumps(args_dict, ensure_ascii=False)
    # searcher = LiaoNing()
    # searcher.submit_search_request(keyword=args_dict['companyName'], account_id=args_dict['accountId'], task_id=args_dict['taskId'])
    # p, t = '210200000011992092800017', '6210'
    # p, t = '21060200002200908053570X', '1151'
    # self.info(searcher.get_gu_dong_detail('210200000011992092800017', '754198044')
    # pattern = re.compile("\s")
    # self.info(pattern.sub('', '12 434 5')
