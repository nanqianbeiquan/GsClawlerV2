# coding=utf-8

import PackageTool
from gs.Searcher import Searcher
from gs.Searcher import get_args
from gs import MSSQL
import requests
from PIL import Image
import os
import sys
import uuid
import re
import random
import subprocess
from bs4 import BeautifulSoup
from GuiZhouConfig import *
from gs.KafkaAPI import KafkaAPI
from gs.TimeUtils import get_cur_time
import json
from requests.exceptions import RequestException


class GuiZhouSearcher(Searcher):
    load_func_dict = {}
    lock_id = 0
    list_path = 0
    nbxh = 0

    def __init__(self):
        super(GuiZhouSearcher, self).__init__(use_proxy=True)
        self.load_func_dict['base'] = self.get_ji_ben
        self.load_func_dict['investors'] = self.get_gu_dong
        self.load_func_dict['alters'] = self.get_bian_geng
        self.load_func_dict['members'] = self.get_zhu_yao_ren_yuan
        self.load_func_dict['brunchs'] = self.get_fen_zhi_ji_gou
        self.load_func_dict['accounts'] = self.get_qing_suan
        self.load_func_dict['motage'] = self.get_dong_chan_di_ya
        self.load_func_dict['stock'] = self.get_gu_quan_chu_zhi
        self.load_func_dict['punishments'] = self.get_xing_zheng_chu_fa
        self.load_func_dict['qyjy'] = self.get_jing_ying_yi_chang
        self.load_func_dict['illegalssx'] = self.get_yan_zhong_wei_fa
        self.load_func_dict['ccjc'] = self.get_chou_cha_jian_cha
        # self.load_func_dict[u'主管部门（出资人）信息'] = self.get_zhu_guan_bu_men     #Modified by Jing
        # self.load_func_dict[u'参加经营的家庭成员姓名'] = self.load_jiatingchengyuan     # Modified by Jing
        # self.load_func_dict[u'合伙人信息'] = self.load_hehuoren     #Modified by Jing
        # self.load_func_dict[u'成员名册'] = self.load_chengyuanmingce     # Modified by Jing
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:45.0) Gecko/20100101 Firefox/45.0",
                        "Host": "gsxt.gzgs.gov.cn",
                        "Accept": "*/*",
                        "Accept-Encoding": "gzip, deflate",
                        "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
                        "Referer": "http://gsxt.gzgs.gov.cn/2016/xq.jsp",
                        "Connection": "keep-alive"
                        }
        self.set_config()
        self.log_name = self.topic + "_" + str(uuid.uuid1())

    def set_config(self):
        self.plugin_path = os.path.join(sys.path[0], '../gui_zhou/ocr/guizhou/guizhou.bat')
        self.list_path = os.path.join(sys.path[0], '../gui_zhou/Data/company')
        self.group = 'Crawler'  # 正式
        self.kafka = KafkaAPI("GSCrawlerResult")  # 正式
        # self.group = 'CrawlerTest'  # 测试
        # self.kafka = KafkaAPI("GSCrawlerTest")  # 测试
        self.topic = 'GsSrc52'
        self.province = u'贵州省'
        self.kafka.init_producer()

    def download_yzm(self):
        image_url = 'http://gsxt.gzgs.gov.cn/2016/search!generateCode.shtml?validTag=searchImageCode&1473748323288'
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
        url = 'http://gsxt.gzgs.gov.cn/query!searchSczt.shtml'
        for t in range(20):
            # yzm = self.get_yzm()
            # params = {'q': keyword, 'validCode': yzm}
            params = {'q': keyword}
            r = self.post_request(url=url, params=params)
            r.encoding = 'utf-8'
            if u'验证码不正确' in r.text or 'false' in r.text:
                continue
            else:
                search_result_json = {}
                result_text = r.text
                start_idx = result_text.index('[')
                stop_idx = result_text.index(']')
                result_text = result_text[start_idx:stop_idx+1]
                # print 'result_text:', result_text
                result_json = json.loads(result_text)
                # print result_json.get['data']
                if len(result_json) > 0:
                    self.nbxh = ''
                    k = result_json[0]
                    for j in k:
                        text_detail = k[j]
                        if j == 'zch':
                            self.cur_zch = text_detail.split('/')[0]
                        if j == 'nbxh':
                            self.nbxh = text_detail
                        if j == 'qymc':
                            self.cur_mc = text_detail
                    if flags:
                        search_result_json['entname'] = self.cur_mc
                    else:
                        self.cur_mc = keyword
                    search_result_json['regno'] = self.cur_zch
                    search_result_json['nbxh'] = self.nbxh
                    tag_a = json.dumps(search_result_json, ensure_ascii=False)
                    return tag_a
                else:
                    return None

    def get_search_args(self, tag_a, keyword):
        self.keyword = keyword
        search_result_json = json.loads(tag_a)
        if search_result_json.get('entname', None) == keyword:
            nbxh = search_result_json['nbxh']
            self.nbxh = nbxh
            self.cur_mc = search_result_json['entname'].replace('(', u'（').replace(')', u'）')  # 公司名称括号统一转成全角
            self.cur_zch = search_result_json['regno']
            return 1
        elif keyword in search_result_json['regno']:
            nbxh = search_result_json['nbxh']
            self.nbxh = nbxh
            self.cur_mc = keyword
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
        # keyword = self.keyword
        # self.parse_company_detail(keyword)
        nbxh = self.nbxh
        self.get_ji_ben(nbxh)
        self.get_gu_dong(nbxh)
        self.get_bian_geng(nbxh)
        self.get_zhu_yao_ren_yuan(nbxh)
        self.get_fen_zhi_ji_gou(nbxh)
        self.get_dong_chan_di_ya(nbxh)
        self.get_xing_zheng_chu_fa(nbxh)
        self.get_gu_quan_chu_zhi(nbxh)
        self.get_jing_ying_yi_chang(nbxh)
        self.get_chou_cha_jian_cha(nbxh)

    def get_ji_ben(self, param_nbxh):
        """
        查询基本信息
        :return: 基本信息结果
        """
        self.info(u'解析基本信息...')
        family = 'Registered_Info'
        table_id = '01'
        self.json_result[family] = []
        self.json_result[family].append({})
        url = "http://gsxt.gzgs.gov.cn/2016/nzgs/query!searchData.shtml"
        params = {'nbxh': param_nbxh,'c':'0','t':'5'}
        r = self.post_request(url=url, params=params)
        r.encoding = 'utf-8'
        result_text = r.text
        start_idx = result_text.index('[')
        stop_idx = result_text.rindex(']')
        result_text = result_text[start_idx:stop_idx+1]
        result_json = json.loads(result_text)
        for j in result_json:
            for k in j:
                if k in ji_ben_dict:
                    col = family + ':' + ji_ben_dict[k]
                    val = j[k]
                    if k == 'zch':
                        for f in range(len(val.split('/'))):
                            if len(val.split('/')[f]) == 18:
                                self.json_result[family][0][family +':tyshxy_code'] = val.split('/')[f]
                            else:
                                self.json_result[family][0][family +':zch'] = val.split('/')[f]
                    else:
                        self.json_result[family][-1][col] = val
        self.json_result[family][-1]['rowkey'] = '%s_%s_%s_' % (self.cur_mc, table_id, self.cur_zch)
        self.json_result[family][-1][family + ':registrationno'] = self.cur_zch
        self.json_result[family][-1][family + ':enterprisename'] = self.cur_mc
        self.json_result[family][-1][family + ':province'] = self.province
        self.json_result[family][-1][family + ':lastupdatetime'] = get_cur_time()
        # print json.dumps(self.json_result[family], ensure_ascii=False)

    def get_tou_zi_ren(self, param_corpid, table_element):
        pass

    def get_gu_dong(self, param_nbxh):
        """
        查询股东信息
        :param param_nbxh:
        :return:
        """
        self.info(u'解析股东信息...')
        family = 'Shareholder_Info'
        table_id = '04'
        self.json_result[family] = []
        xqmc = ''
        detail_list = None
        url = "http://gsxt.gzgs.gov.cn/2016/nzgs/query!searchData.shtml"
        params = {'nbxh': param_nbxh,'c':'2','t':'3'}
        r = self.post_request(url=url, params=params)
        r.encoding = 'utf-8'
        result_text = r.text
        start_idx = result_text.index('[')
        stop_idx = result_text.rindex(']')
        result_text = result_text[start_idx:stop_idx+1]
        # print 'result_text_gu_dong', result_text
        result_json = json.loads(result_text)
        for j in result_json:
            self.json_result[family].append({})
            for k in j:
                if k in gu_dong_dict:
                    col = family + ':' + gu_dong_dict[k]
                    val = j[k]
                    self.json_result[family][-1][col] = val
                    if k == 'czmc':
                        xqmc = j[k]
            self.get_gu_dong_company_detail(param_nbxh, xqmc)
            if self.get_gu_dong_company_detail(param_nbxh, xqmc):
                detail_list = self.get_gu_dong_company_detail(param_nbxh, xqmc)
            if detail_list:
                for x in detail_list:
                    for y in x:
                        col = y
                        val = x[y]
                        self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family][i], ensure_ascii=False)

    def get_gu_dong_company_detail(self, param_nbxh, xqmc):
        family = 'Shareholder_Info'
        for s in range(10):
            detail_dict_list = []
            url = "http://gsxt.gzgs.gov.cn/2016/frame/query!searchTzr.shtml"
            params = {'nbxh': param_nbxh,'c':'2','t':'4','czmc':xqmc}
            r = self.post_request(url=url, params=params)
            r.encoding = 'utf-8'
            result_text = r.text
            if 'false' in result_text:
                continue
            else:
                start_idx = result_text.index('[')
                stop_idx = result_text.rindex(']')
                result_text = result_text[start_idx:stop_idx+1]
                result_json = json.loads(result_text)
                for j in result_json:
                    detail_dict_list.append({})
                    for k in j:
                        if k in gu_dong_detail_dict:
                            col = family + ':' + gu_dong_detail_dict[k]
                            val = j[k]
                            detail_dict_list[-1][col] = val
            # print 'result_json', result_json
            # print 'detail_dict_list', detail_dict_list
            if detail_dict_list:
                if detail_dict_list[0]['Shareholder_Info:subscripted_amount'] ==u' 万人民币元' and detail_dict_list[0]['Shareholder_Info:actualpaid_time'] == None:
                    return None
                else:
                    return detail_dict_list
            else:
                return None


    def get_bian_geng(self, param_nbxh):
        """
        查询变更信息
        :param param_entid:
        :param table_element:
        :return:
        """
        self.info(u'解析变更信息...')
        family = 'Changed_Announcement'
        table_id = '05'
        self.json_result[family] = []
        url = "http://gsxt.gzgs.gov.cn/2016/nzgs/query!searchData.shtml"
        params = {'nbxh': param_nbxh,'c':'0','t':'3'}
        r = self.post_request(url=url, params=params)
        r.encoding = 'utf-8'
        result_text = r.text
        result_text = result_text.replace(u'[以下空白]','')
        start_idx = result_text.index('[')
        stop_idx = result_text.rindex(']')
        result_text=result_text[start_idx:stop_idx+1]
        result_json = json.loads(result_text)
        for j in result_json:
            self.json_result[family].append({})
            for k in j:
                if k in bian_geng_dict:
                    col = family + ':' + bian_geng_dict[k]
                    val = j[k]
                    self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family][i], ensure_ascii=False)

    def get_zhu_yao_ren_yuan(self, param_nbxh):
        """
        查询主要人员信息
        :param param_nbxh:
        :return:
        """
        family = 'KeyPerson_Info'
        table_id = '06'
        self.json_result[family] = []
        url = "http://gsxt.gzgs.gov.cn/2016/nzgs/query!searchData.shtml"
        params = {'nbxh': param_nbxh,'c':'0','t':'8'}
        r = self.post_request(url=url, params=params)
        r.encoding = 'utf-8'
        result_text = r.text
        start_idx = result_text.index('[')
        stop_idx = result_text.rindex(']')
        result_text = result_text[start_idx:stop_idx+1]
        result_json = json.loads(result_text)
        for j in result_json:
            self.json_result[family].append({})
            for k in j:
                if k in zhu_yao_ren_yuan_dict:
                    col = family + ':' + zhu_yao_ren_yuan_dict[k]
                    val = j[k]
                    self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family][i], ensure_ascii=False)

    def get_fen_zhi_ji_gou(self, param_nbxh):
        """
        查询分支机构信息
        :param param_nbxh:
        :param table_element:
        :return:
        """
        family = 'Branches'
        table_id = '08'
        self.json_result[family] = []
        url = "http://gsxt.gzgs.gov.cn/2016/nzgs/query!searchData.shtml"
        params = {'nbxh': param_nbxh, 'c': '0', 't': '9'}
        r = self.post_request(url=url, params=params)
        r.encoding = 'utf-8'
        result_text = r.text
        start_idx = result_text.index('[')
        stop_idx = result_text.index(']')
        result_text = result_text[start_idx:stop_idx+1]
        result_json = json.loads(result_text)
        for j in result_json:
            self.json_result[family].append({})
            for k in j:
                if k in fen_zhi_ji_gou_dict:
                    col = family + ':' + fen_zhi_ji_gou_dict[k]
                    val = j[k]
                    self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family][i], ensure_ascii=False)

    def get_qing_suan(self, param_nbxh, table_detail):
        """
        查询清算信息
        :param param_nbxh:
        :return:
        """
        family = 'liquidation_Information'
        table_id = '09'
        self.json_result[family] = []
        for j in table_detail:
            self.json_result[family].append({})
            for k in j:
                if k in qing_suan_dict:
                    col = family + ':' + qing_suan_dict[k]
                    val = j[k]
                    self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family][i], ensure_ascii=False)

    def get_dong_chan_di_ya(self, param_nbxh):
        """
        查询动产抵押信息
        :param param_nbxh:
        :return:
        """
        self.info(u'解析动产抵押信息...')
        family = 'Chattel_Mortgage'
        table_id = '11'
        self.json_result[family] = []
        url = "http://gsxt.gzgs.gov.cn/2016/grdzgs/query!searchData.shtml"
        params = {'nbxh': param_nbxh, 'c': '0', 't': '25'}
        r = self.post_request(url=url, params=params)
        r.encoding = 'utf-8'
        result_text = r.text
        # print 'result_text', result_text
        start_idx = result_text.index('[')
        stop_idx = result_text.rindex(']')
        result_text = result_text[start_idx:stop_idx+1]
        result_json = json.loads(result_text)
        # print 'result_json:', result_json
        for j in result_json:
            self.json_result[family].append({})
            for k in j:
                if k in dong_chan_di_ya_dict:
                    col = family + ':' + dong_chan_di_ya_dict[k]
                    val = j[k]
                    self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family], ensure_ascii=False)

    def get_gu_quan_chu_zhi(self, param_nbxh):
        """
        查询股权出资信息
        :param param_nbxh:
        :return:
        """
        self.info(u'解析股权出质信息...')
        family = 'Equity_Pledge'
        table_id = '13'
        self.json_result[family] = []
        url = "http://gsxt.gzgs.gov.cn/2016/nzgs/query!searchGqcz.shtml"
        params = {'nbxh': param_nbxh, 'c': '0', 't': '4'}
        r = self.post_request(url=url, params=params)
        r.encoding = 'utf-8'
        result_text = r.text
        # print 'result_text', result_text
        start_idx = result_text.index('[')
        stop_idx = result_text.rindex(']')
        result_text = result_text[start_idx:stop_idx+1]
        result_json = json.loads(result_text)
        for j in result_json:
            self.json_result[family].append({})
            for k in j:
                if k in gu_quan_chu_zhi_dict:
                    col = family + ':' + gu_quan_chu_zhi_dict[k]
                    val = j[k]
                    self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family][i], ensure_ascii=False)

    def get_xing_zheng_chu_fa(self, param_nbxh):
        """
        查询行政处罚信息
        :param param_nbxh:
        :return:
        """
        self.info(u'解析行政处罚信息...')
        family = 'Administrative_Penalty'
        table_id = '13'
        self.json_result[family] = []
        url = "http://gsxt.gzgs.gov.cn/2016/gfgs/query!searchOldData.shtml"
        params = {'nbxh': param_nbxh,'c':'0','t':'38'}
        r = self.post_request(url=url, params=params)
        r.encoding = 'utf-8'
        result_text = r.text
        start_idx = result_text.index('[')
        stop_idx = result_text.rindex(']')
        result_text=result_text[start_idx:stop_idx+1]
        result_json = json.loads(result_text)
        # print 'result_json_Administrative_Penalty', result_json
        for j in result_json:
            self.json_result[family].append({})
            for k in j:
                if k in xing_zheng_chu_fa_dict:
                    col = family + ':' + xing_zheng_chu_fa_dict[k]
                    val = j[k]
                    self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family], ensure_ascii=False)

    def get_jing_ying_yi_chang(self, param_nbxh):
        """
        查询经营异常信息
        :param param_nbxh:
        :return:
        """
        self.info(u'解析经营异常信息...')
        family = 'Business_Abnormal'
        table_id = '14'
        self.json_result[family] = []
        url = "http://gsxt.gzgs.gov.cn/2016/nzgs/query!searchData.shtml"
        params = {'nbxh': param_nbxh,'c':'0','t':'33'}
        r = self.post_request(url=url, params=params)
        r.encoding = 'utf-8'
        result_text = r.text
        start_idx = result_text.index('[')
        stop_idx = result_text.rindex(']')
        result_text = result_text[start_idx:stop_idx+1]
        result_json = json.loads(result_text)
        # print 'result_json_jing_ying', result_json
        for j in result_json:
            self.json_result[family].append({})
            for k in j:
                if k in jing_ying_yi_chang_dict:
                    col = family + ':' + jing_ying_yi_chang_dict[k]
                    val = j[k]
                    self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family][i], ensure_ascii=False)

    def get_yan_zhong_wei_fa(self, param_nbxh):
        """
        查询严重违法信息
        :param param_nbxh:
        :return:
        """
        pass
        # family = 'Serious_Violations'
        # table_id = '15'
        # self.json_result[family] = []
        # for j in table_detail:
        #     self.json_result[family].append({})
        #     for k in j:
        #         if k in yan_zhong_wei_fa_dict:
        #             col = family + ':' + yan_zhong_wei_fa_dict[k]
        #             val = j[k]
        #             self.json_result[family][-1][col] = val
        # for i in range(len(self.json_result[family])):
        #     self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
        #     self.json_result[family][i][family + ':registrationno'] = self.cur_zch
        #     self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
        #     self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family], ensure_ascii=False)

    def get_chou_cha_jian_cha(self, param_nbxh):
        """
        查询抽查检查信息
        :param param_nbxh:
        :return:
        """
        self.info(u'解析抽查检查信息...')
        family = 'Spot_Check'
        table_id = '16'
        self.json_result[family] = []
        url = "http://gsxt.gzgs.gov.cn/2016/nzgs/query!searchData.shtml"
        params = {'nbxh': param_nbxh,'c':'0','t':'35'}
        r = self.post_request(url=url, params=params)
        r.encoding = 'utf-8'
        result_text = r.text
        # print 'result_text_chou_cha', result_text
        start_idx = result_text.index('[')
        stop_idx = result_text.rindex(']')
        result_text = result_text[start_idx:stop_idx+1]
        result_json = json.loads(result_text)
        # print 'result_json_jing_ying', result_json
        for j in result_json:
            self.json_result[family].append({})
            for k in j:
                if k in chou_cha_jian_cha_dict:
                    col = family + ':' + chou_cha_jian_cha_dict[k]
                    val = j[k]
                    self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family][i], ensure_ascii=False)

if __name__ == '__main__':
    args_dict = get_args()
    searcher = GuiZhouSearcher()
    # searcher.delete_tag_a_from_db('91522328314243590L')
    searcher.submit_search_request(u'贵州五星酒业集团茅台镇五星酒厂')
    # searcher.submit_search_request('91522328314243590L', False)
    # print json.dumps(searcher.json_result, ensure_ascii=False)
    # args_dict = {'companyName': u'爱晚宏宙（贵州）投资有限公司', 'accountId': '123', 'taskId': '456'}
    # searcher.submit_search_request(keyword=args_dict['companyName'], account_id=args_dict['accountId'], task_id=args_dict['taskId'])
