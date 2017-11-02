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
from gs.ProxyConf import ProxyConf, key1 as app_key
from TableConfig import *
from gs.KafkaAPI import KafkaAPI
from gs.TimeUtils import get_cur_time
import json
from requests.exceptions import RequestException
from gs.TimeUtils import *
from lxml import html
import uuid

class SShanXiSearcher(Searcher):

    load_func_dict = dict()
    lock_id = 0

    def __init__(self):
        super(SShanXiSearcher, self).__init__(use_proxy=False)
        self.load_func_dict[u'营业执照信息'] = self.get_ji_ben
        self.load_func_dict[u'股东及出资信息'] = self.get_gu_dong
        self.load_func_dict[u'变更信息'] = self.get_bian_geng
        self.load_func_dict[u'主要人员信息'] = self.get_zhu_yao_ren_yuan
        self.load_func_dict[u'分支机构信息'] = self.get_fen_zhi_ji_gou
        self.load_func_dict[u'清算信息'] = self.get_qing_suan
        self.load_func_dict[u'动产抵押登记信息'] = self.get_dong_chan_di_ya
        self.load_func_dict[u'股权出质登记信息'] = self.get_gu_quan_chu_zhi
        self.load_func_dict[u'抽查检查结果信息'] = self.get_chou_cha_jian_cha

        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:45.0) Gecko/20100101 Firefox/45.0",
                        "Host": "xygs.snaic.gov.cn",
                        "Accept": "*/*",
                        "Accept-Encoding": "gzip, deflate",
                        "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
                        "Referer": "http://xygs.snaic.gov.cn/ztxy.do",
                        "Connection": "keep-alive"
                        }
        self.set_config()
        self.log_name = self.topic + "_" + str(uuid.uuid1())
        self.use_proxy = True
        self.add_proxy(app_key)
        self.priId = ''
        self.tag_a = ''
        self.jcxx = ''
        self.xzcf = ''
        self.jyyc = ''
        # self.get_request

    def set_config(self):
        # self.plugin_path = os.path.join(sys.path[0], '../sshan_xi/ocr/shanxi/shanxi.bat')
        self.group = 'Crawler'  # 正式
        self.kafka = KafkaAPI("GSCrawlerResult")  # 正式
        # self.group = 'CrawlerTest'  # 测试
        # self.kafka = KafkaAPI("GSCrawlerTest")  # 测试
        self.topic = 'GsSrc61'
        self.province = u'陕西省'
        self.kafka.init_producer()
        self.set_request_timeout(20)

    # def download_yzm(self):
    #     time_url = get_cur_ts_mil()
    #     image_url = 'http://xygs.snaic.gov.cn/ztxy.do?method=createYzm&dt=1474516070060&random=1474516070060'
    #     # image_url = 'http://xygs.snaic.gov.cn/ztxy.do?method=createYzm3&dt=%s&random=%s' % (time_url, time_url)
    #     params = {'method': 'createYzm', 'dt': get_cur_ts_mil(),'random' :get_cur_ts_mil()}
    #     r = self.get_request(image_url,params=params)
    #     yzm_path = self.get_yzm_path()
    #     with open(yzm_path, 'wb') as f:
    #         for chunk in r.iter_content(chunk_size=1024):
    #             if chunk:  # filter out keep-alive new chunks
    #                 f.write(chunk)
    #                 f.flush()
    #         f.close()
    #     return yzm_path

    def get_tag_a_from_page(self, keyword, flags=True):
        self.info(u'数据库没有tag_a')
            # yzm = self.get_yzm()
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0",
                   "Host": "xygs.snaic.gov.cn",
                   "Connection": "keep-alive",
                    }
        params = {
                  'maent.entname': keyword.encode('gbk'),
                  }
        url = 'http://xygs.snaic.gov.cn/ztxy.do?method=sslist&djjg=&random=%s' % long(time.time()*1000)
        r =self.post_request(url=url, data=params, headers=headers)
        tree = html.fromstring(r.text)
        result_list = tree.xpath(".//*[@class='result_item']")
        for result in result_list:
            name = result.xpath(".//*[@id='mySpan']")[0].xpath('string(.)').replace('(', u'（').replace(')', u'）').strip()
            if name != keyword:
                self.save_mc_to_db(name)
        for result in result_list:
            name = result.xpath(".//*[@id='mySpan']")[0].xpath('string(.)').replace('(', u'（').replace(')', u'）').strip()
            if flags:
                if name == keyword:
                    self.info(u'找到结果')
                    self.tag_a = result.get('onclick').replace("'",'"')
                    return self.tag_a
            else:
                self.info(u'找到结果')
                self.tag_a = result.get('onclick').replace("'",'"')
                return self.tag_a

    def get_search_args(self, tag_a, keyword):
        self.cur_mc = keyword
        self.priId = re.findall('\("(.*?)",', tag_a)[0]
        url = 'http://xygs.snaic.gov.cn/ztxy.do?method=qyinfo_jcxx&pripid=%s&random=201608111029' % self.priId
        r = self.get_request(url)
        if u'错误日志' in r.text:
            raise Exception('Website is wrong')
        self.jcxx = html.fromstring(r.text)  # 基础信息
        url = "http://xygs.snaic.gov.cn/ztxy.do?method=qyinfo_xzcfxx&pripid=%s&random=%s" % (self.priId, long(time.time()*1000))
        r = self.get_request(url)
        self.xzcf = html.fromstring(r.text)  # 行政处罚信息
        url = "http://xygs.snaic.gov.cn/ztxy.do?method=qyinfo_jyycxx&pripid=%s&random=%s" % (self.priId, long(time.time()*1000))
        r = self.get_request(url)
        self.jyyc = html.fromstring(r.text)  # 经营异常信息
        return 1

    def parse_detail(self):
        tables = self.jcxx.xpath(".//p[@class='part_title']")
        finish_list = list()
        for table in tables:
            table_name = table.xpath("string(.)").split()[0]  # 表格名称
            if table_name in self.load_func_dict and table_name not in finish_list:
                self.load_func_dict[table_name](table.xpath("following-sibling::*")[0])
                # self.load_func_dict[table_name](table.xpath("following-sibling::ul[1]")[0].get('outerHTML'))  # 主要人员信息
                finish_list.append(table_name)
        if len(finish_list) == 0:  # 基本信息查询失败
            raise Exception
        self.get_xing_zheng_chu_fa()
        self.get_jing_ying_yi_chang()


    def get_ji_ben(self, table_tree):
        """
        查询基本信息
        :return: 基本信息结果
        """
        family = 'Registered_Info'
        table_id = '01'
        result_values = dict()
        self.info(family)
        td_list = table_tree.xpath(".//tr/td[2]")
        td_list.extend(table_tree.xpath(".//tr/td[4]"))
        for i in range(len(td_list)):
            td = td_list[i]
            desc = td.xpath("strong")[0].xpath("string(.)").split(u'：', 1)[0]
            val = td.xpath("string(.)").split(u'：', 1)[-1]
            if val:
                val = val.strip().replace("\n", '')
            if desc:
                if desc == u'统一社会信用代码/注册号':
                    self.cur_zch = val
                    if val:
                        if len(self.cur_zch) == 18:
                            result_values[family + ':tyshxy_code'] = self.cur_zch
                        else:
                            result_values[family + ':zch'] = self.cur_zch
                if desc in jiben_column_dict and val:
                    desc = jiben_column_dict[desc]
                    result_values[desc] = val
        result_values['rowkey'] = '%s_%s_%s_' % (self.cur_mc, table_id, self.cur_zch)
        result_values[family + ':registrationno'] = self.cur_zch
        result_values[family + ':enterprisename'] = self.cur_mc
        result_values[family + ':province'] = self.province
        result_values[family + ':lastupdatetime'] = get_cur_time()
        self.json_result[family] = [result_values]

    def get_gu_dong(self, table_element):
        """
        查询股东信息
        :param table_element:
        :param table_element:
        :return:
        """
        family = 'Shareholder_Info'
        table_id = '04'
        self.info(family)
        result_list = []
        result_values = {}
        j = 1
        th_list = table_element.xpath(".//th")
        tr_list = table_element.xpath(".//tr")[1:]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                if len(td_list) == 1:
                    break
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.text.strip()
                    if td.xpath("a"):
                        # self.info(u'查看股东详情' showRyxx('610000102015314786','6100001020153')
                        value = td.xpath("a")[0].get("onclick")
                        value = re.findall("\('(.*?)','(.*?)'", value)
                        gu_dong_detail = self.get_gu_dong_detail(value)
                        for detail_key in gu_dong_detail:
                                result_values[gudong_column_dict[detail_key]] = gu_dong_detail[detail_key]
                    else:
                        val = td.text
                    if val:
                        val = val.strip().replace("\n", "")
                    if desc in gudong_column_dict:
                            result_values[gudong_column_dict[desc]] = val
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result[family] = result_list

    def get_gu_dong_detail(self, val):
        self.info(u'****解析股东详情信息****')
        url = 'http://xygs.snaic.gov.cn/ztxy.do?method=frInfoDetail&maent.xh=%s&maent.pripid=%s&random=%s' % (val[0][0], val[0][1], long(time.time()))
        r = self.get_request(url)
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

    def get_tou_zi_ren(self, table_element):
        pass

    def get_bian_geng(self, table_element):
        """
        查询变更信息
        :param table_element:
        :return:
        """
        family = 'Changed_Announcement'
        table_id = '05'
        self.info(family)
        result_list = []
        result_values = {}
        j = 1
        th_list = table_element.xpath(".//th")
        tr_list = table_element.xpath(".//tr")[1:]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                if len(td_list) == 1:
                    break
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.text.strip()
                    val = td.text
                    if val:
                        val = val.strip().replace("\n", "")
                    if desc in biangeng_column_dict:
                            result_values[biangeng_column_dict[desc]] = val
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result[family] = result_list


    def get_zhu_yao_ren_yuan(self, table_element):
        """
        查询主要人员信息
        :param param_pripid:
        :param param_orgno:
        :return:
        """
        family = 'KeyPerson_Info'
        table_id = '06'
        self.info(family)
        result_list = []
        result_values = {}
        j = 1
        th_list = [u'姓名', u'职务']
        tr_list = table_element.xpath(".//li")
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("p")
                for i in range(len(td_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th
                    val = td.text
                    if val:
                        val = val.strip().replace("\n", "").replace('\r', '')
                    if desc in zhuyaorenyuan_column_dict and val:
                            result_values[zhuyaorenyuan_column_dict[desc]] = val
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result[family] = result_list

    def get_fen_zhi_ji_gou(self, table_element):
        """
        查询分支机构信息
        :param table_element:
        :return:
        """
        family = 'Branches'
        table_id = '08'
        self.info(family)
        result_list = []
        result_values = {}
        j = 1
        th_list = [u'名称', u'注册号/统一社会信用代码', u'登记机关']
        tr_list = table_element.xpath(".//li")
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("p")
                for i in range(len(td_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th
                    val = td.xpath("string(.)").split(u'：')[-1]
                    if val:
                        val = val.strip().replace("\n", "").replace('\r', '')
                    if desc in fenzhijigou_column_dict and val:
                            result_values[fenzhijigou_column_dict[desc]] = val
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result[family] = result_list

    def get_qing_suan(self, table_element):
        """
        查询清算信息
        :param table_element:
        :return:
        """
        pass
        # family = 'liquidation_Information'
        # table_id = '09'
        # self.json_result[family] = []
        # cheng_yuan = ''
        # fu_ze_ren = ''
        # if u'暂无数据' not in table_element.text.strip():
        #     tr_element_list = table_element.select('tr')[1:]
        #     # self.json_result[family].append({})
        #     for tr_element in tr_element_list:
        #         td_element = tr_element.select('td')
        #         th_element = tr_element.select('th')
        #         col_dec = th_element[0].text.strip()
        #         col = qingsuan_column_dict[col_dec]
        #         val = self.pattern.sub('', td_element[0].text)
        #         # self.json_result[family][-1][col] = val
        #         if col_dec == u'清算组负责人':
        #             cheng_yuan = val
        #         else:
        #             fu_ze_ren = val
        #     # print cheng_yuan,fu_ze_ren
        #     result_json = []
        # if cheng_yuan != '' and fu_ze_ren != '':
        #     result_json.append({'rowkey': '%s_%s_%s_' % (self.cur_mc, table_id, self.cur_zch),
        #                         family + ':' + 'liquidation_member': 'cheng_yuan',
        #                         family + ':' + 'liquidation_pic': 'fu_ze_ren',
        #                         family + ':registrationno': self.cur_zch,
        #                         family + ':enterprisename': self.cur_mc
        #                         })
        #     self.json_result[family].extend(result_json)
        #     # print json.dumps(self.json_result[family], ensure_ascii=False)

    def get_dong_chan_di_ya(self, table_element):
        """
        查询动产抵押信息
        :param param_param_pripid:
        :param table_element:
        :return:
        """
        family = 'Chattel_Mortgage'
        table_id = '11'
        self.info(family)
        result_list = []
        result_values = {}
        j = 1
        th_list = table_element.xpath(".//th")
        tr_list = table_element.xpath(".//tr")[1:]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                if len(td_list) == 1:
                    break
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.text.strip()
                    val = td.text
                    if val:
                        val = val.strip().replace("\n", "")
                    if td.xpath("a"):  # http://xygs.snaic.gov.cn/ztxy.do?method=getdcdyDetail&maent.pripid=6101012210818&maent.xh=610132000000000265&random=1478754643223
                        val = td.xpath("a")[0].get("onclick")
                        val = re.findall("\('(.*?)'", val)[0]
                        val = "http://xygs.snaic.gov.cn/ztxy.do?method=getdcdyDetail&maent.pripid=%s&maent.xh=%s&random=%s" % (self.priId, val, long(time.time()*1000))
                    if desc in dongchandiyadengji_column_dict:
                            result_values[dongchandiyadengji_column_dict[desc]] = val
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result[family] = result_list
        # self.info(json.dumps(result_json_2, ensure_ascii=False)

    def get_gu_quan_chu_zhi(self, table_element):
        """
        查询股权出质信息
        :param table_element:
        :return:
        """
        family = 'Equity_Pledge'
        table_id = '13'
        self.info(family)
        result_list = []
        result_values = {}
        j = 1
        th_list = table_element.xpath(".//th")
        tr_list = table_element.xpath(".//tr")[1:]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                if len(td_list) == 1:
                    break
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.xpath("string(.)").strip().replace("\n", "")
                    if i == 3 and desc == u'证照/证件号码':
                        desc = u'证照/证件号码(出质人)'
                    elif i == 6 and desc == u'证照/证件号码':
                        desc = u'证照/证件号码(质权人)'
                    val = td.text
                    if val:
                        val = val.strip().replace("\n", "")
                    # if td.xpath("a"):
                    #     val = td.xpath("a")[0].get("href")
                    if desc in guquanchuzhidengji_column_dict:
                            result_values[guquanchuzhidengji_column_dict[desc]] = val
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
        :param param_pripid:
        :param table_element:
        :return:
        """
        family = 'Administrative_Penalty'
        table_id = '13'
        self.info(family)
        result_list = []
        result_values = {}
        j = 1
        th_list = self.xzcf.xpath(".//*[@id='table_xzcf']//th")
        tr_list = self.xzcf.xpath(".//*[@id='table_xzcf']//tr")[1:]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                if len(td_list) == 1:
                    break
                if len(td_list) == len(th_list):
                    for i in range(len(th_list)):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th.xpath("string(.)").strip().replace("\n", "")
                        if td.xpath('input'):
                            val = td.xpath('input')[0].get('value')
                        else:
                            val = td.text
                        if val:
                            if val == u'查看':  # http://xygs.snaic.gov.cn/ztxy.do?method=xzfyDetail&maent.pripid=610100000022012122400056&maent.xh=6101338572014090003&random=1478756548173
                                val = td.xpath('a').get('onclick')  # doXzfyDetail('610100000022012122400056','6101338572014090003');
                                val = re.findall(",'(.*?)'", val)[0]
                                val = "http://xygs.snaic.gov.cn/ztxy.do?method=xzfyDetail&maent.pripid=%s&maent.xh=%s&random=%s" % (self.priId, val, long(time.time()*1000))
                            val = val.strip().replace("\n", "").replace("\r", '')
                        if desc in xingzhengchufa_column_dict:
                                result_values[xingzhengchufa_column_dict[desc]] = val
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result[family] = result_list

    def get_jing_ying_yi_chang(self):
        """
        查询经营异常信息
        :param table_element:
        :return:
        """
        family = 'Business_Abnormal'
        table_id = '14'
        self.info(family)
        result_list = []
        result_values = {}
        j = 1
        th_list = self.jyyc.xpath(".//*[@id='table_jyyc']//th")
        tr_list = self.jyyc.xpath(".//*[@id='table_jyyc']//tr")[1:]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                if len(td_list) == 1:
                    break
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.xpath("string(.)").strip().replace("\n", "")
                    val = td.text
                    if val:
                        val = val.strip().replace("\n", "")
                    # if td.xpath("a"):
                    #     val = td.xpath("a")[0].get("href")
                    if desc in jingyingyichang_column_dict:
                            result_values[jingyingyichang_column_dict[desc]] = val
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result[family] = result_list

    def get_yan_zhong_wei_fa(self):
        pass
    #     """
    #     查询严重违法信息
    #     :param table_element:
    #     :return:
    #     """
    #     family = 'Serious_Violations'
    #     table_id = '15'
    #     self.json_result[family] = []
    #     url = 'http://xygs.snaic.gov.cn/ztxy.do'
    #     params = {'czmk':'czmk4','maent.pripid':  self.pripid, 'method': 'yzwfInfo','random':get_cur_ts_mil()}
    #     r = self.get_request(url = url, params = params)
    #     soup = BeautifulSoup(r.text, 'lxml')
    #     if u'严重违法' in r.text:
    #         table_element = soup.select("div#yanzhongweifa > table")[0]
    #         th_element_list = table_element.select('th')[1:-1]
    #         tr_element_list = table_element.select('tr')[2:-1]
    #         for tr_element in tr_element_list:
    #             td_element_list = tr_element.select('td')
    #             col_nums = len(td_element_list)
    #             self.json_result[family].append({})
    #             for j in range(col_nums):
    #                 col_dec = th_element_list[j].text.strip().replace('\n', '')
    #                 col = yanzhongweifa_column_dict[col_dec]
    #                 td = td_element_list[j]
    #                 val = self.pattern.sub('', td.text)
    #                 self.json_result[family][-1][col] = val
    #     for i in range(len(self.json_result[family])):
    #         self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
    #         self.json_result[family][i][family + ':registrationno'] = self.cur_zch
    #         self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
    #         self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family], ensure_ascii=False)

    def get_chou_cha_jian_cha(self, table_element):
        """
        查询抽查检查信息
        :param param_pripid:
        :param table_element:
        :return:
        """
        family = 'Spot_Check'
        table_id = '16'
        self.info(family)
        result_list = []
        result_values = {}
        j = 1
        th_list = table_element.xpath(".//th")
        tr_list = table_element.xpath(".//tr")[1:]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                if len(td_list) == 1:
                    break
                for i in range(len(td_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.xpath("string(.)").strip().replace("\n", "")
                    val = td.text
                    if val:
                        val = val.strip().replace("\n", "")
                    if desc in chouchajiancha_column_dict:
                            result_values[chouchajiancha_column_dict[desc]] = val
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result[family] = result_list

if __name__ == '__main__':
    searcher = SShanXiSearcher()
    args_dict = get_args()
    if args_dict:
        searcher.submit_search_request(keyword=args_dict['companyName'], account_id=args_dict['accountId'], task_id=args_dict['taskId'])
    else:
        searcher.submit_search_request(u"甘肃天水")
        searcher.info(json.dumps(searcher.json_result, ensure_ascii=False))

    # 动产抵押 西安雄峰印刷包装有限公司
    # 分支机构 华陆工程科技有限责任公司
    # 股权出质 91610125757806401B 西安天汇置业有限公司  fine
    # 行政处罚 西安雄发商贸有限公司 fine
    # 经营异常 西安骏瑞电子科技有限公司 fine

    # 抽查检查 西安速达航空货运服务有限公司东郊营业部 fine