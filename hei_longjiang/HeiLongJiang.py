# coding=utf-8

import requests
import os
import uuid
import PackageTool
from PIL import Image
from bs4 import BeautifulSoup
import json
import re
from gs.KafkaAPI import KafkaAPI
import datetime
from requests.exceptions import RequestException
import sys
import subprocess
import time
from Tables_dict import *
from gs.Searcher import Searcher
from gs.Searcher import get_args

from gs.ProxyConf import *
from gs.TimeUtils import *


class HeiLongJiang(Searcher):

    json_result = {}
    pattern = re.compile("\s")
    save_tag_a = True
    lock_id = 0
    cur_time = None

    cur_mc = None
    cur_zch = None
    entName = None
    entId = None
    entNo = None
    creditt = None
    credit_ticket = None
    iframe_src = {}

    def __init__(self):
        super(HeiLongJiang, self).__init__(use_proxy=True)
        # self.session = requests.session()
        # self.session.proxies = {'http': '123.56.238.200:8123', 'https': '123.56.238.200:8123'}
        # self.session.proxies = {'http': '121.28.134.29:80'}

        self.headers = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Encoding": "gzip, deflate",
                        "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
                        "Connection": "keep-alive",
                        "Content-type": "application/x-www-form-urlencoded",
                        "Host": "222.171.236.78:9080",
                        "Referer": "http://222.171.236.78:9080/search.jspx",
                        "User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0"
                        }
        # self.cur_time = '%d' % (time.time() * 1000)
        self.get_credit_ticket()
        self.json_result = {}  # json输出结果
        self.iframe_name = {'qyjbqk': u'基本信息', 'tzrczxx': u'股东信息', 'qybgxx': u'变更信息',
                           'qybaxxzyryxx': u'主要人员信息', 'qybaxxfgsxx': u'分支机构信息', 'qybaxxqsxx': u'清算信息',
                            'gqczxx': u'股权出质登记信息', 'dcdyxx': u'动产抵押登记信息', 'jyycxx':u'经营异常信息',
                            'yzwfxx': u'严重违法信息', 'xzcfxx': u'行政处罚信息', 'ccjcxx':u'抽查检查信息'}
        self.domain = 'http://222.171.236.78:9080'
        self.set_config()
        self.log_name = self.topic + "_" + str(uuid.uuid1())

    def set_config(self):
        self.plugin_path = sys.path[0] + r'\..\hei_longjiang\ocr\beijing.bat'
        self.group = 'Crawler'  # 正式
        self.kafka = KafkaAPI("GSCrawlerResult")  # 正式
        # self.group = 'CrawlerTest'  # 测试
        # self.kafka = KafkaAPI("GSCrawlerTest")  # 测试
        self.topic = 'GsSrc23'
        self.province = u'黑龙江省'
        self.kafka.init_producer()

    def download_yzm(self):
        # self.lock_id = self.proxy_config.get_lock_id()
        self.cur_time = '%d' % (time.time() * 1000)
        params = {'currentTimeMillis': self.cur_time}
        # image_url = 'http://qyxy.baic.gov.cn/CheckCodeCaptcha'
        image_url = "http://222.171.236.78:9080/validateCode.jspx?type=0"
        r = self.get_request(url=image_url, params={})
        # print r.headers
        # yzm_path = os.path.join(sys.path[0], str(random.random())[2:]+'.jpg')
        yzm_path = self.get_yzm_path()
        with open(yzm_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    f.flush()
            f.close()
        return yzm_path

    def get_credit_ticket(self):
        # r = self.get_request('http://qyxy.baic.gov.cn/gjjbj/gjjQueryCreditAction!toIndex.dhtml')
        # print 'credit_headers',r.headers
        # soup = BeautifulSoup(r.text, 'lxml')
        # # print soup
        # self.credit_ticket = soup.select('input#credit_ticket')[0].attrs['value']
        pass

    def get_tag_a_from_db(self, keyword):
        return None

    def save_tag_a_to_db(self, keyword):
        pass

    def get_the_mc_or_code(self, keyword):
        if keyword:
            if len(keyword) == 15 or len(keyword) == 18:
                cnt = 0
                for i in keyword:
                    if i in 'abcdefghijklmnopqrstuvwxyz1234567890':
                        cnt += 1
                if cnt > 10:
                    return False
            else:
                return True
        else:
            self.info(u'输入keyword有误')
            return True

    def get_tag_a_from_page(self, keyword, flags=0):
        return self.get_tag_a_from_page0(keyword)

    def get_tag_a_from_page0(self, keyword):
        self.flag = self.get_the_mc_or_code(keyword)
        for t in range(50):
            time.sleep(1)
            # print u'验证码识别中...第%s次' %(t+1)
            self.info(u'验证码识别中...第%s次' %(t+1))
            self.today = str(datetime.date.today()).replace('-', '')
            yzm = self.get_yzm()
            # print 'yzm', yzm
            url = 'http://222.171.236.78:9080/searchList.jspx'
            params = {'checkNo': yzm, 'entName': keyword}
            # print 'params:', params
            r = self.post_request(url=url, data=params)
            # print 'r.headers',r.headers
            r.encoding = 'utf-8'
            # print '**************************', r.text
            soup = BeautifulSoup(r.text, 'html5lib')
            # print 'soup:',soup
            # print '*******cpn_request_ok?:', soup.select('.list')[0], 'next_siblings', soup.select('.list')[0].find_next_sibling()
            # tgr = soup.find(id='alert_win').find(id='MzImgExpPwd').get('alt')
            # print '*************', soup.find(class_='list')
            if u'您搜索的条件无查询结果' in soup.text:
                # print u'***验证码识别通过***no_result***'
                self.info(u'***验证码识别通过***no_result***')
                return None
            if soup.find(class_='list'):
                # print 'r.headers', r.headers
                # print u'**********验证码识别通过***heilongjiang*********'  #, soup.find(class_='list')
                self.info(u'**********验证码识别通过***heilongjiang*********')
                # if False:
                cp_list = []
                cp_two = []
                div_list = soup.select('.list')
                #  新增保存类似关键词的其它公司名称
                if len(div_list) > 1:
                    for nm in div_list:
                        name = nm.find('a').text.strip().replace('(', u'（').replace(')', u'）')
                        cp_list.append(name)

                    if len(cp_list) > 0:
                        # print u'去重前', cp_list
                        [cp_two.append(p) for p in cp_list if not p in cp_two]  # 去重
                        # print u'其它公司名', cp_two
                        if len(cp_two) > 1:
                            for mc in cp_two:
                                # print '**', mc
                                self.save_company_name_to_db(mc)
                if soup.find(class_='list').text.strip() != '':
                    return soup.select('.list')[0]
                else:
                    return None
        self.info(u'验证码验证失败')
        raise

    # def save_mc_a_to_db(self, mc):
    #     """
    #     将查询衍生出的公司名称存入数据库
    #     :param mc: 公司名称
    #     :return:
    #     """
    #     sql = "insert into %s(mc,update_status,last_update_time,province) values ('%s',-1,getdate(),'%s')" \
    #           % (self.topic, mc, self.province)
    #     print sql
    #     try:
    #         MSSQL.execute_update(sql)
    #     except pyodbc.IntegrityError:
    #         pass

    def get_search_args(self, tag_a, keyword):
        # print 'tag_a',tag_a  #不是连接地址tagA
        name = tag_a.find('a').text    # name为公司查询结果名；keyword为查询前数据库公司名
        name_link = tag_a.find('a').get('href')
        mainID = re.search(r'(?<=id=).*',name_link).group()
        code = tag_a.find_all('span')[0].text    # 注册号
        tagA = self.domain + name_link  # 验证码通过后链接地址

        self.mainID = mainID  # 黑龙江有分页情况可能用到
        self.cur_mc = name.replace('(', u'（').replace(')', u'）')
        self.cur_zch = code
        self.tagA = tagA  # 宁夏三大参数，公司名称name，注册号code， 跳过验证码的地址tagA

        self.xydm_if = ''
        self.zch_if = ''
        if len(code) == 18:
            self.xydm_if = code
        else:
            self.zch_if = code
        # print u'公司名(name)cur_mc: %s, 注册号(code)cur_zch: %s, 链接地址tagA: %s' % (name, code, tagA), 'mainID:', mainID
        if self.flag:
            if self.cur_mc == keyword:
                return 1
            else:
                self.save_company_name_to_db(self.cur_mc)
                return 0
        else:
            self.info(self.cur_mc)
            return 1

    def parse_detail(self):
        """
        解析公司详情信息
        :param kwargs:
        :return:
        """
        # print '****************HIHI************************'
        r = self.get_request(self.tagA)
        # print r.text
        bs = BeautifulSoup(r.text, 'html5lib')
        bd = bs.find(class_='dConBox')
        # print '#hei_long_soup',  bd, '**'

        # print '&&&&&&&&&&&&&&&&&&&&&&&', len(bs.select('#dConBox div iframe')), bs.select('#dConBox div iframe')
        self.get_ji_ben(bd)
        # print 'jb_step_json', self.json_result
        self.get_gu_dong(bd)
        # print 'gd_step_json', self.json_result
        self.get_bian_geng(bd)
        # print 'bg_step_json', self.json_result
        self.get_zhu_yao_ren_yuan(bd)
        self.get_fen_zhi_ji_gou(bd)
        self.get_qing_suan(bd)
        self.get_dong_chan_di_ya(bd)
        self.get_gu_quan_chu_zhi(bd)
        self.get_xing_zheng_chu_fa(bd)
        self.get_jing_ying_yi_chang(bd)
        self.get_yan_zhong_wei_fa(bd)
        self.get_chou_cha_jian_cha(bd)
        # print 'the_last_json_result', len(self.json_result), self.json_result

        json_go = json.dumps(self.json_result, ensure_ascii=False)
        # print 'the_last_json_result:', len(self.json_result), get_cur_time(),  json_go

    def get_ji_ben(self, bd):
        """
        查询基本信息
        :return: 基本信息结果
        """
        json_list = []
        family = 'Registered_Info'
        table_id = '01'
        self.json_result[family] = []
        # url = self.iframe_src['qyjbqk']
        # # print 'jiben_url', url
        # r = self.get_request(url=url, params={})
        # # r.encoding = 'gbk'
        # r.encoding = 'utf-8'
        # soup = BeautifulSoup(r.text, 'html5lib')
        soup = bd
        # print '*******ji_ben*******', soup
        tr_element_list = soup.find(class_='detailsList').find_all('tr')#(".//*[@id='jbxx']/table/tbody/tr")
        values = {}
        for tr_element in tr_element_list[1:]:
            th_element_list = tr_element.find_all('th')
            td_element_list = tr_element.find_all('td')
            if len(th_element_list) == len(td_element_list):
                col_nums = len(th_element_list)
                for i in range(col_nums):
                    col_dec = th_element_list[i].text.strip()
                    val = td_element_list[i].text.strip()
                    if col_dec != u'':
                        col = jiben_column_dict[col_dec]
                        values[col] = val
        values['rowkey'] = '%s_%s_%s_' % (self.cur_mc, table_id, self.cur_zch)
        values[family + ':registrationno'] = self.cur_zch
        values[family + ':enterprisename'] = self.cur_mc
        values[family + ':tyshxy_code'] = self.xydm_if
        values[family + ':zch'] = self.zch_if
        values[family + ':lastupdatetime'] = get_cur_time()
        values[family + ':province'] = u'黑龙江省'
        json_list.append(values)
        self.json_result[family] = json_list
        # print 'jiben_values', values

    def get_gu_dong(self, aa):
        """
        查询股东信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Shareholder_Info'
        table_id = '04'
        # self.json_result[family] = []
        json_list = []
        json_dict = {}
        soup = aa
        try:
            url = soup.find(id='invDiv').text  # 此处url不是连接地址，是判断内容是否为空的参数
        except:
            url = ''
        # print 'gudong_url', self.cur_time,url
        if url:
            soup = aa.find(id='invDiv')
            # print '*******gudong*******', soup
            # print 'gu_dong_turn_page', turn_page
            # print 'body_tr',len(soup.select('#table2 tr a')),soup.select('#table2 tr a')
            # print 'gd_tr1',soup.select('#tr1')

            gd_th = aa.find(id='invDiv').find_previous_sibling().find_all('tr')[1].find_all('th')
            iftr = soup.find_all('tr')
            if len(iftr) > 0:
                cnt = 1
                thn = len(gd_th)
                if thn == 4:
                    family = 'Partner_Info'
                elif thn == 6:
                    family = 'DIC_Info'
                elif thn == 2:
                    family = 'Investor_Info'
                else:
                    family = 'Shareholder_Info'
                # print 'len(th):', thn
                for i in range(len(iftr)):
                    gd_td = iftr[i].find_all('td')
                    for j in range(len(gd_th)):
                        th = gd_th[j].text.strip()
                        td = gd_td[j].text.strip()
                        if td == u'详情':
                            td = gd_td[j].a.get('onclick')
                            # print 'gudong', td
                            td = re.search(r'(?<=[(]).*(?=[)])', td).group().strip("'")
                            detail_url = self.domain+td
                            # print 'detail_url', detail_url
                            td = detail_url
                            self.get_gu_dong_detail(detail_url, json_dict)
                            # self.load_func(td)  抓取详情页内容方法，见cnt分页内容
                        if thn == 4:
                            json_dict[hehuoren_column_dict[th]] = td
                        elif thn == 6:
                            json_dict[DICInfo_column_dict[th]] = td
                        elif thn == 2:
                            json_dict[touziren_column_dict[th]] = td
                        else:
                            json_dict[gudong_column_dict[th]] = td
                    json_dict['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, cnt)
                    json_dict[family + ':registrationno'] = self.cur_zch
                    json_dict[family + ':enterprisename'] = self.cur_mc
                    json_dict[family + ':id'] = str(cnt)
                    json_list.append(json_dict)
                    json_dict = {}
                    cnt += 1

                turn_page = len(aa.find(id='invDiv').find_next_sibling().find_all('a'))    #判断是否有分页，需要post分页地址，暂不处理
                # print 'len_gudong_page', turn_page
                # 股东分页情况处理
                if turn_page > 1:
                    for p in range(2, turn_page+1):
                        link = 'http://222.171.236.78:9080/QueryInvList.jspx?pno='+str(p)+'&mainId='+self.mainID
                        # print '***********gudongfenyelink******************', link
                        url = link
                        r = self.get_request(url=url, params={})
                        # r.encoding = 'gbk'
                        soup = BeautifulSoup(r.text, 'html5lib')
                        # print '*******gudong**fenye*****',soup
                        # gd_th = soup.find_all(class_='detailsList')[0].find_all('tr')[1].find_all('th')
                        iftr = soup.find_all(class_='detailsList')[0].find_all('tr')
                        for i in range(len(iftr)):
                            gd_td = iftr[i].find_all('td')
                            for j in range(len(gd_th)):
                                th = gd_th[j].text.strip()
                                td = gd_td[j].text.strip()
                                if td == u'详情':
                                    td = gd_td[j].a.get('onclick')
                                    # print 'gudong', td
                                    td = re.search(r'(?<=[(]).*(?=[)])', td).group().strip("'")
                                    detail_url = self.domain+td
                                    # print 'detail_url', detail_url
                                    td = detail_url
                                    self.get_gu_dong_detail(detail_url, json_dict)
                                    # self.load_func(td)  抓取详情页内容方法，见cnt分页内容
                                if thn == 4:
                                    json_dict[hehuoren_column_dict[th]] = td
                                elif thn == 6:
                                    json_dict[DICInfo_column_dict[th]] = td
                                elif thn == 2:
                                    json_dict[touziren_column_dict[th]] = td
                                else:
                                    json_dict[gudong_column_dict[th]] = td

                            json_dict['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, cnt)
                            json_dict[family + ':registrationno'] = self.cur_zch
                            json_dict[family + ':enterprisename'] = self.cur_mc
                            json_dict[family + ':id'] = str(cnt)
                            json_list.append(json_dict)
                            json_dict = {}
                            cnt += 1

                self.json_result[family] = json_list
                # print '-,-**gudong_json_list', len(json_list), json_list

    def get_gu_dong_detail(self, url, values):
        """
        查询股东详情
        :param param_pripid:
        :param param_invid:
        :return:
        """
        family = 'Shareholder_Info'
        table_id = '04'
        # print 'gudong_detail_url',url
        r = self.get_request(url=url, params={})
        # r.encoding = 'gbk'
        soup = BeautifulSoup(r.text, 'html5lib')
        # print '***__****gudong_detail*******',soup

        detail_tr_list = soup.find(class_='detailsList').find_all('tr')
        detail_th_list = ['subscripted_capital','actualpaid_capital','subscripted_method','subscripted_amount','subscripted_time','actualpaid_method','actualpaid_amount','actualpaid_time']
        detail_th_new_list = [family+':'+x for x in detail_th_list]
        # print 'detail_th_new_list', detail_th_new_list
        for tr_ele in detail_tr_list[3:]:
            td_ele_list = tr_ele.find_all('td')[1:]
            detail_col_nums = len(td_ele_list)
            # print detail_col_nums
            for m in range(detail_col_nums):
                col = detail_th_new_list[m]
                td = td_ele_list[m]
                val = td.text.strip()
                values[col] = val
        #         print col,val
        # print 'gdl_values',len(values),values

    def get_bian_geng(self, cc):
        """
        查询变更信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Changed_Announcement'
        table_id = '05'
        # self.json_result[family] = []
        json_list = []
        json_dict = {}
        soup = cc
        # print '*******biangeng*******',soup
        try:
            url = soup.find(id='altDiv').text
        except:
            url = ''

        if url:
            gd_th = cc.find(id='altDiv').find_previous_sibling().find_all('tr')[1].find_all('th')
            # print 'th_previous',cc.find(id='altDiv').find_previous_sibling().text
            iftr = cc.find(id='altDiv').find_all('tr')

            if len(iftr) > 0:
                cnt = 1
                for i in range(len(iftr)):
                    gd_td = iftr[i].find_all('td')
                    for j in range(len(gd_th)):
                        th = gd_th[j].text.strip()
                        td = gd_td[j].text.strip()
                        # print i,j,th,td
                        json_dict[biangeng_column_dict[th]] = td
                    json_dict['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, cnt)
                    json_dict[family + ':registrationno'] = self.cur_zch
                    json_dict[family + ':enterprisename'] = self.cur_mc
                    json_dict[family + ':id'] = str(cnt)
                    json_list.append(json_dict)
                    json_dict = {}
                    cnt += 1

                try:
                    turn_page = len(cc.find(id='altDiv').find_next_sibling().find_all('a'))    # 判断是否有分页
                except:
                    turn_page = 0
                if turn_page > 1:
                    # print 'biangeng_page_splitter***************'
                    for p in range(2, turn_page+1):
                        bgurl = 'http://222.171.236.78:9080/QueryAltList.jspx?pno='+str(p)+'&mainId='+self.mainID
                        # print 'biangeng_fen_ye_link', bgurl
                        rc = self.get_request(url=bgurl)
                        soup = BeautifulSoup(rc.text,'lxml')
                        # print 'biangeng_turn_soup', soup

                        # gd_th = soup.find_all(class_='detailsList')[0].find_all('tr')[1].find_all('th')
                        iftr = soup.find_all(class_='detailsList')[0].find_all('tr')
                        for i in range(len(iftr)):
                            gd_td = soup.find_all(class_='detailsList')[0].find_all('tr')[i].find_all('td')
                            for j in range(len(gd_th)):
                                th = gd_th[j].text.strip()
                                td = gd_td[j].text.strip()
                                # print i,j,th,td
                                json_dict[biangeng_column_dict[th]] = td
                            # print '****************json_dict',json_dict
                            json_dict['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, cnt)
                            json_dict[family + ':registrationno'] = self.cur_zch
                            json_dict[family + ':enterprisename'] = self.cur_mc
                            json_dict[family + ':id'] = str(cnt)
                            json_list.append(json_dict)
                            json_dict = {}
                            cnt += 1
                self.json_result[family] = json_list
                # print '-,-**biangeng_json_list****', len(json_list), json_list

    def get_detail(self, sop):  # 北京变更详情专用, 其他省份暂时无用
        row_data = []
        # tables=self.driver.find_elements_by_xpath("//*[@id='tableIdStyle']/tbody")
        tables=sop.find_all(id='tableIdStyle')
        for t in tables:
            time.sleep(1)
            trs = t.find_all("tr")
            bt = trs[0].text
            ths = trs[1].find_all("th")
            for tr in trs[2:]:
                tds = tr.find_all("td")
                col_nums = len(ths)
                for j in range(col_nums):
                    col = ths[j].text.strip().replace('\n','')
                    td = tds[j]
                    val = td.text.strip()
                    row = col+u'：'+val
#                     print 'row',row
                    row_data.append(row)
            if u'变更前' in bt:
                self.bgq = u'；'.join(row_data)
                # print 'bgq',self.bgq
            elif u'变更后' in bt:
                self.bgh = u'；'.join(row_data)
                # print 'bgh',self.bgh
            row_data = []

    def get_zhu_yao_ren_yuan(self, zz):
        """
        查询主要人员信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'KeyPerson_Info'
        table_id = '06'
        # self.json_result[family] = []
        json_list = []
        values = {}
        soup = zz
        try:
            url = soup.find(id='memDiv').text
        except:
            url = ''
        # print 'zhuyaorenyuan_url',self.cur_time,url
        if url:
            soup = zz.find(id='beian')

            # print '*******zhuyaorenyuan*******',soup

            iftr = soup.find(id='memDiv').find_all('tr')
            gd_th = soup.find(id='memDiv').find_previous_sibling().find_all('tr')[1].find_all('th')

            try:
                turn_page = len(soup.find(id='memDiv').find_next_sibling().find_all('a'))    # 判断是否有分页
            except:
                turn_page = 0

            # print 'zhuyaorenyuan_turn_page', turn_page
            # print 'body_tr',len(soup.select('#table2 tr a')),soup.select('#table2 tr a')
            # print 'ry_tr1',soup.select('#tr1')
            idn = 1
            if len(iftr) > 0:
                # print 'zhuyaorenyuan*****'
                tr_element_list = soup.find(id='memDiv').find_all('tr')
                # tr_element_list = soup.find_all(class_='detailsList')[0].find_all('tr')
                # th_element_list = tr_element_list[1].find_all('th')
                th_element_list = gd_th
                for tr_element in tr_element_list:
                    if tr_element.text == u'':
                        # print 'zhuyaorenyuan_boom'
                        break
                    td_element_list = tr_element.find_all('td')
                    list_length = len(td_element_list)
                    fixed_length = list_length - list_length % 3
                    for j in range(fixed_length):
                        col_dec = th_element_list[j].text.strip().replace('\n','')
                        col = zhuyaorenyuan_column_dict[col_dec]
                        td = td_element_list[j]
                        val = td.text.strip()
                        values[col] = val
                        if len(values) == 3:
                            # values['RegistrationNo']=self.cur_code
                            # values['EnterpriseName']=self.org_name
                            # values['rowkey'] = values['EnterpriseName']+'_06_'+ values['RegistrationNo']+'_'+str(id)
                            values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, idn)
                            values[family + ':registrationno'] = self.cur_zch
                            values[family + ':enterprisename'] = self.cur_mc
                            values[family + ':id'] = str(idn)
                            json_list.append(values)
                            values = {}
                            idn += 1

                if turn_page > 1:
                    soupt = soup
                    for p in range(2, turn_page+1):
                        url = 'http://222.171.236.78:9080/QueryMemList.jspx?pno='+str(p)+'&mainId='+self.mainID
                        # print url
                        r = self.get_request(url=url, params={})
                        # r.encoding = 'gbk'
                        soup = BeautifulSoup(r.text, 'lxml')
                        # print '*******zhuyaorenyuan2*******',soup
                        gd_th = soupt.find_all(class_='detailsList')[0].find_all('tr')[1].find_all('th')

                        # print 'zhuyaorenyuan_fenye_turn_page', turn_page
                        # print 'body_tr',len(soup.select('#table2 tr a')),soup.select('#table2 tr a')
                        # print 'ry_tr1',soup.select('#tr1')
                        tr_element_list = soup.find_all(class_='detailsList')[0].find_all('tr')
                        th_element_list = gd_th
                        for tr_element in tr_element_list:
                            td_element_list = tr_element.find_all('td')
                            list_length = len(td_element_list)
                            fixed_length = list_length - list_length % 3
                            for j in range(fixed_length):
                                col_dec = th_element_list[j].text.strip().replace('\n','')
                                col = zhuyaorenyuan_column_dict[col_dec]
                                td = td_element_list[j]
                                val = td.text.strip()
                                values[col] = val
                                if len(values) == 3:
                                    # values['RegistrationNo']=self.cur_code
                                    # values['EnterpriseName']=self.org_name
                                    # values['rowkey'] = values['EnterpriseName']+'_06_'+ values['RegistrationNo']+'_'+str(id)
                                    values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, idn)
                                    values[family + ':registrationno'] = self.cur_zch
                                    values[family + ':enterprisename'] = self.cur_mc
                                    values[family + ':id'] = str(idn)
                                    json_list.append(values)
                                    values = {}
                                    idn += 1
                self.json_result[family] = json_list
                # print '-,-**zhuyaorenyuan_json_list', len(json_list), json_list

    def get_fen_zhi_ji_gou(self, ff):
        """
        查询分支机构信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Branches'
        table_id = '08'
        # self.json_result[family] = []
        soup = ff
        try:
            url = soup.find(id='childDiv').text
        except:
            url = ''
        # print 'fenzhijigou_url',self.cur_time,url
        if url:
            soup = ff.find(id='beian')
            # print '*******fenzhijigou*******',soup

            values = {}
            json_list = []
            gd_th = soup.find(id='childDiv').find_previous_sibling().find_all('tr')[1].find_all('th')
            iftr = soup.find(id='childDiv').find_all('tr')
            turn_page = 0
            if len(iftr) > 5:
                turn_page = len(soup.find(id='memDiv').find_next_sibling().find_all('a'))

            if len(iftr) > 0:
                tr_element_list = soup.find(id='childDiv').find_all('tr')
                th_element_list = soup.find(id='childDiv').find_previous_sibling().find_all('tr')[1].find_all('th')
                idn = 1
                for tr_element in tr_element_list:
                    if tr_element.text == u'':
                        # print 'fenzhijigou_boom_/breaker'
                        break
                    td_element_list = tr_element.find_all("td")
                    col_nums = len(th_element_list)
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n','')
                        col = fenzhijigou_column_dict[col_dec]
                        td = td_element_list[j]
                        val = td.text.strip()
                        values[col] = val
                    # values['RegistrationNo']=self.cur_code
                    # values['EnterpriseName']=self.org_name
                    # values['rowkey'] = values['EnterpriseName']+'_08_'+ values['RegistrationNo']+'_'+str(id)
                    values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, idn)
                    values[family + ':registrationno'] = self.cur_zch
                    values[family + ':enterprisename'] = self.cur_mc
                    values[family + ':id'] = str(idn)
                    json_list.append(values)
                    # json_fenzhijigou=json.dumps(values,ensure_ascii=False)
                    # print 'json_fenzhijigou',json_fenzhijigou
                    values = {}
                    idn += 1

                if turn_page > 1:
                    for p in range(2, turn_page+1):
                        url = 'http://222.171.236.78:9080/QueryChildList.jspx?pno='+str(p)+'&mainId='+self.mainID

                        r = self.get_request(url=url, params={})
                        # r.encoding = 'gbk'
                        soup = BeautifulSoup(r.text, 'lxml')
                        # print '*******fenzhijigou_fenye*******',soup

                        values = {}
                        json_list = []
                        iftr = soup.find_all(class_='detailsList')[0].find_all('tr')

                        # print 'fen_zhi_jigou_len_turn_page',turn_page
                        if len(iftr) > 0:
                            tr_element_list = soup.find_all(class_='detailsList')[0].find_all('tr')
                            th_element_list = gd_th
                            for tr_element in tr_element_list:
                                td_element_list = tr_element.find_all("td")
                                col_nums = len(th_element_list)
                                for j in range(col_nums):
                                    col_dec = th_element_list[j].text.strip().replace('\n','')
                                    col = fenzhijigou_column_dict[col_dec]
                                    td = td_element_list[j]
                                    val = td.text.strip()
                                    values[col] = val
                                # values['RegistrationNo']=self.cur_code
                                # values['EnterpriseName']=self.org_name
                                # values['rowkey'] = values['EnterpriseName']+'_08_'+ values['RegistrationNo']+'_'+str(id)
                                values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, idn)
                                values[family + ':registrationno'] = self.cur_zch
                                values[family + ':enterprisename'] = self.cur_mc
                                values[family + ':id'] = str(idn)
                                json_list.append(values)
                                # json_fenzhijigou=json.dumps(values,ensure_ascii=False)
                                # print 'json_fenzhijigou',json_fenzhijigou
                                values = {}
                                idn += 1

                self.json_result[family] = json_list
                # print '-,-**fenzhijigou_json_list', len(json_list), json_list

    def get_qing_suan(self, qq):
        """
        查询清算信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'liquidation_Information'
        table_id = '09'
        # self.json_result[family] = []
        values = {}
        json_list = []
        soup = qq.find(id='beian')
        try:
            soup.text
        except AttributeError:
            return
        if u'清算信息' in soup.text:
            table = soup.find_all(class_='detailsList')[-1]
            tr_list = table.find_all('tr')
            fzr = tr_list[1]  # 清算负责人
            cy = tr_list[2]  # 清算组成员
            fzrtd = fzr.td.text.strip()
            cytd = cy.td.text.strip()
            # print '****qingsuanyisen**'
            if fzrtd or cytd:
                # print u'清算有内容'
                self.info(u'清算有内容')
                values[qingsuan_column_dict[u'清算负责人']] = fzrtd
                values[qingsuan_column_dict[u'清算组成员']] = cytd
                values['rowkey'] = '%s_%s_%s_%s_' % (self.cur_mc, table_id, self.cur_zch, self.today)
                values[family + ':registrationno'] = self.cur_zch
                values[family + ':enterprisename'] = self.cur_mc
                json_list.append(values)
                if json_list:
                    # print 'qingsuan', json_list
                    self.json_result[family] = json_list

    def get_dong_chan_di_ya(self, dd):
        """
        查询动产抵押信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Chattel_Mortgage'
        table_id = '11'
        # self.json_result[family] = []
        values = {}
        json_list = []

        soup = dd
        try:
            url = soup.find(id='mortDiv').text
        except:
            url = ''
        # print '*******dongchandiya*******',soup
        if url:
            soup = dd.find(id='dongchandiya')

            row_cnt = len(soup.find_all(class_="detailsList")[1].find_all('tr'))
            if row_cnt > 0:
                # print 'come_on_bb_not_OK'
                tr_element_list = soup.find_all(class_="detailsList")[1].find_all('tr')
                th_element_list = soup.find_all(class_="detailsList")[0].find_all('tr')[1].find_all('th')
                idn = 1
                for tr_element in tr_element_list:
                    td_element_list = tr_element.find_all('td')
                    col_nums = len(th_element_list)
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n','')
                        col = dongchandiyadengji_column_dict[col_dec]
                        td = td_element_list[j]
                        val = td.text.strip()
                        if val == u'详情':
                            mex = td.a.get('onclick')
                            td = re.search(r'(?<=[(]).*(?=[)])', mex).group().replace("'", "")
                            val = self.domain+td
                            print ' 动产抵押详情', val
                            values[col] = val
                        else:
                            values[col] = val
                    # values['RegistrationNo']=self.cur_code
                    # values['EnterpriseName']=self.org_name
                    # values['rowkey'] = values['EnterpriseName']+'_11_'+ values['RegistrationNo']+'_'+str(id)
                    values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, idn)
                    values[family + ':registrationno'] = self.cur_zch
                    values[family + ':enterprisename'] = self.cur_mc
                    values[family + ':id'] = str(idn)
                    json_list.append(values)
                    # json_dongchandiyadengji=json.dumps(values,ensure_ascii=False)
                    # print 'json_dongchandiyadengji',json_dongchandiyadengji
                    values = {}
                    idn += 1
                self.json_result[family] = json_list
                # print '-,-**dongchandiya_json_list', len(json_list), json_list

    def get_gu_quan_chu_zhi(self, gg):
        """
        查询股权出置信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Equity_Pledge'
        table_id = '12'
        # self.json_result[family] = []
        json_list = []
        values = {}

        soup = gg
        try:
            url = soup.find(id='pledgeDiv').text
        except:
            url = ''
        # print 'gudongchuzhi_url',self.cur_time,url
        if url:
            # print '*******guquanchuzhi*******',soup
            soup = gg.find(id='guquanchuzhi')
            table_element = soup.find_all(class_="detailsList")
            row_cnt = len(soup.find_all(class_="detailsList")[1].find_all('tr'))
            if row_cnt > 0:
                tr_element_list = soup.find_all(class_="detailsList")[1].find_all('tr')
                th_element_list = soup.find_all(class_="detailsList")[0].find_all('tr')[1].find_all('th')
                idn = 1
                for tr_element in tr_element_list:
                    td_element_list = tr_element.find_all('td')
                    col_nums = len(th_element_list)
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n','')
                        # print 'col_dec',col_dec
                        if col_dec == u'证照/证件号码' and th_element_list[j-1].text.strip().replace('\n','') == u'出质人':
                            # print '**',col_dec
                            col = guquanchuzhidengji_column_dict[col_dec]
                        elif col_dec == u'证照/证件号码' and th_element_list[j-1].text.strip().replace('\n','') == u'质权人':
                            # print '***',col_dec
                            col = guquanchuzhidengji_column_dict[u'证照/证件号码1']
                        else:
                            col = guquanchuzhidengji_column_dict[col_dec]
                        td = td_element_list[j]
                        val = td.text.strip()
                        if val == u'详情':
                            mex = td.a.get('onclick')
                            td = re.search(r'(?<=[(]).*(?=[)])', mex).group().replace("'", "")
                            val = self.domain+td
                            values[col] = val
                            # print u'股权出质详情', link, 'fl', fake_link
                        else:
                            values[col] = val
                    # values['RegistrationNo']=self.cur_code
                    # values['EnterpriseName']=self.org_name
                    # values['rowkey'] = values['EnterpriseName']+'_12_'+ values['RegistrationNo']+'_'+str(id)
                    values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, idn)
                    values[family + ':registrationno'] = self.cur_zch
                    values[family + ':enterprisename'] = self.cur_mc
                    values[family + ':id'] = str(idn)
                    json_list.append(values)
                    # json_guquanchuzhidengji=json.dumps(values,ensure_ascii=False)
                    # print 'json_guquanchuzhidengji',json_guquanchuzhidengji
                    values = {}
                    idn += 1

                if len(table_element) == 3:
                    turn_page = table_element[2].find_all('a')
                    if len(turn_page) > 1:
                        # print u'股权出质有分页'
                        self.info(u'股权出质有分页')
                self.json_result[family] = json_list
                # print '-,-**guquanchuzhi_json_list**',len(json_list),json_list

    def get_xing_zheng_chu_fa(self, xx):
        """
        查询行政处罚信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Administrative_Penalty'
        table_id = '13'
        # self.json_result[family] = []
        values = {}
        json_list = []
        soup = xx
        try:
            url = soup.find(id='punDiv').text
        except:
            url = ''

        if url:
            # print '*******xingzhengchufa*******',soup
            soup = xx.find(id='xingzhengchufa')
            table_element = soup.find_all(class_='detailsList')
            row_cnt = len(soup.find_all(class_="detailsList")[1].find_all('tr'))
            if row_cnt > 0:
                tr_element_list = soup.find_all(class_="detailsList")[1].find_all('tr')
                th_element_list = soup.find_all(class_="detailsList")[0].find_all('tr')[1].find_all('th')
                idn = 1
                for tr_element in tr_element_list:
                    td_element_list = tr_element.find_all('td')
                    col_nums = len(th_element_list)
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n','')
                        col = xingzhengchufa_column_dict[col_dec]
                        td = td_element_list[j]
                        val = td.text.strip()
                        if val == u'详情':
                            mex = td.a.get('onclick')
                            td = re.search(r'(?<=[(]).*(?=[)])', mex).group().replace("'", "")
                            val = self.domain+td
                            print 'xingzhengchufa__val', val
                        values[col] = val
                    # values['RegistrationNo']=self.cur_code
                    # values['EnterpriseName']=self.org_name
                    # values['rowkey'] = values['EnterpriseName']+'_13_'+ values['RegistrationNo']+'_'+str(id)
                    values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, idn)
                    values[family + ':registrationno'] = self.cur_zch
                    values[family + ':enterprisename'] = self.cur_mc
                    values[family + ':id'] = str(idn)
                    json_list.append(values)
                    # json_xingzhengchufa=json.dumps(values,ensure_ascii=False)
                    # print 'json_xingzhengchufa',json_xingzhengchufa
                    values = {}
                    idn += 1
                if len(table_element) == 3:
                    turn_page = table_element[2].find_all('a')
                    if len(turn_page) > 1:
                        print u'行政处罚有分页'
                self.json_result[family] = json_list
                # print '-,-**xingzhengchufa_jsonlist***', len(json_list), json_list

    def get_jing_ying_yi_chang(self, jj):
        """
        查询经营异常信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Business_Abnormal'
        table_id = '14'
        # self.json_result[family] = []
        values = {}
        json_list = []
        soup = jj
        try:
            url = soup.find(id='excDiv').text
        except:
            url = ''
        # print '*******jingyingyichang*******',soup
        if url:
            soup = jj.find(id='jingyingyichangminglu')
            table_element = soup.find_all(class_='detailsList')
            row_cnt = len(soup.find_all(class_="detailsList")[1].find_all('tr'))
            if row_cnt > 0:
                idn = 1
                tr_element_list = soup.find_all(class_="detailsList")[1].find_all('tr')
                th_element_list = soup.find_all(class_="detailsList")[0].find_all('tr')[1].find_all('th')
                for tr_element in tr_element_list:
                    td_element_list = tr_element.find_all('td')
                    col_nums = len(th_element_list)
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n','')
                        # print 'col_dec',col_dec
                        col = jingyingyichang_column_dict[col_dec]
                        td = td_element_list[j]
                        val = td.text.strip().replace('\t','').replace('\n','')
                        values[col] = val
                        # print 'iii',col,val
                    # values['RegistrationNo']=self.cur_code
                    # values['EnterpriseName']=self.org_name
                    # values['rowkey'] = values['EnterpriseName']+'_14_'+ values['RegistrationNo']+'_'+str(id)
                    values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, idn)
                    values[family + ':registrationno'] = self.cur_zch
                    values[family + ':enterprisename'] = self.cur_mc
                    values[family + ':id'] = str(idn)
                    json_list.append(values)
                    # json_jingyingyichang=json.dumps(values,ensure_ascii=False)
                    # print 'json_jingyingyichang',json_jingyingyichang
                    values = {}
                    idn += 1
                if len(table_element) == 3:
                    turn_page = table_element[2].find_all('a')
                    if len(turn_page) > 1:
                        # print u'经营异常有分页'
                        self.info(u'经营异常有分页')
                self.json_result[family] = json_list
                # print '-,-**jingyingyichang',json_list

    def get_yan_zhong_wei_fa(self, ww):
        """
        查询严重违法信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Serious_Violations'
        table_id = '15'
        # self.json_result[family] = []
        values = {}
        json_list = []
        soup = ww
        try:
            url = soup.find(id='serillDiv').text
        except:
            url = ''
        # print '*******yanzhongweifa*******',soup
        if url:
            soup = ww.find(id='yanzhongweifaqiye')
            table_element = soup.find_all(class_='detailsList')
            row_cnt = len(soup.find_all(class_="detailsList")[1].find_all('tr'))
            if row_cnt > 0:
                tr_element_list = soup.find_all(class_="detailsList")[1].find_all('tr')
                th_element_list = soup.find_all(class_="detailsList")[0].find_all('tr')[1].find_all('th')
                idn = 1
                for tr_element in tr_element_list:
                    td_element_list = tr_element.find_all('td')
                    col_nums = len(th_element_list)
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n','')
                        col = yanzhongweifa_column_dict[col_dec]
                        td = td_element_list[j]
                        val = td.text.strip()
                        values[col]=val
                    # values['RegistrationNo']=self.cur_code
                    # values['EnterpriseName']=self.org_name
                    # values['rowkey'] = values['EnterpriseName']+'_15_'+ values['RegistrationNo']+'_'+str(id)
                    values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, idn)
                    values[family + ':registrationno'] = self.cur_zch
                    values[family + ':enterprisename'] = self.cur_mc
                    values[family + ':id'] = str(idn)
                    json_list.append(values)
                    # json_yanzhongweifa=json.dumps(values,ensure_ascii=False)
                    # print 'json_yanzhongweifa',json_yanzhongweifa
                    values = {}
                    idn += 1
                if len(table_element) == 3:
                    turn_page = table_element[2].find_all('a')
                    if len(turn_page) > 1:
                        # print u'严重违法有分页'
                        self.info(u'严重违法有分页')
                self.json_result[family] = json_list
                # print '-,-**yanzhongweifa_json_list', len(json_list), json_list

    def get_chou_cha_jian_cha(self, ca):
        """
        查询抽查检查信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Spot_Check'
        table_id = '16'
        # self.json_result[family] = []
        values = {}
        json_list = []
        soup = ca
        try:
            url = soup.find(id='spotCheckDiv').text
        except:
            url = ''
        # print '*******chouchajiancha*******',soup

        if url:
            soup = ca.find(id='chouchaxinxi')
            try:
                row_cnt = len(soup.find_all(class_='detailsList')[1].find_all('tr'))
            except:
                row_cnt = 0
            # print 'ccjc_row_cnt',row_cnt

            if row_cnt > 0:
                # print '*****mmmm****'
                table_element = soup.find_all(class_='detailsList')
                tr_element_list = soup.find_all(class_='detailsList')[1].find_all('tr')
                th_element_list = soup.find_all(class_='detailsList')[0].find_all('tr')[1].find_all('th')
                idn = 1
                for tr_element in tr_element_list:
                    td_element_list = tr_element.find_all('td')
                    col_nums = len(th_element_list)
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n','')
                        col = chouchajiancha_column_dict[col_dec]
                        td = td_element_list[j]
                        val = td.text.strip()
                        values[col] = val
                    # values['RegistrationNo']=self.cur_code
                    # values['EnterpriseName']=self.org_name
                    # values['rowkey'] = values['EnterpriseName']+'_16_'+ values['RegistrationNo']+'_'+str(id)
                    values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, idn)
                    values[family + ':registrationno'] = self.cur_zch
                    values[family + ':enterprisename'] = self.cur_mc
                    values[family + ':id'] = str(idn)
                    json_list.append(values)
                    # json_chouchajiancha=json.dumps(values,ensure_ascii=False)
                    # print 'json_chouchajiancha',json_chouchajiancha
                    values = {}
                    idn += 1
                if len(table_element) == 3:
                    turn_page = table_element[2].find_all('a')
                    if len(turn_page) > 1:
                        # print u'抽查检查有分页'
                        self.info(u'抽查检查有分页')
                self.json_result[family] = json_list
                # print '-,-**chouchajiancha', len(json_list), json_list

    # def get_request(self, url, params={}, t=0):
    #     try:
    #         if self.use_proxy:
    #             self.headers['Proxy-Authorization'] = self.proxy_config.get_auth_header(lock_id=self.lock_id)
    #         return self.session.get(url=url, headers=self.headers, params=params, timeout=5)
    #     except RequestException, e:
    #         if t == 5:
    #             raise e
    #         else:
    #             return self.get_request(url, params, t+1)
    #
    # def post_request(self, url, params={}, t=0):
    #     try:
    #         if self.use_proxy:
    #             self.headers['Proxy-Authorization'] = self.proxy_config.get_auth_header(lock_id=self.lock_id)
    #         return self.session.post(url=url, headers=self.headers, data=params, timeout=5)
    #     except RequestException, e:
    #         if t == 5:
    #             raise e
    #         else:
    #             return self.post_request(url, params, t+1)

    # def get_request(self, url, params={}, verify=True, t=0, release_lock_id=False):
    #     """
    #     发送get请求,包含添加代理,锁定ip与重试机制
    #     :param url: 请求的url
    #     :param params: 请求参数
    #     :param verify: 忽略ssl
    #     :param t: 重试次数
    #     :param release_lock_id: 是否需要释放锁定的ip资源
    #     """
    #     try:
    #         if self.use_proxy:
    #             if not release_lock_id:
    #                 self.headers['Proxy-Authorization'] = self.proxy_config.get_auth_header(lock_id=self.lock_id)
    #             else:
    #                 self.headers['Proxy-Authorization'] = self.proxy_config.get_auth_header(lock_id=self.lock_id, release_id=self.lock_id)
    #         r = self.session.get(url=url, headers=self.headers, data=params, verify=verify, timeout=15)
    #         if r.status_code != 200:
    #             # print u'错误的响应代码 -> %d' % r.status_code, url
    #             self.info(u'错误的响应代码 -> %d' % r.status_code + url)
    #             raise RequestException()
    #         return r
    #     except RequestException, e:
    #         if t == 15:
    #             raise e
    #         else:
    #             return self.get_request(url, params, verify, t+1, release_lock_id)
    #
    # def post_request(self, url, params={}, verify=True, t=0, release_lock_id=False):
    #     """
    #     发送post请求,包含添加代理,锁定ip与重试机制
    #     :param url: 请求的url
    #     :param params: 请求参数
    #     :param verify: 忽略ssl
    #     :param t: 重试次数
    #     :param release_lock_id: 是否需要释放锁定的ip资源
    #     :return:
    #     """
    #     try:
    #         if self.use_proxy:
    #             if not release_lock_id:
    #                 self.headers['Proxy-Authorization'] = self.proxy_config.get_auth_header(lock_id=self.lock_id)
    #             else:
    #                 self.headers['Proxy-Authorization'] = self.proxy_config.get_auth_header(lock_id=self.lock_id, release_id=self.lock_id)
    #         r = self.session.post(url=url, headers=self.headers, data=params, verify=verify, timeout=15)
    #         if r.status_code != 200:
    #             # print u'错误的响应代码 -> %d' % r.status_code
    #             self.info( u'错误的响应代码 -> %d' % r.status_code)
    #             raise RequestException()
    #         return r
    #     except RequestException, e:
    #         if t == 15:
    #             raise e
    #         else:
    #             return self.post_request(url, params, verify, t+1, release_lock_id)

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
    searcher = HeiLongJiang()
    searcher.submit_search_request(u"友谊县立娟游戏厅")  # 哈尔滨安上源股权投资基金管理中心")
    # 黑龙江省公安厅劳动服务公司铅印室")
    # 黑龙江省保利地方煤炭有限公司")
    # 牡丹江市金环石化设备有限公司")#哈尔滨市创实文化传媒有限责任公司")
    # 集贤县宏发煤炭有限责任公司 dcdydetail
    # searcher.get_tag_a_from_page(u"银川塔木金商贸有限公司")
    # searcher.parse_detail(1)
    # rst = searcher.parse_detail(1)
    # print 'rst',rst
    # searcher.get_credit_ticket()
    # print searcher.credit_ticket

    # print json.dumps(args_dict, ensure_ascii=False)
    # searcher = LiaoNing()
    # searcher.submit_search_request(keyword=args_dict['companyName'], account_id=args_dict['accountId'], task_id=args_dict['taskId'])
    # p, t = '210200000011992092800017', '6210'
    # p, t = '21060200002200908053570X', '1151'
    # print searcher.get_gu_dong_detail('210200000011992092800017', '754198044')
    # pattern = re.compile("\s")
    # print pattern.sub('', '12 434 5')
