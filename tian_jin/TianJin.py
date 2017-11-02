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

reload(sys)
sys.setdefaultencoding('utf8')


class TianJinSearcher(Searcher):

    def __init__(self):
        super(TianJinSearcher, self).__init__()
        self.error_judge = False  # 判断网站是否出错，False正常，True错误
        self.session = requests.session()
        self.proxy_config = ProxyConf(app_key)
        self.tag_a = ''
        self.corp_id = ''
        self.corp_org = ''
        self.corp_seq_id = ''
        self.set_config()
        self.headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:47.0) Gecko/20100101 Firefox/47.0",
                        "Host": "tjcredit.gov.cn",
                        }
        self.dengji_tree = ""
        self.beian_tree = ""
        self.ent_id = ''
        self.log_name = 'tian_jin'

    def set_config(self):
        self.plugin_path = os.path.join(sys.path[0],  r'..\tian_jin\ocr\tianjinnewocr.exe')
        self.group = 'Crawler'  # 正式
        self.kafka = KafkaAPI("GSCrawlerResult")  # 正式
        # self.group = 'CrawlerTest'  # 测试
        # self.kafka = KafkaAPI("GSCrawlerTest")  # 测试
        self.topic = 'GsSrc12'
        self.province = u'天津市'
        self.kafka.init_producer()

    def get_tag_a_from_page(self, keyword, flags=True):
        headers = {
            "Host": "tjcredit.gov.cn",
            "Referer": "http://tjcredit.gov.cn/platform/saic/search.ftl",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0",
            "X-Requested-With": "XMLHttpRequest",
        }
        for t in range(10):
            yzm = self.get_yzm()
            params = {'searchContent': keyword, 'vcode': yzm, 'matchCondition': 1}
            url = 'http://tjcredit.gov.cn/platform/saic/search.ftl'
            r = self.session.post(url=url, data=params, headers=headers)
            # self.info(r.text
            # result_list = json.loads(r.text)
            if u'验证码错误' in r.text:
                self.info(u'验证错误，重试')
            else:
                self.info(u'验证成功')
                break
        if u'验证码错误' in r.text:
            raise ValueError(u'验证失败')
        tree = html.fromstring(r.text)
        result_name_list = tree.xpath(".//div[@class='result-item']//a")
        for i in range(len(result_name_list)):
            result = result_name_list[i].xpath("string(.)").replace('(', u'（').replace(')', u'）').strip()
            name = re.match(u'^(.*)\uFF08.*\uFF09$', result.decode('utf-8')).groups()[0]
            if name != keyword:
                self.save_mc_to_db(name)
        for i in range(len(result_name_list)):
            result = result_name_list[i].xpath("string(.)").replace('(', u'（').replace(')', u'）').strip()
            name = re.match(u'^(.*)\uFF08.*\uFF09$', result.decode('utf-8')).groups()[0]
            # self.info(name
            if flags:
                if name == keyword:
                    self.info(u'查询到指定公司')
                    self.tag_a = "http://tjcredit.gov.cn" + result_name_list[i].get("href")
                    return self.tag_a
            else:
                self.info(u'查询到指定公司')
                self.tag_a = "http://tjcredit.gov.cn" + result_name_list[i].get("href")
                return self.tag_a

    def recognize_yzm(self, yzm_path):
        """
        识别验证码
        :param yzm_path: 验证码保存路径
        :return: 验证码识别结果
        """
        cmd = self.plugin_path + " " + yzm_path
        # self.info(cmd)
        process = subprocess.Popen(cmd.encode('GBK', 'ignore'), stdout=subprocess.PIPE)
        process_out = process.stdout.read()

        # answer = process_out.split('\r\n')[6].strip()
        # self.info('answer: '+ process_out)
