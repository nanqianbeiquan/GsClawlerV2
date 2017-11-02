# coding=utf-8

import PackageTool

# import sys
import os
import itertools
import codecs
# import traceback
from ocr.HubeiOcr import recognize
# from pip._vendor.requests.exceptions import Timeout
# from selenium.common.exceptions import TimeoutException, NoSuchElementException
# from selenium.webdriver.common.action_chains import ActionChains
# import json
# from bs4 import BeautifulSoup
import sys
# import requests
from gs.KafkaAPI import KafkaAPI
from gs.Searcher import Searcher
# from gs.Searcher import get_args
# from PIL import Image
# from bs4 import BeautifulSoup
# import urllib2
# import random
import json
# from json.decoder import JSONArray
# from gs.TimeUtils import get_cur_time_jiangsu
from gs.TimeUtils import get_cur_time,get_cur_ts_mil
from lxml import html
# from gs.ProxyConf import ProxyConf, key1 as app_key
from Table_dict import *
import re
# import tesseract


class HuBeiSearcher(Searcher):

    def __init__(self):
        super(HuBeiSearcher, self).__init__()
        self.headers = {
            "Host": "xyjg.egs.gov.cn",
            # "Referer": "http://xyjg.egs.gov.cn/ECPS_HB/search.jspx",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0"
        }
        self.s = set()
        self.get_word_set()
        self.set_config()
        self.ent_id = ''
        self.log_name = 'hu_bei'

    def set_config(self):
        # self.plugin_path = os.path.join(sys.path[0], '../guangdong/ocr/guangdong.bat')
        self.group = 'Crawler'  # 正式
        self.kafka = KafkaAPI("GSCrawlerResult")  # 正式
        # self.group = 'CrawlerTest'  # 测试
        # self.kafka = KafkaAPI("GSCrawlerTest")  # 测试
        self.topic = 'GsSrc42'
        self.province = u'湖北省'
        self.kafka.init_producer()

    def get_word_set(self):
        chengyu_path = os.path.join(sys.path[0], r"..\hu_bei\ocr\chengyu.txt")
        print chengyu_path
        f = codecs.open(chengyu_path, "r", "gbk", "ignore")
        # 将成语字典全部加载到set里面
        for line in f:
            word = line.strip()
            self.s.add(word)

    def permute(self, wordline):
        idiom = []
        wl = wordline.split(',')
        alter = list(itertools.permutations(wl, 4))
        for l1 in alter:
            word = ''.join(l1)
            if word in self.s:
                idiom.append(word)
        return ','.join(idiom)

    def download_yzm(self):
        r = self.get_request("http://xyjg.egs.gov.cn/ECPS_HB/validateCode.jspx?type=1&_=%s" % get_cur_ts_mil())
        yzm_path = self.get_yzm_path()
        with open(yzm_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    f.flush()
            f.close()
        r = self.post_request("http://xyjg.egs.gov.cn/ECPS_HB/validateCodeCo.jspx")
        # print r.text
        word_dict = json.loads(r.text)
        word_line = ",".join(word_dict.values())
        idiom = self.permute(word_line)
        # print idiom
        return yzm_path, idiom

    def get_yzm(self):
        """
        获取验证码
        :rtype: str
        :return: 验证码识别结果
        """
        yzm_path, idiom = self.download_yzm()
        print yzm_path
        yzm = recognize(yzm_path, idiom)
        print 'answer:', yzm
        os.remove(yzm_path)
        return yzm

    def get_tag_a_from_page(self, keyword):
        self.ent_id = ''
        for i in range(10):
            yzm = self.get_yzm()
            params = {"checkNo": yzm, "entName": keyword}
            url = "http://xyjg.egs.gov.cn/ECPS_HB/searchList.jspx"
            r = self.post_request(url, params=params)
            r.encoding = 'utf-8'
            if u'验证码不正确或已失效！' not in r.text:
                print u'验证成功'
                # print r.text
                break
            if u'您搜索的条件无查询结果' in r.text:
                # print r.text
                print u'查询无结果'
                return
        if u'验证码不正确或已失效！' in r.text:
            raise ValueError(u'达到验证次数上限！')
        tree = html.fromstring(r.text)
        result_list = tree.xpath(".//div/ul/li[1]/a")
        for ent in result_list:
            ent_name = ent.text.replace('(', u'（').replace(')', u'）')
            if ent_name == keyword:
                print u'查到指定公司'
                # self.cur_mc = keyword
                tag_a = "http://xyjg.egs.gov.cn/" + ent.get("href")
                return tag_a

    def get_search_args(self, tag_a, keyword):
        self.cur_mc = keyword
        self.ent_id = re.findall('.*?id=(.*)$', tag_a)[0]
        return 1

    def get_ji_ben(self):
        family = 'Registered_Info'
        table_id = '01'

        url = "http://xyjg.egs.gov.cn/ECPS_HB/businessPublicity.jspx?id=" + self.ent_id
        r = self.get_request(url)
        r.encoding = 'utf-8'
        dengji_tree = html.fromstring(r.text)

        th_list = dengji_tree.xpath(".//*[@id='jibenxinxi']/table[1]//th")[1:]
        td_list = dengji_tree.xpath(".//*[@id='jibenxinxi']/table[1]//td")
        result_values = {}
        for i in range(len(td_list)):
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
                    self.cur_zch = val
                    if len(self.cur_zch) == 18:
                        result_values[family + ':tyshxy_code'] = self.cur_zch
                    else:
                        result_values[family + ':zch'] = self.cur_zch
                # print '*', desc, val
                if desc in ji_ben_dict:
                    desc = family + ':' + ji_ben_dict[desc]
                    if val:
                        result_values[desc] = val.strip().replace('\n', '')
        result_values['rowkey'] = '%s_%s_%s_' % (self.cur_mc, table_id, self.cur_zch)
        result_values[family + ':registrationno'] = self.cur_zch
        result_values[family + ':enterprisename'] = self.cur_mc
        result_values[family + ':province'] = u'湖北省'
        result_values[family + ':lastupdatetime'] = get_cur_time()
        self.json_result[family] = [result_values]
        # print json.dumps(self.json_result, ensure_ascii=False)

    def get_gu_dong(self):
        family = 'Shareholder_Info'
        table_id = '04'
        result_list = []
        result_values = dict()
        j = 1
        text_list = []
        print u'股东信息'
        # self.json_result[family] = []
        for num in range(1, 100):
            url = 'http://xyjg.egs.gov.cn/ECPS_HB/QueryInvList.jspx?pno=%d&mainId=%s' % (num, self.ent_id)
            r = self.get_request(url)
            r.encoding = 'utf-8'
            # print r.text
            shareholder_table = html.fromstring(r.text)
            th_list = [u'股东（发起人）', u'证照/证件类型', u'证照/证件号码', u'股东（发起人）类型', u'详情']
            tr_list = shareholder_table.xpath("table/tr")
            if tr_list:
                judge_anchor = shareholder_table.xpath("table/tr[1]/td[1]")[0].text  # 如果和之前请求结果相同，结束查询
                if judge_anchor in text_list:
                    break
                text_list.append(judge_anchor)
                for tr in tr_list:
                    td_list = tr.xpath("td")
                    for i in range(5):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th
                        if td.xpath("a"):
                            # print u'查看股东详情'
                            val = "http://xyjg.egs.gov.cn" + td.xpath("a")[0].get("onclick")[13:-2]
                            gu_dong_detail = self.get_gu_dong_detail(val)
                            for detail_key in gu_dong_detail:
                                result_values[family + ":" + gu_dong_dict[detail_key]] = gu_dong_detail[detail_key]
                        else:
                            val = td.text
                        if desc in gu_dong_dict:
                            if val:
                                result_values[family + ":" + gu_dong_dict[desc]] = val
                    result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                    result_values[family + ':registrationno'] = self.cur_zch
                    result_values[family + ':enterprisename'] = self.cur_mc
                    result_values[family + ':id'] = j
                    result_list.append(result_values)
                    result_values = {}
                    j += 1
        self.json_result[family] = result_list
        # print json.dumps(self.json_result, ensure_ascii=False)

    def get_gu_dong_detail(self, url):
        r = self.get_request(url)
        r.encoding = 'utf-8'
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
        # print json.dumps(values,ensure_ascii=False)
        return values

    def get_bian_geng(self):
        print u'查询变更信息'
        family = 'Changed_Announcement'
        table_id = '05'
        result_list = []
        result_values = dict()
        j = 1
        text_list = []
        # self.json_result[family] = []
        for num in range(1, 100):
            url = 'http://xyjg.egs.gov.cn/ECPS_HB/QueryAltList.jspx?pno=%d&mainId=%s' % (num, self.ent_id)
            r = self.get_request(url)
            r.encoding = 'utf-8'
            alt_table = html.fromstring(r.text)
            th_list = [u'变更事项', u'变更前内容', u'变更后内容', u'变更日期']
            tr_list = alt_table.xpath("table/tr")
            if tr_list:
                judge_anchor = alt_table.xpath("table/tr[1]/td[2]")[0].text
                if judge_anchor in text_list:
                    break
                text_list.append(judge_anchor)
                for tr in tr_list:
                    td_list = tr.xpath("td")
                    for i in range(4):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th
                        # if td.xpath("a"):
                        #     # print u'查看股东详情'
                        #     val = "http://www.szcredit.com.cn/web/GSZJGSPT/" + td.xpath("a")[0].get("onclick")[13:-2]
                        #     gu_dong_detail = self.get_gu_dong_detail(val)
                        #     for detail_key in gu_dong_detail:
                        #         result_values[family + ":" + gu_dong_dict[detail_key]] = gu_dong_detail[detail_key]
                        # else:
                        val = td.text
                        if desc in bian_geng_dict and val:
                            result_values[family + ":" + bian_geng_dict[desc]] = val
                    result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                    result_values[family + ':registrationno'] = self.cur_zch
                    result_values[family + ':enterprisename'] = self.cur_mc
                    result_values[family + ':id'] = j
                    result_list.append(result_values)
                    result_values = {}
                    j += 1
            if len(tr_list) < 5:
                break
        self.json_result[family] = result_list
        # print json.dumps(self.json_result, ensure_ascii=False)

    def get_zhu_yao_ren_yuan(self):
        print u'主要人员信息'
        family = 'KeyPerson_Info'
        table_id = '06'
        result_list = []
        result_values = dict()
        j = 1
        text_list = []
        # self.json_result[family] = []
        for num in range(1, 100):
            url = 'http://xyjg.egs.gov.cn/ECPS_HB/QueryMemList.jspx?pno=%d&mainId=%s' % (num, self.ent_id)
            r = self.get_request(url)
            r.encoding = 'utf-8'
            mem_table = html.fromstring(r.text)

            # print judge_anchor
            th_list = [u'序号', u'姓名', u'职务', u'序号', u'姓名', u'职务']
            tr_list = mem_table.xpath("table/tr")
            if tr_list:
                judge_anchor = mem_table.xpath("table/tr[1]/td[2]")[0].text
                if judge_anchor in text_list:
                    break
                text_list.append(judge_anchor)
                for tr in tr_list:
                    td_list = tr.xpath("td")
                    for i in range(6):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th
                        val = td.text
                        if desc in zhu_yao_ren_yuan_dict:
                            result_values[family + ":" + zhu_yao_ren_yuan_dict[desc]] = val
                        if len(result_values) == 3:
                            result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                            result_values[family + ':registrationno'] = self.cur_zch
                            result_values[family + ':enterprisename'] = self.cur_mc
                            result_values[family + ':id'] = j
                            if result_values[family + ":" + zhu_yao_ren_yuan_dict[u'姓名']]:
                                result_list.append(result_values)
                            result_values = {}
                            j += 1
            if len(tr_list) < 5:
                break
        self.json_result[family] = result_list
        # print json.dumps(self.json_result, ensure_ascii=False)

    def get_fen_zhi_ji_gou(self):
        print u'查询分支机构'
        family = 'Branches'
        table_id = '08'
        result_list = []
        result_values = dict()
        j = 1
        text_list = []
        # self.json_result[family] = []
        for num in range(1, 100):
            url = 'http://xyjg.egs.gov.cn/ECPS_HB/QueryChildList.jspx?pno=%d&mainId=%s' % (num, self.ent_id)
            r = self.get_request(url)
            r.encoding = 'utf-8'
            # print r.text
            branches_table = html.fromstring(r.text)

            # print judge_anchor
            th_list = [u'序号', u'注册号/统一社会信用代码', u'名称', u'登记机关']
            tr_list = branches_table.xpath("table/tr")
            if tr_list:
                judge_anchor = branches_table.xpath("table/tr[1]/td[3]")[0].text  # 如果和之前请求结果相同，结束查询
                if judge_anchor in text_list:
                    break
                text_list.append(judge_anchor)
                for tr in tr_list:
                    td_list = tr.xpath("td")
                    for i in range(4):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th
                        val = td.text
                        if desc in fen_zhi_ji_gou_dict and val:
                            result_values[family + ":" + fen_zhi_ji_gou_dict[desc]] = val
                    result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                    result_values[family + ':registrationno'] = self.cur_zch
                    result_values[family + ':enterprisename'] = self.cur_mc
                    result_values[family + ':id'] = j
                    result_list.append(result_values)
                    result_values = {}
                    j += 1
            if len(tr_list) < 5:
                break
        self.json_result[family] = result_list
        # print json.dumps(self.json_result, ensure_ascii=False)

    def get_qing_suan(self):
        pass

    def get_dong_chan_di_ya(self):
        print u'查询动产抵押信息'
        family = 'Chattel_Mortgage'
        table_id = '11'
        result_list = []
        result_values = dict()
        j = 1
        text_list = []
        # self.json_result[family] = []
        for num in range(1, 100):
            url = 'http://xyjg.egs.gov.cn/ECPS_HB/QueryMortList.jspx?pno=%d&mainId=%s' % (num, self.ent_id)
            r = self.get_request(url)
            r.encoding = 'utf-8'
            mortage_table = html.fromstring(r.text)
            th_list = [u'序号', u'登记编号', u'登记日期', u'登记机关', u'被担保债权数额', u'状态', u'公示日期', u'详情']
            tr_list = mortage_table.xpath("table/tr")
            if tr_list:
                judge_anchor = mortage_table.xpath("table/tr[1]/td[2]")[0].text  # 如果和之前请求结果相同，结束查询
                if judge_anchor in text_list:
                    break
                text_list.append(judge_anchor)
                for tr in tr_list:
                    td_list = tr.xpath("td")
                    for i in range(8):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th
                        val = td.text
                        if td.xpath("a"):
                            val = "http://xyjg.egs.gov.cn" + td.xpath("a")[0].get("onclick")[13:-2]
                        if desc in dong_chan_di_ya_dict and val:
                            result_values[family + ":" + dong_chan_di_ya_dict[desc]] = val
                    result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                    result_values[family + ':registrationno'] = self.cur_zch
                    result_values[family + ':enterprisename'] = self.cur_mc
                    result_values[family + ':id'] = j
                    result_list.append(result_values)
                    result_values = {}
                    j += 1
            if len(tr_list) < 5:
                break
        self.json_result[family] = result_list
        # print json.dumps(self.json_result, ensure_ascii=False)

    def get_gu_quan_chu_zhi(self):
        print u'股权出质'
        family = 'Equity_Pledge'
        table_id = '12'
        result_list = []
        result_values = dict()
        j = 1
        text_list = []
        # self.json_result[family] = []
        for num in range(1, 100):
            url = 'http://xyjg.egs.gov.cn/ECPS_HB/QueryPledgeList.jspx?pno=%d&mainId=%s' % (num, self.ent_id)
            r = self.get_request(url)
            r.encoding = 'utf-8'
            pledge_table = html.fromstring(r.text)
            th_list = [u'序号', u'登记编号', u'出质人', u'证照/证件号码（出质人）', u'出质股权数额', u'质权人', u'证照/证件号码（质权人）', u'股权出质设立登记日期',u'状态',
                       u'公示日期', u'变化情况']
            tr_list = pledge_table.xpath("table/tr")
            if tr_list:
                judge_anchor = pledge_table.xpath("table/tr[1]/td[2]")[0].text  # 如果和之前请求结果相同，结束查询
                if judge_anchor in text_list:
                    break
                text_list.append(judge_anchor)
                for tr in tr_list:
                    td_list = tr.xpath("td")
                    for i in range(11):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th
                        val = td.text
                        if td.xpath("a"):
                            val = "http://xyjg.egs.gov.cn" + td.xpath("a")[0].get("onclick")[13:-2]
                        if desc in gu_quan_chu_zhi_dict and val:
                            result_values[family + ":" + gu_quan_chu_zhi_dict[desc]] = val
                    result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                    result_values[family + ':registrationno'] = self.cur_zch
                    result_values[family + ':enterprisename'] = self.cur_mc
                    result_values[family + ':id'] = j
                    result_list.append(result_values)
                    result_values = {}
                    j += 1
            if len(tr_list) < 5:
                break
        self.json_result[family] = result_list
        # print json.dumps(self.json_result, ensure_ascii=False)

    def get_xing_zheng_chu_fa(self):
        print u'查询行政处罚信息'
        family = 'Administrative_Penalty'
        table_id = '13'
        result_list = []
        result_values = dict()
        j = 1
        text_list = []
        # self.json_result[family] = []
        for num in range(1, 100):
            url = 'http://xyjg.egs.gov.cn/ECPS_HB/QueryPunList.jspx?pno=%d&mainId=%s' % (num, self.ent_id)
            r = self.get_request(url)
            r.encoding = 'utf-8'
            penalty_table = html.fromstring(r.text)

            th_list = [u'序号', u'行政处罚决定书文号', u'违法行为类型', u'行政处罚内容', u'作出行政处罚决定机关名称', u'作出行政处罚决定日期', u'公示日期', u'详情']
            tr_list = penalty_table.xpath("table/tr")
            if tr_list:
                judge_anchor = penalty_table.xpath("table/tr[1]/td[2]")[0].text  # 如果和之前请求结果相同，结束查询
                if judge_anchor in text_list:
                    break
                text_list.append(judge_anchor)
                for tr in tr_list:
                    td_list = tr.xpath("td")
                    for i in range(8):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th
                        val = td.text
                        if td.xpath("a"):
                            val = "http://xyjg.egs.gov.cn" + td.xpath("a")[0].get("onclick")[13:-2]
                        if desc in xing_zheng_chu_fa_dict and val:
                            result_values[family + ":" + xing_zheng_chu_fa_dict[desc]] = val
                    result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                    result_values[family + ':registrationno'] = self.cur_zch
                    result_values[family + ':enterprisename'] = self.cur_mc
                    result_values[family + ':id'] = j
                    result_list.append(result_values)
                    result_values = {}
                    j += 1
            if len(tr_list) < 5:
                break
        self.json_result[family] = result_list
        # print json.dumps(self.json_result, ensure_ascii=False)

    def get_jing_ying_yi_chang(self):
        print u'查询经营异常信息'
        family = 'Business_Abnormal'
        table_id = '14'
        result_list = []
        result_values = dict()
        j = 1
        text_list = []
        # self.json_result[family] = []
        for num in range(1, 100):
            url = 'http://xyjg.egs.gov.cn/ECPS_HB/QueryExcList.jspx?pno=%d&mainId=%s' % (num, self.ent_id)
            r = self.get_request(url)
            r.encoding = 'utf-8'
            abnormal_table = html.fromstring(r.text)

            th_list = [u'序号', u'列入经营异常名录原因', u'列入日期', u'移出经营异常名录原因', u'移出日期', u'作出决定机关']
            tr_list = abnormal_table.xpath("table/tr")
            if tr_list:
                judge_anchor = abnormal_table.xpath("table/tr[1]/td[2]")[0].text  # 如果和之前请求结果相同，结束查询
                if judge_anchor in text_list:
                    break
                text_list.append(judge_anchor)
                for tr in tr_list:
                    td_list = tr.xpath("td")
                    for i in range(6):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th
                        val = td.text
                        if td.xpath("a"):
                            val = "http://xyjg.egs.gov.cn" + td.xpath("a")[0].get("onclick")[13:-2]
                        if desc in jing_ying_yi_chang_dict and val:
                            result_values[family + ":" + jing_ying_yi_chang_dict[desc]] = val
                    result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                    result_values[family + ':registrationno'] = self.cur_zch
                    result_values[family + ':enterprisename'] = self.cur_mc
                    result_values[family + ':id'] = j
                    result_list.append(result_values)
                    result_values = {}
                    j += 1
            if len(tr_list) < 5:
                break
        self.json_result[family] = result_list
        # print json.dumps(self.json_result, ensure_ascii=False)
    # http://xyjg.egs.gov.cn/ECPS_HB/QueryExcList.jspx?pno=1&mainId=AB1314B579B813C337CD29781C6F43AA&ran=0.06644298357250478

    def get_yan_zhong_wei_fa(self):
        pass

    def get_chou_cha_jian_cha(self):
        print u'查询抽查检查信息'
        family = 'Spot_Check'
        table_id = '16'
        result_list = []
        result_values = dict()
        j = 1
        text_list = []
        # self.json_result[family] = []
        for num in range(1, 100):
            url = 'http://xyjg.egs.gov.cn/ECPS_HB/QuerySpotCheckList.jspx?pno=%d&mainId=%s' % (num, self.ent_id)
            r = self.get_request(url)
            r.encoding = 'utf-8'

            spotcheck_table = html.fromstring(r.text)

            th_list = [u'序号', u'检查实施机关', u'类型', u'日期', u'结果']
            tr_list = spotcheck_table.xpath("table/tr")
            if tr_list:
                judge_anchor = spotcheck_table.xpath("table/tr[1]/td[4]")[0].text  # 如果和之前请求结果相同，结束查询
                if judge_anchor in text_list:
                    break
                text_list.append(judge_anchor)
                for tr in tr_list:
                    td_list = tr.xpath("td")
                    for i in range(5):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th
                        val = td.text
                        if td.xpath("a"):
                            val = "http://xyjg.egs.gov.cn" + td.xpath("a")[0].get("onclick")[13:-2]
                        if desc in chou_cha_jian_cha_dict and val:
                            result_values[family + ":" + chou_cha_jian_cha_dict[desc]] = val
                    result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                    result_values[family + ':registrationno'] = self.cur_zch
                    result_values[family + ':enterprisename'] = self.cur_mc
                    result_values[family + ':id'] = j
                    result_list.append(result_values)
                    result_values = {}
                    j += 1
            if len(tr_list) < 5:
                break
        self.json_result[family] = result_list
        # print json.dumps(self.json_result, ensure_ascii=False)

if __name__ == "__main__":
    # print recognize("‪D:\GsClawlerV2\hu_bei\img\80hbyzm.jpg", '舍己为人,百年树人')
    searcher = HuBeiSearcher()
    searcher.submit_search_request(u'九州通医药集团股份有限公司')
    print json.dumps(searcher.json_result, ensure_ascii=False)