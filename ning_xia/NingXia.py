# coding=utf-8

import requests
import os
import uuid
import subprocess
import PackageTool
from PIL import Image
from bs4 import BeautifulSoup
import json
import re
from gs.KafkaAPI import KafkaAPI
import datetime
from requests.exceptions import RequestException
import sys
import uuid
import time
from Tables_dict import *
from gs.Searcher import Searcher
from gs.Searcher import get_args
from gs.ProxyConf import *
from gs.TimeUtils import *
from ocr.NingxiaOcr import recognize_yzm


class NingXia(Searcher):

    json_result = {}
    pattern = re.compile("\s")
    save_tag_a = True
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
        super(NingXia, self).__init__(use_proxy=True)
        # self.session = requests.session()
        # self.session.proxies = {'http': '123.56.238.200:8123', 'https': '123.56.238.200:8123'}
        # self.session.proxies = {'http': '121.28.134.29:80'}

        self.headers = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Encoding": "gzip, deflate",
                        "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
                        "Connection": "keep-alive",
                        "Content-type": "application/x-www-form-urlencoded",
                        "Host": "gsxt.ngsh.gov.cn",
                        "Referer": "http://gsxt.ngsh.gov.cn/ECPS/index.jsp",
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:47.0) Gecko/20100101 Firefox/47.0"
                        }
        # self.cur_time = '%d' % (time.time() * 1000)
        self.get_credit_ticket()
        self.json_result = {}  # json输出结果
        self.iframe_name = {'qyjbqk': u'基本信息', 'tzrczxx': u'股东信息', 'qybgxx': u'变更信息',
                           'qybaxxzyryxx': u'主要人员信息', 'qybaxxfgsxx': u'分支机构信息', 'qybaxxqsxx': u'清算信息',
                            'gqczxx': u'股权出质登记信息', 'dcdyxx': u'动产抵押登记信息', 'jyycxx':u'经营异常信息',
                            'yzwfxx': u'严重违法信息', 'xzcfxx': u'行政处罚信息', 'ccjcxx':u'抽查检查信息'}
        self.domain = 'http://gsxt.ngsh.gov.cn/ECPS/'
        self.set_config()
        self.log_name = self.topic + "_" + str(uuid.uuid1())

    def set_config(self):
        self.plugin_path = sys.path[0] + r'\..\ning_xia\nxocr\ningxia.bat'
        # self.plugin_path = sys.path[0] + r'\ocr\ningxia.bat'
        self.group = 'Crawler'  # 正式
        self.kafka = KafkaAPI("GSCrawlerResult")  # 正式
        # self.group = 'CrawlerTest'  # 测试
        # self.kafka = KafkaAPI("GSCrawlerTest")  # 测试
        self.topic = 'GsSrc64'
        self.province = u'宁夏回族自治区'
        self.kafka.init_producer()
        self.log_name = self.topic + "_" + str(uuid.uuid1())

    def download_yzm(self):
        # self.lock_id = self.proxy_config.get_lock_id()
        self.cur_time = '%d' % (time.time() * 1000)
        params = {'currentTimeMillis': self.cur_time}
        # image_url = 'http://qyxy.baic.gov.cn/CheckCodeCaptcha'
        image_url = "http://gsxt.ngsh.gov.cn/ECPS/verificationCode.jsp?"
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

    def recognize_yzm(self, yzm_path):
        """
        识别验证码
        :param yzm_path: 验证码保存路径
        :return: 验证码识别结果
        """
        cmd = self.plugin_path + " " + yzm_path
        # print 'cmd:', cmd
        process = subprocess.Popen(cmd.encode('GBK', 'ignore'), stdout=subprocess.PIPE)
        process_out = process.stdout.read()
        answer = process_out.split('\r\n')[6].strip()
        return answer.decode('gbk', 'ignore')

    # def recognize_yzm(self, yzm_path):
    #     """
    #     识别验证码
    #     :param yzm_path: 验证码保存路径
    #     :return: 验证码识别结果
    #     """
    #     return recognize_yzm(yzm_path)

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
        os.remove(yzm_path)
        return yzm

    def get_tag_a_from_page(self, keyword, flags=0):
        return self.get_tag_a_from_page0(keyword)

    def get_tag_a_from_page0(self, keyword):
        # url0 = 'http://gsxt.ngsh.gov.cn/ECPS/index.jsp'
        # self.get_request(url=url0, params={})
        for t in range(50):
            # print u'验证码识别中...第%s次' %(t+1)
            self.info(u'验证码识别中...第%s次' %(t+1))
            self.today = str(datetime.date.today()).replace('-', '')
            yzm = self.get_yzm()
            # print 'yzm', yzm
            url = 'http://gsxt.ngsh.gov.cn/ECPS/qyxxgsAction_queryXyxx.action'
            params = {'isEntRecord': '', 'loginInfo.entname': '', 'loginInfo.idNo': '', 'loginInfo.mobile': '',
                      'loginInfo.password': '', 'loginInfo.regno': '', 'loginInfo.verificationCode': '',
                      'otherLoginInfo.name': '', 'otherLoginInfo.password': '', 'otherLoginInfo.verificationCode': '',
                      'password': yzm, 'selectValue': keyword}
            # print 'params:', params
            r = self.post_request(url=url, data=params)
            # print 'r.headers',r.headers
            r.encoding = 'utf-8'
            # print '**************************', r.text
            soup = BeautifulSoup(r.text, 'html5lib')
            # print 'soup:',soup
            # print '*******cpn_request_ok?:', soup.select('.list')[0], 'next_siblings', soup.select('.list')[0].find_next_sibling()
            # tgr = soup.find(id='alert_win').find(id='MzImgExpPwd').get('alt')
            if soup.find(class_='list'):
                # print 'r.headers', r.headers
                # print u'**********验证码识别通过************'  #, soup.find(class_='list')
                self.info(u'**********验证码识别通过************')
                if soup.find(class_='list').text.strip() != '':
                    return soup.select('.list')[0]
                else:
                    self.info(u'您搜索的条件无查询结果')
                    return None
        self.info(u'验证码加载失败')
        raise

    def get_search_args(self, tag_a, keyword):
        # print 'tag_a',tag_a  #不是连接地址tagA
        name = tag_a.find('a').text    # name为公司查询结果名；keyword为查询前数据库公司名
        name_link = tag_a.find('a').get('href')
        code = tag_a.find_all('span')[0].text    # 注册号
        tagA = self.domain +  name_link  # 验证码后连接地址

        self.cur_mc = name.replace('(', u'（').replace(')', u'）').strip()
        self.cur_zch = code
        self.tagA = tagA  # 宁夏三大参数，公司名称name，注册号code， 跳过验证码的地址tagA
        self.xydm_if = ''
        self.zch_if = ''
        if len(code) == 18:
            self.xydm_if = code
        else:
            self.zch_if = code
        # print u'公司名(name)cur_mc: %s, 注册号(code)cur_zch: %s, 链接地址tagA: %s' % (name, code, tagA)
        if self.cur_mc == keyword:
            return 1
        else:
            return 0

    def parse_detail(self):
        """
        解析公司详情信息
        :param kwargs:
        :return:
        """
        # print '****************HIHI************************',self.tagA
        # self.info(u'****parse**')
        r = self.get_request(self.tagA)
        # print r.text
        bs = BeautifulSoup(r.text,'html5lib')
        # print '#zhege iframe', bs  # , bs.select('#dConBox')[0], '**'
        self.nbxh = bs.find(id='nbxh').get('value')  # 内部序号，在xx详情link中可能用到，如股权出质详情
        self.qylx = bs.find(id='qylx').get('value')
        self.qymc = bs.find(id='qymc').get('value')
        self.zch = bs.find(id='zch').get('value')
        # print 'link_element:', 'nbxh', self.nbxh, 'qylx', self.qylx, 'qymc', self.qymc, 'zch', self.zch

        # print '&&&&&&&&&&&&&&&&&&&&&&&', len(bs.select('#dConBox div iframe')), bs.select('#dConBox div iframe')
        a = len(bs.select('#dConBox div iframe'))
        b = bs.select('#dConBox div iframe')
        for i in range(a):
            link = self.domain + b[i].get('src')
            imc = b[i].get('onload')
            # print i, imc,link
            if not imc:
                if u'Gtjbqk' in link:
                    self.iframe_src[u'Gtjbqk'] = link
            if imc:
                mc = re.search(r'(?<=[(]).*(?=[)])', imc).group().strip('"')
                # print '****&********', i, b[i], type(b[i]), '====='
                # print 'link:', i, link, '\n'
                self.iframe_src[mc] = link
        # print 'src', self.iframe_src
        # print 'um', self.iframe_src['dcdyxx']
        kwargs = ''
        self.get_ji_ben(kwargs)
        # print 'jb_step_json', self.json_result
        self.get_gu_dong(kwargs)
        # print 'gd_step_json', self.json_result
        self.get_bian_geng(kwargs)
        # print 'bg_step_json', self.json_result
        self.get_zhu_yao_ren_yuan(kwargs)
        self.get_fen_zhi_ji_gou(kwargs)
        # # self.get_qing_suan(kwargs)
        self.get_dong_chan_di_ya(kwargs)
        self.get_gu_quan_chu_zhi(kwargs)
        # self.get_xing_zheng_chu_fa(kwargs)
        self.get_jing_ying_yi_chang(kwargs)
        self.get_yan_zhong_wei_fa(kwargs)
        self.get_chou_cha_jian_cha(kwargs)
        # print 'the_last_json_result', len(self.json_result), self.json_result

        json_go = json.dumps(self.json_result, ensure_ascii=False)
        # print 'the_last_json_result:', len(self.json_result), get_cur_time(),  json_go

    def get_ji_ben(self, table_desc):
        """
        查询基本信息
        :return: 基本信息结果
        """
        json_list = []
        family = 'Registered_Info'
        table_id = '01'
        self.json_result[family] = []
        try:
            url = self.iframe_src['qyjbqk']
            # print 'jiben_url', url
        except:
            self.info(u'出现个体户信息')
            url = self.iframe_src[u'Gtjbqk']

        r = self.get_request(url=url, params={})
        # r.encoding = 'gbk'
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html5lib')
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
        values[family + ':province'] = u'宁夏回族自治区'
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
        try:
            url = self.iframe_src['tzrczxx']
        except:
            url = ''
        # print 'gudong_url', self.cur_time,url
        if url:
            r = self.get_request(url=url, params={})
            # r.encoding = 'gbk'
            soup = BeautifulSoup(r.text, 'html5lib')
            # print '*******gudong*******', soup
            turn_page = len(soup.find_all(class_='detailsList')[1].find_all('a'))    #判断是否有分页，需要post分页地址，暂不处理
            # print 'gu_dong_turn_page', turn_page
            # print 'body_tr',len(soup.select('#table2 tr a')),soup.select('#table2 tr a')
            # print 'gd_tr1',soup.select('#tr1')
            gd_th = soup.find_all(class_='detailsList')[0].find_all('tr')[1].find_all('th')
            iftr = soup.find_all(class_='detailsList')[0].find_all('tr')
            if len(iftr) > 2:
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
                for i in range(len(iftr[2:])):
                    gd_td = iftr[i+2].find_all('td')
                    for j in range(len(gd_th)):
                        th = gd_th[j].text.strip()
                        td = gd_td[j].text.strip()
                        if td == u'详情':
                            td = gd_td[j].a.get('href')
                            # print 'gudong', td
                            detail_url = self.domain+td
                            # print 'detail_url', detail_url
                            td = detail_url
                            try:
                                self.get_gu_dong_detail(detail_url, json_dict)
                                # self.info(u'股东详情不加载')
                            except:
                                self.info(u'股东详情打不开，忽略')
                            # self.load_func(td)  抓取详情页内容方法，见cnt分页内容
                                pass
                        if thn == 4:
                            try:
                                json_dict[hehuoren_column_dict[th]] = td
                            except KeyError:
                                return
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
                # 股东分页情况处理
                if turn_page > 3:
                    for p in range(2, turn_page-1):
                        linka = soup.find_all(class_='detailsList')[1].find_all('a')[p].get('href')
                        link = self.domain + linka
                        # print '***********gudongfenyelink******************', link
                        url = link
                        r = self.get_request(url=url, params={})
                        # r.encoding = 'gbk'
                        soup = BeautifulSoup(r.text, 'html5lib')
                        # print '*******gudong**fenye*****',soup
                        gd_th = soup.find_all(class_='detailsList')[0].find_all('tr')[1].find_all('th')
                        iftr = soup.find_all(class_='detailsList')[0].find_all('tr')
                        for i in range(len(iftr[2:])):
                            gd_td = iftr[i+2].find_all('td')
                            for j in range(len(gd_th)):
                                th = gd_th[j].text.strip()
                                td = gd_td[j].text.strip()
                                if td == u'详情':
                                    td = gd_td[j].a.get('href')
                                    # print 'gudong', td
                                    detail_url = self.domain+td
                                    # print 'detail_url', detail_url
                                    td = detail_url
                                    try:
                                        self.get_gu_dong_detail(detail_url, json_dict)
                                        # self.info(u'股东详情不加载')
                                    except:
                                        # print u'股东详情页面打不开，忽略'
                                        pass
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
        try:
            url = self.iframe_src['qybgxx']
            # print 'biangeng_url',self.cur_time,url
        except KeyError:
            # self.info(u'个体户变更信息不加载')
            return
        r = self.get_request(url=url, params={})
        # r.encoding = 'gbk'
        soup = BeautifulSoup(r.text, 'lxml')
        # print '*******biangeng*******',soup
        gd_th = soup.find_all(class_='detailsList')[0].find_all('tr')[1].find_all('th')
        iftr = soup.find_all(class_='detailsList')[0].find_all('tr')

        turn_page = len(soup.find_all(class_='detailsList')[1].find_all('a'))    # 判断是否有分页
        # print 'bian_geng_turn_page', turn_page
        # print 'body_tr',len(soup.select('#table2 tr a')),soup.select('#table2 tr a')
        # print 'bg_tr1',soup.select('#tr1')
        # print 'len_biangeng',len(soup.select('#tr1'))
        if len(iftr) > 2:
            cnt = 1
            for i in range(len(iftr[2:])):
                gd_td = iftr[i+2].find_all('td')
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

            if turn_page > 3 and '2' in soup.find_all(class_='detailsList')[1].text:
                # print 'biangeng_page_splitter***************'
                for p in range(2, turn_page-1):
                    linka = soup.find_all(class_='detailsList')[1].find_all('a')[p].get('href')
                    bgurl = self.domain + linka
                    # print 'biangeng_fen_ye_link', bgurl
                    rc = self.get_request(url = bgurl)
                    soup = BeautifulSoup(rc.text,'lxml')
                    # print 'biangeng_turn_soup', soup

                    gd_th = soup.find_all(class_='detailsList')[0].find_all('tr')[1].find_all('th')
                    iftr = soup.find_all(class_='detailsList')[0].find_all('tr')
                    for i in range(len(iftr[2:])):
                        gd_td = soup.find_all(class_='detailsList')[0].find_all('tr')[i+2].find_all('td')
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
        try:
            url = self.iframe_src['qybaxxzyryxx']
        except:
            url = ''
        # print 'zhuyaorenyuan_url',self.cur_time,url
        if url:
            r = self.get_request(url=url, params={})
            # r.encoding = 'gbk'
            soup = BeautifulSoup(r.text, 'lxml')
            # print '*******zhuyaorenyuan*******',soup
            gd_th = soup.find_all(class_='detailsList')[0].find_all('tr')[1].find_all('th')
            try:
                iftr = soup.find_all(class_='detailsList')[0].find_all('tr')
            except:
                iftr = 0
            try:
                turn_page = len(soup.find_all(class_='detailsList')[1].find_all('a'))    # 判断是否有分页
            except:
                turn_page = 0
            # print 'zhuyaorenyuan_turn_page', turn_page
            # print 'body_tr',len(soup.select('#table2 tr a')),soup.select('#table2 tr a')
            # print 'ry_tr1',soup.select('#tr1')
            gd_th = soup.find_all(class_='detailsList')[1].find_all('th')
            idn = 1
            if len(iftr) > 2:
                # print 'zhuyaorenyuan*****'
                tr_element_list = soup.find_all(class_='detailsList')[0].find_all('tr')
                th_element_list = tr_element_list[1].find_all('th')
                for tr_element in tr_element_list[2:]:
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

                if turn_page > 3:
                    for p in range(2, turn_page-1):
                        linka = soup.find_all(class_='detailsList')[1].find_all('a')[p].get('href')
                        url = self.domain + linka

                        r = self.get_request(url=url, params={})
                        # r.encoding = 'gbk'
                        soup = BeautifulSoup(r.text, 'lxml')
                        # print '*******zhuyaorenyuan*******',soup
                        gd_th = soup.find_all(class_='detailsList')[0].find_all('tr')[1].find_all('th')
                        iftr = soup.find_all(class_='detailsList')[0].find_all('tr')

                        # print 'zhuyaorenyuan_fenye_turn_page', turn_page
                        # print 'body_tr',len(soup.select('#table2 tr a')),soup.select('#table2 tr a')
                        # print 'ry_tr1',soup.select('#tr1')
                        gd_th = soup.find_all(class_='detailsList')[1].find_all('th')
                        tr_element_list = soup.find_all(class_='detailsList')[0].find_all('tr')
                        th_element_list = tr_element_list[1].find_all('th')
                        for tr_element in tr_element_list[2:]:
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
        try:
            url = self.iframe_src['qybaxxfgsxx']
        except:
            url = ''
        # print 'fenzhijigou_url',self.cur_time,url
        if url:
            r = self.get_request(url=url, params={})
            # r.encoding = 'gbk'
            soup = BeautifulSoup(r.text, 'lxml')
            # print '*******fenzhijigou*******',soup

            values = {}
            json_list = []
            # gd_th = soup.find_all(class_='detailsList')[0].find_all('tr')[1].find_all('th')
            try:
                iftr = soup.find_all(class_='detailsList')[0].find_all('tr')
            except:
                iftr = 0
            try:
                turn_page = len(soup.find_all(class_='detailsList')[1].find_all('a'))
            except:
                turn_page = 0

            # print 'fen_zhi_jigou_len_turn_page',turn_page
            # for i in range(turn_page):
            #     print i,soup.find(id='table2').find_all('tr')[-1].find_all('a')[i]
            # if u'...' in soup.find(id='table2').find_all('tr')[-1].text:
            #     print '************...*******'
            table_tr_elements = soup.find_all(class_='detailsList')[0].find_all('tr')
            if len(iftr) > 2:
                tr_element_list = soup.find_all(class_='detailsList')[0].find_all('tr')
                th_element_list = soup.find_all(class_='detailsList')[0].find_all('tr')[1].find_all('th')
                idn = 1
                for tr_element in tr_element_list[2:]:
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

                if turn_page > 3 and u'2' in soup.find_all(class_='detailsList')[1].text:
                    for p in range(2, turn_page-1):
                        linka = soup.find_all(class_='detailsList')[1].find_all('a')[p].get('href')
                        url = self.domain + linka

                        r = self.get_request(url=url, params={})
                        # r.encoding = 'gbk'
                        soup = BeautifulSoup(r.text, 'lxml')
                        # print '*******fenzhijigou_fenye*******',soup

                        values = {}
                        json_list = []
                        gd_th = soup.find_all(class_='detailsList')[0].find_all('tr')[1].find_all('th')
                        iftr = soup.find_all(class_='detailsList')[0].find_all('tr')

                        # print 'fen_zhi_jigou_len_turn_page',turn_page
                        table_tr_elements = soup.find_all(class_='detailsList')[0].find_all('tr')
                        if len(iftr) > 2:
                            tr_element_list = soup.find_all(class_='detailsList')[0].find_all('tr')
                            th_element_list = soup.find_all(class_='detailsList')[0].find_all('tr')[1].find_all('th')
                            for tr_element in tr_element_list[2:]:
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
        self.json_result[family] = []
        url = self.iframe_src['qybaxxqsxx']
        r = self.get_request(url)
        soup = BeautifulSoup(r.text, 'lxml')
        script_list = soup.select('html > head > script')
        if len(script_list) > 0:
            result_text = script_list[-1].text.strip()
            # print result_text
            result_text = result_text[len('$(document).ready(function()'):-2]

            start_idx = result_text.index('[')
            stop_idx = result_text.index(']') + len(']')
            result_text = result_text[start_idx:stop_idx]
            # print result_text
            result_json = json.loads(result_text)
        else:
            result_json = []
        cheng_yuan_list = []
        for j in result_json:
            cheng_yuan_list.append(j['liqmem'])
        cheng_yuan = ','.join(cheng_yuan_list)
        fu_ze_ren = ''
        fu_ze_ren_list = soup.select('html > body > table > thead > tr:nth-of-type(2) > td')
        if len(fu_ze_ren_list) > 0:
            fu_ze_ren = self.pattern.sub('', fu_ze_ren_list[0].text)
        result_json = []
        if cheng_yuan != '' and fu_ze_ren != '':
            result_json.append({'rowkey': '%s_%s_%s_' % (self.cur_mc, table_id, self.cur_zch),
                                family + ':' + 'liquidation_member': 'cheng_yuan',
                                family + ':' + 'liquidation_pic': 'fu_ze_ren',
                                family + ':registrationno': self.cur_zch,
                                family + ':enterprisename': self.cur_mc
                                })
            self.json_result[family].extend(result_json)

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
        values={}
        json_list=[]
        url = self.iframe_src['dcdyxx']
        # print 'dongchandiya_url',self.cur_time,url
        r = self.get_request(url=url, params={})
        # r.encoding = 'gbk'
        soup = BeautifulSoup(r.text, 'lxml')
        # print '*******dongchandiya*******',soup

        gd_th = soup.find_all(class_='detailsList')[0].find_all('tr')[1].find_all('th')
        iftr = soup.find_all(class_='detailsList')[0].find_all('tr')
        turn_page = len(soup.find_all(class_='detailsList')[1].find_all('a'))

        row_cnt = len(soup.find_all(class_="detailsList")[0].find_all('tr'))
        if row_cnt > 2:
            # print 'come_on_bb_not_OK'
            tr_element_list = soup.find_all(class_="detailsList")[0].find_all('tr')
            th_element_list = soup.find_all(class_="detailsList")[0].find_all('tr')[1].find_all('th')
            idn = 1
            for tr_element in tr_element_list[2:]:
                td_element_list = tr_element.find_all('td')
                col_nums = len(th_element_list)
                for j in range(col_nums):
                    col_dec = th_element_list[j].text.strip().replace('\n','')
                    col = dongchandiyadengji_column_dict[col_dec]
                    td = td_element_list[j]
                    val = td.text.strip()
                    if val == u'详情':
                        link = td.a.get('href')
                        # print ' 动产抵押详情', link
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
            if json_list:
                self.json_result[family] = json_list
                # print '-,-**dongchandiya_json_list',len(json_list),json_list

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
        try:
            url = self.iframe_src['gqczxx']
        except:
            url = ''
        # print 'gudongchuzhi_url',self.cur_time,url
        if url:
            r = self.get_request(url=url, params={})
            # r.encoding = 'gbk'
            soup = BeautifulSoup(r.text, 'lxml')
            # print '*******guquanchuzhi*******',soup

            gd_th = soup.find_all(class_='detailsList')[0].find_all('tr')[1].find_all('th')
            iftr = soup.find_all(class_='detailsList')[0].find_all('tr')
            # turn_page = len(soup.find_all(class_='detailsList')[1].find_all('a'))

            table_element = soup.select("detailsList")
            try:
                row_cnt = len(soup.find_all(class_="detailsList")[0].find_all('tr'))
            except:
                row_cnt = 0
            if row_cnt > 2:
                tr_element_list = soup.find_all(class_="detailsList")[0].find_all('tr')
                th_element_list = soup.find_all(class_="detailsList")[0].find_all('tr')[1].find_all('th')
                idn = 1
                for tr_element in tr_element_list[2:]:
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
                            link = td.a.get('onclick')
                            czxh = re.search(r'\d+', link).group()
                            # print 'czxh', czxh
                            fake_link = 'http://gsxt.ngsh.gov.cn/ECPS/gqczdjxxAction_bgxq.action?czxh='+czxh+'&zch='+self.zch+'&qymc='+self.qymc+'&nbxh='+self.nbxh
                            link = fake_link
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
        url = self.iframe_src['xzcfxx']
        # print 'xingzhengchufai_url',self.cur_time,url
        r = self.get_request(url=url, params={})
        # r.encoding = 'gbk'
        soup = BeautifulSoup(r.text, 'lxml')
        # print '*******xingzhengchufa*******',soup
        gd_th = soup.find_all(class_='detailsList')[0].find_all('tr')[1].find_all('th')
        iftr = soup.find_all(class_='detailsList')[0].find_all('tr')
        # turn_page = len(soup.find_all(class_='detailsList')[1].find_all('a'))
        try:
            row_cnt = len(soup.find_all(class_="detailsList")[0].find_all('tr'))
        except:
            row_cnt = 0
        if row_cnt > 2:
            tr_element_list = soup.find_all(class_="detailsList")[0].find_all('tr')
            th_element_list = soup.find_all(class_="detailsList")[0].find_all('tr')[1].find_all('th')
            idn = 1
            for tr_element in tr_element_list[2:]:
                td_element_list = tr_element.find_all('td')
                col_nums = len(th_element_list)
                for j in range(col_nums):
                    col_dec = th_element_list[j].text.strip().replace('\n','')
                    col=xingzhengchufa_column_dict[col_dec]
                    td = td_element_list[j]
                    val = td.text.strip()
                    if val == u'详情':
                        val = self.domain+td.a.get('href')
                        # print val
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
            self.json_result[family] = json_list
            # print '-,-**xingzhengchufa_jsonlist***', len(json_list), json_list
        # params = {'pripid': param_pripid, 'type': param_type}
        # result_json = self.get_result_json(url, params)
        # for j in result_json:
        #     self.json_result[family].append({})
        #     for k in j:
        #         if k in xing_zheng_chu_fa_dict:
        #             col = family + ':' + xing_zheng_chu_fa_dict[k]
        #             val = j[k]
        #             self.json_result[family][-1][col] = val
        # for i in range(len(self.json_result[family])):
        #     self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i)
        #     self.json_result[family][i][family + ':registrationno'] = self.cur_zch
        #     self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
        # print json.dumps(result_json_2, ensure_ascii=False)

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
        url = self.iframe_src['jyycxx']
        # print 'jingyingyichang_url',self.cur_time,url
        r = self.get_request(url=url, params={})
        # r.encoding = 'gbk'
        soup = BeautifulSoup(r.text, 'html5lib')
        # print '*******jingyingyichang*******',soup
        try:
            row_cnt = len(soup.find_all(class_="detailsList")[0].find_all('tr'))
        except:
            row_cnt = 0
        if row_cnt > 2:
            idn = 1
            tr_element_list = soup.find_all(class_="detailsList")[0].find_all('tr')
            th_element_list = soup.find_all(class_="detailsList")[0].find_all('tr')[1].find_all('th')
            for tr_element in tr_element_list[2:]:
                td_element_list = tr_element.find_all('td')
                col_nums = len(th_element_list)
                for j in range(col_nums):
                    col_dec = th_element_list[j].text.strip().replace('\n','')
                    # print 'col_dec',col_dec
                    col=jingyingyichang_column_dict[col_dec]
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
        url = self.iframe_src['yzwfxx']
        # print 'yanzhongweifa_url',self.cur_time,url
        r = self.get_request(url=url, params={})
        # r.encoding = 'gbk'
        soup = BeautifulSoup(r.text, 'lxml')
        # print '*******yanzhongweifa*******',soup
        try:
            row_cnt = len(soup.find_all(class_="detailsList")[0].find_all('tr'))
        except:
            row_cnt = 0
        if row_cnt > 2:
            tr_element_list = soup.find_all(class_="detailsList")[0].find_all('tr')[2:-1]
            th_element_list = soup.find_all(class_="detailsList")[0].find_all('tr')[1].find_all('th')
            idn = 1
            for tr_element in tr_element_list[2:]:
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
        url = self.iframe_src['ccjcxx']
        # print 'chouchajiancha_url',self.cur_time,url
        r = self.get_request(url=url, params={})
        # r.encoding = 'gbk'
        soup = BeautifulSoup(r.text, 'html5lib')
        # print '*******chouchajiancha*******',soup

        # row_cnt = len(soup.find_all('tbody'))  #结构和之前稍微不一样，不是tr，是3个tbody
        row_cnt = len(soup.find_all('tbody'))
        # print 'ccjc_row_cnt',row_cnt

        if row_cnt > 2:
            # print '*****mmmm****'
            tr_element_list = soup.find_all('tbody')[2].find_all('tr')[:-1]
            th_element_list = soup.find(id="tableChoucha").find_all('th')
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
    #         r = self.session.get(url=url, headers=self.headers, data=params, verify=verify)
    #         if r.status_code != 200:
    #             print u'错误的响应代码 -> %d' % r.status_code, url
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
    #         r = self.session.post(url=url, headers=self.headers, data=params, verify=verify)
    #         if r.status_code != 200:
    #             print u'错误的响应代码 -> %d' % r.status_code
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
    searcher = NingXia()
    searcher.submit_search_request(u"宁夏维尔铸造有限责任公司")#宁夏云飞扬文化传播有限公司")#宁夏云飞扬文化传播有限公司 贺兰县育才巷明朗眼镜店")#舍弗勒（宁夏）有限公司")#宁夏千里马管理咨询合伙企业（有限合伙）")
    # 宁夏回族自治区石油总公司")#宁夏东升科工贸有限公司")#吴忠市金鼎汽车运输有限公司")
    # 固原龙达货物运输有限公司")#同心县穆云石材工艺有限公司")  # 同心县穆云石材工艺有限公司
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
