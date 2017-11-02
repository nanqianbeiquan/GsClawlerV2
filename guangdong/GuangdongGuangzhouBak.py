# coding=utf-8

import requests
import os
from bs4 import BeautifulSoup
import json
import re
import datetime
from requests.exceptions import RequestException
import sys
from lxml import html
from GuangdongConfig import *
from gs.ProxyConf import ProxyConf
from gs.ProxyConf import key1 as app_key
from gs.TimeUtils import get_cur_time
from gs.Searcher import Searcher, save_dead_company


class GuangdongGuangzhou(Searcher):

    search_result_json = None
    pattern = re.compile("\s")
    cur_mc = ''
    cur_zch = ''
    json_result_data = {}
    today = None
#     kafka = KafkaAPI("GSCrawlerTest")
    credit_ticket = None
    cur_time = None
    # plugin_path = os.path.join(sys.path[0], 'ocr/guangdong.bat')
    ent_url = ''
    params = dict()
    tag_a = ""

    def __init__(self):
        super(GuangdongGuangzhou, self).__init__(True)
        self.error_judge = False  # 判断网站是否出错
        self.today = str(datetime.date.today()).replace('-', '')
        # self.session = requests.session()
#         self.session.proxies = {'http': '123.56.238.200:8123', 'https': '123.56.238.200:8123'}
        # self.session.proxies = {'http': '121.28.134.29:80'}
        self.headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:47.0) Gecko/20100101 Firefox/47.0",
                        "Host": "gsxt.gdgs.gov.cn",
                        # "Proxy-Authorization": self.proxy_conf.get_auth_header()
                        }

    def parse_detail_guang_zhou(self, ent_url):
        # self.session.proxies.clear()
        self.get_ji_ben(ent_url)
        if self.error_judge:  # 若网站搜索结果出错，结束搜索
            self.info(u'网站出错')
            return
        self.get_gu_dong()
        # self.get_tou_zi_ren()
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
        # self.get_nian_bao_link()

        # for j in self.json_result_data:
        #     self.info(json.dumps(j, ensure_ascii=False)

    def get_ji_ben(self, ent_url):
        """
        查询基本信息
        :return: 基本信息结果
        """
        self.info(u'查询基本信息')
        self.info(ent_url)
        r = self.get_request(ent_url, headers=self.headers)
        r.encoding = 'utf-8'
        dengji_tree = html.fromstring(r.text)
        ent_no = dengji_tree.xpath(".//*[@id='entNo']")[0].get('value')
        ent_type = dengji_tree.xpath(".//*[@id='entType']")[0].get('value')
        reg_org = dengji_tree.xpath(".//*[@id='regOrg']")[0].get('value')
        self.params = {
            'entNo': ent_no,
            'entType': ent_type,
            'regOrg': reg_org
            }

        family = 'Registered_Info'
        table_id = '01'
        th_list = dengji_tree.xpath(".//*[@id='jibenxinxi']/table[1]//th")[1:]
        td_list = dengji_tree.xpath(".//*[@id='jibenxinxi']/table[1]//td")
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
        if not result_values:
            self.error_judge = True
            self.info(u'网站出错')
            return
        if result_values[family + ":" + 'tyshxy_code']:
            self.cur_zch = result_values[family + ":" + 'tyshxy_code']
        else:
            self.cur_zch = result_values[family + ":" + 'zch']
        result_values['rowkey'] = '%s_%s_%s_' % (self.cur_mc, table_id, self.cur_zch)
        result_values[family + ':registrationno'] = self.cur_zch
        result_values[family + ':enterprisename'] = self.cur_mc
        result_values[family + ':province'] = u'广东省'
        result_values[family + ':lastupdatetime'] = get_cur_time()
        self.json_result_data["Registered_Info"] = [result_values]

    def get_gu_dong(self):
        """
        查询股东信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        self.info(u'查询股东信息')
        family = 'Shareholder_Info'
        table_id = '04'
        result_list = []
        result_values = {}
        j = 1
        gudong_headers = {
            'Referer': 'http://gsxt.gzaic.gov.cn/aiccips/GSpublicity/GSpublicityList.html?service=entInfo',
            'Host': 'gsxt.gzaic.gov.cn',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0',
            'X-Requested-With': 'XMLHttpRequest',
            # "Proxy-Authorization": self.proxy_conf.get_auth_header()
        }
        params = self.params.copy()
        params['pageNo'] = '2'
        del params['entType']
        for i in range(5):
            try:
                r = self.post_request("http://gsxt.gzaic.gov.cn/aiccips/GSpublicity/invInfoPage.html", params=params, headers=gudong_headers)
                r.encoding = 'utf-8'
                inv_list = json.loads(r.text).get('list', '')
                break
            except ValueError:
                pass
        for inv_dic in inv_list:
            result_values[family + ":" + 'shareholder_type'] = inv_dic.get('invType', '')
            result_values[family + ":" + 'shareholder_name'] = inv_dic.get('inv', '')
            result_values[family + ":" + 'shareholder_certificationno'] = inv_dic.get('certNo', '')
            result_values[family + ":" + 'subscripted_amount'] = inv_dic.get('subConAm', '')
            result_values[family + ":" + 'actualpaid_amount'] = inv_dic.get('acConAm', '')
            # result_values[]
            """
            出资详情在json中解析得到
            """
            result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
            result_values[family + ':registrationno'] = self.cur_zch
            result_values[family + ':enterprisename'] = self.cur_mc
            result_values[family + ':id'] = j
            result_list.append(result_values)
            result_values = {}
            j += 1
        self.json_result_data["Shareholder_Info"] = result_list
        # self.info(json.dumps(self.json_result_data, ensure_ascii=False)

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
        bian_geng_headers = {
            'Referer': 'http://gsxt.gzaic.gov.cn/aiccips/GSpublicity/GSpublicityList.html?service=entInfo',
            'Host': 'gsxt.gzaic.gov.cn',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0',
            'X-Requested-With': 'XMLHttpRequest',
            # "Proxy-Authorization": self.proxy_conf.get_auth_header()
        }
        params = self.params.copy()
        params['pageNo'] = '2'
        # self.info(params
        for i in range(5):
            try:
                r = self.post_request('http://gsxt.gzaic.gov.cn/aiccips/GSpublicity/entChaPage', headers=bian_geng_headers, params=params)
                r.encoding = 'utf-8'
                # self.info(r.text
                biangeng_list = json.loads(r.text).get('list', '')
                break
            except ValueError:
                pass
        for biangeng_dic in biangeng_list:
            result_values[family + ":" + 'changedannouncement_events'] = biangeng_dic.get('altFiled', '')
            result_values[family + ":" + 'changedannouncement_before'] = biangeng_dic.get('altBe', '')
            result_values[family + ":" + 'changedannouncement_after'] = biangeng_dic.get('altAf', '')
            result_values[family + ":" + 'changedannouncement_date'] = biangeng_dic.get('altDate', '')
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
        self.info(u'查询主要人员信息')
        family = 'KeyPerson_Info'
        table_id = '06'
        result_list = []
        result_values = {}
        j = 1
        bian_geng_headers = {
            'Referer': 'http://gsxt.gzaic.gov.cn/aiccips/GSpublicity/GSpublicityList.html?service=entInfo',
            'Host': 'gsxt.gzaic.gov.cn',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0',
            'X-Requested-With': 'XMLHttpRequest',
            # "Proxy-Authorization": self.proxy_conf.get_auth_header()
        }
        params = self.params
        params['pageNo'] = '2'
        del params['entType']
        for i in range(5):
            try:
                r = self.post_request('http://gsxt.gzaic.gov.cn/aiccips/GSpublicity/vipInfoPage', headers=bian_geng_headers, params=params)
                r.encoding = 'utf-8'
                # self.info(r.text
                zhuyaorenyuan_list = json.loads(r.text).get('list', '')
                break
            except ValueError:
                pass
        for biangeng_dic in zhuyaorenyuan_list:
            result_values[family + ":" + 'keyperson_name'] = biangeng_dic.get('name', '')
            result_values[family + ":" + 'keyperson_position'] = biangeng_dic.get('position', '')
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
        self.info(u'查询分支机构信息')
        family = 'Branches'
        table_id = '08'
        result_list = []
        result_values = {}
        j = 1
        headers = {
            'Referer': 'http://gsxt.gzaic.gov.cn/aiccips/GSpublicity/GSpublicityList.html?service=entInfo',
            'Host': 'gsxt.gzaic.gov.cn',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0',
            # "Proxy-Authorization": self.proxy_conf.get_auth_header()
            # 'X-Requested-With': 'XMLHttpRequest'
        }
        r = self.post_request("http://gsxt.gzaic.gov.cn/aiccips/GSpublicity/GSpublicityList.html?service=entCheckInfo", headers=headers, params=self.params)
        r.encoding = 'utf-8'
        # self.info(r.text
        tree = html.fromstring(r.text)

        th_list = tree.xpath(".//*[@id='beian']/table[2]//th")[1:]
        tr_list = tree.xpath(".//*[@id='branch']//tr")
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                if len(td_list) > 1:
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
        self.info(u'查询动产抵押信息')
        family = 'Chattel_Mortgage'
        table_id = '11'
        result_list = []
        result_values = {}
        j = 1
        headers = {
            # 'Referer': 'http://gsxt.gzaic.gov.cn/aiccips/GSpublicity/GSpublicityList.html?service=entInfo',
            'Host': 'gsxt.gzaic.gov.cn',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0',
            # "Proxy-Authorization": self.proxy_conf.get_auth_header()
            # 'X-Requested-With': 'XMLHttpRequest'
        }
        for i in range(1, 100):
            params = self.params.copy()
            params["pageNo"] = i
            params["aiccipsUrl"] = "http://gsxt.gzaic.gov.cn/aiccips/"
            # url = "http://gsxt.gzaic.gov.cn/aiccips/GSpublicity/GSpublicityList.html?service=pleInfo" + "&pageNo=%s" % i + "entNo=%s" % self.params["entNo"] + \
            r = self.get_request("http://gsxt.gzaic.gov.cn/aiccips/GSpublicity/GSpublicityList.html?service=pleInfo", headers=headers, params=params)
            # self.info(r.url
            # self.info(params
            r.encoding = 'utf-8'
            # self.info(r.text
            tree = html.fromstring(r.text)
            # page_no = tree.xpath(".//*[@id='dongchandiya']/table[2]//th")[0].text.split('/')[1].strip()
            # self.info(u'动产抵押共有%s页' % page_no
            th_list = tree.xpath(".//*[@id='dongchandiya']/table[1]//th")[1:]
            tr_list = tree.xpath(".//*[@id='dongchandiya']/table[1]//tr")
            # self.info(len(tr_list)
            if tr_list and len(tr_list) > 3:
                for tr in tr_list[2:-1]:
                    td_list = tr.xpath("td")
                    if len(td_list) > 1:
                        for i in range(7):
                            th = th_list[i]
                            td = td_list[i]
                            desc = th.text.strip()
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
            else:
                break
        self.json_result_data["Chattel_Mortgage"] = result_list
        # self.info(json.dumps(self.json_result_data, ensure_ascii=False)

    def get_gu_quan_chu_zhi(self):
        """
        查询股权出质信息
        :return: 股权出质信息结果
        """
        self.info(u'查询股权出质信息')
        family = 'Equity_Pledge'
        table_id = '12'
        result_list = []
        result_values = {}
        j = 1
        headers = {
            'Referer': 'http://gsxt.gzaic.gov.cn/aiccips/GSpublicity/GSpublicityList.html?service=entInfo',
            'Host': 'gsxt.gzaic.gov.cn',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0',
            # "Proxy-Authorization": self.proxy_conf.get_auth_header()
            # 'X-Requested-With': 'XMLHttpRequest'
        }
        r = self.post_request("http://gsxt.gzaic.gov.cn/aiccips/GSpublicity/GSpublicityList.html?service=curStoPleInfo", headers=headers, params=self.params)
        r.encoding = 'utf-8'
        tree = html.fromstring(r.text)

        th_list = tree.xpath(".//*[@id='guquanchuzhi']//th")[1:]
        tr_list = tree.xpath(".//*[@id='guquanchuzhi']//tr")
        if tr_list and len(tr_list) > 2:
            for tr in tr_list[2:]:
                td_list = tr.xpath("td")
                if len(td_list) > 1:
                    for i in range(len(th_list)):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th.text.strip()
                        if desc == u'证照/证件号码':
                            if i == 3:
                                desc = u'证照/证件号码(出质人)'
                            else:
                                desc = u'证照/证件号码(质权人)'
                        val = td.text
                        if td.xpath("a"):
                            val = td.xpath("a")[0].get("href")
                        if val:
                            result_values[family + ":" + gu_quan_chu_zhi_dict[desc]] = val
                    result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                    result_values[family + ':registrationno'] = self.cur_zch
                    result_values[family + ':enterprisename'] = self.cur_mc
                    result_values[family + ':id'] = j
                    result_list.append(result_values)
                    result_values = {}
                    j += 1
        self.json_result_data["Equity_Pledge"] = result_list
        # self.info(json.dumps(self.json_result_data, ensure_ascii=False)

    def get_xing_zheng_chu_fa(self):
        """
        查询行政处罚信息
        :return: 行政处罚信息结果
        """
        self.info(u'查询行政处罚信息')
        family = 'Administrative_Penalty'
        table_id = '13'
        result_list = []
        result_values = {}
        j = 1
        headers = {
            'Referer': 'http://gsxt.gzaic.gov.cn/aiccips/GSpublicity/GSpublicityList.html?service=entInfo',
            'Host': 'gsxt.gzaic.gov.cn',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0',
            # "Proxy-Authorization": self.proxy_conf.get_auth_header()
            # 'X-Requested-With': 'XMLHttpRequest'
        }
        r = self.post_request("http://gsxt.gzaic.gov.cn/aiccips/GSpublicity/GSpublicityList.html?service=cipPenaltyInfo", headers=headers, params=self.params)
        r.encoding = 'utf-8'
        tree = html.fromstring(r.text)
        th_list = tree.xpath(".//*[@id='xingzhengchufa']//th")[1:]
        tr_list = tree.xpath(".//*[@id='xingzhengchufa']//tr")
        if tr_list and len(tr_list) > 2:
            for tr in tr_list[2:]:
                td_list = tr.xpath("td")
                if len(td_list) > 1:
                    for i in range(len(th_list)):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th.xpath("string(.)").replace("\n", '').strip()
                        val = td.text
                        if td.xpath("a"):
                            val = "http://gsxt.gzaic.gov.cn/aiccips/GSpublicity/" + td.xpath("a")[0].get("href")
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
        self.info(u'查询经营异常信息')
        family = 'Business_Abnormal'
        table_id = '14'
        result_list = []
        result_values = {}
        j = 1
        headers = {
            'Referer': 'http://gsxt.gzaic.gov.cn/aiccips/GSpublicity/GSpublicityList.html?service=entInfo',
            'Host': 'gsxt.gzaic.gov.cn',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0',
            # "Proxy-Authorization": self.proxy_conf.get_auth_header()
            # 'X-Requested-With': 'XMLHttpRequest'
        }
        r = self.post_request("http://gsxt.gzaic.gov.cn/aiccips/GSpublicity/GSpublicityList.html?service=cipUnuDirInfo", headers=headers, params=self.params)
        r.encoding = 'utf-8'
        tree = html.fromstring(r.text)
        th_list = tree.xpath(".//*[@id='yichangminglu']//th")[1:]
        tr_list = tree.xpath(".//*[@id='yichangminglu']//tr")
        if tr_list and len(tr_list) > 2:
            for tr in tr_list[2:]:
                td_list = tr.xpath("td")
                if len(td_list) > 1:
                    for i in range(len(th_list)):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th.text.strip()
                        val = td.text
                        if td.xpath("a"):
                            val = td.xpath("a")[0].get("href")
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
        self.info(u'查询严重违法信息')
        family = 'Serious_Violations'
        table_id = '15'
        result_list = []
        result_values = {}
        j = 1
        headers = {
            'Referer': 'http://gsxt.gzaic.gov.cn/aiccips/GSpublicity/GSpublicityList.html?service=entInfo',
            'Host': 'gsxt.gzaic.gov.cn',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0',
            # "Proxy-Authorization": self.proxy_conf.get_auth_header()
            # 'X-Requested-With': 'XMLHttpRequest'
        }
        r = self.post_request("http://gsxt.gzaic.gov.cn/aiccips/GSpublicity/GSpublicityList.html?service=cipUnuDirInfo", headers=headers, params=self.params)
        r.encoding = 'utf-8'
        tree = html.fromstring(r.text)
        th_list = tree.xpath(".//*[@id='heimingdan']//th")[1:]
        tr_list = tree.xpath(".//*[@id='heimingdan']//tr")
        if tr_list and len(tr_list) > 2:
            for tr in tr_list[2:]:
                td_list = tr.xpath("td")
                if len(td_list) > 1:
                    for i in range(len(th_list)):
                        th = th_list[i].xpath("string(.)")
                        td = td_list[i]
                        desc = th.text.strip()
                        val = td.text
                        if td.xpath("a"):
                            val = td.xpath("a")[0].get("href")
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
        self.info(u'查询抽查检查信息')
        family = 'Spot_Check'
        table_id = '16'
        result_list = []
        result_values = {}
        j = 1
        headers = {
            'Referer': 'http://gsxt.gzaic.gov.cn/aiccips/GSpublicity/GSpublicityList.html?service=entInfo',
            'Host': 'gsxt.gzaic.gov.cn',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0',
            "Proxy-Authorization": self.proxy_conf.get_auth_header()
            # 'X-Requested-With': 'XMLHttpRequest'
        }
        r = self.post_request("http://gsxt.gzaic.gov.cn/aiccips/GSpublicity/GSpublicityList.html?service=cipUnuDirInfo", headers=headers, params=self.params)
        r.encoding = 'utf-8'
        tree = html.fromstring(r.text)
        th_list = tree.xpath(".//*[@id='chouchajiancha']//th")[1:]
        tr_list = tree.xpath(".//*[@id='chouchajiancha']//tr")
        if tr_list and len(tr_list) > 3:
            for tr in tr_list[2:-1]:
                td_list = tr.xpath("td")
                if len(td_list) > 1:
                    for i in range(len(th_list)):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th.text.strip()
                        val = td.text
                        if td.xpath("a"):
                            val = td.xpath("a")[0].get("href")
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

    def get_result_json(self, url, params, t=0):
        """
        将get请求返回结果解析成json数组
        :param url:
        :param params:
        :param t:
        :return:
        """
        r = self.get_request(url=url, params=params)
        soup = BeautifulSoup(r.text, 'lxml')
        script_list = soup.select('html > head > script')
        if len(script_list) > 0:
            result_text = script_list[-1].text.strip()
            # self.info(result_text
            result_text = result_text[len('$(document).ready(function()'):-2]

            start_idx = result_text.index('[')
            stop_idx = result_text.index(']') + len(']')
            result_text = result_text[start_idx:stop_idx]
            # self.info(result_text
            result_json = json.loads(result_text)
        else:
            result_json = []
        return result_json

        # self.info(json.dumps(result_json, ensure_ascii=False)

    def get_nian_bao_link(self, param_pripid, param_type):
        """
        获取年报url
        :param param_pripid:
        :param param_type:
        :return:
        """
        url = 'http://gsxt.lngs.gov.cn/saicpub/entPublicitySC/entPublicityDC/getQygsQynbxxAction.action'
        params = {'pripid': param_pripid, 'type': param_type}
        return self.get_result_json(url, params)

    # def get_request(self, url, headers={}, params={}, t=0):
    #     self.headers['Proxy-Authorization'] = self.proxy_conf.get_auth_header()
    #     try:
    #         if headers:
    #             return self.session.get(url=url, headers=headers, params=params, proxies=self.proxy_conf.get_proxy(), timeout=20)
    #         else:
    #             return self.session.get(url=url, headers=self.headers, params=params, proxies=self.proxy_conf.get_proxy(), timeout=20)
    #     except RequestException, e:
    #         if t == 5:
    #             raise e
    #         else:
    #             return self.get_request(url, headers, params, t+1)
    #
    # def post_request(self, url, params, headers={}, t=0):
    #     self.headers['Proxy-Authorization'] = self.proxy_conf.get_auth_header()
    #     try:
    #         if headers:
    #             return self.session.post(url=url, headers=headers, params=params, proxies=self.proxy_conf.get_proxy(), timeout=20)
    #         else:
    #             return self.session.post(url=url, headers=self.headers, params=params, proxies=self.proxy_conf.get_proxy(), timeout=20)
    #     except RequestException, e:
    #         if t == 5:
    #             raise e
    #         else:
    #             return self.post_request(url, params, headers, t+1)

