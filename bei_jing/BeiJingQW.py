# coding=utf-8

import json
import os
import re
import sys

from bs4 import BeautifulSoup
from bei_jing.Tables_dict import *
from gs.KafkaAPI import KafkaAPI
from gs.ProxyConf import *
from gs.Searcher import Searcher
from gs.Searcher import get_args
from gs.TimeUtils import *
from gs.QuanWangProxy import get_proxy
from requests.exceptions import ReadTimeout
from requests.exceptions import ProxyError
import traceback


class BeiJingQW(Searcher):

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

    def __init__(self):
        super(BeiJingQW, self).__init__(use_proxy=True, lock_ip=False)
        self.headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:47.0) Gecko/20100101 Firefox/47.0",
                        "Host": "qyxy.baic.gov.cn",
                        "Accept": "*/*",
                        "Accept-Encoding": "gzip, deflate",
                        "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
                        "Connection": "keep-alive",
                        "Referer": "http://qyxy.baic.gov.cn/beijing",
                        "Upgrade-Insecure-Requests": "1",
                        "Content-type": "application/json"
                        }
        # self.cur_time = '%d' % (time.time() * 1000)
        self.json_result = {}  # json输出结果
        self.domain = 'http://qyxy.baic.gov.cn'
        self.set_config()
        # self.set_proxy()
        self.get_credit_ticket()

    def set_config(self):
        self.plugin_path = sys.path[0] + r'\..\bei_jing\ocr\beijing.bat'
        self.group = 'Crawler'  # 正式
        self.kafka = KafkaAPI("GSCrawlerResult")  # 正式
        # self.group = 'CrawlerTest'  # 测试
        # self.kafka = KafkaAPI("GSCrawlerTest")  # 测试
        self.topic = 'GsSrc11'
        self.province = u'北京市'
        self.kafka.init_producer()

    def download_yzm(self):
        # self.lock_id = self.proxy_config.get_lock_id()
        self.cur_time = '%d' % (time.time() * 1000)
        params = {'currentTimeMillis': self.cur_time}
        # image_url = 'http://qyxy.baic.gov.cn/CheckCodeCaptcha'
        image_url = "http://qyxy.baic.gov.cn/CheckCodeYunSuan"
        r = self.get_request_qw(url=image_url,  params=params)
        # self.update_lock_time()
        # print u'uuid: %s, lockid: %d' % (self.uuid, self.lock_id)
        # print r.headers
        yzm_path = self.get_yzm_path()
        with open(yzm_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    f.flush()
            f.close()
        return yzm_path

    def get_credit_ticket(self):
        try:
            print u'获取ticket'
            timeout_bak = self.timeout
            self.timeout = 5
            r = self.get_request('http://qyxy.baic.gov.cn/gjjbj/gjjQueryCreditAction!toIndex.dhtml')
            self.timeout = timeout_bak
            # print 'credit_headers',r.headers
            soup = BeautifulSoup(r.text, 'lxml')
            # print soup
            self.credit_ticket = soup.select('input#credit_ticket')[0].attrs['value']
        except:
            self.get_credit_ticket()

    def get_tag_a_from_db(self, keyword):
        return None

    def save_tag_a_to_db(self, keyword):
        pass

    def get_tag_a_from_page(self, keyword):
        self.reset_proxy_qw(force_change=False)
        # self.get_credit_ticket()
        for t in range(100):
            print u'验证码识别中...第%s次' %(t+1)
            self.today = str(datetime.date.today()).replace('-', '')
            yzm = self.get_yzm()
            # print 'yzm', yzm
            url = 'http://qyxy.baic.gov.cn/gjjbj/gjjQueryCreditAction!getBjQyList.dhtml'
            params = {'checkcode': yzm, 'keyword': keyword, 'currentTimeMillis': self.cur_time, 'credit_ticket': self.credit_ticket}
            # print params
            r = self.post_request_qw(url=url, params=params)
            # print 'r.headers',r.headers
            r.encoding = 'utf-8'
            # print r.text
            soup = BeautifulSoup(r.text, 'html5lib')
            # print 'soup',soup,'202',soup.find(id='alert_win').find(id='MzImgExpPwd').get('alt')
            # tgr = soup.find(id='alert_win').find(id='MzImgExpPwd').get('alt')
            if soup.find(class_='list'):
                # print 'r.headers', r.headers
                print u'**********验证码识别通过************'  # soup.find(class_='list')
                if soup.find(class_='list').text.strip() != '':
                    return soup.find(class_='list').find_all('ul')[0].find_all('li')
                break
        return None

    def get_search_args(self, tag_a, keyword):
        # print 'tag_a', tag_a
        name = tag_a[0].a.text    # name为公司查询结果名；keyword为查询前数据库公司名
        name_link = tag_a[0].a.get('onclick')
        para_list = re.search(u'(?<=[(]).*(?=[)])',name_link).group()
        ent_name = para_list.split(',')[0].strip("'")
        ent_id = para_list.split(',')[1].strip("'")
        ent_no = para_list.split(',')[2].strip("'")
        creditt = para_list.split(',')[3].strip().strip("'").replace("'",'')
        code = tag_a[1].find_all('span')[0].text    # 注册号
        self.xydm = ''
        self.zch = ''
        if len(code) == 18:
            self.xydm = code
        else:
            self.zch = code
        self.cur_mc = name.replace('(', u'（').replace(')', u'）')
        self.cur_zch = code
        self.entName = ent_name
        self.entId = ent_id
        self.entNo = ent_no
        self.creditt = creditt

        if self.cur_mc == keyword:
            return [0]
        else:
            return []

    def parse_detail(self, kwargs):
        """
        解析公司详情信息
        :param kwargs:
        :return:
        """
        print u'解析基本信息',time.ctime()
        self.get_ji_ben(kwargs)
        # print 'jb_step_json', self.json_result
        print u'解析股东信息', time.ctime()
        self.get_gu_dong(kwargs)
        # print 'gd_step_json', self.json_result
        print u'解析变更信息',time.ctime()
        self.get_bian_geng(kwargs)
        # print 'bg_step_json', self.json_result
        print u'解析主要人员',time.ctime()
        self.get_zhu_yao_ren_yuan(kwargs)
        print u'解析分支机构',time.ctime()
        self.get_fen_zhi_ji_gou(kwargs)
        # # self.get_qing_suan(kwargs)
        print u'解析动产抵押',time.ctime()
        self.get_dong_chan_di_ya(kwargs)
        print u'解析股权出质',time.ctime()
        self.get_gu_quan_chu_zhi(kwargs)
        print u'解析行政处罚',time.ctime()
        self.get_xing_zheng_chu_fa(kwargs)
        print u'解析经营异常',time.ctime()
        self.get_jing_ying_yi_chang(kwargs)
        # print u'解析严重违法',time.ctime()
        # self.get_yan_zhong_wei_fa(kwargs)
        print u'解析抽查检查',time.ctime()
        self.get_chou_cha_jian_cha(kwargs)
        # print 'the_last_json_result', len(self.json_result), self.json_result

        json_go = json.dumps(self.json_result, ensure_ascii=False)
        # print 'the_last_json_result:', len(self.json_result), get_cur_time()   ,  json_go

    def get_ji_ben(self, table_desc):
        """
        查询基本信息
        :return: 基本信息结果
        """
        json_list = []
        family = 'Registered_Info'
        table_id = '01'
        self.json_result[family] = []
        url = 'http://qyxy.baic.gov.cn/gjjbj/gjjQueryCreditAction!openEntInfo.dhtml?' \
              'entId=%s&credit_ticket=%s&entNo=%s&timeStamp=%s' % (self.entId, self.creditt,  self.entNo, self.cur_time)
        # print 'jiben_url', url
        # params = {'credit_ticket':self.credit_ticket,'entId':self.entId,'entNo':self.entNo,'timeStamp':self.cur_time}

        r = self.get_request(url=url, params={})
        # r.encoding = 'gbk'
        r.encoding = 'utf-8'
        # print '<*>', r.text
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
                        # print col_dec
                        col = jiben_column_dict[col_dec]
                        values[col] = val
        values['rowkey'] = '%s_%s_%s_' % (self.cur_mc, table_id, self.cur_zch)
        values[family + ':registrationno'] = self.cur_zch
        values[family + ':enterprisename'] = self.cur_mc
        values[family + ':tyshxy_code'] = self.xydm
        values[family + ':zch'] = self.zch
        values[family + ':lastupdatetime'] = get_cur_time()
        values[family + ':province'] = u'北京市'
        json_list.append(values)
        self.json_result[family] = json_list
        # print 'jiben_values',values

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
        url = 'http://qyxy.baic.gov.cn/gjjbj/gjjQueryCreditAction!tzrFrame.dhtml?ent_id=%s&entName=&clear=true&timeStamp=%s' %(self.entId,self.cur_time)
        # print 'gudong_url', self.cur_time,url
        r = self.get_request(url=url, params={})
        # r.encoding = 'gbk'
        soup = BeautifulSoup(r.text, 'lxml')
        # print '*******gudong*******',soup
        turn_page = len(soup.select('#table2 tr')[-1].find_all('a'))    #判断是否有分页，需要post分页地址，暂不处理
        # print 'gu_dong_turn_page', turn_page
        # print 'body_tr',len(soup.select('#table2 tr a')),soup.select('#table2 tr a')
        # print 'gd_tr1',soup.select('#tr1')
        gd_th = soup.select_one('#table2 tr').find_all('th')

        for i in range(len(soup.select('#tr1'))):
            gd_td = soup.select('#tr1')[i].find_all('td')
            for j in range(len(gd_th)):
                th = gd_th[j].text.strip()
                td = gd_td[j].text.strip()
                if td == u'详情':
                    td = gd_td[j].a.get('onclick')
                    # print 'gudong', td
                    chr_id = re.search(u'(?<=[(]).*(?=[)])',td).group().strip("'")
                    detail_url = 'http://qyxy.baic.gov.cn/gjjbj/gjjQueryCreditAction!touzirenInfo.dhtml?chr_id=%s&entName=&timeStamp=%s&fqr=' %(chr_id,self.cur_time)
                    # print 'detail_url', detail_url
                    td = detail_url
                    self.get_gu_dong_detail(detail_url, json_dict)
                    # self.load_func(td)  抓取详情页内容方法，见cnt分页内容
                json_dict[gudong_column_dict[th]]=td
            json_dict['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            json_dict[family + ':registrationno'] = self.cur_zch
            json_dict[family + ':enterprisename'] = self.cur_mc
            json_dict[family + ':id'] = str(i+1)
            json_list.append(json_dict)
            json_dict = {}

        #分页内容测试抓取
        cnt = 2
        if turn_page > 2 and '2' in soup.select('#table2 tr')[-1].text:
            for p in range(1, turn_page-1):
                if cnt > turn_page:
                    break
                post_url = 'http://qyxy.baic.gov.cn/%sgjjQueryCreditAction!tzrFrame.dhtml' %('gjjbj/'*cnt)
                params = {'clear':'', 'ent_id':self.entId, 'fqr':'', 'pageNo':p, 'pageNos':p+1, 'pageSize':5}
                rp = self.post_request(post_url,params=params)
                soup = BeautifulSoup(rp.text, 'lxml')
                turn_page = len(soup.select('#table2 tr a'))    #判断是否有分页，需要post分页地址，暂不处理
                gd_th = soup.select_one('#table2 tr').find_all('th')

                for i in range(len(soup.select('#tr1'))):
                    gd_td = soup.select('#tr1')[i].find_all('td')
                    for j in range(len(gd_th)):
                        th = gd_th[j].text.strip()
                        td = gd_td[j].text.strip()
                        if td==u'详情':
                            td=gd_td[j].a.get('onclick')
                            # print 'gudong',td
                            chr_id = re.search(u'(?<=[(]).*(?=[)])',td).group().strip("'")
                            detail_url = 'http://qyxy.baic.gov.cn/gjjbj/gjjQueryCreditAction!touzirenInfo.dhtml?chr_id=%s&entName=&timeStamp=%s&fqr=' %(chr_id,self.cur_time)
                            # print 'detail_url',detail_url
                            td = detail_url
                            self.get_gu_dong_detail(detail_url, json_dict)
                        json_dict[gudong_column_dict[th]] = td
                    json_dict['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1+p*5)
                    json_dict[family + ':registrationno'] = self.cur_zch
                    json_dict[family + ':enterprisename'] = self.cur_mc
                    json_dict[family + ':id'] = str(i+1+p*5)
                    json_list.append(json_dict)
                    json_dict = {}
                cnt += 1
        if json_list:
            self.json_result[family] = json_list

    def get_gu_dong_detail(self, url,values):
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
        detail_th_new_list=[family+':'+x for x in detail_th_list]
        # print 'detail_th_new_list', detail_th_new_list
        for tr_ele in detail_tr_list[3:-1]:
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
        url = 'http://qyxy.baic.gov.cn/gjjbj/gjjQueryCreditAction!biangengFrame.dhtml?ent_id=%s&entName=&clear=true&timeStamp=%s' %(self.entId,self.cur_time)
        # print 'biangeng_url',self.cur_time,url
        r = self.get_request(url=url, params={})
        # r.encoding = 'gbk'
        soup = BeautifulSoup(r.text, 'lxml')
        # print '*******biangeng*******',soup

        turn_page = len(soup.select('#table2 tr')[-1].find_all('a'))    #判断是否有分页，需要post分页地址，暂不处理
        # print 'bian_geng_turn_page',turn_page
        # print 'body_tr',len(soup.select('#table2 tr a')),soup.select('#table2 tr a')
        # print 'bg_tr1',soup.select('#tr1')
        result_if = len(soup.select('#tr1'))
        # print 'len_biangeng',len(soup.select('#tr1'))
        if result_if > 0:
            gd_th = soup.select('#table2 tr')[1].find_all('th')
            for i in range(len(soup.select('#tr1'))):
                gd_td = soup.select('#tr1')[i].find_all('td')
                if len(gd_td) == 4:
                    for j in range(len(gd_th)):
                        th = gd_th[j].text.strip()
                        td = gd_td[j].text.strip()
                        # print i,j,th,td
                        json_dict[biangeng_column_dict[th]]=td
                if len(gd_td) == 3:
                    linka = gd_td[1].a.get('onclick')
                    sub_ling = re.search(u'(?<=[(]).*(?=[)])',linka).group()
                    sub_lin = sub_ling.split(',')[0].strip().replace("'", '')
                    link = self.domain+sub_lin
                    # print 'linka',linka,'sub_lin',sub_lin
                    # print link
                    r2 = self.get_request(link,params={})
                    sop = BeautifulSoup(r2.text,'html5lib')
                    # print i,'sop', sop
                    self.get_detail(sop)
                    json_dict[biangeng_column_dict[gd_th[0].text.strip()]]=gd_td[0].text.strip()
                    json_dict[biangeng_column_dict[gd_th[1].text.strip()]] = self.bgq
                    json_dict[biangeng_column_dict[gd_th[2].text.strip()]] = self.bgh
                    json_dict[biangeng_column_dict[gd_th[3].text.strip()]]=gd_td[2].text.strip()
                    # print '****************json_dict',json_dict
                json_dict['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
                json_dict[family + ':registrationno'] = self.cur_zch
                json_dict[family + ':enterprisename'] = self.cur_mc
                json_dict[family + ':id'] = str(i+1)
                json_list.append(json_dict)
                json_dict = {}

            if turn_page > 3 and '2' in soup.select('#table2 tr')[-1].text:
                # print 'biangeng_page_splitter***************'
                cnt = 1
                soupt = ''
                for p in range(1,turn_page-3):
                    json_dict = {}
                    if cnt > turn_page-3:
                        # print 'biangeng_turn_page_over'
                        break
                    bgurl = 'http://qyxy.baic.gov.cn/%sgjjQueryCreditAction!biangengFrame.dhtml' %('gjjbj/'*(p+1))
                    params = {'clear': '', 'ent_id': self.entId, 'pageNo': p, 'pageNos': p+1, 'pageSize': 5}
                    rc = self.post_request(bgurl, params=params)
                    soup = BeautifulSoup(rc.text, 'lxml')
                    # print 'biangeng_turn_soup', soup
                    if soupt == soup.select('#tr1')[0].text:
                        print '**************biangengsoupout**********'
                        break
                    soupt = soup.select('#tr1')[0].text

                    gd_th = soup.select('#table2 tr')[1].find_all('th')
                    for i in range(len(soup.select('#tr1'))):
                        gd_td = soup.select('#tr1')[i].find_all('td')
                        if len(gd_td) == 4:
                            for j in range(len(gd_th)):
                                th = gd_th[j].text.strip()
                                td = gd_td[j].text.strip()
                                # print i,j,th,td
                                json_dict[biangeng_column_dict[th]]=td
                        if len(gd_td) == 3:
                            linka = gd_td[1].a.get('onclick')
                            sub_ling = re.search(u'(?<=[(]).*(?=[)])',linka).group()
                            sub_lin = sub_ling.split(',')[0].strip().replace("'", '')
                            link = self.domain+sub_lin
                            # print 'linka',linka,'sub_lin',sub_lin
                            # print link
                            r2 = self.get_request(link,params={})
                            sop = BeautifulSoup(r2.text, 'html5lib')
                            # print i,'sop', sop
                            self.get_detail(sop)
                            json_dict[biangeng_column_dict[gd_th[0].text.strip()]]=gd_td[0].text.strip()
                            json_dict[biangeng_column_dict[gd_th[1].text.strip()]] = self.bgq
                            json_dict[biangeng_column_dict[gd_th[2].text.strip()]] = self.bgh
                            json_dict[biangeng_column_dict[gd_th[3].text.strip()]]=gd_td[2].text.strip()
                            # print '****************json_dict',json_dict
                        json_dict['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1+cnt*5)
                        json_dict[family + ':registrationno'] = self.cur_zch
                        json_dict[family + ':enterprisename'] = self.cur_mc
                        json_dict[family + ':id'] = str(i+1+cnt*5)
                        json_list.append(json_dict)
                        json_dict = {}
                    cnt += 1
            if json_list:
                self.json_result[family] = json_list
            # print '-,-**biangeng_jslist****', len(json_list), json_list

    def get_detail(self,sop):    # 变更详情专用
        row_data=[]
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
                    if len(tds) == col_nums and u'无' not in tr.text:
                        td = tds[j]
                        val = td.text.strip()
                    else:
                        val = u'无'
                    row = col+u'：'+val
                    # print 'row', j, row
                    row_data.append(row)
            if u'变更前' in bt:
                self.bgq = u'；'.join(row_data)
                # print 'bgq',self.bgq
            elif u'变更后' in bt:
                self.bgh = u'；'.join(row_data)
                # print 'bgh',self.bgh
            row_data = []

    def get_zhu_yao_ren_yuan(self,zz):
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
        url = 'http://qyxy.baic.gov.cn/gjjbj/gjjQueryCreditAction!zyryFrame.dhtml?ent_id=%s&entName=&clear=true&timeStamp=%s' %(self.entId,self.cur_time)
        # print 'zhuyaorenyuan_url',self.cur_time,url
        r = self.get_request(url=url, params={})
        # r.encoding = 'gbk'
        soup = BeautifulSoup(r.text, 'lxml')
        # print '*******zhuyaorenyuan*******',soup

        turn_page = len(soup.select('#table2 tr th a'))    # 判断是否有分页，需要post分页地址，暂不处理
        # print 'zhuyaorenyuan_turn_page', turn_page
        # print 'body_tr',len(soup.select('#table2 tr a')),soup.select('#table2 tr a')
        # print 'ry_tr1',soup.select('#tr1')
        gd_th = soup.select('#table2 tr')[1].find_all('th')
        idn = 1
        if len(soup.select('#table2 tr')) > 2:
            # print 'zhuyaorenyuan*****'
            tr_element_list = soup.select('#table2 tr')
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

            #  分页判断
            if turn_page > 2:
                soupt = ''
                # print u'主要人员分页抓取...'
                q = 1
                for p in range(1, turn_page+11):
                    url = 'http://qyxy.baic.gov.cn/%sgjjQueryCreditAction!zyryFrame.dhtml' %('gjjbj/'*(p+1))
                    params = {'clear': '', 'ent_id': self.entId, 'pageNo': q, 'pageNos': q+1, 'pageSize':10}
                    # os.system('tskill python')
                    r = self.post_request(url, params=params)
                    soup = BeautifulSoup(r.text, 'lxml')
                    # print '*'*p, soup
                    if len(soup.select('#tr1')) == 0:
                        continue
                    q += 1
                    if soupt == soup.select('#table2 tr')[2].text:
                        # print '*************dashipu*************'  # 分页跳出逻辑
                        break
                    soupt = soup.select('#table2 tr')[2].text
                    tr_element_list = soup.select('#table2 tr')
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

            if json_list:
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
        url = 'http://qyxy.baic.gov.cn/gjjbj/gjjQueryCreditAction!fzjgFrame.dhtml?ent_id=&entName=&clear=true&timeStamp=%s' %(self.cur_time)
        # print 'fenzhijigou_url',self.cur_time,url
        r = self.get_request(url=url, params={})
        # r.encoding = 'gbk'
        soup = BeautifulSoup(r.text, 'lxml')
        # print '*******fenzhijigou*******',soup

        values = {}
        json_list = []
        turn_page=len(soup.find(id='table2').find_all('tr')[-1].find_all('a'))
        # print 'fen_zhi_jigou_len_turn_page',turn_page
        # for i in range(turn_page):
        #     print i,soup.find(id='table2').find_all('tr')[-1].find_all('a')[i]
        # if u'...' in soup.find(id='table2').find_all('tr')[-1].text:
        #     print '************...*******'
        table_tr_elements = soup.select("#table2 tr")
        if len(table_tr_elements) > 3:
            tr_element_list = soup.select("#tr1")
            th_element_list = soup.select("#table2 tr")[1].find_all('th')
            idn = 1
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

            #翻页加载
            cnt = 1
            if turn_page > 3:
                soupt = ''
                q = 1
                for p in range(1, turn_page+10):
                    # if u'...' in soup.find(id='table2').find_all('tr')[-1].text:
                        # print 'fenzhijigou_turn_page_..._more'
                    fz_url = 'http://qyxy.baic.gov.cn/%sgjjQueryCreditAction!fzjgFrame.dhtml' %('gjjbj/'*(p+1))
                    params = {'clear': '', 'ent_id': '', 'pageNo': q, 'pageNos': q+1, 'pageSize': 5}
                    rp = self.post_request(fz_url, params=params)
                    soup = BeautifulSoup(rp.text, 'lxml')

                    if len(soup.select('#tr1')) == 0:
                        continue
                    q += 1
                    # print '*******fenzhijigou*******',p, soup
                    if soupt == soup.select('#tr1')[0].text:
                        print '**************fenzhijigousoupout****p%s******' % p
                        break
                    soupt = soup.select('#tr1')[0].text

                    values = {}
                    # json_list=[]
                    table_tr_elements=soup.select("#table2 tr")
                    # if len(table_tr_elements)>3:
                    tr_element_list = soup.select("#tr1")
                    th_element_list = soup.select("#table2 tr")[1].find_all('th')
                    idn = 1
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
                        values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, idn+p*5)
                        values[family + ':registrationno'] = self.cur_zch
                        values[family + ':enterprisename'] = self.cur_mc
                        values[family + ':id'] = str(idn + p*5)
                        json_list.append(values)
                        # print '1111111111fenzhijigou1111111111111111111'
                        # json_fenzhijigou=json.dumps(values,ensure_ascii=False)
                        # print 'json_fenzhijigou',json_fenzhijigou
                        values = {}
                        idn += 1
                    cnt += 1

            if json_list:
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
        url = 'http://qyxy.baic.gov.cn/gjjbj/gjjQueryCreditAction!qsxxFrame.dhtml?ent_id=948C13E290484EF4BA1CB9C8DA516145&timeStamp=1472087885653'
        params = {'ent_id':'948C13E290484EF4BA1CB9C8DA516145','timeStamp':'1472087885653'}
        r = self.post_request(url=url, headers=self.headers, params=params)
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
        url = 'http://qyxy.baic.gov.cn/gjjbjTab/gjjTabQueryCreditAction!dcdyFrame.dhtml?ent_id=%s&entName=&clear=true&timeStamp=%s' %(self.entId,self.cur_time)
        # print 'dongchandiya_url',self.cur_time,url
        r = self.get_request(url=url, params={})
        # r.encoding = 'gbk'
        soup = BeautifulSoup(r.text, 'lxml')
        # print '*******dongchandiya*******',soup

        row_cnt = len(soup.find(class_="detailsList").find_all('tr'))
        if row_cnt > 3:
            # print 'come_on_bb_not_OK'
            tr_element_list = soup.find(class_="detailsList").find_all('tr')
            th_element_list = soup.find(class_="detailsList").find_all('tr')[1].find_all('th')
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
        url = 'http://qyxy.baic.gov.cn/gdczdj/gdczdjAction!gdczdjFrame.dhtml?ent_id=%s&entName=&clear=true&timeStamp=%s' %(self.entId,self.cur_time)
        # print 'gudongchuzhi_url',self.cur_time,url
        r = self.get_request(url=url, params={})
        # r.encoding = 'gbk'
        soup = BeautifulSoup(r.text, 'lxml')
        # print '*******guquanchuzhi*******',soup

        table_element = soup.select("detailsList")
        row_cnt = len(soup.find(class_="detailsList").find_all('tr'))
        if row_cnt > 2:
            tr_element_list = soup.find(class_="detailsList").find_all('tr')
            th_element_list = soup.find(class_="detailsList").find_all('tr')[1].find_all('th')
            idn = 1
            for tr_element in tr_element_list[2:]:
                td_element_list = tr_element.find_all('td')
                col_nums = len(th_element_list)
                for j in range(col_nums):
                    col_dec = th_element_list[j].text.strip().replace('\n','')
                    col=guquanchuzhidengji_column_dict[col_dec]
                    td = td_element_list[j]
                    val = td.text.strip()
                    if val == u'详情':
                        link=td.a.get('href')
                        values[col]=link
                        # print link
                    else:
                        values[col]=val
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
            if json_list:
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
        url = 'http://qyxy.baic.gov.cn/gsgs/gsxzcfAction!list.dhtml?entId=%s&clear=true&timeStamp=%s' %(self.entId,self.cur_time)
        # print 'xingzhengchufai_url',self.cur_time,url
        r = self.get_request(url=url, params={})
        # r.encoding = 'gbk'
        soup = BeautifulSoup(r.text, 'lxml')
        # print '*******xingzhengchufa*******',soup

        row_cnt = len(soup.find(class_="detailsList").find_all('tr'))
        if row_cnt > 3:
            tr_element_list = soup.find(class_="detailsList").find_all('tr')
            th_element_list = soup.find(class_="detailsList").find_all('tr')[1].find_all('th')
            idn = 1
            for tr_element in tr_element_list[2:-1]:
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
            if json_list:
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
        url = 'http://qyxy.baic.gov.cn/gsgs/gsxzcfAction!list_jyycxx.dhtml?entId=%s&clear=true&timeStamp=%s' %(self.entId, self.cur_time)
        # print 'jingyingyichang_url',self.cur_time,url
        r = self.get_request(url=url, params={})
        # r.encoding = 'gbk'
        soup = BeautifulSoup(r.text, 'html5lib')
        # print '*******jingyingyichang*******',soup

        row_cnt = len(soup.find(class_="detailsList").find_all('tr'))
        if row_cnt > 2:
            idn = 1
            tr_element_list = soup.find(class_="detailsList").find_all('tr')
            th_element_list = soup.find(class_="detailsList").find_all('tr')[1].find_all('th')
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
            if json_list:
                self.json_result[family] = json_list
            # print '-,-**jingyingyichang',json_list

        # params = {'pripid': param_pripid, 'type': param_type}
        # result_json = self.get_result_json(url, params)
        # for j in result_json:
        #     self.json_result[family].append({})
        #     for k in j:
        #         if k in jing_ying_yi_chang_dict:
        #             col = family + ':' + jing_ying_yi_chang_dict[k]
        #             val = j[k]
        #             self.json_result[family][-1][col] = val
        # for i in range(len(self.json_result[family])):
        #     self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i)
        #     self.json_result[family][i][family + ':registrationno'] = self.cur_zch
        #     self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
        # print json.dumps(result_json_2, ensure_ascii=False)

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
        url = 'http://qyxy.baic.gov.cn/gsgs/gsxzcfAction!list_yzwfxx.dhtml?ent_id=%s&clear=true&timeStamp=%s' %(self.entId,self.cur_time)
        # print 'yanzhongweifa_url',self.cur_time,url
        r = self.get_request(url=url, params={})
        # r.encoding = 'gbk'
        soup = BeautifulSoup(r.text, 'lxml')
        # print '*******yanzhongweifa*******',soup

        row_cnt = len(soup.find(class_="detailsList").find_all('tr'))
        if row_cnt > 3:
            tr_element_list = soup.find(class_="detailsList").find_all('tr')[2:-1]
            th_element_list = soup.find(class_="detailsList").find_all('tr')[1].find_all('th')
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
            if json_list:
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
        url = 'http://qyxy.baic.gov.cn/gsgs/gsxzcfAction!list_ccjcxx.dhtml?ent_id=%s&clear=true&timeStamp=%s' %(self.entId,self.cur_time)
        # print 'chouchajiancha_url',self.cur_time,url
        r = self.get_request(url=url, params={})
        # r.encoding = 'gbk'
        soup = BeautifulSoup(r.text, 'html5lib')
        # print '*******chouchajiancha*******',soup

        # row_cnt = len(soup.find_all('tbody'))  #结构和之前稍微不一样，不是tr，是3个tbody
        row_cnt = len(soup.find_all('tbody')[-1].find_all('tr'))
        # print 'ccjc_row_cnt',row_cnt

        if row_cnt >1:
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
            if json_list:
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
    #         return self.session.post(url=url, headers=self.headers, params=params, timeout=5)
    #     except RequestException, e:
    #         if t == 5:
    #             raise e
    #         else:
    #             return self.post_request(url, params, t+1)



if __name__ == '__main__':
    args_dict = get_args()
    searcher = BeiJingQW()
    # for i in range(20):
    #     print '*'*i,i
    searcher.submit_search_request(u"乐视云计算有限公司")#北京链家房地产经纪有限公司")#北斗中科卫士物联科技（北京）有限公司")#北京兴盛建业机电设备有限公司")
    #乐视网信息技术（北京）股份有限公司")#北京中视乾元文化发展有限公司")
    #北京链家房地产经纪有限公司")#中信国安黄金有限责任公司")  # 北京正北经贸有限公司 本草汇（北京）环境治理有限公司")#北京链家房地产经纪有限公司")
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
