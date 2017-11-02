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
from gs.Searcher import Searcher
from gs.Searcher import get_args
from PIL import Image
from bs4 import BeautifulSoup
import urllib2
import random
import json
from gs.TimeUtils import get_cur_time_jiangsu
from gs.TimeUtils import get_cur_time
from lxml import html
from gs.ProxyConf import ProxyConf, key1 as app_key
from Table_dict import *
from threading import Thread

reload(sys)
sys.setdefaultencoding('utf8')


class HuNanSearcher(Searcher):

    def __init__(self):
        super(HuNanSearcher, self).__init__()
        self.error_judge = False  # 判断网站是否出错，False正常，True错误
        self.session = requests.session()
        # self.proxy_config = ProxyConf(app_key)
        self.tag_a = ''
        self.result_page = ''
        self.set_config()
        self.headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:47.0) Gecko/20100101 Firefox/47.0",
                        "Host": "gsxt.hnaic.gov.cn",
                        "Accept": "*/*",
                        "Accept-Encoding": "gzip, deflate",
                        "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
                        "Connection": "keep-alive",
                        # "Content-Type": " application/x-www-form-urlencoded; charset=UTF-8"
                        }
        self.log_name = 'hu_nan'

    def set_config(self):
        self.plugin_path = os.path.join(sys.path[0],  r'..\hu_nan\ocr\hunanocr.exe')
        self.group = 'Crawler'  # 正式
        self.kafka = KafkaAPI("GSCrawlerResult")  # 正式
        # self.group = 'CrawlerTest'  # 测试
        # self.kafka = KafkaAPI("GSCrawlerTest")  # 测试
        self.topic = 'GsSrc43'
        self.province = u'湖南省'
        self.kafka.init_producer()

    def get_token(self):
        r = self.session.get("http://gsxt.hnaic.gov.cn/notice", timeout=30)
        r.encoding = 'utf-8'
        token = re.findall('"session\.token":\s"(.*?)"', r.text)[0]
        # self.info(token
        return token

    def get_tag_a_from_page(self, keyword, flags=True):
        self.result_page = ''
        token = self.get_token()
        headers = {
            "Host": "gsxt.hnaic.gov.cn",
            "Referer": "http://gsxt.hnaic.gov.cn/notice/",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0",
            # "X-Requested-With": "XMLHttpRequest",
            # 'Proxy-Authorization': self.proxy_config.get_auth_header()
        }
        for i in range(10):
            yzm = self.get_yzm()
            self.info(u'验证码:%s'% yzm)
            params = {'condition.keyword': keyword, 'condition.insType': '', 'session.token': token, "captcha": yzm, "condition.pageNo": 1}
            url = 'http://gsxt.hnaic.gov.cn/notice/search/ent_info_list'
            r = self.session.post(url=url, data=params, headers=headers, timeout=30)
            r.encoding = 'utf-8'
            # result_list = []
            # result_list = json.loads(r.text)
            if u'您搜索的条件无查询结果' in r.text:
                self.info(u'您搜索的条件无查询结果')
                return
            else:
                tree = html.fromstring(r.text)
                # self.info(r.text
                result_list = tree.xpath(".//div[@class='list-info']//a")
            if result_list:
                self.info(u'找到列表')
                for result in result_list:
                    ent_name = result.text.replace('(', u'（').replace(')', u'）')
                    if ent_name != keyword:
                        self.save_mc_to_db(ent_name)
                for result in result_list:
                    ent_name = result.text.replace('(', u'（').replace(')', u'）')
                    if flags:
                        if ent_name == keyword:
                            self.info(u'找到结果')
                            self.tag_a = result.get("href")
                            return self.tag_a
                    else:
                        self.info(u'找到结果')
                        self.tag_a = result.get("href")
                        return self.tag_a
                return self.tag_a
            else:
                self.info(u'重试验证码')
                if i ==9:
                    raise ValueError # 验证码错误

    def get_search_args(self, tag_a, keyword):
        self.info(u'解析查询参数')
        self.cur_mc = keyword
        # self.info(tag_a
        r = self.get_request(tag_a)
        r.encoding = 'utf-8'
        if u'该市场主体不在公示范围' in r.text:
            return 0
        if u'出错了' in r.text:
            raise ValueError('!!!!!!!!!!!!websie is wrong!!!!!!!!!!!')
        self.result_page = html.fromstring(r.text)
        return 1

    def download_yzm(self):
        # time_url = get_cur_time_jiangsu()
        image_url = 'http://gsxt.hnaic.gov.cn/notice/captcha?preset=&ra=%s' % random.random()
        r = self.get_request(image_url)
        yzm_path = self.get_yzm_path()
        with open(yzm_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    f.flush()
            f.close()
        return yzm_path

    def recognize_yzm(self, yzm_path):
        """
        识别验证码
        :param yzm_path: 验证码保存路径
        :return: 验证码识别结果
        """
        cmd = self.plugin_path + " " + yzm_path
        process = subprocess.Popen(cmd.encode('GBK', 'ignore'), stdout=subprocess.PIPE)
        process_out = process.stdout.read()
        answer = process_out.split('\r\n')[0].strip()
        return answer.decode('gbk', 'ignore')


    def parse_detail(self):
        """
        解析公司详情信息
        :param kwargs:
        :return:
        """
        # self.get_result_page(kwargs)
        self.get_ji_ben()
        self.get_gu_dong()
        self.get_bian_geng()
        self.get_zhu_yao_ren_yuan()
        self.get_fen_zhi_ji_gou()
        # self.get_qing_suan()
        self.get_dong_chan_di_ya()
        self.get_gu_quan_chu_zhi()
        self.get_xing_zheng_chu_fa()
        self.get_jing_ying_yi_chang()
        # self.get_yan_zhong_wei_fa()
        self.get_chou_cha_jian_cha()
        # self.get_nian_bao_link()

    def get_result_page(self, ent_url):
        r = self.get_request(ent_url)
        r.encoding = 'utf-8'
        if u'该市场主体不在公示范围' in r.text:
            self.info(u'公司已移除公示')
            return
        self.result_page = html.fromstring(r.text)

    def get_ji_ben(self):
        """
        查询基本信息
        :return: 基本信息结果
        """
        family = 'Registered_Info'
        table_id = '01'
        result_values = dict()
        # self.info(family)
        # self.info(r.text
        th_list = self.result_page.xpath(".//div[@rel='layout-01_01']//table")[0].xpath(".//th")[1:]
        # self.info(len(th_list)
        td_list = self.result_page.xpath(".//div[@rel='layout-01_01']//table")[0].xpath(".//td")
        # self.info(len(td_list)
        for i in range(len(td_list)):
            # self.info(i
            th = th_list[i]
            td = td_list[i]
            desc = th.xpath("string(.)")
            if td.xpath("span"):
                val = td.xpath("span")[0].text
            else:
                val = td.text
            if val:
                val = val.strip().replace("\n", '')
            if desc:
                if desc == u'注册号/统一社会信用代码':
                    self.cur_zch = val if val else ''
                    if len(self.cur_zch) == 18:
                        result_values[family + ':tyshxy_code'] = self.cur_zch
                    else:
                        result_values[family + ':zch'] = self.cur_zch
                # self.info('*', desc, val
                if desc in ji_ben_dict and val:
                    desc = family + ':' + ji_ben_dict[desc]
                    result_values[desc] = val
        result_values['rowkey'] = '%s_%s_%s_' % (self.cur_mc, table_id, self.cur_zch)
        result_values[family + ':registrationno'] = self.cur_zch
        result_values[family + ':enterprisename'] = self.cur_mc
        result_values[family + ':province'] = self.province
        result_values[family + ':lastupdatetime'] = get_cur_time()
        self.json_result[family] = [result_values]
        # self.info(json.dumps(self.json_result, ensure_ascii=False)

    def get_gu_dong(self):
        """
        查询股东信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Shareholder_Info'
        table_id = '04'
        self.info(family)
        result_list = []
        result_values = {}
        j = 1
        th_list = self.result_page.xpath(".//div[@rel='layout-01_01']/*[@id='investorTable']//th")[1:-1]
        tr_list = self.result_page.xpath(".//div[@rel='layout-01_01']/*[@id='investorTable']//tr")[2:-1]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.text.strip()
                    if td.xpath("a"):
                        # self.info(u'查看股东详情'
                        val = td.xpath("a")[0].get("href")
                        gu_dong_detail = self.get_gu_dong_detail(val)
                        result_values.update(gu_dong_detail)
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
        self.json_result[family] = result_list

    def get_gu_dong_detail(self, url):
        family = 'Shareholder_Info'
        result_values = dict()
        r = self.get_request(url)
        r.encoding = 'utf-8'
        # self.info(r.text
        if re.findall('invt\.subConAm\s=\s"(.*?)";', r.text):
            result_values[family + ':subscripted_amount'] = re.findall('invt\.subConAm\s=\s"(.*?)";', r.text)[0]
            result_values[family + ':subscripted_time'] = re.findall("invt\.conDate\s=\s'(.*?)';", r.text)[0]
            result_values[family + ':subscripted_method'] = re.findall('invt\.conForm\s=\s"(.*?)";', r.text)[0]
        if re.findall('invtActl\.acConAm\s=\s"(.*?)"', r.text):
            result_values[family + ':actualpaid_amount'] = re.findall('invtActl\.acConAm\s=\s"(.*?)"', r.text)[0]
            result_values[family + ':actualpaid_time'] = re.findall("invtActl\.conDate\s=\s'(.*?)'", r.text)[0]
            result_values[family + ':actualpaid_method'] = re.findall('invtActl\.conForm\s=\s"(.*?)"', r.text)[0]
        return result_values

    def get_bian_geng(self):
        """
        查询变更信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Changed_Announcement'
        table_id = '05'
        self.info(family)
        result_list = []
        result_values = {}
        j = 1
        th_list = self.result_page.xpath(".//*[@id='alterTable']//th")[1:-1]
        tr_list = self.result_page.xpath(".//*[@id='alterTable']//tr")[2:-1]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.text.strip()
                    val = td.text
                    if val:
                        val = val.strip().replace("\n", "")
                    if desc in bian_geng_dict:
                            result_values[family + ":" + bian_geng_dict[desc]] = val
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result[family] = result_list

    def get_zhu_yao_ren_yuan(self):
        """
        查询主要人员信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'KeyPerson_Info'
        table_id = '06'
        self.info(family)
        result_list = []
        result_values = {}
        j = 1
        th_list = self.result_page.xpath(".//*[@id='memberTable']//th")[1:-1]
        tr_list = self.result_page.xpath(".//*[@id='memberTable']//tr")[2:-1]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.text.strip()
                    val = td.text
                    if val:
                        val = val.strip().replace("\n", "")
                    if desc in zhu_yao_ren_yuan_dict:
                            result_values[family + ":" + zhu_yao_ren_yuan_dict[desc]] = val
                    if len(result_values) == 3:
                        result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                        result_values[family + ':registrationno'] = self.cur_zch
                        result_values[family + ':enterprisename'] = self.cur_mc
                        result_values[family + ':id'] = j
                        result_list.append(result_values)
                        result_values = {}
                        j += 1
        self.json_result[family] = result_list

    def get_fen_zhi_ji_gou(self):
        """
        查询分支机构信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Branches'
        table_id = '08'
        self.info(family)
        result_list = []
        result_values = {}
        j = 1
        th_list = self.result_page.xpath(".//*[@id='branchTable']//th")[1:-1]
        tr_list = self.result_page.xpath(".//*[@id='branchTable']//tr")[2:-1]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.text.strip()
                    val = td.text
                    if val:
                        val = val.strip().replace("\n", "")
                    if desc in fen_zhi_ji_gou_dict:
                            result_values[family + ":" + fen_zhi_ji_gou_dict[desc]] = val
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result[family] = result_list

    def get_qing_suan(self):
        pass

    def get_dong_chan_di_ya(self):
        """
        查询动产抵押信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Chattel_Mortgage'
        table_id = '11'
        self.info(family)
        result_list = []
        result_values = {}
        j = 1
        th_list = self.result_page.xpath(".//*[@id='mortageTable']//th")[1:-1]
        tr_list = self.result_page.xpath(".//*[@id='mortageTable']//tr")[2:-1]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.text.strip()
                    val = td.text
                    if val:
                        val = val.strip().replace("\n", "")
                    if td.xpath("a"):
                        val = td.xpath("a")[0].get("href")
                    if desc in dong_chan_di_ya_dict:
                            result_values[family + ":" + dong_chan_di_ya_dict[desc]] = val
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result[family] = result_list
        # self.info(json.dumps(result_json_2, ensure_ascii=False)

    def get_gu_quan_chu_zhi(self):  # finished
        """
        查询股权出置信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Equity_Pledge'
        table_id = '12'
        self.info(family)
        result_list = []
        result_values = {}
        j = 1
        th_list = self.result_page.xpath(".//*[@id='pledgeTable']//th")[1:-1]
        tr_list = self.result_page.xpath(".//*[@id='pledgeTable']//tr")[2:-1]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.xpath("string(.)").strip().replace("\n", "")
                    val = td.text
                    if val:
                        val = val.strip().replace("\n", "")
                    if td.xpath("a"):
                        val = td.xpath("a")[0].get("href")
                    if desc in gu_quan_chu_zhi_dict:
                            result_values[family + ":" + gu_quan_chu_zhi_dict[desc]] = val
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result[family] = result_list

    def get_xing_zheng_chu_fa(self):
        """
        查询行政处罚信息
        return:
        """
        family = 'Administrative_Penalty'
        table_id = '13'
        self.info(family)
        result_list = []
        result_values = {}
        j = 1
        th_list = self.result_page.xpath(".//*[@id='punishTable']//th")[1:-1]
        tr_list = self.result_page.xpath(".//*[@id='punishTable']//tr")[2:-1]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                if len(td_list) == len(th_list):
                    for i in range(len(th_list)):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th.xpath("string(.)").strip().replace("\n", "")
                        val = td.text
                        if val:
                            val = val.strip().replace("\n", "")
                        if td.xpath("a"):
                            val = td.xpath("a")[0].get("href")
                        if desc in xing_zheng_chu_fa_dict:
                                result_values[family + ":" + xing_zheng_chu_fa_dict[desc]] = val
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result[family] = result_list
        # self.info(json.dumps(result_json_2, ensure_ascii=False)

    def get_jing_ying_yi_chang(self):
        """
        查询经营异常信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Business_Abnormal'
        table_id = '14'
        self.info(family)
        result_list = []
        result_values = {}
        j = 1
        th_list = self.result_page.xpath(".//*[@id='exceptTable']//th")[1:-1]
        tr_list = self.result_page.xpath(".//*[@id='exceptTable']//tr")[2:-1]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.xpath("string(.)").strip().replace("\n", "")
                    val = td.text
                    if val:
                        val = val.strip().replace("\n", "")
                    if td.xpath("a"):
                        val = td.xpath("a")[0].get("href")
                    if desc in jing_ying_yi_chang_dict:
                            result_values[family + ":" + jing_ying_yi_chang_dict[desc]] = val
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result[family] = result_list
        # self.info(json.dumps(result_json_2, ensure_ascii=False)

    def get_yan_zhong_wei_fa(self):
        """
        查询严重违法信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        pass

    def get_chou_cha_jian_cha(self):
        """
        查询抽查检查信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Spot_Check'
        table_id = '16'
        self.info(family)
        result_list = []
        result_values = {}
        j = 1
        th_list = self.result_page.xpath(".//*[@id='spotcheckTable']//th")[1:-1]
        tr_list = self.result_page.xpath(".//*[@id='spotcheckTable']//tr")[2:-1]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.xpath("string(.)").strip().replace("\n", "")
                    val = td.text
                    if val:
                        val = val.strip().replace("\n", "")
                    if td.xpath("a"):
                        val = td.xpath("a")[0].get("href")
                    if desc in chou_cha_jian_cha_dict:
                            result_values[family + ":" + chou_cha_jian_cha_dict[desc]] = val
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result[family] = result_list
        # self.info(self.json_result
        # self.info(json.dumps(self.json_result, ensure_ascii=False)
        # self.info(json.dumps(result_json_2, ensure_ascii=False)

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

    # def get_nian_bao_link(self):
    #     """
    #     获取年报url
    #     :param param_pripid:
    #     :param param_type:
    #     :return:
    #     """
    #     pass

    def get_request(self, url, params={}, t=0):
        try:
            return self.session.get(url=url, headers=self.headers, params=params, timeout=30)
        except RequestException, e:
            if t == 5:
                raise e
            else:
                return self.get_request(url, params, t+1)

    def post_request(self, url, params, t=0):
        try:
            return self.session.post(url=url, headers=self.headers, data=params)
        except RequestException, e:
            if t == 5:
                raise e
            else:
                return self.post_request(url, params, t+1)


if __name__ == '__main__':
    searcher = HuNanSearcher()
    args_dict = get_args()
    if args_dict:
        searcher.submit_search_request(keyword=args_dict['companyName'], account_id=args_dict['accountId'], task_id=args_dict['taskId'])
    else:
        searcher.submit_search_request(u"望城县旺利塑料包装厂")
        searcher.info(json.dumps(searcher.json_result, ensure_ascii=False))
