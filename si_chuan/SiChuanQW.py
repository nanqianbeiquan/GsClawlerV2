# coding=utf-8

import PackageTool
import sys
import requests
from requests.exceptions import RequestException
from gs.KafkaAPI import KafkaAPI
import os
import re
import time
import traceback
import subprocess
from gs.Searcher import *
from gs.Searcher import get_args
from PIL import Image
from bs4 import BeautifulSoup
import urllib2
import random
import json
from gs.TimeUtils import *
from lxml import html
from gs.ProxyConf import ProxyConf, key1 as app_key
from Table_dict import *
import urllib
from requests.exceptions import ReadTimeout
from gs.QuanWangProxy import get_proxy

reload(sys)
sys.setdefaultencoding('utf8')


class SiChuanQW(Searcher):

    # proxy_conf = ProxyConf(app_key)
    timeout = 30

    def __init__(self):
        super(SiChuanQW, self).__init__()
        self.error_judge = False  # 判断网站是否出错，False正常，True错误
        # self.session = requests.session()
        # self.proxy_config = ProxyConf(app_key)
        self.tag_a = ''
        self.corp_id = ''
        self.corp_org = ''
        self.corp_seq_id = ''
        self.set_config()
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0",
                        "Host": "gsxt.scaic.gov.cn",
                        "Connection": "keep-alive",
                        "Referer": "http://gsxt.scaic.gov.cn/ztxy.do?method=list&djjg=&random=%s" % get_cur_ts_mil(),
                        "Accept": 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        "Accept-Encoding": "gzip, deflate",
                        }
        self.dengji_tree = ""
        self.beian_tree = ""

    def set_config(self):
        # self.add_proxy(app_key)
        self.plugin_path = os.path.join(sys.path[0],  r'..\si_chuan\ocr\sichuanocr.exe')
        self.group = 'Crawler'  # 正式
        self.kafka = KafkaAPI("GSCrawlerResult")  # 正式
        # self.group = 'CrawlerTest'  # 测试
        # self.kafka = KafkaAPI("GSCrawlerTest")  # 测试
        self.topic = 'GsSrc51'
        self.province = u'四川省'
        self.kafka.init_producer()

    def submit_search_request(self, keyword, account_id='null', task_id='null'):
        """
        提交查询请求
        :param keyword: 查询关键词(公司名称或者注册号/信用代码)
        :param account_id: 在线更新,kafka所需参数
        :param task_id: 在线更新kafka所需参数
        :return:
        """
        self.session.proxies = {'http': get_proxy()}
        self.cur_mc = ''  # 当前查询公司名称
        self.cur_zch = ''  # 当前查询公司注册号
        self.today = str(datetime.date.today()).replace('-', '')
        self.json_result.clear()
        self.json_result['inputCompanyName'] = keyword
        self.json_result['accountId'] = account_id
        self.json_result['taskId'] = task_id
        self.save_tag_a = True
        keyword = keyword.replace('(', u'`（').replace(')', u'）')  # 公司名称括号统一转成全角
        self.info(u'keyword: %s' % keyword)
        tag_a = self.get_tag_a_from_db(keyword)
        if not tag_a:
            tag_a = self.get_tag_a_from_page(keyword)
        if tag_a:
            args = self.get_search_args(tag_a, keyword)
            if len(args) > 0:
                if self.save_tag_a:  # 查询结果与所输入公司名称一致时,将其写入数据库
                    self.save_tag_a_to_db(tag_a)
                self.info(u'解析详情信息')
                self.parse_detail(args)
            else:
                self.info(u'查询结果不一致')
                save_dead_company(keyword)
        else:
            self.info(u'查询无结果')
            save_dead_company(keyword)
        self.info(u'消息写入kafka')
        self.kafka.send(json.dumps(self.json_result, ensure_ascii=False))
        # self.info(json.dumps(self.json_result, ensure_ascii=False)

    def get_tag_a_from_page(self, keyword):
        for t in range(10):
            yzm = self.get_yzm()
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0",
                       "Host": "gsxt.scaic.gov.cn",
                       "Connection": "keep-alive",
                       "Referer": "http://gsxt.scaic.gov.cn/ztxy.do?method=list&djjg=&random=%s" % get_cur_ts_mil(),
                       "Accept": 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                       "Accept-Encoding": "gzip, deflate",
                       }
            params = {'maent.entname': keyword.encode('gbk'), 'yzm': yzm, 'currentPageNo': 1, 'cxym': 'cxlist'}
            url = 'http://gsxt.scaic.gov.cn/ztxy.do?method=list&djjg=&random=%s' % get_cur_ts_mil()
            r = self.post_request(url, data=params)
            r.encoding = 'gbk'
            tree = html.fromstring(r.text)
            if "var flag = 'fail';" in r.text:
                self.info(u'验证码错误，重试')
            elif "var flag = 'outtime';" in r.text:
                self.info(u'验证码过期,重试')
            else:
                self.info(u'验证成功')
                break
        # self.info(r.text
        if tree.xpath(".//form/div[5]/div[2]/ul/li[2]"):
            self.info(u'找到结果')
        else:
            self.info(u'未查询到结果')
            return
            # result_list = json.loads(r.text)
        tree = html.fromstring(r.text)
        # self.info(r.text
        result_name_list = tree.xpath(".//form/div[5]/div/ul/li[1]/a")
        for i in range(len(result_name_list)):
            result = result_name_list[i].xpath("string(.)").replace('(', u'（').replace(')', u'）').strip()
            # name = re.match(u'^(.*)（.*）$', result).groups()[0]
            # self.info(name
            if result == keyword:
                self.info(u'查询到指定公司')
                # self.cur_mc = keyword
                self.tag_a = result_name_list[i].get("onclick").replace("'", '"')
                return self.tag_a

    def recognize_yzm(self, yzm_path):
        """
        识别验证码
        :param yzm_path: 验证码保存路径
        :return: 验证码识别结果
        """
        cmd = self.plugin_path + " " + yzm_path
        self.info(cmd)
        process = subprocess.Popen(cmd.encode('GBK', 'ignore'), stdout=subprocess.PIPE)
        process_out = process.stdout.read()
        self.info('answer: ', process_out.decode('gbk', 'ignore'))
        return process_out.replace('\r\n', '').strip()

    def get_search_args(self, tag_a, keyword):
        self.info(u'解析查询参数')
        self.cur_mc = keyword
        tag_a = tag_a.replace('"', "'")
        return re.findall('openView\(\'(.*?)\',', tag_a)[0]

    def download_yzm(self):
        time_url = get_cur_ts_mil()
        image_url = 'http://gsxt.scaic.gov.cn/ztxy.do?method=createYzm3&dt=%s&random=%s' % (time_url, time_url)
        # self.info(image_url
        r = self.get_request(image_url)
        r.encoding = 'gbk'
        yzm_path = self.get_yzm_path()
        with open(yzm_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    f.flush()
            f.close()
        return yzm_path

    def parse_detail(self, kwargs):
        """
        解析公司详情信息
        :param kwargs:
        :return:
        """
        self.get_ji_ben(kwargs)
        if self.error_judge:
            raise ValueError("!!!!!bug in website!!!!!")
        self.get_gu_dong()
        self.get_bian_geng()
        self.get_zhu_yao_ren_yuan(kwargs)
        self.get_fen_zhi_ji_gou()
        self.get_qing_suan(kwargs)
        self.get_dong_chan_di_ya(kwargs)
        self.get_gu_quan_chu_zhi(kwargs)
        self.get_xing_zheng_chu_fa(kwargs)
        self.get_jing_ying_yi_chang(kwargs)
        self.get_yan_zhong_wei_fa(kwargs)
        self.get_chou_cha_jian_cha(kwargs)
        # self.get_nian_bao_link(kwargs)

    def get_ji_ben(self, ent_id):
        """
        查询基本信息
        :return: 基本信息结果
        """
        family = 'Registered_Info'
        table_id = '01'
        self.info(u'基本信息')
        result_values = dict()
        url = 'http://gsxt.scaic.gov.cn/ztxy.do'
        params = {"czmk": "czmk1", "from": '', "maent.pripid": ent_id, "method": "qyInfo", "random": get_cur_ts_mil()}
        r = self.post_request(url, data=params)
        r.encoding = 'gbk'
        self.dengji_tree = html.fromstring(r.text)
        th_list = self.dengji_tree.xpath(".//table[1]//th")[1:]
        td_list = self.dengji_tree.xpath(".//table[1]//td")
        for i in range(len(td_list)):
            th = th_list[i]
            td = td_list[i]
            desc = th.xpath("string(.)")
            val = td.xpath("string(.)")
            if val:
                val = val.strip().replace('\n', '')
            if desc:
                if desc == u'注册号/统一社会信用代码':
                    self.cur_zch = val
                    if len(val) == 18:
                        result_values[family + ':tyshxy_code'] = val
                    else:
                        result_values[family + ':zch'] = val
                if desc in ji_ben_dict :
                        result_values[family + ':' + ji_ben_dict[desc]] = val
        result_values['rowkey'] = '%s_%s_%s_' % (self.cur_mc, table_id, self.cur_zch)
        result_values[family + ':registrationno'] = self.cur_zch
        result_values[family + ':enterprisename'] = self.cur_mc
        result_values[family + ':province'] = self.province
        result_values[family + ':lastupdatetime'] = get_cur_time()
        self.json_result[family] = [result_values]

    def get_gu_dong(self):
        """
        查询股东信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Shareholder_Info'
        table_id = '04'
        self.info(u'股东信息')
        result_list = []
        result_values = {}
        j = 1
        if not self.dengji_tree.xpath(".//*[@id='table_fr']"):  # 没有股东表格
            return
        th_list = self.dengji_tree.xpath(".//*[@id='table_fr']//tr[2]/th")
        tr_list = self.dengji_tree.xpath(".//*[@name='fr']")
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                if len(td_list) == 1:
                    continue
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.xpath("string(.)")
                    if td.xpath("a"):
                        # self.info(u'查看股东详情'
                        val_detail = td.xpath("a")[0].get("onclick")
                        gudong_id = re.findall("\('(.*?)',", val_detail)[0]
                        ent_id = re.findall(",'(.*?)'\)", val_detail)[0]
                        gudong_detail = self.get_gudong_detail(gudong_id, ent_id)
                        for detail_key in gudong_detail:
                            result_values[family + ":" + gu_dong_dict[detail_key]] = gudong_detail[detail_key]
                    else:
                        val = td.text
                    if val:
                        val = val.strip().replace("\n", "")
                    if desc in gu_dong_dict:
                        result_values[family + ":" + gu_dong_dict[desc]] = val
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result["Shareholder_Info"] = result_list

    def get_gudong_detail(self, gudong_id, ent_id):
        params = {"maent.pripid": ent_id, "maent.xh": gudong_id, "method": "tzrCzxxDetial", "random": get_cur_ts_mil()}
        url = "http://gsxt.scaic.gov.cn/ztxy.do"
        r = self.post_request(url, data=params)
        r.encoding = 'gbk'
        tree = html.fromstring(r.text)
        colum_name_list = tree.xpath('.//table//th')[1:]
        td_element_list = tree.xpath(".//table//td")
        del colum_name_list[3:5]
        col_num = len(colum_name_list)
        values = {}
        for i in range(col_num):
            col = colum_name_list[i].xpath("string(.)").strip().replace('\n', '')
            val = td_element_list[i].xpath("string(.)")
            if td_element_list[i].xpath(".//li"):
                val = td_element_list[i].xpath(".//li")[-1].xpath("string(.)")
            if val:
                values[col] = val.strip().replace('\n', '')
        # self.info(json.dumps(values,ensure_ascii=False)
        return values

    def get_bian_geng(self):
        """
        查询变更信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Changed_Announcement'
        table_id = '05'
        self.info(u'变更信息')
        result_list = []
        result_values = {}
        j = 1
        th_list = self.dengji_tree.xpath(".//*[@id='table_bg']//tr[2]//th")
        tr_list = self.dengji_tree.xpath(".//*[@name='bg']")
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                if len(td_list) == 1:
                    continue
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.xpath("string(.)").strip()
                    if td.xpath("span"):
                        val = td.xpath("span")[-1].text.strip()
                    else:
                        val = td.xpath("string(.)")
                    if val:
                        val = val.strip().replace("\n", "")
                    result_values[family + ":" + bian_geng_dict[desc]] = val
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result["Changed_Announcement"] = result_list

    def get_zhu_yao_ren_yuan(self, ent_id):
        """
        查询主要人员信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'KeyPerson_Info'
        table_id = '06'
        self.info(u'主要人员信息')
        result_list = []
        result_values = dict()
        j = 1
        params = {"czmk": "czmk2", "maent.pripid": ent_id, "method": "baInfo", "random": get_cur_ts_mil()}
        url = 'http://gsxt.scaic.gov.cn/ztxy.do'
        r = self.post_request(url, data=params)
        r.encoding = 'gbk'
        self.beian_tree = html.fromstring(r.text)

        th_list = [u'序号', u'姓名', u'职务', u'序号', u'姓名', u'职务']
        tr_list = self.beian_tree.xpath(".//*[@name='ry1']")
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                for i in range(len(td_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th
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
        self.json_result["KeyPerson_Info"] = result_list

    def get_fen_zhi_ji_gou(self):
        """
        查询分支机构信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Branches'
        table_id = '08'
        self.info(u'分支机构')
        result_list = []
        result_values = {}
        j = 1
        if not len(self.beian_tree):
            return
        th_list = self.beian_tree.xpath(".//*[@id='table_fr2']//tr[2]/th")
        tr_list = self.beian_tree.xpath(".//*[@name='fr2']")
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.text.strip()
                    val = td.text
                    if val:
                        val = val.strip()
                    result_values[family + ":" + fen_zhi_ji_gou_dict[desc]] = val
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result["Branches"] = result_list

    def get_qing_suan(self, ent_id):
        pass

    def get_dong_chan_di_ya(self, ent_id):
        """
        查询动产抵押信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Chattel_Mortgage'
        table_id = '11'
        self.info(u'动产抵押信息')
        result_list = []
        j = 1
        result_values = dict()
        params = {"czmk": "czmk4", "maent.pripid": ent_id, "method": "dcdyInfo", "random": get_cur_ts_mil()}
        url = 'http://gsxt.scaic.gov.cn/ztxy.do'
        r = self.post_request(url, data=params)
        r.encoding = 'gbk'
        tree = html.fromstring(r.text)
        th_list = tree.xpath(".//*[@id='table_dc']//tr[2]/th")
        tr_list = tree.xpath(".//tr[@name='dc']")
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.xpath("string(.)").strip()
                    val = td.xpath("string(.)")
                    if val:
                        val = val.strip().replace("\n", '')
                    if desc in dong_chan_di_ya_dict:
                        result_values[family + ":" + dong_chan_di_ya_dict[desc]] = val
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result["Chattel_Mortgage"] = result_list
        # self.info(json.dumps(result_json_2, ensure_ascii=False)

    def get_gu_quan_chu_zhi(self, ent_id):  # finished
        """
        查询股权出置信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Equity_Pledge'
        table_id = '12'
        self.info(u'股权出质')
        result_list = []
        j = 1
        result_values = dict()
        params = {"czmk": "czmk4", "maent.pripid": ent_id, "method": "gqczxxInfo", "random": get_cur_ts_mil()}
        url = 'http://gsxt.scaic.gov.cn/ztxy.do'
        r = self.post_request(url, data=params)
        r.encoding = 'gbk'
        tree = html.fromstring(r.text)
        th_list = tree.xpath(".//*[@id='table_gq']//tr[2]/th")
        tr_list = tree.xpath(".//tr[@name='gq']")
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.xpath("string(.)").strip()
                    if desc == u'证照/证件号码' and i == 3:
                        desc = u'证照/证件号码(出质人)'
                    if desc == u'证照/证件号码' and i == 6:
                        desc = u'证照/证件号码(质权人)'
                    val = td.xpath("string(.)").strip()
                    if val:
                        val = val.strip().replace("\n", '')
                    result_values[family + ":" + gu_quan_chu_zhi_dict[desc]] = val
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result["Equity_Pledge"] = result_list

    def get_xing_zheng_chu_fa(self, ent_id):
        """
        查询行政处罚信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Administrative_Penalty'
        table_id = '13'
        self.info(u'行政处罚')
        result_list = []
        j = 1
        result_values = dict()
        params = {"czmk": "czmk3", "maent.pripid": ent_id, "method": "cfInfo", "random": get_cur_ts_mil()}
        url = 'http://gsxt.scaic.gov.cn/ztxy.do'
        r = self.post_request(url, data=params)
        r.encoding = 'gbk'
        tree = html.fromstring(r.text)
        # self.info(r.text
        th_list = tree.xpath(".//*[@id='table_gscfxx']//th")[1:9]
        tr_list = tree.xpath(".//tr[@name='gscfxx']")
        # self.info(len(tr_list)
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                if len(td_list) == 1:
                    continue
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.xpath("string(.)").strip()
                    if td.xpath("span"):
                        val = td.xpath("span")[-1].text.strip()
                    else:
                        val = td.xpath("string(.)")
                    if val:
                        val = val.strip().replace("\n", "")
                    result_values[family + ":" + xing_zheng_chu_fa_dict[desc]] = val
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result["Administrative_Penalty"] = result_list
        # self.info(json.dumps(result_json_2, ensure_ascii=False)

    def get_jing_ying_yi_chang(self, ent_id):
        """
        查询经营异常信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Business_Abnormal'
        table_id = '14'
        self.info(u'经营异常')
        result_list = []
        j = 1
        result_values = dict()
        params = {"czmk": "czmk6", "maent.pripid": ent_id, "method": "jyycInfo", "random": get_cur_ts_mil()}
        url = 'http://gsxt.scaic.gov.cn/ztxy.do'
        r = self.post_request(url, data=params)
        r.encoding = 'gbk'
        tree = html.fromstring(r.text)
        th_list = tree.xpath(".//*[@id='table_yc']//tr[2]//th")
        tr_list = tree.xpath(".//*[@name='yc']")
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                if len(td_list) == 1:
                    continue
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.xpath("string(.)").strip()
                    val = td.xpath("string(.)")
                    if td.xpath("span"):
                        val = td.xpath("span")[-1].text.strip()
                    if val:
                        val = val.strip().replace("\n", '')
                    result_values[family + ":" + jing_ying_yi_chang_dict[desc]] = val
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result["Business_Abnormal"] = result_list
        # self.info(json.dumps(result_json_2, ensure_ascii=False)

    def get_yan_zhong_wei_fa(self, ent_id):
        """
        查询严重违法信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Serious_Violations'
        table_id = '15'
        self.info(u'严重违法')
        result_list = []
        j = 1
        result_values = dict()
        params = {"czmk": "czmk14", "maent.pripid": ent_id, "method": "yzwfInfo", "random": get_cur_ts_mil()}
        url = 'http://gsxt.scaic.gov.cn/ztxy.do'
        r = self.post_request(url, data=params)
        r.encoding = 'gbk'
        tree = html.fromstring(r.text)
        th_list = tree.xpath(".//*[@id='table_wfxx']//tr[2]/th")
        tr_list = tree.xpath(".//*[@name='wfxx']")
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                if len(td_list) == 1:
                    continue
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.xpath("string(.)").strip()
                    val = td.xpath("string(.)")
                    if val:
                        val = val.strip().replace("\n", "")
                    result_values[family + ":" + yan_zhong_wei_fa_dict[desc]] = val
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result["Serious_Violations"] = result_list

    def get_chou_cha_jian_cha(self, ent_id):
        """
        查询抽查检查信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Spot_Check'
        table_id = '16'
        self.info(u'抽查检查')
        result_list = []
        j = 1
        result_values = dict()
        params = {"czmk": "czmk7", "maent.pripid": ent_id, "method": "ccjcInfo", "random": get_cur_ts_mil()}
        url = 'http://gsxt.scaic.gov.cn/ztxy.do'
        r = self.post_request(url, data=params, release_lock_id=True)
        r.encoding = 'gbk'
        tree = html.fromstring(r.text)
        th_list = tree.xpath(".//*[@id='table_ccjc']//tr[2]/th")
        tr_list = tree.xpath(".//*[@name='ccjc']")
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                if len(td_list) == 1:
                    return
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.xpath("string(.)").strip()
                    val = td.xpath("string(.)")
                    if val:
                        val = val.strip()
                    result_values[family + ":" + chou_cha_jian_cha_dict[desc]] = val
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result["Spot_Check"] = result_list

    def get_nian_bao_link(self, corp_org, corp_id, corp_seq_id):
        """
        获取年报url
        :param param_pripid:
        :param param_type:
        :return:
        """
        pass


if __name__ == '__main__':
    args_dict = {'companyName': u'泸州市鑫和净水材料有限公司', 'accountId': '123', 'taskId': '456'}
    searcher = SiChuanQW()
    searcher.submit_search_request(keyword=args_dict['companyName'], account_id=args_dict['accountId'], task_id=args_dict['taskId'])
    # self.info(json.dumps(searcher.json_result, ensure_ascii=False)