#         os.remove(validate_path)
        return process_out

    def get_search_args(self, tag_a, keyword):
        self.cur_mc = keyword
        self.info(u'解析查询参数')
        self.ent_id = re.findall('entId=(.*)$', tag_a)[0]
        return 1

    def download_yzm(self):
        time_url = get_cur_ts_mil()
        image_url = 'http://tjcredit.gov.cn/verifycode?date=' + time_url
        r = self.get_request(image_url)
        yzm_path = self.get_yzm_path()
        with open(yzm_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    f.flush()
            f.close()
        return yzm_path

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
        self.get_qing_suan()
        self.get_dong_chan_di_ya()
        self.get_gu_quan_chu_zhi()
        self.get_xing_zheng_chu_fa()
        self.get_jing_ying_yi_chang()
        self.get_yan_zhong_wei_fa()
        self.get_chou_cha_jian_cha()
        # self.get_nian_bao_link(kwargs)

    def get_ji_ben(self):
        """
        查询基本信息
        :return: 基本信息结果
        """
        family = 'Registered_Info'
        table_id = '01'
        self.info(u'基本信息')
        result_values = dict()
        url = 'http://tjcredit.gov.cn/platform/saic/baseInfo.json?entId=%s&departmentId=scjgw&infoClassId=dj' % self.ent_id
        r = self.get_request(url=url)
        r.encoding = 'utf-8'
        # self.info(r.text
        self.dengji_tree = html.fromstring(r.text)
        th_list = self.dengji_tree.xpath(".//table[1]//td")[1::2]
        td_list = self.dengji_tree.xpath(".//table[1]//td")[2::2]
        for i in range(len(td_list)):
            th = th_list[i]
            td = td_list[i]
            desc = th.xpath("string(.)")
            val = td.xpath("string(.)")
            if val:
                val = val.strip()
            if desc:
                if desc == u'营业执照注册号统一社会信用代码':
                    val_list = val.split("\n")
                    if len(val_list) == 2:
                        self.cur_zch = val_list[1].strip().replace(u'无', '')
                        result_values[family + ':zch'] = val_list[0].strip().replace(u'无', '')
                        result_values[family + ':tyshxy_code'] = val_list[1].strip().replace(u'无', '')
                        if not self.cur_zch:
                            self.cur_zch = val_list[0].strip().replace(u'无', '')
                    elif len(val_list) == 1:
                        self.cur_zch = val_list[0].strip()
                        if len(val_list[0]) != 18:
                            result_values[family + ':zch'] = val_list[0].strip()
                        else:
                            result_values[family + ':tyshxy_code'] = val_list[0].strip()
                # self.info('*', desc, val
                if desc in ji_ben_dict:
                    desc = family + ':' + ji_ben_dict[desc]
                    if val:
                        result_values[desc] = val.strip().replace('\n', '')
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
        if not self.dengji_tree.xpath(".//*[@id='touziren']//tr"):  # 没有股东表格
            return
        th_list = self.dengji_tree.xpath(".//*[@id='touziren']//tr")[1].xpath("td")
        tr_list = self.dengji_tree.xpath(".//*[@id='touziren']//tr")[2:]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                if len(td_list) == 1:
                    return
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.xpath("string(.)")
                    if td.xpath("a"):
                        # self.info(u'查看股东详情'
                        val = td.xpath("a")[0].get("onclick")
                        gudong_id = re.findall("Holder\('(.*?)',", val)[0]
                        ent_id = re.findall(",'(.*?)'", val)[0]
                        gudong_detail = self.get_gudong_detail(gudong_id, ent_id)
                        for detail_key in gudong_detail:
                            result_values[family + ":" + gu_dong_dict[detail_key]] = gudong_detail[detail_key]
                    else:
                        val = td.text
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
        url = "http://tjcredit.gov.cn/saicpf/gsgdcz?gdczid=%s&entid=%s&issaic=1&hasInfo=0" % (gudong_id, ent_id)
        r = self.get_request(url)
        r.encoding = 'utf-8'
        tree = html.fromstring(r.text)
        colum_name_list = tree.xpath('.//tr[@width="95%"]//td')
        td_element_list = tree.xpath(".//td")[12:21]
        del colum_name_list[3:5]
        td_num = len(td_element_list)
        values = {}
        for i in range(td_num):
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
        th_list = self.dengji_tree.xpath(".//table[3]//tr[2]/td")
        tr_list = self.dengji_tree.xpath(".//table[3]//tr")[2:]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                if len(td_list) == 1:
                    return
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.xpath("string(.)")
                    val = td.xpath("string(.)")
                    if desc in bian_geng_dict:
                            result_values[family + ":" + bian_geng_dict[desc]] = val
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result["Changed_Announcement"] = result_list

    def get_zhu_yao_ren_yuan(self):
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
        url = 'http://tjcredit.gov.cn/platform/saic/baseInfo.json?entId=%s&departmentId=scjgw&infoClassId=ba' % self.ent_id
        r = self.get_request(url)
        r.encoding = 'utf-8'
        if not r.text:
            return
        self.beian_tree = html.fromstring(r.text)

        th_list = [u'序号', u'姓名', u'职务', u'序号', u'姓名', u'职务']
        tr_list = self.beian_tree.xpath(".//table[1]//tr")[1:]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                if len(td_list) == 1:
                    return
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
        th_list = self.beian_tree.xpath(".//*[@id='t31']//tr[2]/td")
        tr_list = self.beian_tree.xpath(".//*[@id='t31']//tr")[2:]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                if len(td_list) == 1:
                    return
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.text.strip()
                    val = td.text
                    if val:
                        result_values[family + ":" + fen_zhi_ji_gou_dict[desc]] = val.strip()
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result["Branches"] = result_list

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
        self.info(u'动产抵押信息')
        result_list = []
        j = 1
        result_values = dict()
        url = 'http://tjcredit.gov.cn/platform/saic/baseInfo.json?entId=%s&departmentId=scjgw&infoClassId=dcdydjxx' % self.ent_id
        r = self.get_request(url)
        r.encoding = 'utf-8'
        if not r.text:
            return
        tree = html.fromstring(r.text)
        th_list = tree.xpath(".//tr[2]/td")
        tr_list = tree.xpath(".//tr")[2:]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                if len(td_list) == 1:
                    return
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.xpath("string(.)").strip()
                    val = td.xpath("string(.)").strip()
                    if td.xpath("td"):
                        val = re.findall("getChaMore\('(.*?)',", td.xpath('td')[0].get("onclick"))[0]
                        val = "http://tjcredit.gov.cn/saicpf/gsdcdy?id=%s&entid=%s&issaic=1&hasInfo=0" % (val, self.ent_id)
                    if val:
                        result_values[family + ":" + dong_chan_di_ya_dict[desc]] = val.strip()
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result["Chattel_Mortgage"] = result_list
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
        self.info(u'股权出质')
        result_list = []
        j = 1
        result_values = dict()
        url = 'http://tjcredit.gov.cn/platform/saic/baseInfo.json?entId=%s&departmentId=scjgw&infoClassId=gqczdjxx' % self.ent_id
        r = self.get_request(url)
        r.encoding = 'utf-8'
        if not r.text:
            return
        tree = html.fromstring(r.text)
        th_list = tree.xpath(".//tr[2]/td")
        tr_list = tree.xpath(".//table//tr")[2:]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                if len(td_list) == 1:
                    return
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.xpath("string(.)").strip()
                    val = td.xpath("string(.)").strip()
                    if val:
                        result_values[family + ":" + gu_quan_chu_zhi_dict[desc]] = val.strip()
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result["Equity_Pledge"] = result_list

    def get_xing_zheng_chu_fa(self):
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
        url = 'http://tjcredit.gov.cn/platform/saic/baseInfo.json?entId=%s&departmentId=scjgw&infoClassId=xzcf' % self.ent_id
        r = self.get_request(url)
        r.encoding = 'utf-8'
        if not r.text:
            return
        tree = html.fromstring(r.text)
        th_list = tree.xpath(".//tr[2]/td")
        tr_list = tree.xpath(".//tr")[2:]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                if len(td_list) == 1:
                    return
                for i in range(len(th_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.xpath("string(.)").strip()
                    val = td.xpath("string(.)").strip()
                    # if td.xpath("td"):
                    #     val = re.findall("getChaMore\('(.*?)',", td.xpath('td')[0].get("onclick"))[0]
                    #     val = "http://tjcredit.gov.cn/saicpf/gsdcdy?id=%s&entid=%s&issaic=1&hasInfo=0" % (val, ent_id)
                    if val:
                        result_values[family + ":" + xing_zheng_chu_fa_dict[desc]] = val.strip()
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result["Administrative_Penalty"] = result_list
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
        self.info(u'经营异常')
        result_list = []
        j = 1
        result_values = dict()
        url = 'http://tjcredit.gov.cn/platform/saic/baseInfo.json?entId=%s&departmentId=scjgw&infoClassId=qyjyycmlxx' % self.ent_id
        r = self.get_request(url)
        r.encoding = 'utf-8'
        if not r.text:
            return
        tree = html.fromstring(r.text)
        th_list = tree.xpath(".//tr[2]/td")
        tr_list = tree.xpath(".//tr")[2:]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                if len(td_list) == 1:
                    return
                for i in range(len(td_list)):
                    th = th_list[i]
                    td = td_list[i]
                    desc = th.xpath("string(.)").strip()
                    val = td.xpath("string(.)").strip()
                    if val and desc in jing_ying_yi_chang_dict:
                        result_values[family + ":" + jing_ying_yi_chang_dict[desc]] = val.strip()
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result["Business_Abnormal"] = result_list
        # self.info(json.dumps(result_json_2, ensure_ascii=False)

    def get_yan_zhong_wei_fa(self):
        """
        查询严重违法信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        pass
        # family = 'Serious_Violations'
        # table_id = '15'
        # self.info(u'严重违法'
        # result_list = []
        # j = 1
        # result_values = dict()
        # url = 'http://tjcredit.gov.cn/platform/saic/baseInfo.json?entId=%s&departmentId=scjgw&infoClassId=yzwfqyxx' % ent_id
        # r = self.get_request(url)
        # r.encoding = 'utf-8'
        # tree = html.fromstring(r.text)
        # th_list = tree.xpath(".//table//tr[2]/td")
        # tr_list = tree.xpath(".//table//tr")[2:]
        # if tr_list:
        #     for tr in tr_list:
        #         td_list = tr.xpath("td")
        #         for i in range(len(th_list)):
        #             th = th_list[i]
        #             td = td_list[i]
        #             desc = th.xpath("string(.)").strip()
        #             val = td.xpath("string(.)").strip()
        #             # if td.xpath("td"):
        #             #     val = re.findall("getChaMore\('(.*?)',", td.xpath('td')[0].get("onclick"))[0]
        #             #     val = "http://tjcredit.gov.cn/saicpf/gsdcdy?id=%s&entid=%s&issaic=1&hasInfo=0" % (val, ent_id)
        #             if val == u'无':
        #                 return
        #             if val and desc in yan_zhong_wei_fa_dict:
        #                 result_values[family + ":" + yan_zhong_wei_fa_dict[desc]] = val.strip()
        #         result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
        #         result_values[family + ':registrationno'] = self.cur_zch
        #         result_values[family + ':enterprisename'] = self.cur_mc
        #         result_values[family + ':id'] = j
        #         result_list.append(result_values)
        #         result_values = {}
        #         j += 1
        # self.json_result["Serious_Violations"] = result_list

    def get_chou_cha_jian_cha(self):
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
        url = 'http://tjcredit.gov.cn/platform/saic/baseInfo.json?entId=%s&departmentId=scjgw&infoClassId=ccjcxx' % self.ent_id
        r = self.get_request(url)
        r.encoding = 'utf-8'
        if not r.text:
            return

        tree = html.fromstring(r.text)
        th_list = tree.xpath(".//tbody/tr[1]/td")
        tr_list = tree.xpath(".//tr")[2:]
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
                    # self.info(desc+" "+val)
                    # if td.xpath("td"):
                    #     val = re.findall("getChaMore\('(.*?)',", td.xpath('td')[0].get("onclick"))[0]
                    #     val = "http://tjcredit.gov.cn/saicpf/gsdcdy?id=%s&entid=%s&issaic=1&hasInfo=0" % (val, ent_id)
                    if val and desc in chou_cha_jian_cha_dict:
                        result_values[family + ":" + chou_cha_jian_cha_dict[desc]] = val.strip()
                result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                result_values[family + ':registrationno'] = self.cur_zch
                result_values[family + ':enterprisename'] = self.cur_mc
                result_values[family + ':id'] = j
                result_list.append(result_values)
                result_values = {}
                j += 1
        self.json_result["Spot_Check"] = result_list

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

    def get_nian_bao_link(self, corp_org, corp_id, corp_seq_id):
        """
        获取年报url
        :param param_pripid:
        :param param_type:
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
    searcher = TianJinSearcher()
    args_dict = get_args()
    if args_dict:
        searcher.submit_search_request(keyword=args_dict['companyName'], account_id=args_dict['accountId'], task_id=args_dict['taskId'])
    else:
        searcher.submit_search_request(u"甘肃天水")
        searcher.info(json.dumps(searcher.json_result, ensure_ascii=False))

