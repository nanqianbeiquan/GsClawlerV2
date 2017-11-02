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
from gs.TimeUtils import *
from lxml import html
from gs.ProxyConf import ProxyConf, key1 as app_key
from Table_dict import *
from threading import Thread
from selenium import webdriver

reload(sys)
sys.setdefaultencoding('utf8')


class GanSuSearcher(Searcher):

    def __init__(self):
        super(GanSuSearcher, self).__init__()
        self.error_judge = False  # 判断网站是否出错，False正常，True错误
        self.session = requests.session()
        self.tag_a = ''
        self.set_config()
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.63 Safari/537.36",
                        "Host": "xygs.gsaic.gov.cn",
                        "Referer": "http://xygs.gsaic.gov.cn/gsxygs/pub!list.do",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Encoding": "gzip, deflate",
                        "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
                        "Connection": "keep-alive"
                        }
        self.result_page = ""
        self.zch = ""
        self.log_name = 'gan_su'

    def set_config(self):
        # self.plugin_path = os.path.join(sys.path[0],  r'..\gan_su\ocr\gansuocr.exe')
        self.group = 'Crawler'  # 正式
        self.kafka = KafkaAPI("GSCrawlerResult")  # 正式
        # self.group = 'CrawlerTest'  # 测试
        # self.kafka = KafkaAPI("GSCrawlerTest")  # 测试
        self.topic = 'GsSrc62'
        self.province = u'甘肃省'
        self.kafka.init_producer()

    def get_tag_a_from_page(self, keyword, flags=True):
        for t in range(10):
            # yzm = self.get_yzm()
            params = {'keyword': keyword}
            # time.sleep(3)http://xygs.gsaic.gov.cn/gsxygs/pubSearch/pubAll
            url = 'http://xygs.gsaic.gov.cn/gsxygs/pubSearch/pubAll?queryType=query'
            r = self.post_request(url=url, params=params)
            print r.text
            # self.info('!!!!!!!'
            # self.info(r.text
            # self.info('!!!!!!'
            # result_list = json.loads(r.text)
            if u'验证码输入错误' in r.text:
                self.info(u'验证错误，重试')
            else:
                self.info(u'甘肃验证成功')
                break
        if u'验证码输入错误' in r.text:
            raise ValueError(u'验证失败')
        tree = html.fromstring(r.text)

        result_name_list = tree.xpath(".//div[@class='entInfo']/div")
        for i in range(len(result_name_list)):
            name = result_name_list[i].xpath("string(.)").replace('(', u'（').replace(')', u'）').strip()
            if name != keyword:
                self.save_mc_to_db(name)
        for i in range(len(result_name_list)):
            name = result_name_list[i].xpath("string(.)").replace('(', u'（').replace(')', u'）').strip()
            # self.info(name)
            if flags:
                if name == keyword:
                    self.info(u'查询到指定公司')
                    # self.cur_mc = keyword
                    self.tag_a = result_name_list[i].get("onclick").replace("'", '"')
                    return self.tag_a
            else:
                self.info(u'查询到指定公司')
                self.tag_a = result_name_list[i].get("onclick").replace("'", '"')
                return self.tag_a

    def get_search_args(self, tag_a, keyword):
        self.cur_mc = keyword
        # self.info(tag_a
        pripid = re.findall('"(.*?)","(.*?)"', tag_a)[0][0]
        entcate = re.findall('"(.*?)","(.*?)"', tag_a)[0][1]
        params = {"entcate": entcate, "pripid": pripid, "queryType": 'query', "entname": keyword}
        for i in range(10):
            r = self.post_request("http://xygs.gsaic.gov.cn/gsxygs/pubSearch/basicView", params=params)
            r.encoding = 'utf-8'
            if u'系统出现错误!' not in r.text:
                break
        if u'该市场主体不在公示范围' in r.text:
            return 0
        self.result_page = html.fromstring(r.text)

        # self.info(r.text
        return 1

    def get_yzm(self):
        """
        获取验证码
        :rtype: str
        :return: 验证码识别结果
        """
        self.info(u'下载验证码...')
        yzm_path = self.download_yzm()
        self.info(u'识别验证码...')
        yzm = self.recognize_yzm(yzm_path)
        return yzm

    def recognize_yzm(self, yzm_path):
        """
        识别验证码
        :param yzm_path: 验证码保存路径
        :return: 验证码识别结果
        """
        return yzm_path

    def download_yzm(self):
        time_url = get_cur_ts_mil()
        image_url = 'http://xygs.gsaic.gov.cn/gsxygs/securitycode.jpg?v=%s' % time_url
        r = self.get_request(image_url)
        # self.info(requests.utils.dict_from_cookiejar(r.cookies)
        return requests.utils.dict_from_cookiejar(r.cookies)  # cookie值就是验证结果

    def parse_detail(self):
        """
        解析公司详情信息
        :param kwargs:
        :return:
        """
        self.get_ji_ben()
        if self.error_judge:
            return
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
        # self.get_nian_bao_link(kwargs)

    def get_ji_ben(self):
        """
        查询基本信息
        :return: 基本信息结果
        """
        family = 'Registered_Info'
        table_id = '01'
        result_values = dict()
        self.info(family)
        th_list = self.result_page.xpath(".//*[@id='con_three_1']//dl/dt")
        td_list = self.result_page.xpath(".//*[@id='con_three_1']//dl/dd")
        for i in range(len(td_list)):
            th = th_list[i]
            td = td_list[i]
            desc = th.xpath("string(.)").split(u'：')[0][1:].strip()
            if td.xpath("p"):
                desc = td.xpath("p")[0].xpath("string(.)").split(u'：')[0].strip(u'•')
                val = td.xpath("p")[0].xpath("string(.)").split(u'：')[1]
            else:
                val = td.text
            if val:
                val = val.strip().replace("\n", '')
            if desc:
                if u'注册号' in desc:
                    val_list = val.split('/')
                    tyshxy_code = [val_list[0].strip() if u'无' not in val_list[0] else ''][0]
                    zch = [val_list[1].strip() if u'无' not in val_list[1] else ''][0]
                    if tyshxy_code:
                        self.cur_zch = tyshxy_code
                    else:
                        self.cur_zch = zch
                    result_values[family + ':tyshxy_code'] = tyshxy_code
                    result_values[family + ':zch'] = zch
                if desc in ji_ben_dict:
                    result_values[family + ':' + ji_ben_dict[desc]] = val
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
        th_list = self.result_page.xpath(".//table[@id='invTab']//th")
        tr_list = self.result_page.xpath(".//table[@id='invTab']//tr")[1:]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.text.strip()
                    if td.xpath("a"):
                        # self.info(u'查看股东详情'
                        val = td.xpath("a")[0].get("onclick")
                        val = "http://xygs.gsaic.gov.cn/gsxygs/pubSearch/gqczrDetail?invid=" + re.findall("\('(.*?)'", val)[0]
                        # self.info(val
                        gu_dong_detail = self.get_gu_dong_detail(val)
                        for detail_key in gu_dong_detail:
                                result_values[family + ":" + gu_dong_dict[detail_key]] = gu_dong_detail[detail_key]
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
        r = self.get_request(url)
        r.encoding = 'utf-8'
        tree = html.fromstring(r.text)
        colum_name_list = tree.xpath(".//th")
        td_element_list = tree.xpath(".//td")
        col_num = min(len(td_element_list), len(colum_name_list))
        values = {}
        for i in range(col_num):
            col = colum_name_list[i].text.strip().replace('\n', '')
            if td_element_list[i].xpath("span"):
                val = td_element_list[i].xpath("span")[0].text
            else:
                val = td_element_list[i].text
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
        self.info(family)
        result_list = []
        result_values = {}
        j = 1
        th_list = self.result_page.xpath(".//*[@id='changeTab']//th")
        tr_list = self.result_page.xpath(".//*[@id='changeTab']//tr")[1:]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.text.strip()
                    val = td.text
                    if val:
                        val = val.strip().replace("\n", "").replace('\r', '')
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
        th_list = [u'姓名', u'职务']
        tr_list = self.result_page.xpath(".//*[@id='per270']")
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("p/span")
                for i in range(len(td_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th
                    val = td.text
                    if val:
                        val = val.strip().replace("\n", "").replace('\r', '')
                    if desc in zhu_yao_ren_yuan_dict and val:
                            result_values[family + ":" + zhu_yao_ren_yuan_dict[desc]] = val
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
        th_list = [u'名称', u'注册号', u'登记机关']
        tr_list = self.result_page.xpath(".//*[@id='fzjg308']")
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("p/span[last()]")
                for i in range(len(td_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th
                    val = td.text
                    if val:
                        val = val.strip().replace("\n", "").replace('\r', '')
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
        th_list = self.result_page.xpath(".//*[@id='moveTab']//th")
        tr_list = self.result_page.xpath(".//*[@id='moveTab']//tr")[1:]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.text.strip()
                    val = td.xpath("string(.)")
                    if td.xpath("a"):
                        mor_id = re.findall("\('(.*?)'", td.xpath("a")[0].get("onclick"))[0]
                        val = "http://xygs.gsaic.gov.cn/gsxygs/pubSearch/dcdyDetail?morreg_id=" + mor_id
                    if val:
                        val = val.strip().replace("\n", "").replace('\r', '')
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
        th_list = self.result_page.xpath(".//*[@id='stockTab']//th")
        tr_list = self.result_page.xpath(".//*[@id='stockTab']//tr")[1:]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.xpath("string(.)").strip().replace("\n", "")
                    if u'证照/证件号码' in desc:
                        if i == 3:
                            desc = u'证照/证件号码(出质人)'
                        if i == 6:
                            desc = u'证照/证件号码(质权人)'
                    val = td.xpath("string(.)")
                    if val:
                        val = val.replace("\n", "").replace('\r', '').strip()
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
        th_list = self.result_page.xpath(".//*[@id='xzcfTab']//th")
        tr_list = self.result_page.xpath(".//*[@id='xzcfTab']//tr")[1:]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                if len(td_list) == len(th_list):
                    for i in range(len(th_list)):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th.xpath("string(.)").strip().replace("\n", "")
                        if td.xpath("a"):
                            val = td.xpath("a")[0].get("onclick")
                            val = "http://xygs.gsaic.gov.cn/gsxygs/pubSearch/xzcfDetail?caseid=" + re.findall("\('(.*?)'", val)[0]
                        else:
                            val = td.text
                        if val:
                            val = val.strip().replace("\n", "").replace('\r', '')
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
        th_list = self.result_page.xpath(".//*[@id='excpTab']//th")
        tr_list = self.result_page.xpath(".//*[@id='excpTab']//tr")[1:]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.xpath("string(.)").strip().replace("\n", "")
                    val = td.text
                    if val:
                        val = val.strip().replace("\n", "").replace('\r', '')
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
        th_list = self.result_page.xpath(".//*[@id='checkTab']//th")
        tr_list = self.result_page.xpath(".//*[@id='checkTab']//tr")[1:]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.xpath("string(.)").strip().replace("\n", "")
                    val = td.text
                    if val:
                        val = val.strip().replace("\n", "").replace('\r', '')
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
            result_json = json.loads(result_text)
        else:
            result_json = []
        return result_json

        # self.info(json.dumps(result_json, ensure_ascii=False)

    def get_nian_bao_link(self, corp_org, corp_id, corp_seq_id):
        """
        获取年报url
        :param corp_org:
        :param corp_id:
        :param corp_seq_id
        :return:
        """
        pass

    def get_request(self, url, params={}, t=0):
        try:
            return self.session.get(url=url, headers=self.headers, params=params)
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
    searcher = GanSuSearcher()
    args_dict = get_args()
    if args_dict:
        searcher.submit_search_request(keyword=args_dict['companyName'], account_id=args_dict['accountId'], task_id=args_dict['taskId'])
    else:
        searcher.submit_search_request(u"ABB（中国）有限公司兰州分公司")
        searcher.info(json.dumps(searcher.json_result, ensure_ascii=False))

