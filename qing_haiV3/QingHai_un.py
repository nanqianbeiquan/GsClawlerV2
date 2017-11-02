# coding=utf-8

import requests
import os
import uuid
from urllib import quote
import PackageTool
from PIL import Image
from bs4 import BeautifulSoup
import json
import re
from gs.KafkaAPI import KafkaAPI
import datetime
from requests.exceptions import RequestException
import sys
import PyV8
import random
import subprocess
import time
from Tables_dict import *
from gs.Searcher import Searcher
from gs.Searcher import get_args
from gs.ProxyConf import *
from gs.TimeUtils import *


class QingHai(Searcher):

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
        super(QingHai, self).__init__(use_proxy=True)
        self.session = requests.session()
        # self.session.proxies = {'http': '123.56.238.200:8123', 'https': '123.56.238.200:8123'}
        # self.session.proxies = {'http': '121.28.134.29:80'}

        self.headers = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Encoding": "gzip, deflate",
                        "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
                        "Connection": "keep-alive",
                        "Content-type": "application/x-www-form-urlencoded",
                        "Host": "gsxt.qhaic.gov.cn:8005",
                        # "Referer": "http://gsxt.qhaic.gov.cn:8005/ECPS/search.jspx",
                        "Referer": "http://gsxt.qhaic.gov.cn:8005/ECPS/",
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:47.0) Gecko/20100101 Firefox/47.0"
                        }
        # self.cur_time = '%d' % (time.time() * 1000)
        self.get_credit_ticket()
        self.json_result = {}  # json输出结果
        self.iframe_name = {'qyjbqk': u'基本信息', 'tzrczxx': u'股东信息', 'qybgxx': u'变更信息',
                           'qybaxxzyryxx': u'主要人员信息', 'qybaxxfgsxx': u'分支机构信息', 'qybaxxqsxx': u'清算信息',
                            'gqczxx': u'股权出质登记信息', 'dcdyxx': u'动产抵押登记信息', 'jyycxx':u'经营异常信息',
                            'yzwfxx': u'严重违法信息', 'xzcfxx': u'行政处罚信息', 'ccjcxx':u'抽查检查信息'}
        self.domain = 'http://gsxt.qhaic.gov.cn:8005/ECPS'
        self.set_config()
        self.log_name = self.topic + "_" + str(uuid.uuid1())

    def set_config(self):
        self.plugin_path = sys.path[0] + r'\..\qing_hai\ocr\beijing.bat'
        # self.group = 'Crawler'  # 正式
        # self.kafka = KafkaAPI("GSCrawlerResult")  # 正式
        self.group = 'CrawlerTest'  # 测试
        self.kafka = KafkaAPI("GSCrawlerTest")  # 测试
        self.topic = 'GsSrc63'
        self.province = u'青海省'
        self.kafka.init_producer()
        # try:
        #     self.go_cookies()
        # except AttributeError:
        #     pass

    def download_yzm(self):
        pass
        # self.lock_id = self.proxy_config.get_lock_id()
        # self.cur_time = '%d' % (time.time() * 1000)
        # params = {'currentTimeMillis': self.cur_time}
        # image_url = 'http://gsxt.qhaic.gov.cn:8005/ECPS/validateCode.jspx?type=2'
        # r = self.get_request(url=image_url, params={})
        # # print r.headers
        # # print r.status_code,r.text
        # yzm_path = os.path.join(sys.path[0], str(random.random())[2:]+'.jpg')
        # with open(yzm_path, 'wb') as f:
        #     for chunk in r.iter_content(chunk_size=1024):
        #         if chunk:  # filter out keep-alive new chunks
        #             f.write(chunk)
        #             f.flush()
        #     f.close()
        # return yzm_path

    def get_credit_ticket(self):
        # r = self.get_request('http://qyxy.baic.gov.cn/gjjbj/gjjQueryCreditAction!toIndex.dhtml')
        # print 'credit_headers',r.headers
        # soup = BeautifulSoup(r.text, 'lxml')
        # # print soup
        # self.credit_ticket = soup.select('input#credit_ticket')[0].attrs['value']
        pass

    def go_cookies(self):
        url = 'http://gsxt.qhaic.gov.cn:8005/ECPS/search.jspx#'
        r = self.get_request(url=url)
        r.encoding = 'utf-8'
        set_cookie = [r.headers['Set-Cookie']]
        soup = BeautifulSoup(r.text, 'lxml')
        script = soup.select('script')[0].text
        script = script[len('eval(')+1:-1]
        # print 'script', script
        ctxt = PyV8.JSContext()
        ctxt.enter()
        res = ctxt.eval(script)
        # print 'eval_after', res
        res = res.replace('if(findDimensions()) {} else ', '')
        res = res.replace('window.location=dynamicurl', '')
        res = res.replace('document.cookie = cookieString;	var confirm = QWERTASDFGXYSF()', 'res=cookieString;	var confirm = QWERTASDFGXYSF()')
        res = res.replace("document.cookie = cookieString;", "res = res+', '+cookieString;return res")
        # print 'res', res
        js_res_text = ctxt.eval(res)
        # print 'dealt_JSresult', js_res_text
        set_cookie.extend(js_res_text.split(', '))
        # print set_cookie
        for x in set_cookie:
            y = x.split(';')[0]
            idx_1 = y.index('=')
            name = y[:idx_1]
            value = y[idx_1+1:]
            self.session.cookies.set(name=name, value=value, domain='gsxt.qhaic.gov.cn:8005/ECPS', path='/')

    def get_tag_a_from_db(self, keyword):
        return None

    def save_tag_a_to_db(self, keyword):
        pass

    def get_tag_a_from_page(self, keyword):

        for t in range(50):
            time.sleep(3)
            print u'验证码识别中...第%s次' %(t+1)
            self.today = str(datetime.date.today()).replace('-', '')
            # yzm = self.get_yzm()
            # print 'yzm', yzm
            # url = 'http://gsxt.qhaic.gov.cn:8005/ECPS/searchList.jspx'
            # params = {'checkNo': yzm, 'entName': keyword}
            url = 'http://gsxt.qhaic.gov.cn:8005/ECPS/queryListData.jspx'
            params = {'currentPageIndex': 1, 'entName': keyword, 'searchType': 1, }
            # print 'params:', params
            r = self.post_request(url=url, params=params)
            # print 'r.headers',r.headers
            r.encoding = 'utf-8'
            # print '**************************', r.text
            soup = BeautifulSoup(r.text, 'html5lib')
            # print 'soup:', soup
            # print '*******cpn_request_ok?:', soup.select('.list')[0], 'next_siblings', soup.select('.list')[0].find_next_sibling()
            # tgr = soup.find(id='alert_win').find(id='MzImgExpPwd').get('alt')
            # print '*************', soup.select('#gggscpnametext')[0]
            # if u'请开启JavaScript并刷新该页' in soup.text:
            #     print u'cookie失效，更新cookie'  # 安徽360特色
            #     self.go_cookies()
            #
            if not soup.text.strip():
                print u'***验证码识别通过***no_result***'
                break
            if soup.find(id='gggscpnametext'):
                # print 'r.headers', r.headers
                print u'**********验证码识别通过***安徽*********'  #, soup.find(class_='list')
                if soup.find(id='gggscpnametext').text.strip() != '':
                    return soup.select('#gggscpnametext')[0]
                break
        return None

    def get_search_args(self, tag_a, keyword):
        # print 'tag_a', tag_a  # 不是连接地址tagA
        name = tag_a.find_all('p')[0].text.strip().split('\n')[0]   # name为公司查询结果名；keyword为查询前数据库公司名
        # name_link = tag_a.find('a').get('href')
        # mainID = re.search(r'(?<=id=).*',name_link).group()
        mainID = tag_a.find_all('p')[0].find_all('span')[-1].get('class')[0]
        code = tag_a.find_all('p')[1].find_all('span')[0].text.strip().replace(' ', '').split(u'：')[1]    # 注册号
        # tagA = self.domain + name_link  # 验证码通过后链接地址
        print '+++++++', name, '##', code, 'mainID:', mainID
        self.mainID = mainID  # 安徽有分页情况可能用到
        self.cur_mc = name.replace('(', u'（').replace(')', u'）').strip()
        self.cur_zch = code
        # self.tagA = tagA  # 安徽三大参数，公司名称name，注册号code， 跳过验证码的地址tagA

        self.xydm_if = ''
        self.zch_if = ''
        if len(code) == 18:
            self.xydm_if = code
        else:
            self.zch_if = code
        # print u'公司名(name)cur_mc: %s, 注册号(code)cur_zch: %s, 链接地址tagA: %s' % (name, code, tagA), 'mainID:', mainID
        if self.cur_mc == keyword:
            print 'same'
            return 1
        else:
            print 'insane'
            return 0

    def parse_detail(self):
        """
        解析公司详情信息
        :param kwargs:
        :return:
        """
        print '****************HIHI************************'
        # r = self.get_request(self.tagA)
        # print r.text
        # bs = BeautifulSoup(r.text, 'html5lib')
        # bd = bs.find(class_='dConBox')
        # print '#hei_long_soup',  bd, '**'

        # print '&&&&&&&&&&&&&&&&&&&&&&&', len(bs.select('#dConBox div iframe')), bs.select('#dConBox div iframe')
        self.get_ji_ben()
        # print 'jb_step_json', self.json_result
        self.get_gu_dong()
        # print 'gd_step_json', self.json_result
        self.get_bian_geng()
        # print 'bg_step_json', self.json_result
        # self.get_zhu_yao_ren_yuan()
        # self.get_fen_zhi_ji_gou()
        # self.get_qing_suan()
        # self.get_dong_chan_di_ya()
        # self.get_gu_quan_chu_zhi()
        # self.get_xing_zheng_chu_fa()
        # self.get_jing_ying_yi_chang()
        # self.get_yan_zhong_wei_fa()
        # self.get_chou_cha_jian_cha()
        self.get_nian_bao()
        # print 'the_last_json_result', len(self.json_result), self.json_result

        json_go = json.dumps(self.json_result, ensure_ascii=False)
        print 'the_last_json_result:', len(self.json_result), get_cur_time(),  json_go

    def get_ji_ben(self):
        """
        查询基本信息
        :return: 基本信息结果
        """
        json_list = []
        family = 'Registered_Info'
        table_id = '01'
        self.json_result[family] = []

        url = 'http://gsxt.qhaic.gov.cn:8005/ECPS/business/YYZZ.jspx?id='+self.mainID
        print 'jiben_url', url
        r = self.get_request(url=url, params={})
        # r.encoding = 'gbk'
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html5lib')
        # soup = bd
        # print '*******ji_ben*******', soup
        tr_element_list = soup.find_all('tr')#(".//*[@id='jbxx']/table/tbody/tr")
        values = {}
        for tr_element in tr_element_list:
            # th_element_list = tr_element.find_all('th')
            td_element_list = tr_element.find_all('td')
            for td in td_element_list:
                if td.text.strip():
                    td_list = td.text.replace(u'·', '').replace(u' ', '').strip().replace(u' ', '').split(u'：',1)
                    col = td_list[0].strip()
                    val = td_list[1].strip()
                    # print col, val
                    col = jiben_column_dict[col]
                    values[col] = val

            # if len(th_element_list) == len(td_element_list):
            #     col_nums = len(th_element_list)
            #     for i in range(col_nums):
            #         col_dec = th_element_list[i].text.strip()
            #         val = td_element_list[i].text.strip()
            #         if col_dec != u'':
            #             col = jiben_column_dict[col_dec]
            #             values[col] = val
        values['rowkey'] = '%s_%s_%s_' % (self.cur_mc, table_id, self.cur_zch)
        values[family + ':registrationno'] = self.cur_zch
        values[family + ':enterprisename'] = self.cur_mc
        values[family + ':tyshxy_code'] = self.xydm_if
        values[family + ':zch'] = self.zch_if
        values[family + ':lastupdatetime'] = get_cur_time()
        values[family + ':province'] = u'安徽省'
        json_list.append(values)
        self.json_result[family] = json_list
        print 'jiben_values', values

    def get_gu_dong(self):
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
        url = 'http://gsxt.qhaic.gov.cn:8005/ECPS/business/GDCZ.jspx?id='+self.mainID
        print 'gudongurl', url
        r = self.get_request(url=url)
        soup = BeautifulSoup(r.text, 'html5lib')
        # soup = aa
        # try:
        #     url = soup.find(id='invDiv').text  # 此处url不是连接地址，是判断内容是否为空的参数
        # except:
        #     url = ''
        # print 'gudong_url', self.cur_time, url
        # print '******gudong_soup******', soup
        if soup.text.strip():
            soup = soup.find(id='paging')
            # print '*******gudong*******', soup
            # print 'gu_dong_turn_page', turn_page
            # print 'body_tr',len(soup.select('#table2 tr a')),soup.select('#table2 tr a')
            # print 'gd_tr1',soup.select('#tr1')
            tr_num = soup.find_all(class_='detailsList')
            if len(tr_num) >= 2:
                gd_th = soup.find_all(class_='detailsList')[0].find_all('tr')[0].find_all('th')
                iftr = soup.find_all(class_='detailsList')[1].find_all('tr')

            # if len(iftr) > 0:
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
                        if td == u'查看':
                            td = gd_td[j].a.get('onclick')
                            # print 'gudong', td
                            td = re.search(r'(?<=[(]).*(?=[)])', td).group().strip("'")
                            detail_url = 'http://gsxt.qhaic.gov.cn:8005/ECPS/queryInvDetailAction.jspx?invId='+td
                            print 'detail_url', detail_url
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

                turn_pageo = soup.find_all('div', recursive=False)[1].ul.find_all('li')[1].text.strip()[1:-1]    #判断是否有分页，需要post分页地址，暂不处理
                print 'gudong_turn_page:', turn_pageo
                turn_page = int(turn_pageo)


                # 股东分页情况处理
                if turn_page > 1:
                    print '*'*1000
                    print 'len_gudong_page', turn_page
                    for p in range(2, turn_page+1):
                        # link = 'http://gsxt.qhaic.gov.cn:8005/ECPS/QueryInvList.jspx?pno='+str(p)+'&mainId='+self.mainID
                        fkurl = 'http://gsxt.qhaic.gov.cn:8005/ECPS/business/QueryInvList.jspx?pno='+str(p)+'&order=0&mainId='+self.mainID
                        # print '***********gudongfenyelink******************', link
                        url = fkurl
                        r = self.get_request(url=url, params={})
                        # r.encoding = 'gbk'
                        soup = BeautifulSoup(r.text, 'html5lib')
                        # print '*******gudong**fenye*****',soup
                        # gd_th = soup.find_all(class_='detailsList')[0].find_all('tr')[1].find_all('th')
                        iftr = soup.find_all(class_='detailsList')[0].find_all('tr')[1:]
                        for i in range(len(iftr)):
                            gd_td = iftr[i].find_all('td')
                            for j in range(len(gd_th)):
                                th = gd_th[j].text.strip()
                                td = gd_td[j].text.strip()
                                if td == u'查看':
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
                print '-,-**gudong_json_list', len(json_list), json_list

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

        detail_tb_list = soup.find_all(class_='detailsList')
        # detail_th_list = ['subscripted_capital','actualpaid_capital','subscripted_method','subscripted_amount','subscripted_time','actualpaid_method','actualpaid_amount','actualpaid_time']
        # detail_th_new_list = [family+':'+x for x in detail_th_list]
        # print 'detail_th_new_list', detail_th_new_list
        n = 0
        for tr_ele in detail_tb_list:
            tr_ele_list = tr_ele.find_all('tr')
            if n == 0:

                for tr in tr_ele_list[1:]:
                    col = tr.th.text
                    val = tr.td.text
                    # print 'gddetails', col, val
                    values[gudong_column_dict[col]] = val
            else:
                th_list = tr_ele_list[0].find_all('th')
                if len(tr_ele_list) == 1:
                    for c in range(len(th_list)):
                        col = th_list[c].text.strip()
                        val = u''
                        values[gudong_column_dict[col]] = val
                if len(tr_ele_list) > 1:
                    for tr in tr_ele_list[1:]:
                        td_list = tr.find_all('td')
                        for c in range(len(th_list)):
                            col = th_list[c].text.strip()
                            val = td_list[c].text.strip()
                            # print col,val
                            values[gudong_column_dict[col]] = val
            n += 1

        # print 'gdl_values',len(values),values

    def get_bian_geng(self):
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

        url = 'http://gsxt.qhaic.gov.cn:8005/ECPS/business/BGXX.jspx?id='+self.mainID
        print 'biangeng_url', url
        r = self.get_request(url=url, params={})
        # r.encoding = 'gbk'
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html5lib')
        # print '*******biangeng*******',soup
        try:
            tr_num = len(soup.find_all(class_='detailsList'))
        except:
            tr_num = 0

        if tr_num > 1:
            gd_th = soup.find_all(class_='detailsList')[0].find_all('th')
            # print 'th_previous',cc.find(id='altDiv').find_previous_sibling().text
            iftr = soup.find_all(class_='detailsList')[1].find_all('tr')

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

                turn_pageo = soup.find(id='altDiv2').find_all('div', recursive=False)[1].ul.find_all('li')[1].text.strip()[1:-1]    #判断是否有分页，需要post分页地址，暂不处理
                print 'biangeng_turn_page:', turn_pageo
                turn_page = int(turn_pageo)

                if turn_page > 1:
                    print '*3'*1000
                    # sys.exit()
                    # print 'biangeng_page_splitter***************'
                    for p in range(2, turn_page+1):
                        # bgurl = 'http://gsxt.qhaic.gov.cn:8005/ECPS/QueryAltList.jspx?pno='+str(p)+'&mainId='+self.mainID
                        fkurl = 'http://gsxt.qhaic.gov.cn:8005/ECPS/business/QueryAltList.jspx?pno='+str(p)+'&order=0&mainId='+self.mainID
                        print 'biangeng_fen_ye_link', fkurl
                        rc = self.get_request(url=fkurl)
                        soup = BeautifulSoup(rc.text, 'lxml')
                        print 'biangeng_turn_soup', soup

                        # gd_th = soup.find_all(class_='detailsList')[0].find_all('tr')[1].find_all('th')
                        iftr = soup.find_all(class_='detailsList')[1].find_all('tr')
                        for i in range(len(iftr)):
                            gd_td = soup.find_all(class_='detailsList')[1].find_all('tr')[i].find_all('td')
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
                print '-,-**biangeng_json_list****', len(json_list), json_list

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

    def get_zhu_yao_ren_yuan(self):
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

        url = 'http://gsxt.qhaic.gov.cn:8005/ECPS/business/ZYRY.jspx?id='+self.mainID
        print 'zhuyaorenyuan_url', url
        r = self.get_request(url=url, params={})
        # r.encoding = 'gbk'
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html5lib')
        # print '*******zhuyaorenyuan*******', soup

        try:
            tr_num = len(soup.find_all(class_='keyPerInfo'))
        except:
            tr_num = 0
        print 'zyry()*)(', tr_num
        if tr_num > 0:
            soup = soup.find_all(class_='keyPerInfo')  # 有几个人员

            # print '*******zhuyaorenyuan*******',soup
            cnt = 1
            for t in range(tr_num):
                pson = soup[t].find_all('p')
                if len(pson):
                    name = pson[0].text.strip()
                    posn = pson[1].text.strip()
                    print '******', t, 'name:', name, 'position:', posn
                    values[zhuyaorenyuan_column_dict[u'姓名']] = name
                    values[zhuyaorenyuan_column_dict[u'职务']] = posn
                    values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, cnt)
                    values[family + ':registrationno'] = self.cur_zch
                    values[family + ':enterprisename'] = self.cur_mc
                    values[family + ':id'] = str(cnt)
                    json_list.append(values)
                    values = {}
                    cnt += 1
            if json_list:
                print 'zhuyaorenyuan_jsonlist:', json_list
                self.json_result[family] = json_list


    def get_fen_zhi_ji_gou(self):
        """
        查询分支机构信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Branches'
        table_id = '08'
        # self.json_result[family] = []

        url = 'http://gsxt.qhaic.gov.cn:8005/ECPS/business/FZJG.jspx?id='+self.mainID
        print 'fenzhijigou_url', url
        r = self.get_request(url=url, params={})
        # r.encoding = 'gbk'
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html5lib')
        print '*******fenzhijigou*******', soup
        try:
            tr_num = len(soup.find_all('p'))
        except:
            tr_num = 0
        print 'fenzhijigou:', tr_num
        if tr_num > 1:
            soup = soup.find(class_='xxwk')
            print '*******fenzhijigou*******', soup

            values = {}
            json_list = []

            if soup.text.strip():
                tr_element_list = soup.find_all(class_='fenzhixinxin')
                idn = 1
                for tr_element in tr_element_list:
                    if tr_element.text == u'':
                        print 'fenzhijigou_boom_breaker'
                        break
                    td_element_list = tr_element.find_all("p")
                    values[fenzhijigou_column_dict[u'名称']] = td_element_list[0].text.strip()
                    values[fenzhijigou_column_dict[u'注册号']] = td_element_list[1].text.strip().replace(u'·', '').split(u'：')[1]
                    values[fenzhijigou_column_dict[u'登记机关']] = td_element_list[2].text.strip().replace(u'·', '').split(u'：')[1]
                    values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, idn)
                    values[family + ':registrationno'] = self.cur_zch
                    values[family + ':enterprisename'] = self.cur_mc
                    values[family + ':id'] = str(idn)
                    json_list.append(values)
                    # json_fenzhijigou=json.dumps(values,ensure_ascii=False)
                    # print 'json_fenzhijigou',json_fenzhijigou
                    values = {}
                    idn += 1

                turn_page = 0
                if turn_page > 1:
                    for p in range(2, turn_page+1):
                        url = 'http://gsxt.qhaic.gov.cn:8005/ECPS/QueryChildList.jspx?pno='+str(p)+'&mainId='+self.mainID

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

    def get_qing_suan(self):
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
        url = 'http://gsxt.qhaic.gov.cn:8005/ECPS/business/QSXX.jspx?id='+self.mainID
        print 'qingsuan_url:', url
        r = self.get_request(url=url, params={})
        # r.encoding = 'gbk'
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html5lib')
        # print 'qingsuan', soup
        if u'清算信息' in soup.text:
            table = soup.find_all(class_='details')[0]
            tr_list = table.find_all('tr')
            fzr = tr_list[0]  # 清算负责人
            cy = tr_list[1]  # 清算组成员
            fzrtd = fzr.td.text.strip()
            cytd = cy.td.text.strip()
            print '****qingsuanyisen**'
            if fzrtd or cytd:
                print u'清算有内容'
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

    def get_dong_chan_di_ya(self):
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

        url = 'http://gsxt.qhaic.gov.cn:8005/ECPS/business/DCDY.jspx?id='+self.mainID
        print 'dcdyurl:', url
        r = self.get_request(url=url, params={})
        # r.encoding = 'gbk'
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html5lib')
        # print '*******dongchandiya*******', soup
        try:
            tr_num = len(soup.find_all('p'))
        except:
            tr_num = 0
        print 'fenzhijigou:', tr_num
        if tr_num:
            soup = soup.find(id='mortDiv2')

            row_cnt = len(soup.find_all(class_="detailsList")[1].find_all('tr'))
            if row_cnt > 0:
                print 'come_on_bb_not_OK'
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
                            link = self.domain+td
                            print u'动产抵押详情', link
                            values[col] = link
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
                print '-,-**dongchandiya_json_list',len(json_list),json_list

    def get_gu_quan_chu_zhi(self):
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

        url = 'http://gsxt.qhaic.gov.cn:8005/ECPS/business/GQCZ.jspx?id='+self.mainID
        print 'gqczurl:', url
        r = self.get_request(url=url, params={})
        # r.encoding = 'gbk'
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html5lib')
        # print '*******guquanchuzhi*******', soup
        try:
            tr_num = len(soup.find_all('p'))
        except:
            tr_num = 0
        print 'fenzhijigou:', tr_num
        if tr_num:
            # print '*******guquanchuzhi*******',soup
            soup = soup.find(id='pledgeDiv2')
            table_element = soup.find_all(class_="detailsList")
            row_cnt = len(soup.find_all(class_="detailsList")[1].find_all('tr'))
            if row_cnt > 0:
                tr_element_list = soup.find_all(class_="detailsList")[1].find_all('tr')
                th_element_list = soup.find_all(class_="detailsList")[0].find_all('tr')[0].find_all('th')
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
                            link = self.domain+td
                            print 'gqcz_link', link
                            values[col] = link
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
                        print u'股权出质有分页'
                self.json_result[family] = json_list
                print '-,-**guquanchuzhi_json_list**',len(json_list),json_list

    def get_xing_zheng_chu_fa(self):
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

        url = 'http://gsxt.qhaic.gov.cn:8005/ECPS/business/XZCF.jspx?id='+self.mainID
        print 'xzcfurl:', url
        r = self.get_request(url=url, params={})
        # r.encoding = 'gbk'
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html5lib')
        # print '*******xingzhengchufa*******', soup
        try:
            tr_num = len(soup.find_all('p'))
        except:
            tr_num = 0
        print 'xingzhengchufa:', tr_num
        if tr_num:
            # print '*******xingzhengchufa*******',soup
            soup = soup.find(id='punDiv2')
            table_element = soup.find_all(class_='detailsList')
            row_cnt = len(soup.find_all(class_="detailsList")[1].find_all('tr'))
            if row_cnt > 0:
                tr_element_list = soup.find_all(class_="detailsList")[1].find_all('tr')
                th_element_list = soup.find_all(class_="detailsList")[0].find_all('tr')[0].find_all('th')
                idn = 1
                for tr_element in tr_element_list:
                    td_element_list = tr_element.find_all('td')
                    col_nums = len(th_element_list)
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n','')
                        col = xingzhengchufa_column_dict[col_dec]
                        td = td_element_list[j]
                        val = td.text.strip()
                        if val == u'查看':
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

    def get_jing_ying_yi_chang(self):
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

        url = 'http://gsxt.qhaic.gov.cn:8005/ECPS/business/JYYC.jspx?id='+self.mainID
        print 'jyycurl:', url
        r = self.get_request(url=url, params={})
        # r.encoding = 'gbk'
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html5lib')
        # print '*******jingyingyichang*******', soup
        try:
            tr_num = len(soup.find_all('p'))
        except:
            tr_num = 0
        print 'jingyingyichang:', tr_num
        if tr_num:
            soup = soup.find(id='excDiv2')
            table_element = soup.find_all(class_='detailsList')
            row_cnt = len(soup.find_all(class_="detailsList")[1].find_all('tr'))
            if row_cnt > 0:
                idn = 1
                tr_element_list = soup.find_all(class_="detailsList")[1].find_all('tr')
                th_element_list = soup.find_all(class_="detailsList")[0].find_all('tr')[0].find_all('th')
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
                        print u'经营异常有分页'
                self.json_result[family] = json_list
                # print '-,-**jingyingyichang',json_list

    def get_yan_zhong_wei_fa(self):
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

        url = 'http://gsxt.qhaic.gov.cn:8005/ECPS/business/YZWF.jspx?id='+self.mainID
        print 'yzwfurl:', url
        r = self.get_request(url=url, params={})
        # r.encoding = 'gbk'
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html5lib')
        # print '*******yanzhongweifa*******', soup
        try:
            tr_num = len(soup.find_all('p'))
        except:
            tr_num = 0
        print 'yanzhongweifa:', tr_num
        if tr_num:
            soup = soup.find(id='serillDiv2')
            table_element = soup.find_all(class_='detailsList')
            row_cnt = len(soup.find_all(class_="detailsList")[1].find_all('tr'))
            if row_cnt > 0:
                tr_element_list = soup.find_all(class_="detailsList")[1].find_all('tr')
                th_element_list = soup.find_all(class_="detailsList")[0].find_all('tr')[0].find_all('th')
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
                        print u'严重违法有分页'
                self.json_result[family] = json_list
                # print '-,-**yanzhongweifa_json_list', len(json_list), json_list

    def get_chou_cha_jian_cha(self):
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

        url = 'http://gsxt.qhaic.gov.cn:8005/ECPS/business/CCJC.jspx?id='+self.mainID
        print 'ccjcurl:', url
        r = self.get_request(url=url, params={})
        # r.encoding = 'gbk'
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html5lib')
        # print '*******chouchajiancha*******', soup
        try:
            tr_num = len(soup.find_all('p'))
        except:
            tr_num = 0
        print 'chouchajiancha:', tr_num
        if tr_num:
            soup = soup.find(id='spotCheck2')
            try:
                row_cnt = len(soup.find_all(class_='detailsList')[1].find_all('tr'))
            except:
                row_cnt = 0
            # print 'ccjc_row_cnt',row_cnt

            if row_cnt > 0:
                # print '*****mmmm****'
                table_element = soup.find_all(class_='detailsList')
                tr_element_list = soup.find_all(class_='detailsList')[1].find_all('tr')
                th_element_list = soup.find_all(class_='detailsList')[0].find_all('tr')[0].find_all('th')
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
                        print u'抽查检查有分页'
                self.json_result[family] = json_list
                # print '-,-**chouchajiancha', len(json_list), json_list

    def get_nian_bao(self):

        url = 'http://gsxt.qhaic.gov.cn:8005/ECPS/yearExm/QYNBXX.jspx?ram='+str(random.random())+'&id='+self.mainID
        print 'nianbaourl:', url
        r = self.get_request(url=url)
        soup = BeautifulSoup(r.text, 'html5lib')
        soup = soup.find(class_='panel_state_content')
        # print '****niaobao_soup****', soup
        div_list = soup.find_all('div', recursive=False)

        year_opt = div_list[0].select('option')[1]
        nball = div_list[0].select('option')[1:]
        for yb in nball:
            yr = yb.text.strip()[:4]
            yid = yb.get('value').strip()
            print '**', yr, '*', yid
        # for y in year_opt:
        print 'year', year_opt
        self.y = year_opt.text.strip()[:4]
        cnt = 0
        for div in div_list[1:]:
            cnt += 1
            dn = div.find_all('span')[0].text.strip()
            print cnt, dn
            if dn == u'基本信息':
                self.load_nianbaojiben(div)
            elif dn == u'网站或网店信息':
                self.load_nianbaowangzhan(div)
            elif dn == u'股东及出资信息':
                self.load_nianbaogudongchuzi(div)
            elif dn == u'对外投资信息':
                self.load_nianbaoduiwaitouzi(div)
            elif dn == u'企业资产状况信息':
                self.load_nianbaozichanzhuangkuang(div)
            elif dn == u'对外提供保证担保信息':
                self.load_nianbaoduiwaidanbao(div)
            elif dn == u'股权变更信息':
                self.load_nianbaoguquanbiangeng(div)
            elif dn == u'修改记录':
                self.load_nianbaoxiugai(div)
            else:
                print u'未知区域div，看看是什么', dn

    def load_nianbaojiben(self, soup):
        family = 'report_base'
        table_id = '40'
        tr_element_list = soup.find_all('tr')#(".//*[@id='jbxx']/table/tbody/tr")
        values = {}
        json_list = []
        for tr_element in tr_element_list[1:]:
            # th_element_list = tr_element.find_all('th')
            td_element_list = tr_element.find_all('td')
            for td in td_element_list:
                if td.text.strip():
                    td_list = td.text.replace(u'·', '').replace(u' ', '').strip().replace(u' ', '').split(u'：',1)
                    col = td_list[0].strip()
                    val = td_list[1].strip()
                    # print col, val
                    col = qiyenianbaojiben_column_dict[col]
                    values[col] = val
        values['rowkey'] = '%s_%s_%s_' %(self.cur_mc, self.y, table_id)
        values[family + ':registrationno'] = self.cur_zch
        values[family + ':enterprisename'] = self.cur_mc
        json_list.append(values)
        if json_list:
            # print 'nianbaojibenxinxi', json_list
            self.json_result[family] = json_list

    def load_nianbaowangzhan(self, soup):
        family = 'web_site'
        table_id = '41'
        values = {}
        json_list = []
        try:
            tr_num = len(soup.find_all(class_='detailsList'))
        except:
            tr_num = 0
        # print 'lentr', tr_num
        if tr_num > 1:
            gd_th = soup.find_all(class_='detailsList')[0].find_all('th')
            # print 'th_previous',cc.find(id='altDiv').find_previous_sibling().text
            try:
                iftr = soup.find_all(class_='detailsList')[1].find_all('tr')
            except:
                iftr = []
            if len(iftr) > 0:
                cnt = 1
                for i in range(len(iftr)):
                    if iftr[i].text.strip():
                        gd_td = iftr[i].find_all('td')
                        for j in range(len(gd_th)):
                            th = gd_th[j].text.strip()
                            td = gd_td[j].text.strip()
                            # print i,j,th,td
                            values[qiyenianbaowangzhan_column_dict[th]] = td
                        values['rowkey'] = '%s_%s_%s_%d' %(self.cur_mc, self.y, table_id, cnt)
                        values[family + ':registrationno'] = self.cur_zch
                        values[family + ':enterprisename'] = self.cur_mc
                        values[family + ':id'] = str(cnt)
                        json_list.append(values)
                        values = {}
                        cnt += 1
                if json_list:
                    print 'nianbaowangzhan', json_list
                    self.json_result[family] = json_list

    def load_nianbaogudongchuzi(self, soup):
        family = 'enterprise_shareholder'
        table_id = '42'
        values = {}
        json_list = []
        try:
            tr_num = len(soup.find_all(class_='detailsList'))
        except:
            tr_num = 0

        if tr_num > 1:
            gd_th = soup.find_all(class_='detailsList')[0].find_all('th')
            # print 'th_previous',cc.find(id='altDiv').find_previous_sibling().text
            try:
                iftr = soup.find_all(class_='detailsList')[1].find_all('tr')
            except:
                iftr = []
            if len(iftr) > 0:
                cnt = 1
                for i in range(len(iftr)):
                    if iftr[i].text.strip():
                        gd_td = iftr[i].find_all('td')
                        for j in range(len(gd_th)):
                            th = gd_th[j].text.strip()
                            td = gd_td[j].text.strip()
                            # print i,j,th,td
                            values[qiyenianbaogudong_column_dict[th]] = td
                        values['rowkey'] = '%s_%s_%s_%d' %(self.cur_mc, self.y, table_id, cnt)
                        values[family + ':registrationno'] = self.cur_zch
                        values[family + ':enterprisename'] = self.cur_mc
                        values[family + ':id'] = str(cnt)
                        json_list.append(values)
                        values = {}
                        cnt += 1
                if json_list:
                    print 'nianbaogudongchuzi', json_list
                    self.json_result[family] = json_list

    def load_nianbaoduiwaitouzi(self, soup):
        family = 'investment'
        table_id = '47'
        values = {}
        json_list = []

        try:
            tr_num = len(soup.find_all(class_='detailsList'))
        except:
            tr_num = 0

        if tr_num > 1:
            gd_th = soup.find_all(class_='detailsList')[0].find_all('th')
            # print 'th_previous',cc.find(id='altDiv').find_previous_sibling().text
            try:
                iftr = soup.find_all(class_='detailsList')[1].find_all('tr')
            except:
                iftr = []

            if len(iftr) > 0:
                cnt = 1
                for i in range(len(iftr)):
                    if iftr[i].text.strip():
                        gd_td = iftr[i].find_all('td')
                        for j in range(len(gd_th)):
                            th = gd_th[j].text.strip()
                            td = gd_td[j].text.strip()
                            # print i,j,th,td
                            values[qiyenianbaoduiwaitouzi_column_dict[th]] = td
                        values['rowkey'] = '%s_%s_%s_%d' %(self.cur_mc, self.y, table_id, cnt)
                        values[family + ':registrationno'] = self.cur_zch
                        values[family + ':enterprisename'] = self.cur_mc
                        values[family + ':id'] = str(cnt)
                        json_list.append(values)
                        values = {}
                        cnt += 1
                if json_list:
                    print 'nianbaoduiwaitouzi', json_list
                    self.json_result[family] = json_list

    def load_nianbaozichanzhuangkuang(self, soup):
        family = 'industry_status'
        table_id = '43'

        tr_element_list = soup.find_all("tr")
        values = {}
        json_list = []
        for tr_element in tr_element_list[1:]:
            # th_element_list = tr_element.find_all('th')
            td_element_list = tr_element.find_all('td')
            if len(td_element_list) > 0:
                col_nums = len(td_element_list)
                for i in range(col_nums/2):
                    col = td_element_list[i*2].get_text().strip().replace('\n','')
                    val = td_element_list[i*2+1].get_text().strip().replace('\n','')
                    if col != u'':
                        values[qiyenianbaozichanzhuangkuang_column_dict[col]] = val
#                     print col,val
        values['rowkey'] = '%s_%s_%s_' %(self.cur_mc, self.y, table_id)
        values[family + ':registrationno'] = self.cur_zch
        values[family + ':enterprisename'] = self.cur_mc
        json_list.append(values)
        if json_list:
            print 'json_nianbaozichan', json_list
            self.json_result[family] = json_list

    def load_nianbaoduiwaidanbao(self, soup):
        family = 'guarantee'
        table_id = '44'
        values = {}
        json_list = []

        try:
            tr_num = len(soup.find_all(class_='detailsList'))
        except:
            tr_num = 0

        if tr_num > 1:
            gd_th = soup.find_all(class_='detailsList')[0].find_all('th')
            # print 'th_previous',cc.find(id='altDiv').find_previous_sibling().text
            try:
                iftr = soup.find_all(class_='detailsList')[1].find_all('tr')
            except:
                iftr = []
            if len(iftr) > 0:
                cnt = 1
                for i in range(len(iftr)):
                    if iftr[i].text.strip():
                        gd_td = iftr[i].find_all('td')
                        for j in range(len(gd_th)):
                            th = gd_th[j].text.strip()
                            td = gd_td[j].text.strip()
                            # print i,j,th,td
                            values[qiyenianbaoduiwaidanbao_column_dict[th]] = td
                        values['rowkey'] = '%s_%s_%s_%d' %(self.cur_mc, self.y, table_id, cnt)
                        values[family + ':registrationno'] = self.cur_zch
                        values[family + ':enterprisename'] = self.cur_mc
                        values[family + ':id'] = str(cnt)
                        json_list.append(values)
                        values = {}
                        cnt += 1
                if json_list:
                    print 'nianbaoduiwaidanbao', json_list
                    self.json_result[family] = json_list

    def load_nianbaoguquanbiangeng(self, soup):
        family = 'equity_transfer'
        table_id = '45'
        values = {}
        json_list = []

        try:
            tr_num = len(soup.find_all(class_='detailsList'))
        except:
            tr_num = 0

        if tr_num > 1:
            gd_th = soup.find_all(class_='detailsList')[0].find_all('th')
            # print 'th_previous',cc.find(id='altDiv').find_previous_sibling().text
            try:
                iftr = soup.find_all(class_='detailsList')[1].find_all('tr')
            except:
                iftr = []
            if len(iftr) > 0:
                cnt = 1
                for i in range(len(iftr)):
                    if iftr[i].text.strip():
                        gd_td = iftr[i].find_all('td')
                        for j in range(len(gd_th)):
                            th = gd_th[j].text.strip()
                            td = gd_td[j].text.strip()
                            # print i,j,th,td
                            values[qiyenianbaoguquanbiangeng_column_dict[th]] = td
                        values['rowkey'] = '%s_%s_%s_%d' %(self.cur_mc, self.y, table_id, cnt)
                        values[family + ':registrationno'] = self.cur_zch
                        values[family + ':enterprisename'] = self.cur_mc
                        values[family + ':id'] = str(cnt)
                        json_list.append(values)
                        values = {}
                        cnt += 1
                if json_list:
                    print 'nianbaoguquanbiangeng', json_list
                    self.json_result[family] = json_list

    def load_nianbaoxiugai(self, soup):
        family = 'modify'
        table_id = '46'
        values = {}
        json_list = []

        try:
            tr_num = len(soup.find_all(class_='detailsList'))
        except:
            tr_num = 0

        if tr_num > 1:
            gd_th = soup.find_all(class_='detailsList')[0].find_all('th')
            # print 'th_previous',cc.find(id='altDiv').find_previous_sibling().text
            try:
                iftr = soup.find_all(class_='detailsList')[1].find_all('tr')
            except:
                iftr = []
            if len(iftr) > 0:
                cnt = 1
                for i in range(len(iftr)):
                    if iftr[i].text.strip():
                        gd_td = iftr[i].find_all('td')
                        for j in range(len(gd_th)):
                            th = gd_th[j].text.strip()
                            td = gd_td[j].text.strip()
                            # print i,j,th,td
                            values[qiyenianbaoxiugaijilu_column_dict[th]] = td
                        values['rowkey'] = '%s_%s_%s_%d' %(self.cur_mc, self.y, table_id, cnt)
                        values[family + ':registrationno'] = self.cur_zch
                        values[family + ':enterprisename'] = self.cur_mc
                        values[family + ':id'] = str(cnt)
                        json_list.append(values)
                        values = {}
                        cnt += 1
                if json_list:
                    print 'nianbaoxiugai', json_list
                    self.json_result[family] = json_list

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

    def get_request(self, url, params={}, verify=True, t=0, release_lock_id=False):
        """
        发送get请求,包含添加代理,锁定ip与重试机制
        :param url: 请求的url
        :param params: 请求参数
        :param verify: 忽略ssl
        :param t: 重试次数
        :param release_lock_id: 是否需要释放锁定的ip资源
        """
        try:
            if self.use_proxy:
                if not release_lock_id:
                    self.headers['Proxy-Authorization'] = self.proxy_config.get_auth_header(lock_id=self.lock_id)
                else:
                    self.headers['Proxy-Authorization'] = self.proxy_config.get_auth_header(lock_id=self.lock_id, release_id=self.lock_id)
            r = self.session.get(url=url, headers=self.headers, data=params, verify=verify)
            if r.status_code != 200:
                print u'错误的响应代码 -> %d' % r.status_code, url
                raise RequestException()
            return r
        except RequestException, e:
            if t == 15:
                raise e
            else:
                return self.get_request(url, params, verify, t+1, release_lock_id)

    def post_request(self, url, params={}, verify=True, t=0, release_lock_id=False):
        """
        发送post请求,包含添加代理,锁定ip与重试机制
        :param url: 请求的url
        :param params: 请求参数
        :param verify: 忽略ssl
        :param t: 重试次数
        :param release_lock_id: 是否需要释放锁定的ip资源
        :return:
        """
        try:
            if self.use_proxy:
                if not release_lock_id:
                    self.headers['Proxy-Authorization'] = self.proxy_config.get_auth_header(lock_id=self.lock_id)
                else:
                    self.headers['Proxy-Authorization'] = self.proxy_config.get_auth_header(lock_id=self.lock_id, release_id=self.lock_id)
            r = self.session.post(url=url, headers=self.headers, data=params, verify=verify)
            if r.status_code != 200:
                print u'错误的响应代码 -> %d' % r.status_code, url
                raise RequestException()
            return r
        except RequestException, e:
            if t == 15:
                raise e
            else:
                return self.post_request(url, params, verify, t+1, release_lock_id)

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
    searcher = QingHai()
    searcher.submit_search_request(u"青海邦业工贸有限公司")
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
