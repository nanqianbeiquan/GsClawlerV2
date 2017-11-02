# coding=utf-8

import PackageTool
import requests
import os
from bs4 import BeautifulSoup
import json
import re
from JiangXiConfig import *
from requests.exceptions import RequestException
from gs.KafkaAPI import KafkaAPI
import sys
import uuid
from gs import MSSQL
import random
from gs.Searcher import Searcher
from gs.Searcher import get_args
from gs.TimeUtils import *
import subprocess
import base64


class JiangXiSearcher(Searcher):

    json_result = {}
    pattern = re.compile("\s")
    cur_mc = ''
    cur_code = ''
    # kafka = KafkaAPI("GSCrawlerTest")
    save_tag_a = True

    def __init__(self):
        super(JiangXiSearcher, self).__init__(use_proxy=False)
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:43.0) Gecko/20100101 Firefox/43.0",
                        "Host": "gsxt.jxaic.gov.cn",
                        "Accept": "*/*",
                        "Accept-Encoding": "gzip, deflate",
                        "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
                        "Connection": "keep-alive",
                        "Content-type": "application/json"}
        self. param_pripid = ''
        self.set_config()
        self.log_name = self.topic + "_" + str(uuid.uuid1())

    def set_config(self):
        self.plugin_path = os.path.join(sys.path[0], '../jiang_xi/ocr/jiangxi.bat')
        self.group = 'Crawler'  # 正式
        self.kafka = KafkaAPI("GSCrawlerResult")  # 正式
        # self.group = 'CrawlerTest'  # 测试
        # self.kafka = KafkaAPI("GSCrawlerTest")  # 测试
        self.topic = 'GsSrc36'
        self.province = u'江西省'
        self.kafka.init_producer()

    def download_yzm(self):
        image_url = 'http://gsxt.jxaic.gov.cn/warningetp/reqyzm.do'
        r = self.get_request(image_url)
        yzm_path = self.get_yzm_path()
        with open(yzm_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    f.flush()
            f.close()
        return yzm_path

    def recognize_yzm(self, validate_path):
        cmd = self.plugin_path + " " + validate_path
        # print cmd
        process = subprocess.Popen(cmd.encode('GBK', 'ignore'), stdout=subprocess.PIPE)
        process_out = process.stdout.read()
        answer = process_out.split('\r\n')[6].strip()
        # print 'answer: '+answer
        return answer

    def keyword_translate(self,inputname):
        # inputname.decode('utf-8')
        inputname = inputname.encode('utf-8')
        outputname = base64.b64encode(inputname).replace('+', 'u002B').replace('/', 'u002D').replace('=', 'u002C')
        return outputname

    def get_tag_a_from_page(self, keyword, flags=True):
        keyword_trans=self.keyword_translate(keyword)
        # print keyword_trans
        url_1 = 'http://gsxt.jxaic.gov.cn/search/queryenterpriseinfototalpage.do'
        yzm = self.get_yzm()
        params_1 = {'ename': keyword_trans, 'inputvalue': yzm, 'liketype':'qyxy'}
        r_1 = self.get_request(url=url_1,params=params_1, timeout=20)
        data_1 = json.loads(r_1.text)
        total = data_1['total']
        if total > 0:
            url = 'http://gsxt.jxaic.gov.cn/search/queryenterpriseinfoindex.do'
            params = {'ename': keyword_trans, 'liketype': 'qyxy', 'pageIndex': '0', 'pageSize': '10'}
            r = self.post_request(url=url, params=params, timeout=20)
            search_result_text = json.loads(r.text)
            search_result_list = search_result_text['data']
            if len(search_result_list) > 0:
                if flags:
                    search_result_json = search_result_list[0]
                else:
                    self.cur_mc = keyword
                    search_result_json = search_result_list[0]
            tag_a = json.dumps(search_result_json, ensure_ascii=False)
            return tag_a

    def get_search_args(self, tag_a, keyword):
        search_result_json = json.loads(tag_a)
        entname = search_result_json.get('ENTNAME', None)
        uniscid = search_result_json.get('UNISCID', None)
        # print 'uniscid',uniscid
        if entname:
            entname = entname.replace('(', u'（').replace(')', u'）')  # 公司名称括号统一转成全角
            if entname == keyword:
                pripid = search_result_json['PRIPID']
                self.param_pripid = pripid
                self.cur_mc = entname
                if uniscid:
                    self.cur_code = uniscid
                else:
                    self.cur_code = search_result_json['REGNO']
                return 1
                # print entname,pripid,self.cur_mc,self.cur_code
            elif uniscid == keyword:
                pripid = search_result_json['PRIPID']
                self.param_pripid = pripid
                self.cur_mc = uniscid
                if uniscid:
                    self.cur_code = uniscid
                else:
                    self.cur_code = search_result_json['REGNO']
                return 1
        return 0

    def parse_detail(self):
        param_pripid = self.param_pripid
        self.get_ji_ben(param_pripid)
        # print 'jb_step_json', self.json_result
        self.get_gu_dong(param_pripid)
        # print 'gd_step_json', self.json_result
        self.get_bian_geng(param_pripid)
        # print 'bg_step_json', self.json_result
        self.get_zhu_yao_ren_yuan(param_pripid)
        self.get_fen_zhi_ji_gou(param_pripid)
        # # self.get_qing_suan(kwargs)
        self.get_dong_chan_di_ya(param_pripid)
        self.get_gu_quan_chu_zhi(param_pripid)
        self.get_xing_zheng_chu_fa(param_pripid)
        self.get_jing_ying_yi_chang(param_pripid)
        self.get_yan_zhong_wei_fa(param_pripid)
        self.get_chou_cha_jian_cha(param_pripid)

    def get_ji_ben(self,param_pripid):
        self.info(u'解析基本信息...')
        family = 'Registered_Info'
        table_id = '01'
        jsonarray = []
        values = {}
        param_pripid = self.keyword_translate(param_pripid)
        # print param_pripid
        url = 'http://gsxt.jxaic.gov.cn/baseinfo/queryenterpriseinfoByRegnore.do'
        params = {'pripid': param_pripid}
        r = self.get_request(url=url, params=params)
        data = json.loads(r.text)
        values[family + ':' + 'registeredcapital'] = str(data['REGCAP'])+u'万'+data['REGCAPCUR_CN']
        # print values[family + ':' + 'registeredcapital']
        for col_desc in data:
            if col_desc in ['COMPFORM_CN', 'REGSTATE', 'ENTTYPE', 'PRIPTYPE', 'namelike', 'REGCAP', 'REGCAPCUR_CN','PRIPID']:
                continue
            elif col_desc in jiben_column_dict:
                col = family + ':' + jiben_column_dict[col_desc]
                val = data[col_desc]
                values[col] = val
            else:
                print "unknown column!", col_desc
                raise Exception("unknown column!")
        values[family + ':' + 'registrationno'] = self.cur_code
        values[family + ':' + 'province']=self.province
        values['rowkey']='%s_%s_%s_' % (self.cur_mc, table_id, self.cur_code)
        jsonarray.append(values)
        # print 'jsonarray', json.dumps(jsonarray,ensure_ascii=False)
        self.json_result[family] = jsonarray
        # print 'json_result', json.dumps(self.json_result, ensure_ascii=False)

    def get_gu_dong(self, param_pripid):
        self.info(u'解析股东信息...')
        family = 'Shareholder_Info'
        table_id = '04'
        jsonarray = []
        values_before = {}
        param_pripid = self.keyword_translate(param_pripid)
        url_1 = 'http://gsxt.jxaic.gov.cn/einvperson/queryTotalPage.do'
        params_1 = {'pripid': param_pripid}
        r_1 = self.get_request(url=url_1,params=params_1)
        data_1 = json.loads(r_1.text)
        page = data_1['totalpage']
        if page > 0:
            pagesize = data_1['totalpage']*5
            url = 'http://gsxt.jxaic.gov.cn/einvperson/getqueryeInvPersonService.do'
            params = {'pripid': param_pripid, 'pageIndex': '0', 'pageSize': pagesize}
            r = self.get_request(url=url,params=params)
            search_result_text = json.loads(r.text)
            data = search_result_text['data']
            for i in range(len(data)):
                for col_desc in data[i]:
                    invid = data[i]['INVID']
                    if col_desc in ['INVTYPE', 'INVID', 'CONDATE', 'ESTDATE', 'ALTDATE', 'RESPFORM_CN']:
                        continue
                    elif col_desc in gu_dong_dict:
                        col = family + ':' + gu_dong_dict[col_desc]
                        val = data[i][col_desc]
                        values_before[col] = val
                    else:
                        print "unknown column!",col_desc
                        raise Exception("unknown column!")
                data_detail = self.get_gu_dong_detail(invid)
                values=values_before.copy()
                values.update(data_detail)
                values['rowkey']='%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_code, self.today, i)
                values[family + ':' + 'registrationno'] = self.cur_code
                values[family + ':' + 'enterprisename'] = self.cur_mc
                # print 'values', json.dumps(values,ensure_ascii=False)
                jsonarray.append(values)
                values = {}
            # print 'gudong', json.dumps(jsonarray,ensure_ascii=False)
            self.json_result[family] = jsonarray

    def get_gu_dong_detail(self, invid):
        data_detail = {}
        family = 'Shareholder_Info'
        url_detail = 'http://gsxt.jxaic.gov.cn/einvperson/queryInfo.do'
        params_detail = {'invid': invid}
        r_detail = self.get_request(url=url_detail,params=params_detail)
        soup = BeautifulSoup(r_detail.text, 'lxml')
        h4_list = soup.find_all('h4')
        table_list = soup.find_all(class_='gd-table')
        for i in range(len(h4_list)):
            table_dec = h4_list[i].get_text().strip()
            if table_dec == u'详细信息':
                tr_list = table_list[i].find_all('tr')
                for tr in tr_list[1:]:
                    td_list = tr.find_all('td')
                    th = td_list[0].get_text().strip()
                    col = family + ':' + gu_dong_dict[th]
                    val = td_list[1].get_text().strip()
                    data_detail[col] = val
            else:
                tr_list = table_list[i].find_all('tr')
                th_element_list = tr_list[0].find_all('td')
                td_element_list = tr_list[1].find_all('td')
                if len(th_element_list) == len(td_element_list):
                    col_nums = len(th_element_list)
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n','')
                        col = family + ':' + gu_dong_dict[col_dec]
                        val = td_element_list[j].get_text().strip()
                        data_detail[col] = val
        return data_detail

    def get_bian_geng(self, param_pripid):
        self.info(u'解析变更信息...')
        family = 'Changed_Announcement'
        table_id = '05'
        jsonarray = []
        values = {}
        param_pripid = self.keyword_translate(param_pripid)
        url_1 = 'http://gsxt.jxaic.gov.cn/gtalterrecoder/queryTotalPage.do'
        params_1 = {'pripid': param_pripid}
        r_1 = self.get_request(url=url_1,params=params_1)
        data_1 = json.loads(r_1.text)
        page = data_1['totalpage']
        if page > 0:
            pagesize = data_1['totalpage']*5
            url = 'http://gsxt.jxaic.gov.cn/gtalterrecoder/getquerygtalterrecoder.do'
            params = {'pripid': param_pripid, 'pageIndex': '0', 'pageSize': pagesize}
            r = self.get_request(url=url,params=params)
            search_result_text = json.loads(r.text)
            data = search_result_text['data']
            for i in range(len(data)):
                for col_desc in data[i]:
                    if col_desc in ['ALTITEM']:
                        continue
                    elif col_desc in bian_geng_dict:
                        col = family + ':' + bian_geng_dict[col_desc]
                        val = data[i][col_desc]
                        values[col] = val
                    else:
                        print "unknown column!",col_desc
                        raise Exception("unknown column!")
                values['rowkey']='%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_code, self.today, i)
                values[family + ':' + 'registrationno'] = self.cur_code
                values[family + ':' + 'enterprisename'] = self.cur_mc
                jsonarray.append(values)
                values = {}
            self.json_result[family] = jsonarray
            # print 'biangeng', json.dumps(jsonarray,ensure_ascii=False)

    def get_zhu_yao_ren_yuan(self, param_pripid):
        self.info(u'解析主要人员信息...')
        family = 'KeyPerson_Info'
        table_id = '06'
        jsonarray = []
        values = {}
        param_pripid = self.keyword_translate(param_pripid)
        url = 'http://gsxt.jxaic.gov.cn/epriperson/queryPerson.do'
        params = {'pripid': param_pripid}
        r = self.get_request(url=url,params=params)
        data = json.loads(r.text)
        if data != []:
            for i in range(len(data)):
                for col_desc in data[i]:
                    if col_desc in zhu_yao_ren_yuan_dict:
                        col = family + ':' + zhu_yao_ren_yuan_dict[col_desc]
                        val = data[i][col_desc]
                        values[col] = val
                    else:
                        print "unknown column!",col_desc
                        raise Exception("unknown column!")
                values['rowkey']='%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_code, self.today, i)
                values[family + ':' + 'registrationno'] = self.cur_code
                values[family + ':' + 'enterprisename'] = self.cur_mc
                values[family + ':' + 'id'] = i+1
                jsonarray.append(values)
                values = {}
            self.json_result[family] = jsonarray
            # print 'zhuyaorenyuan', json.dumps(jsonarray,ensure_ascii=False)

    def get_fen_zhi_ji_gou(self, param_pripid):
        self.info(u'解析分支机构信息...')
        family = 'Branches'
        table_id = '08'
        jsonarray = []
        values = {}
        param_pripid = self.keyword_translate(param_pripid)
        url_1 = 'http://gsxt.jxaic.gov.cn/ebrchinfo/queryTotalPage.do'
        params_1 = {'pripid': param_pripid}
        r_1 = self.get_request(url=url_1,params=params_1)
        data_1 = json.loads(r_1.text)
        page = data_1['totalpage']
        if page > 0:
            pagesize = data_1['totalpage']*5
            url = 'http://gsxt.jxaic.gov.cn/ebrchinfo/getqueryEBrchinfo.do'
            params = {'pripid': param_pripid, 'pageIndex': '0', 'pageSize': pagesize}
            r = self.get_request(url=url,params=params)
            search_result_text = r.text
            start_idx = search_result_text.index('"data":') + len('"data":')
            stop_idx = search_result_text.index(']')+1
            search_result_text = search_result_text[start_idx:stop_idx]
            data = json.loads(search_result_text)
            for i in range(len(data)):
                for col_desc in data[i]:
                    if col_desc in fen_zhi_ji_gou_dict:
                        col = family + ':' + fen_zhi_ji_gou_dict[col_desc]
                        val = data[i][col_desc]
                        values[col] = val
                    else:
                        print "unknown column!",col_desc
                        raise Exception("unknown column!")
                values['rowkey']='%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_code, self.today, i)
                values[family + ':' + 'registrationno'] = self.cur_code
                values[family + ':' + 'enterprisename'] = self.cur_mc
                jsonarray.append(values)
                values = {}
            self.json_result[family] = jsonarray
            # print 'fenzhijigou', json.dumps(jsonarray,ensure_ascii=False)


    def get_qing_suan(self):
        pass

    def get_jing_ying_yi_chang(self, param_pripid):
        self.info(u'解析经营异常信息...')
        family = 'Business_Abnormal'
        table_id = '14'
        jsonarray = []
        values = {}
        param_pripid = self.keyword_translate(param_pripid)
        url_1 = 'http://gsxt.jxaic.gov.cn/opadetail/queryTotalPage.do'
        params_1 = {'pripid': param_pripid}
        r_1 = self.get_request(url=url_1, params=params_1)
        data_1 = json.loads(r_1.text)
        page = data_1['totalpage']
        if page > 0:
            pagesize = data_1['totalpage']*5
            url = 'http://gsxt.jxaic.gov.cn/opadetail/getqueryabnoperationinfo.do'
            params = {'pripid': param_pripid, 'pageIndex': '0', 'pageSize': pagesize}
            r = self.get_request(url=url,params=params)
            search_result_text = r.text
            start_idx = search_result_text.index('"data":') + len('"data":')
            stop_idx = search_result_text.index(']')+1
            search_result_text = search_result_text[start_idx:stop_idx]
            data = json.loads(search_result_text)
            for i in range(len(data)):
                for col_desc in data[i]:
                    if col_desc in jing_ying_yi_chang_dict:
                        col = family + ':' + jing_ying_yi_chang_dict[col_desc]
                        val = data[i][col_desc]
                        values[col] = val
                    else:
                        print "unknown column!",col_desc
                        raise Exception("unknown column!")
                values['rowkey']='%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_code, self.today, i)
                values[family + ':' + 'registrationno'] = self.cur_code
                values[family + ':' + 'enterprisename'] = self.cur_mc
                jsonarray.append(values)
                values = {}
            self.json_result[family] = jsonarray
            # print 'yichang', json.dumps(jsonarray,ensure_ascii=False)

    def get_dong_chan_di_ya(self, param_pripid):
        self.info(u'解析动产抵押信息...')
        family = 'Chattel_Mortgage'
        table_id = '11'
        jsonarray = []
        values = {}
        param_pripid = self.keyword_translate(param_pripid)
        url_1 = 'http://gsxt.jxaic.gov.cn/mortreginfo/queryTotalPage.do'
        params_1 = {'pripid': param_pripid}
        r_1 = self.get_request(url=url_1,params=params_1)
        data_1 = json.loads(r_1.text)
        page = data_1['totalpage']
        if page > 0:
            pagesize = data_1['totalpage']*5
            url = 'http://gsxt.jxaic.gov.cn/mortreginfo/getquerymortreginfo.do'
            params = {'pripid': param_pripid, 'pageIndex': '0', 'pageSize': pagesize}
            r = self.get_request(url=url,params=params)
            search_result_text = r.text
            start_idx = search_result_text.index('"data":') + len('"data":')
            stop_idx = search_result_text.index(']}')+1
            search_result_text = search_result_text[start_idx:stop_idx]
            data = json.loads(search_result_text)
            for i in range(len(data)):
                if 'REGCAPCUR_CN' in data[i]:
                    regcapcur = data[i]['REGCAPCUR_CN']
                for col_desc in data[i]:
                    if col_desc == 'PRIPID' or col_desc == 'REGCAPCUR_CN':
                        continue
                    elif col_desc in dong_chan_di_ya_dict:
                        col = family + ':' + dong_chan_di_ya_dict[col_desc]
                        if col_desc == 'MORREG_ID':
                            val = 'http://gsxt.jxaic.gov.cn/mortreginfo/getquerymortreginfo.do?MORREG_ID='+data[i][col_desc]
                        elif col_desc == 'PRICLASECAM':
                            val = str(data[i][col_desc]) + u'万元' + '(' + regcapcur + ')'
                        elif col_desc == 'TYPE':
                            if data[i][col_desc] == '1':
                                val = u'有效'
                            elif data[i][col_desc] == '2':
                                val = u'无效'
                        else:
                            val = data[i][col_desc]
                        values[col] = val
                    else:
                        print "unknown column!",col_desc
                        raise Exception("unknown column!")
                values['rowkey']='%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_code, self.today, i)
                values[family + ':' + 'registrationno'] = self.cur_code
                values[family + ':' + 'enterprisename'] = self.cur_mc
                jsonarray.append(values)
                values = {}
            self.json_result[family] = jsonarray
            # print 'dongchandiya', json.dumps(jsonarray,ensure_ascii=False)

    def get_gu_quan_chu_zhi(self, param_pripid):
        self.info(u'解析股权出质信息...')
        family = 'Equity_Pledge'
        table_id = '12'
        jsonarray = []
        values = {}
        param_pripid = self.keyword_translate(param_pripid)
        url_1 = 'http://gsxt.jxaic.gov.cn/esppledge/queryTotalPage.do'
        params_1 = {'pripid': param_pripid}
        r_1 = self.get_request(url=url_1,params=params_1)
        data_1 = json.loads(r_1.text)
        page = data_1['totalpage']
        if page > 0:
            pagesize = data_1['totalpage']*5
            url = 'http://gsxt.jxaic.gov.cn/esppledge/queryEsppledge.do'
            params = {'pripid': param_pripid, 'pageIndex': '0', 'pageSize': pagesize}
            r = self.get_request(url=url,params=params)
            search_result_text = r.text
            start_idx = search_result_text.index('"data":') + len('"data":')
            stop_idx = search_result_text.index(']}')+1
            search_result_text = search_result_text[start_idx:stop_idx]
            data = json.loads(search_result_text)
            for i in range(len(data)):
                for col_desc in data[i]:
                    if col_desc == 'PLEDBLICTYPE_CN':
                        continue
                    elif col_desc in gu_quan_chu_zhi_dict:
                        col = family + ':' + gu_quan_chu_zhi_dict[col_desc]
                        if col_desc == 'IMPORGID':
                            val = 'http://gsxt.jxaic.gov.cn/esppledge/queryEsppledgeinfo.do?IMPORGID='+data[i][col_desc]
                        elif col_desc == 'TYPE':
                            if data[i][col_desc] == '1':
                                val = u'有效'
                            elif data[i][col_desc] == '2':
                                val = u'无效'
                        else:
                            val = data[i][col_desc]
                        values[col] = val
                    else:
                        print "unknown column!",col_desc
                        raise Exception("unknown column!")
                values['rowkey']='%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_code, self.today, i)
                values[family + ':' + 'registrationno'] = self.cur_code
                values[family + ':' + 'enterprisename'] = self.cur_mc
                jsonarray.append(values)
                values = {}
            self.json_result[family] = jsonarray
            # print 'guquanchuzhi', json.dumps(jsonarray,ensure_ascii=False)

    def get_xing_zheng_chu_fa(self, param_pripid):
        self.info(u'解析行政处罚信息...')
        family = 'Administrative_Penalty'
        table_id = '13'
        jsonarray = []
        values = {}
        param_pripid = self.keyword_translate(param_pripid)
        url_1 = 'http://gsxt.jxaic.gov.cn/casepubbaseinfo/queryTotalPage.do'
        params_1 = {'pripid': param_pripid}
        r_1 = self.get_request(url=url_1,params=params_1)
        data_1 = json.loads(r_1.text)
        page = data_1['totalpage']
        if page > 0:
            pagesize = data_1['totalpage']*5
            url = 'http://gsxt.jxaic.gov.cn/casepubbaseinfo/queryCasepubbaseinfo.do'
            params = {'pripid': param_pripid, 'pageIndex': '0', 'pageSize': pagesize}
            r = self.get_request(url=url,params=params)
            search_result_text = r.text
            # start_idx = search_result_text.index('"data":') + len('"data":')
            # stop_idx = search_result_text.index(']')+1
            # search_result_text = search_result_text[start_idx:stop_idx]
            data = json.loads(search_result_text)['data']
            for i in range(len(data)):
                for col_desc in data[i]:
                    if col_desc in ('PENTYPE_CN','PRIPID', 'REMARK','BGJDZL','BGRQ','BGCBJG','BGXZCF'):
                        continue
                    elif col_desc in xing_zheng_chu_fa_dict:
                        col = family + ':' + xing_zheng_chu_fa_dict[col_desc]
                        if col_desc == 'CASEID':
                            val = 'http://gsxt.jxaic.gov.cn/casepubbaseinfo/querycaseinfomessage.do?caseid='+data[i][col_desc]
                        else:
                            val = data[i][col_desc]
                        values[col] = val
                    else:
                        print "unknown column!",col_desc
                        raise Exception("unknown column!")
                values['rowkey']='%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_code, self.today, i)
                values[family + ':' + 'registrationno'] = self.cur_code
                values[family + ':' + 'enterprisename'] = self.cur_mc
                jsonarray.append(values)
                values = {}
            self.json_result[family] = jsonarray
            # print 'xingzhengchufa', json.dumps(jsonarray,ensure_ascii=False)

    def get_yan_zhong_wei_fa(self, param_pripid):
        """
        获取严重违法信息
        :param kwargs: 查询参数
        :return:
        """
        pass

    def get_chou_cha_jian_cha(self, param_pripid):
        self.info(u'解析抽查检查信息...')
        family = 'Spot_Check'
        table_id = '16'
        jsonarray = []
        values = {}
        param_pripid = self.keyword_translate(param_pripid)
        url_1 = 'http://gsxt.jxaic.gov.cn/epubspotcheck/queryTotalPage.do'
        params_1 = {'pripid': param_pripid}
        r_1 = self.get_request(url=url_1,params=params_1)
        data_1 = json.loads(r_1.text)
        page = data_1['totalpage']
        if page > 0:
            pagesize = data_1['totalpage']*5
            url = 'http://gsxt.jxaic.gov.cn/epubspotcheck/queryEpubspotcheck.do'
            params = {'pripid': param_pripid, 'pageIndex': '0', 'pageSize': pagesize}
            r = self.get_request(url=url,params=params)
            search_result_text = r.text
            start_idx = search_result_text.index('"data":') + len('"data":')
            stop_idx = search_result_text.index(']')+1
            search_result_text = search_result_text[start_idx:stop_idx]
            data = json.loads(search_result_text)
            for i in range(len(data)):
                for col_desc in data[i]:
                    if col_desc in chou_cha_jian_cha_dict:
                        col = family + ':' + chou_cha_jian_cha_dict[col_desc]
                        if col_desc == 'INSTYPE':
                            inslist = data[i][col_desc].split(', ')
                            ins = []
                            for key in inslist:
                                if key == u'1':
                                    key= u'即时信息定向'
                                elif key == u'2':
                                    key= u'即时信息不定向'
                                elif key == u'3':
                                    key= u'年报不定向'
                                elif key == u'4':
                                    key= u'年报定向'
                                elif key == u'5':
                                    key= u'专项'
                                ins.append(key)
                            val = ','.join(ins)
                        else:
                            val = data[i][col_desc]
                        values[col] = val
                    else:
                        print "unknown column!",col_desc
                        raise Exception("unknown column!")
                values['rowkey']='%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_code, self.today, i)
                values[family + ':' + 'registrationno'] = self.cur_code
                values[family + ':' + 'enterprisename'] = self.cur_mc
                jsonarray.append(values)
                values = {}
            self.json_result[family] = jsonarray
            # print 'choucha', json.dumps(jsonarray,ensure_ascii=False)

    def get_nian_bao_link(self, param_pripid):
        """
        获取年报信息
        :param kwargs: 查询参数
        :return:
        """
        pass

if __name__ == '__main__':
    args_dict = get_args()
    searcher = JiangXiSearcher()
    # searcher.delete_tag_a_from_db(u'吉安市中才生物科技有限公司')
    searcher.submit_search_request(u'抚州市临川区银河大酒店有限公司')
    # searcher.submit_search_request('913608235560009541', False)
    # searcher.submit_search_request(keyword=args_dict['companyName'], account_id=args_dict['accountId'], task_id=args_dict['taskId'])
    # print json.dumps(searcher.json_result, ensure_ascii=False)
