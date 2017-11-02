# coding=utf-8

import json
import os
import re
import sys
import uuid
from bs4 import BeautifulSoup
import PackageTool
from requests.exceptions import RequestException
from urllib import quote
from Tables_dict import *
from gs.KafkaAPI import KafkaAPI
from gs.ProxyConf import *
from gs.Searcher import Searcher
from gs.Searcher import get_args
from gs.TimeUtils import *


class XinJiang(Searcher):

    json_result = {}
    pattern = re.compile("\s")
    save_tag_a = True
    flag = True
    cur_time = None

    cur_mc = None
    cur_zch = None
    entName = None
    entId = None
    entNo = None
    creditt = None
    credit_ticket = None
    timeout = 60

    def __init__(self):
        super(XinJiang, self).__init__(use_proxy=False)
        # self.session = requests.session()
        # self.session.proxies = {'http': '123.56.238.200:8123', 'https': '123.56.238.200:8123'}
        # self.session.proxies = {'http': '121.28.134.29:80'}

        self.headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:47.0) Gecko/20100101 Firefox/47.0",
                        "Host": "gsxt.xjaic.gov.cn:7001",
                        "Accept": "*/*",
                        "Accept-Encoding": "gzip, deflate",
                        "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
                        "Connection": "keep-alive",
                        "Referer": "http://gsxt.xjaic.gov.cn:7001/ztxy.do?method=index&random="+get_cur_ts_sec(),
                        # "Upgrade-Insecure-Requests": "1",
                        # "Content-type": "application/json"
                        }
        # self.cur_time = '%d' % (time.time() * 1000)
        self.get_credit_ticket()
        self.json_result = {}  # json输出结果
        self.domain = 'http://gsxt.xjaic.gov.cn:7001'
        self.set_config()
        self.cao = u'请输入营业执照注册号或统一社会信用代码'
        self.log_name = self.topic + "_" + str(uuid.uuid1())

    def set_config(self):
        self.plugin_path = sys.path[0] + r'\..\xin_jiang\ocr\xinjiang.bat'
        self.group = 'Crawler'  # 正式
        self.kafka = KafkaAPI("GSCrawlerResult")  # 正式
        # self.group = 'CrawlerTest'  # 测试
        # self.kafka = KafkaAPI("GSCrawlerTest")  # 测试
        self.topic = 'GsSrc65'
        self.province = u'新疆维吾尔自治区'
        self.kafka.init_producer()

    def download_yzm(self):
        # self.lock_id = self.proxy_config.get_lock_id()
        self.cur_time = '%d' % (time.time() * 1000)
        params = {'currentTimeMillis': self.cur_time}
        # image_url = 'http://qyxy.baic.gov.cn/CheckCodeCaptcha'
        image_url = "http://gsxt.xjaic.gov.cn:7001/ztxy.do?method=createYzm&dt="+get_cur_ts_sec()+"&random="+get_cur_ts_sec()
        r = self.get_request(url=image_url,  params=params)
        # self.update_lock_time()
        # self.info(u'uuid: %s, lockid: %d' % (self.uuid, self.lock_id)
        # self.info(r.headers
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
        # self.info('credit_headers',r.headers
        # soup = BeautifulSoup(r.text, 'lxml')
        # # self.info(soup
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
        url = 'http://gsxt.xjaic.gov.cn:7001/ztxy.do?method=index&random='+get_cur_ts_sec()
        self.flag = self.get_the_mc_or_code(keyword)
        for t in range(100):
            # self.info(u'验证码识别中...第%s次' %(t+1)
            self.info(u'验证码识别中...第%s次' %(t+1))
            self.today = str(datetime.date.today()).replace('-', '')
            yzm = self.get_yzm()
            # self.info('yzm', yzm
            # pName = quote(self.cao.encode('gb2312'))
            # entname = quote(keyword.encode('gb2312'))
            pName = self.cao.encode('gb2312')
            try:
                entname = keyword.encode('gb2312')
            except:
                # self.info(u'公司有特殊字符或乱码'
                return None
            # self.info('pName:', pName, 'entName:', entname
            self.headers['Referer'] = 'http://gsxt.xjaic.gov.cn:7001/ztxy.do?method=index&random=' + get_cur_ts_sec()
            url = 'http://gsxt.xjaic.gov.cn:7001/ztxy.do?method=list&djjg=&random=' + get_cur_ts_sec()
            params = {'BA_ZCH': pName,
                      'currentPageNo': 1,
                      'maent.entname': entname,
                      'pName': pName,
                      'yzm': yzm
                      }
            # self.info(params
            r = self.post_request(url=url, params=params)
            # self.info('r.headers',r.headers
            r.encoding = 'gb2312'
            # self.info(r.text
            soup = BeautifulSoup(r.text, 'html5lib')
            try:
                tgr = soup.find(class_='se-yichang').find_next_sibling()
                # self.info('********************maimaiti*****************', tgr
                # self.info('soup',soup,'202',soup.find(id='alert_win').find(id='MzImgExpPwd').get('alt')

                if u'您搜索的条件无查询结果' in tgr.text:
                    # self.info(u'**********验证码识别通过**********查询无结果**'
                    self.info(u'**********验证码识别通过**********查询无结果**')
                    break
                if tgr:
                    # self.info('r.headers', r.headers
                    # self.info(u'**********验证码识别通过************'  #,  tgr
                    self.info(u'**********验证码识别通过************')
                    if tgr.text.strip() != '':
                        return tgr.find_all('ul')[0].find_all('li')
                    break
            except:
                self.info(u'验证码识别错误')
        return None

    def get_search_args(self, tag_a, keyword):
        # self.info('tag_a', tag_a
        name = tag_a[0].a.text    # name为公司查询结果名；keyword为查询前数据库公司名
        name_link = tag_a[0].a.get('onclick')
        para_list = re.search(u'(?<=[(]).*(?=[)])',name_link).group()
        pripid = para_list.split(',')[0].strip("'")
        entbigtype = para_list.split(',')[1].strip("'")
        entunknown = para_list.split(',')[2].strip("'")
        code = tag_a[1].find_all('span')[0].text    # 注册号
        self.xydm = ''
        self.zch = ''
        if len(code) == 18:
            self.xydm = code
        else:
            self.zch = code
        self.cur_mc = name.replace('(', u'（').replace(')', u'）')
        self.cur_zch = code

        self.pripid = pripid
        self.entbigtype = entbigtype
        self.entunknown = entunknown
        # self.info('get_search_args', self.cur_mc, self.cur_zch, self.pripid
        if self.flag:
            if self.cur_mc == keyword:
                # self.info('aa'
                return 1
            else:
                # self.info('else'
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
        # self.info('*************************hihi**********************'
        url = 'http://gsxt.xjaic.gov.cn:7001/ztxy.do'
        params = {'djjg': '', 'maent.entbigtype': self.entbigtype, 'maent.pripid': self.pripid,
                  'method': 'qyInfo', 'random': get_cur_ts_sec()}
        r = self.post_request(url=url, params=params)
        # self.info('rtex',r.status_code
        soup = BeautifulSoup(r.text, 'html5lib')
        # self.info('soup', soup.find(class_='dConBox')
        bd = soup.find(class_='dConBox')

        self.get_ji_ben(bd)
        # self.info('jb_step_json', self.json_result
        self.get_gu_dong(bd)
        # self.info('gd_step_json', self.json_result
        self.get_bian_geng(bd)
        # self.info('bg_step_json', self.json_result
        self.get_zhu_yao_ren_yuan(bd)
        self.get_fen_zhi_ji_gou(bd)
        # # self.get_qing_suan(kwargs)
        self.get_dong_chan_di_ya(bd)
        self.get_gu_quan_chu_zhi(bd)
        self.get_xing_zheng_chu_fa(bd)
        self.get_jing_ying_yi_chang(bd)
        self.get_yan_zhong_wei_fa(bd)
        self.get_chou_cha_jian_cha(bd)
        # self.info('the_last_json_result', len(self.json_result), self.json_result

        json_go = json.dumps(self.json_result, ensure_ascii=False)
        # self.info('the_last_json_result:', len(self.json_result), get_cur_time()   ,  json_go

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
        # # self.info('jiben_url', url
        # r = self.get_request(url=url, params={})
        # # r.encoding = 'gbk'
        # r.encoding = 'utf-8'
        # soup = BeautifulSoup(r.text, 'html5lib')
        soup = bd
        # self.info('*******ji_ben*******', soup
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
        values[family + ':tyshxy_code'] = self.xydm
        values[family + ':zch'] = self.zch
        values[family + ':lastupdatetime'] = get_cur_time()
        values[family + ':province'] = u'新疆维吾尔自治区'
        json_list.append(values)
        self.json_result[family] = json_list
        # self.info('jiben_values', values

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
            url = soup.find(id='table_fr').text  # 此处url不是连接地址，是判断内容是否为空的参数
        except:
            url = ''
        # self.info('gudong_url', self.cur_time,url
        if url:
            soup = aa.find(id='table_fr')
            # self.info('*******gudong*******', soup
            # self.info('gu_dong_turn_page', turn_page
            # self.info('body_tr',len(soup.select('#table2 tr a')),soup.select('#table2 tr a')
            # self.info('gd_tr1',soup.select('#tr1')

            gd_th = aa.find(id='table_fr').find_all('tr')[1].find_all('th')
            thn = len(gd_th)
            if thn == 4:
                family = 'Partner_Info'
            elif thn == 6:
                family = 'DIC_Info'
            elif thn == 2:
                family = 'Investor_Info'
            else:
                family = 'Shareholder_Info'
            iftr = soup.find_all('tr')[2:-1]
            if len(iftr) > 0:
                cnt = 1
                for i in range(len(iftr)):
                    gd_td = iftr[i].find_all('td')
                    for j in range(len(gd_th)):
                        th = gd_th[j].text.strip()
                        td = gd_td[j].text.strip()
                        if td == u'详情':
                            td = gd_td[j].a.get('onclick')
                            # self.info('gudong', td
                            td = re.search(r'(?<=[(]).*(?=[)])', td).group().strip("'")
                            detail_url = td
                            # self.info('detail_url', detail_url
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
                # self.info('-,-**gudong_json_list', len(json_list), json_list

    def get_gu_dong_detail(self, url, values):
        """
        查询股东详情
        :param param_pripid:
        :param param_invid:
        :return:
        """
        family = 'Shareholder_Info'
        table_id = '04'
        xh = url.split(',')[0].replace("'",'')
        # self.info('gudong_detail_url',url
        url = 'http://gsxt.xjaic.gov.cn:7001/ztxy.do'
        params = {'maent.pripid': self.pripid, 'maent.xh': xh,
                  'method': 'tzrCzxxDetial', 'random': get_cur_ts_sec()}
        r = self.post_request(url=url, params=params)
        # r.encoding = 'gbk'
        soup = BeautifulSoup(r.text, 'html5lib')
        # self.info('***__****gudong_detail*******',soup

        detail_tr_list = soup.find(id='sifapanding').find(class_='detailsList').find_all('tr')
        detail_th_list = ['subscripted_capital','actualpaid_capital','subscripted_method','subscripted_amount','subscripted_time','actualpaid_method','actualpaid_amount','actualpaid_time']
        detail_th_new_list = [family+':'+x for x in detail_th_list]
        # self.info('detail_th_new_list', detail_th_new_list
        # self.info('detailsLENS',len(detail_tr_list)
        for tr_ele in detail_tr_list[3:]:
            td_ele_list = tr_ele.find_all('td')[1:]
            detail_col_nums = len(td_ele_list)
            # self.info(detail_col_nums
            for m in range(detail_col_nums):
                col = detail_th_new_list[m]
                td = td_ele_list[m]
                val = td.text.strip()
                values[col] = val
                # self.info('II', col, val
        # self.info('gdl_values',len(values),values

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
        # self.info('*******biangeng*******',soup
        try:
            url = soup.find(id='biangeng').text
        except:
            url = ''

        if url:
            gd_th = cc.find(id='biangeng').find_all('tr')[1].find_all('th')
            # self.info('th_previous',cc.find(id='altDiv').find_previous_sibling().text
            iftr = cc.find(id='biangeng').find_all('tr')[2:-1]

            if len(iftr) > 0:
                cnt = 1
                for i in range(len(iftr)):
                    if iftr[i].text.strip() == u'':
                        self.info(u'变更数据结束')
                        break
                    gd_td = iftr[i].find_all('td')
                    for j in range(len(gd_th)):
                        th = gd_th[j].text.strip()
                        td = gd_td[j].text.strip()
                        if u'更多' in td:
                            td = gd_td[j].find_all('span')[1].text.strip().strip(u'收起更多')\
                                .replace('\n', '').replace('\t', '').replace(' ', '')
                        # self.info(i,j,th,td
                        json_dict[biangeng_column_dict[th]] = td
                    json_dict['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, cnt)
                    json_dict[family + ':registrationno'] = self.cur_zch
                    json_dict[family + ':enterprisename'] = self.cur_mc
                    json_dict[family + ':id'] = str(cnt)
                    json_list.append(json_dict)
                    json_dict = {}
                    cnt += 1

                self.json_result[family] = json_list
                # self.info('-,-**biangeng_json_list****', len(json_list), json_list

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
#                     self.info('row',row
                    row_data.append(row)
            if u'变更前' in bt:
                self.bgq = u'；'.join(row_data)
                # self.info('bgq',self.bgq
            elif u'变更后' in bt:
                self.bgh = u'；'.join(row_data)
                # self.info('bgh',self.bgh
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
        url = 'http://gsxt.xjaic.gov.cn:7001/ztxy.do'
        params = {'czmk':'czmk2','maent.pripid':self.pripid,
                  'method':'baInfo','random':get_cur_ts_sec()}
        r = self.post_request(url=url, params=params)
        soup = BeautifulSoup(r.text, 'html5lib')

        try:
            url = soup.find(id='beian').text
        except:
            url = ''
        # self.info('zhuyaorenyuan_url',self.cur_time,url
        if url:
            try:
                soup = soup.find(id='table_ry1')
                if not soup.text.strip():
                    soup = None
            except:
                soup = None

            # self.info('*******zhuyaorenyuan*******',soup
            if soup:
                iftr = soup.find_all('tr')
                gd_th = soup.find_all('tr')[1].find_all('th')

                # self.info('zhuyaorenyuan_turn_page', turn_page
                # self.info('body_tr',len(soup.select('#table2 tr a')),soup.select('#table2 tr a')
                # self.info('ry_tr1',soup.select('#tr1')
                idn = 1
                if len(iftr) > 2:
                    # self.info('zhuyaorenyuan*****'
                    tr_element_list = soup.find_all('tr')[2:-1]
                    # tr_element_list = soup.find_all(class_='detailsList')[0].find_all('tr')
                    # th_element_list = tr_element_list[1].find_all('th')
                    th_element_list = gd_th
                    for tr_element in tr_element_list:
                        if tr_element.text == u'':
                            self.info('zhuyaorenyuan_boom')
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

                    self.json_result[family] = json_list
                    # self.info('-,-**zhuyaorenyuan_json_list', len(json_list), json_list

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
        url = 'http://gsxt.xjaic.gov.cn:7001/ztxy.do'
        params = {'czmk':'czmk2','maent.pripid':self.pripid,
                  'method':'baInfo','random':get_cur_ts_sec()}
        r = self.post_request(url=url, params=params)
        soup = BeautifulSoup(r.text, 'html5lib')

        try:
            url = soup.find(id='beian').text
        except:
            url = ''
        # self.info('fenzhijigou_url',self.cur_time,url
        if url:
            try:
                soup = soup.find(id='table_fr2')
                if not soup.text.strip():
                    soup = None
            except:
                soup = None
            print '*******fenzhijigou*******',soup
            if soup:
                values = {}
                json_list = []
                gd_th = soup.find_all('tr')[1].find_all('th')
                iftr = soup.find_all('tr')

                if len(iftr) > 2:
                    tr_element_list = soup.find_all('tr')[2:]
                    th_element_list = gd_th
                    idn = 1
                    for tr_element in tr_element_list:
                        if tr_element.text.strip():
                            self.info('fenzhijigou_boom_breaker')
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
                        # self.info('json_fenzhijigou',json_fenzhijigou
                        values = {}
                        idn += 1

                    self.json_result[family] = json_list
                    # self.info('-,-**fenzhijigou_json_list', len(json_list), json_list

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
            # self.info(result_text
            result_text = result_text[len('$(document).ready(function()'):-2]

            start_idx = result_text.index('[')
            stop_idx = result_text.index(']') + len(']')
            result_text = result_text[start_idx:stop_idx]
            # self.info(result_text
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
        values = {}
        json_list = []

        soup = dd
        url = 'http://gsxt.xjaic.gov.cn:7001/ztxy.do'
        params = {'czmk':'czmk4','maent.pripid':self.pripid,
                  'method':'dcdyInfo','random':get_cur_ts_sec()}
        r = self.post_request(url=url, params=params)
        soup = BeautifulSoup(r.text, 'html5lib')

        try:
            url = soup.find(id='dongchandiya').text.strip()
        except:
            url = ''
        # self.info('*******dongchandiya*******',soup
        if url:
            soup = soup.find(id='dongchandiya')

            row_cnt = len(soup.find_all(class_="detailsList")[0].find_all('tr'))
            if row_cnt > 2:
                # self.info('come_on_bb_not_OK'
                tr_element_list = soup.find_all(class_="detailsList")[0].find_all('tr')[2:-1]
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
                            link = self.domain + td.a.get('onclick')
                            self.info(u'动产抵押详情%s' % link)
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
                    # self.info('json_dongchandiyadengji',json_dongchandiyadengji
                    values = {}
                    idn += 1
                self.info('-,-**dongchandiya_json_list')

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
        url = 'http://gsxt.xjaic.gov.cn:7001/ztxy.do'
        params = {'czmk':'czmk4','maent.pripid':self.pripid,
                  'method':'gqczxxInfo','random':get_cur_ts_sec()}
        r = self.post_request(url=url, params=params)
        soup = BeautifulSoup(r.text, 'html5lib')

        try:
            url = soup.find(id='guquanchuzhi').text.strip()
        except:
            url = ''
        # self.info('gudongchuzhi_url',self.cur_time,url
        if url:
            # self.info('*******guquanchuzhi*******',soup

            soup = soup.find(id='guquanchuzhi')
            tgr = soup.find_all(class_="detailsList")[0].find_all('tr')
            row_cnt = len(tgr)
            if row_cnt > 2:
                tr_element_list = soup.find_all(class_="detailsList")[0].find_all('tr')[2:-1]
                th_element_list = soup.find_all(class_="detailsList")[0].find_all('tr')[1].find_all('th')
                idn = 1
                for tr_element in tr_element_list:
                    if not tr_element.text.strip():
                        self.info(u'获取gqcz数据完成')
                        break
                    td_element_list = tr_element.find_all('td')
                    col_nums = len(th_element_list)
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n','')
                        # self.info('col_dec',col_dec
                        if col_dec == u'证照/证件号码' and th_element_list[j-1].text.strip().replace('\n','') == u'出质人':
                            # self.info('**',col_dec
                            col = guquanchuzhidengji_column_dict[col_dec]
                        elif col_dec == u'证照/证件号码' and th_element_list[j-1].text.strip().replace('\n','') == u'质权人':
                            # self.info('***',col_dec
                            col = guquanchuzhidengji_column_dict[u'证照/证件号码1']
                        else:
                            col = guquanchuzhidengji_column_dict[col_dec]
                        td = td_element_list[j]
                        val = td.text.strip()
                        if val == u'详情':
                            link = self.domain + td.a.get('onclick')  # 详情为onclick的post参数
                            self.info('gqcz_link%s' % link)
                            values[col] = link
                            # self.info(u'股权出质详情', link, 'fl', fake_link
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
                    # self.info('json_guquanchuzhidengji',json_guquanchuzhidengji
                    values = {}
                    idn += 1

                self.json_result[family] = json_list
                self.info('-,-**guquanchuzhi_json_list**')

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
        url = 'http://gsxt.xjaic.gov.cn:7001/ztxy.do'
        params = {'czmk':'czmk3','maent.pripid':self.pripid,
                  'method':'cfInfo','random':get_cur_ts_sec()}
        r = self.post_request(url=url, params=params)
        soup = BeautifulSoup(r.text, 'html5lib')
        # self.info('xingzhengchufasoup', soup.find(id='gsgsxx_xzcf')
        try:
            url = soup.find(id='gsgsxx_xzcf').text.strip()
        except:
            url = ''

        if url:
            # self.info('*******xingzhengchufa*******',soup
            soup = soup.find(id='gsgsxx_xzcf')
            row_cnt = len(soup.find_all(class_="detailsList")[0].find_all('tr'))
            if row_cnt > 2:
                tr_element_list = soup.find_all(class_="detailsList")[0].find_all('tr')[2:-1]
                th_element_list = soup.find_all(class_="detailsList")[0].find_all('tr')[1].find_all('th')
                idn = 1
                for tr_element in tr_element_list:
                    if not tr_element.text.strip():
                        # self.info(u'获取xzcf数据完成'
                        break
                    # self.info('******', tr_element.text.strip()
                    td_element_list = tr_element.find_all('td')
                    col_nums = len(th_element_list)
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n','')
                        col = xingzhengchufa_column_dict[col_dec]
                        td = td_element_list[j]
                        val = td.text.strip()
                        if val == u'详情':
                            val = self.domain+td.a.get('onclick')
                            self.info('xingzhengchufa__val%s' %val)
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
                    # self.info('json_xingzhengchufa',json_xingzhengchufa
                    values = {}
                    idn += 1
                self.json_result[family] = json_list
                # self.info('-,-**xingzhengchufa_jsonlist***', len(json_list), json_list

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

        url = 'http://gsxt.xjaic.gov.cn:7001/ztxy.do'
        params = {'czmk':'czmk6','maent.pripid':self.pripid,
                  'method':'jyycInfo','random':get_cur_ts_sec()}
        r = self.post_request(url=url, params=params)
        soup = BeautifulSoup(r.text, 'html5lib')
        # self.info('jingyingyichang', soup.find(id='yichangminglu')
        try:
            url = soup.find(id='yichangminglu').text.strip()
        except:
            url = ''
        # self.info('*******jingyingyichang*******',soup
        if url:
            soup = soup.find(id='yichangminglu')
            row_cnt = len(soup.find_all(class_="detailsList")[0].find_all('tr'))
            if row_cnt > 2:
                idn = 1
                tr_element_list = soup.find_all(class_="detailsList")[0].find_all('tr')[2:-1]
                th_element_list = soup.find_all(class_="detailsList")[0].find_all('tr')[1].find_all('th')
                for tr_element in tr_element_list:
                    if not tr_element.text.strip():
                        self.info(u'获取jyyc数据完成')
                        break
                    td_element_list = tr_element.find_all('td')
                    col_nums = len(th_element_list)
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n','')
                        # self.info('col_dec',col_dec
                        col = jingyingyichang_column_dict[col_dec]
                        td = td_element_list[j]
                        val = td.text.strip().replace('\t','').replace('\n','')
                        values[col] = val
                        # self.info('iii',col,val
                    # values['RegistrationNo']=self.cur_code
                    # values['EnterpriseName']=self.org_name
                    # values['rowkey'] = values['EnterpriseName']+'_14_'+ values['RegistrationNo']+'_'+str(id)
                    values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, idn)
                    values[family + ':registrationno'] = self.cur_zch
                    values[family + ':enterprisename'] = self.cur_mc
                    values[family + ':id'] = str(idn)
                    json_list.append(values)
                    # json_jingyingyichang=json.dumps(values,ensure_ascii=False)
                    # self.info('json_jingyingyichang',json_jingyingyichang
                    values = {}
                    idn += 1
                self.json_result[family] = json_list
                # self.info('-,-**jingyingyichang',json_list

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
        url = 'http://gsxt.xjaic.gov.cn:7001/ztxy.do'
        params = {'czmk':'czmk14','maent.pripid':self.pripid,
                  'method':'yzwfInfo','random':get_cur_ts_sec()}
        r = self.post_request(url=url, params=params)
        soup = BeautifulSoup(r.text, 'html5lib')

        try:
            url = soup.find(id='yanzhongweifa').text.strip()
        except:
            url = ''
        # self.info('*******yanzhongweifa*******',soup
        if url:
            soup = soup.find(id='yanzhongweifa')
            row_cnt = len(soup.find_all(class_="detailsList")[0].find_all('tr'))
            if row_cnt > 2:
                tr_element_list = soup.find_all(class_="detailsList")[0].find_all('tr')[2:-1]
                th_element_list = soup.find_all(class_="detailsList")[0].find_all('tr')[1].find_all('th')
                idn = 1
                for tr_element in tr_element_list:
                    if not tr_element.text.strip():
                        # self.info(u'获取yzwf数据完成'
                        break
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
                    # self.info('json_yanzhongweifa',json_yanzhongweifa
                    values = {}
                    idn += 1
                self.json_result[family] = json_list
                # self.info('-,-**yanzhongweifa_json_list', len(json_list), json_list

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
        url = 'http://gsxt.xjaic.gov.cn:7001/ztxy.do'
        params = {'czmk':'czmk7','maent.pripid':self.pripid,
                  'method':'ccjcInfo','random':get_cur_ts_sec()}
        r = self.post_request(url=url, params=params)
        soup = BeautifulSoup(r.text, 'html5lib')

        try:
            url = soup.find(id='chouchaxinxi').text.strip()
        except:
            url = ''
        # self.info('*******chouchajiancha*******',soup

        if url:
            soup = soup.find(id='chouchaxinxi')
            try:
                row_cnt = len(soup.find_all(class_='detailsList')[0].find_all('tr'))
            except:
                row_cnt = 0
            # self.info('ccjc_row_cnt',row_cnt

            if row_cnt > 2:
                # self.info('*****mmmm****'
                tr_element_list = soup.find_all(class_='detailsList')[0].find_all('tr')[2:-1]
                th_element_list = soup.find_all(class_='detailsList')[0].find_all('tr')[1].find_all('th')
                idn = 1
                for tr_element in tr_element_list:
                    if not tr_element.text.strip():
                        # self.info(u'获取ccjc数据完成'
                        break
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
                    # self.info('json_chouchajiancha',json_chouchajiancha
                    values = {}
                    idn += 1
                self.json_result[family] = json_list
                # self.info('-,-**chouchajiancha', len(json_list), json_list

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
    #         return self.session.post(url=url, headers=self.headers, params=params, timeout=5)
    #     except RequestException, e:
    #         if t == 5:
    #             raise e
    #         else:
    #             return self.post_request(url, params, t+1)


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
    searcher = XinJiang()
    searcher.submit_search_request(u"阿克苏科特计算机职业培训学校")
    # searcher.submit_search_request(u"阿塞拜疆丝绸之路航空有限责任公司驻乌鲁木齐代表处")
    #  和田沙合迪国际商贸有限公司")  # 博乐赛里木建筑安装工程有限责任公司")  # 乌苏市邦捷物业服务有限公司")
    # 乌苏市高清能源开发有限公司") # 阿塞拜疆丝绸之路航空有限责任公司驻乌鲁木齐代表处
    # 喀什市金龙房地产开发有限公司")#中国电信股份有限公司阿克陶加马铁力克乡营业厅")
    # rst = searcher.parse_detail(1)
    # self.info('rst',rst
    # searcher.get_credit_ticket()
    # self.info(searcher.credit_ticket
