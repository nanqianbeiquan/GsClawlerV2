# coding=utf-8

import json
from PIL import Image
import re
import sys

from bs4 import BeautifulSoup
from requests.exceptions import RequestException
import uuid
from bei_jing.Tables_dict import *
from gs.KafkaAPI import KafkaAPI
from gs.ProxyConf import *
from gs.Searcher import Searcher
from gs.Searcher import get_args
from gs.TimeUtils import *


class BeiJing(Searcher):

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
    log_name = "GsSrc11_"+str(uuid.uuid1())

    tab_url_set = set()

    def __init__(self, use_proxy=True):
        super(BeiJing, self).__init__(use_proxy=use_proxy)
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
        self.set_config()
        self.json_result = {}  # json输出结果
        self.domain = 'http://qyxy.baic.gov.cn'

    def set_config(self):
        # headers = {}
        # rt = self.get_request('http://1212.ip138.com/ic.asp', headers=headers)
        # rt.encoding = 'gb2312'
        # print rt.text

        self.plugin_path = sys.path[0] + r'\..\bei_jing\ocr\beijing.bat'
        self.group = 'Crawler'  # 正式
        self.kafka = KafkaAPI("GSCrawlerResult")  # 正式
        # self.group = 'CrawlerTest'  # 测试
        # self.kafka = KafkaAPI("GSCrawlerTest")  # 测试
        self.topic = 'GsSrc11'
        self.province = u'北京市'
        self.kafka.init_producer()

    def download_yzm(self):
        self.cur_time = '%d' % (time.time() * 1000)
        params = {'currentTimeMillis': self.cur_time}
        image_url = "http://qyxy.baic.gov.cn/CheckCodeYunSuan"
        r = self.get_request(url=image_url,  params=params)
        yzm_path = self.get_yzm_path()
        with open(yzm_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    f.flush()
            f.close()
        return yzm_path

    def get_credit_ticket(self):
        r = self.get_request('http://qyxy.baic.gov.cn/beijing')
        soup = BeautifulSoup(r.text, 'lxml')
        self.credit_ticket = soup.select('input#credit_ticket')[0].attrs['value']

    def get_tag_a_from_db(self, keyword):
        return None

    def save_tag_a_to_db(self, keyword):
        pass

    # def recognize_yzm(self, yzm_path):
    #     self
    #     image = Image.open(yzm_path)
    #     image.show()
    #     print '请输入验证码:'
    #     yzm = raw_input()
    #     yzm = raw_input()
    #     image.close()
    #     # os.remove(path)
    #     return yzm

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
        self.get_credit_ticket()
        self.info(u"获取ticket成功！")
        self.flag = self.get_the_mc_or_code(keyword)
        for t in range(10):
            self.get_lock_id()
            self.info(u'验证码识别中...第%s次' %(t+1))
            self.today = str(datetime.date.today()).replace('-', '')
            yzm = self.get_yzm()
            # self.release_id = '0'
            # print 'yzm', yzm
            url = 'http://qyxy.baic.gov.cn/gjjbj/gjjQueryCreditAction!getBjQyList.dhtml'
            params = {'checkcode': yzm, 'keyword': keyword, 'currentTimeMillis': self.cur_time, 'credit_ticket': self.credit_ticket}
            r = self.post_request_302(url=url, params=params)
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'lxml')
            # continue
            if soup.find(class_='list'):
                # print 'r.headers', r.headers
                self.info(u'**********验证码识别通过************')  # soup.find(class_='list')
                if soup.find(class_='list').text.strip() != '':
                    dvs = len(soup.find(class_='list').find_all('ul'))
                    if dvs > 1:  # 判断是否有其他查询结果
                        for lis in soup.find(class_='list').find_all('ul')[1:]:
                            cpn = lis.find_all('li')[0].a.text
                            # print 'other_name', cpn
                            if self.flag:
                                self.save_mc_to_db(cpn)

                    return soup.find(class_='list').find_all('ul')[0].find_all('li')
                else:
                    return None
        self.info(u'验证码加载失败')
        raise ValueError

    def get_search_args(self, tag_a, keyword):
        name = tag_a[0].a.text    # name为公司查询结果名；keyword为查询前数据库公司名
        name_link = tag_a[0].a.get('onclick')
        para_list = re.search(u'(?<=[(]).*(?=[)])', name_link).group()
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

        if self.flag:
            if self.cur_mc == keyword:
                return 1
            else:
                self.info(u'查询结果与输入不一致，保存公司名')
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
        self.info(u'解析基本信息')
        self.get_ji_ben()
        # print 'jb_step_json', self.json_result
        self.info(u'解析分支机构')
        self.get_fen_zhi_ji_gou()
        self.info(u'解析股东信息')
        self.get_gu_dong()
        self.get_zhu_guan_bu_men()
        # print 'gd_step_json', self.json_result
        self.info(u'解析变更信息')
        self.get_bian_geng()
        # print 'bg_step_json', self.json_result
        self.info(u'解析主要人员')
        self.get_zhu_yao_ren_yuan()
        # self.get_qing_suan()
        self.info(u'解析动产抵押')
        self.get_dong_chan_di_ya()
        self.info(u'解析股权出质')
        self.get_gu_quan_chu_zhi()
        self.info(u'解析行政处罚')
        self.get_xing_zheng_chu_fa()
        self.info(u'解析经营异常')
        self.get_jing_ying_yi_chang()
        self.info(u'解析严重违法')
        self.get_yan_zhong_wei_fa()
        self.info(u'解析抽查检查')
        self.get_chou_cha_jian_cha()
        # self.info(u'开始解析年报')
        # self.get_nian_bao()
        # print 'the_last_json_result', len(self.json_result), self.json_result
        # json_go = json.dumps(self.json_result, ensure_ascii=False)
        # print 'the_last_json_result:', len(self.json_result), get_cur_time()   ,  json_go

    def get_ji_ben(self):
        """
        查询基本信息
        :return: 基本信息结果
        """
        self.tab_url_set.clear()
        json_list = []
        family = 'Registered_Info'
        table_id = '01'
        self.json_result[family] = []
        url = 'http://qyxy.baic.gov.cn/gjjbj/gjjQueryCreditAction!openEntInfo.dhtml?' \
              'entId=%s&credit_ticket=%s&entNo=%s&timeStamp=%s' % (self.entId, self.creditt,  self.entNo, self.cur_time)
        # print 'jiben_url', url
        # params = {'credit_ticket':self.credit_ticket,'entId':self.entId,'entNo':self.entNo,'timeStamp':self.cur_time}

        r = self.get_request(url=url, params={})
        # self.proxy_config.release_lock_id(self.lock_id)
        # self.lock_id = '0'
        # r.encoding = 'gbk'
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'lxml')

        js = soup.select('head script')[-1].text
        # print js
        tab_list = js.split('rootPath+"')
        # print tab_list
        for t in tab_list[1:]:
            tab_url = t.split('?')[0]
            self.tab_url_set.add('http://qyxy.baic.gov.cn' + tab_url)
            # print tab_url
        # print soup
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
        values[family + ':tyshxy_code'] = self.xydm
        values[family + ':zch'] = self.zch
        values[family + ':lastupdatetime'] = get_cur_time()
        values[family + ':province'] = u'北京市'
        json_list.append(values)
        self.json_result[family] = json_list
        # print 'jiben_values',values

    def get_gu_dong(self):
        """
        查询股东信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Shareholder_Info'
        table_id = '04'
        json_list = []
        col_desc_list = []
        url = 'http://qyxy.baic.gov.cn/gjjbj/gjjQueryCreditAction!tzrFrame.dhtml'
        # print self.tab_url_set
        if url not in self.tab_url_set:
            return
        idx = 0
        i = -1
        while i < 1000:
            i += 1
            # self.info(u'股东第%d页' % i)
            if i == 0:
                params = {
                    'ent_id': self.entId,
                    'entName': '',
                    'clear': 'true',
                    # 'timeStamp': self.cur_time
                }
            else:
                params = {
                    'clear': '',
                    'ent_id': self.entId,
                    'fqr': '',
                    'pageNo': str(i),
                    'pageNos': str(i+1),
                    'pageSize': '5'
                }
            r = self.get_request(url=url, params=params)
            soup = BeautifulSoup(r.text, 'lxml')
            tr_list = soup.select('table tbody tr')
            if i == 0:
                if len(tr_list) == 0:
                    i = -1
                    continue
                th_list = tr_list[0].select('th')
                for th in th_list:
                    col_desc_list.append(th.text.strip())
            if len(tr_list) > 2:
                for tr in tr_list[1:-1]:
                    idx += 1
                    json_dict = {}
                    gd_td = tr.select('td')
                    for j in range(len(gd_td)):
                        th = col_desc_list[j]
                        td = gd_td[j].text.strip()
                        if td == u'详情':
                            td = gd_td[j].a.get('onclick')
                            # print 'gudong', td
                            chr_id = re.search(u'(?<=[(]).*(?=[)])', td).group().strip("'")
                            detail_url = 'http://qyxy.baic.gov.cn/gjjbj/gjjQueryCreditAction!touzirenInfo.dhtml?chr_id=%s&entName=&timeStamp=%s&fqr=' %(chr_id,self.cur_time)
                            # print 'detail_url', detail_url
                            td = detail_url
                            self.get_gu_dong_detail(detail_url, json_dict)
                            # self.load_func(td)  抓取详情页内容方法，见cnt分页内容
                        json_dict[gudong_column_dict[th]]=td
                    json_dict['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, idx)
                    json_dict[family + ':registrationno'] = self.cur_zch
                    json_dict[family + ':enterprisename'] = self.cur_mc
                    json_dict[family + ':id'] = str(idx)
                    # print json.dumps(json_dict, ensure_ascii=False)
                    json_list.append(json_dict)

                page_ele_list = tr_list[-1].select('th')[0].findChildren()
                last_page = '0'
                for page_ele in page_ele_list:
                    cur = page_ele.text.strip()
                    if cur == '>>':
                        # print last_page, cur
                        break
                    else:
                        last_page = cur
                if str(i+1) == last_page:
                    break
            else:
                break

    def get_zhu_guan_bu_men(self):
        family = 'Shareholder_Info'
        table_id = '04'
        json_list = []
        col_desc_list = []
        url = 'http://qyxy.baic.gov.cn/gjjbj/gjjQueryCreditAction!zgbmFrame.dhtml'
        if url not in self.tab_url_set:
            return
        idx = 0
        i = -1
        while i < 1000:
            i += 1
            # self.info(u'股东第%d页' % i)
            if i == 0:
                params = {
                    'ent_id': self.entId,
                    'clear': 'true',
                    # 'timeStamp': self.cur_time
                }
            else:
                params = {
                    'clear': '',
                    'ent_id': self.entId,
                    'fqr': '',
                    'pageNo': str(i),
                    'pageNos': str(i + 1),
                    'pageSize': '5'
                }
            r = self.get_request(url=url, params=params)
            soup = BeautifulSoup(r.text, 'lxml')
            tr_list = soup.select('table tr')
            if i == 0:
                if len(tr_list) == 0:
                    i = -1
                    continue
                th_list = tr_list[1].select('th')
                for th in th_list:
                    col_desc_list.append(th.text.strip())
            if len(tr_list) > 2:
                for tr in tr_list[1:-1]:
                    idx += 1
                    json_dict = {}
                    gd_td = tr.select('td')
                    for j in range(len(gd_td)):
                        th = col_desc_list[j]
                        if th == u'序号':
                            continue
                        td = gd_td[j].text.strip()
                        json_dict[zhuguanbumen_column_dict[th]] = td
                    json_dict['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, idx)
                    json_dict[family + ':registrationno'] = self.cur_zch
                    json_dict[family + ':enterprisename'] = self.cur_mc
                    json_dict[family + ':id'] = str(idx)
                    # print json.dumps(json_dict, ensure_ascii=False)
                    json_list.append(json_dict)

                page_ele_list = tr_list[-1].select('th')[0].findChildren()
                last_page = '0'
                for page_ele in page_ele_list:
                    cur = page_ele.text.strip()
                    if cur == '>>':
                        # print last_page, cur
                        break
                    else:
                        last_page = cur
                if str(i + 1) == last_page:
                    break
            else:
                break

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
        soup = BeautifulSoup(r.text, 'lxml')
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

    def get_bian_geng(self):
        family = 'Changed_Announcement'
        table_id = '05'
        change_ele_list = []
        col_desc_list = []
        i = -1
        while i < 1000:
            i += 1
            if i == 0:
                params = {
                    'ent_id': self.entId,
                    'entName': '',
                    'clear': 'true',
                    # 'timeStamp': self.cur_time
                    }
                self.get_lock_id()
            else:
                params = {
                    'ent_id': self.entId,
                    'clear': '',
                    'pageNo': str(i),
                    'pageNos': str(i+1),
                    'pageSize': '5',
                    }
                # self.release_id = '0'
                if 'entName' in params:
                    params.pop('entName')

            # url = 'http://qyxy.baic.gov.cn/gjjbj/gjjQueryCreditAction!biangengFrame.dhtml?ent_id=%s&entName=&clear=true&timeStamp=%s' %(self.entId,self.cur_time)
            url = 'http://qyxy.baic.gov.cn/gjjbj/gjjQueryCreditAction!biangengFrame.dhtml'
            if url not in self.tab_url_set:
                self.release_lock_id()
                return
            r = self.get_request(url, params=params)
            # print r.status_code
            soup = BeautifulSoup(r.text, 'lxml')
            # print soup.select('table  tbody tr')[0]
            if i == 0:
                if len(soup.select('table  tbody tr')) < 2:
                    i = -1
                    continue
                th_list = soup.select('table  tbody tr')[1].select('th')
                for th in th_list:
                    col_desc_list.append(th.text.strip())
            tr_list = soup.select('table  tbody tr')
            if len(tr_list) > 3:
                change_ele_list.extend(tr_list[2:-1])
                page_ele_list = tr_list[-1].select('th')[0].findChildren()
                last_page = '0'
                for page_ele in page_ele_list:
                    cur = page_ele.text.strip()
                    if cur == '>>':
                        break
                    else:
                        last_page = cur
                if str(i+1) == last_page:
                    break
            else:
                break

        self.release_lock_id()
        json_list = []
        idx = 0
        for ele in change_ele_list:
            json_dict = {}
            idx += 1
            # print idx, ele
            td_list = ele.select('td')
            if len(td_list) == 3:
                linka = td_list[1].a.get('onclick')
                sub_ling = re.search(u'(?<=[(]).*(?=[)])', linka).group()
                sub_lin = sub_ling.split(',')[0].strip().replace("'", '')
                link = self.domain+sub_lin
                r2 = self.get_request(link, params={})
                sop = BeautifulSoup(r2.text, 'lxml')
                self.get_detail(sop)
                json_dict[biangeng_column_dict[col_desc_list[0]]] = td_list[0].text.strip()
                json_dict[biangeng_column_dict[col_desc_list[1]]] = self.bgq
                json_dict[biangeng_column_dict[col_desc_list[2]]] = self.bgh
                json_dict[biangeng_column_dict[col_desc_list[3]]] = td_list[2].text.strip()
            elif len(td_list) == 4:
                for k in range(4):
                    json_dict[biangeng_column_dict[col_desc_list[k]]] = td_list[k].text.strip()
            json_dict['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, idx)
            json_dict[family + ':registrationno'] = self.cur_zch
            json_dict[family + ':enterprisename'] = self.cur_mc
            json_dict[family + ':id'] = str(idx)
            json_list.append(json_dict)
            # print idx, json.dumps(json_dict, ensure_ascii=False)
        if json_list:
            self.json_result[family] = json_list
        # print json.dumps(json_list, ensure_ascii=False)

    def get_detail(self, sop):    # 变更详情专用
        row_data = []
        # tables=self.driver.find_elements_by_xpath("//*[@id='tableIdStyle']/tbody")
        tables = sop.find_all(id='tableIdStyle')
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

        url = 'http://qyxy.baic.gov.cn/gjjbj/gjjQueryCreditAction!zyryFrame.dhtml'
        if url not in self.tab_url_set:
            return
        idn = 1
        th_list = []
        i = -1
        while i < 1000:
            i += 1
            values = {}
            if i == 0:
                params = {
                    'ent_id': self.entId,
                    'entName': '',
                    'clear': 'true',
                    # 'timeStamp': self.cur_time
                }
            else:
                params = {
                        'ent_id': self.entId,
                        'clear': '',
                        'pageSize': '10',
                        'pageNo': str(i),
                        'pageNos': str(i+1),
                        }
            # print 'zhuyaorenyuan_url',self.cur_time,url
            r = self.get_request(url=url, params=params)
            # r.encoding = 'gbk'
            soup = BeautifulSoup(r.text, 'lxml')
            # print soup
            tr_list = soup.select('table tr')
            if i == 0:
                if len(tr_list) < 2:
                    i = -1
                    continue
                th_list = tr_list[1].find_all('th')
            if len(tr_list) > 3:
                for tr_element in tr_list[2:-1]:
                    # print tr_element
                    td_element_list = tr_element.find_all('td')
                    list_length = len(td_element_list)
                    fixed_length = list_length - list_length % 3
                    for j in range(fixed_length):
                        col_dec = th_list[j].text.strip().replace('\n','')
                        col = zhuyaorenyuan_column_dict[col_dec]
                        td = td_element_list[j]
                        val = td.text.strip()
                        values[col] = val
                        if len(values) == 3:
                            values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, idn)
                            values[family + ':registrationno'] = self.cur_zch
                            values[family + ':enterprisename'] = self.cur_mc
                            values[family + ':id'] = str(idn)
                            json_list.append(values)
                            # print i, json.dumps(values, ensure_ascii=False)
                            values = {}
                            idn += 1

                page_ele_list = tr_list[-1].select('th')[0].findChildren()
                last_page = '0'
                for page_ele in page_ele_list:
                    cur = page_ele.text.strip()
                    if cur == '>>':
                        # print last_page, cur
                        break
                    else:
                        last_page = cur
                if str(i+1) == last_page:
                    break
            else:
                break
        if json_list:
            self.json_result[family] = json_list

    def get_fen_zhi_ji_gou(self):
        family = 'Branches'
        table_id = '08'
        # self.json_result[family] = []
        url = 'http://qyxy.baic.gov.cn/gjjbj/gjjQueryCreditAction!fzjgFrame.dhtml'
        if url not in self.tab_url_set:
            self.release_lock_id()
            return
        idn = 0
        json_list = []
        th_list = []
        i = -1
        while i < 1000:
            i += 1
            if i == 0:
                params = {
                    'ent_id': self.entId,
                    'clear': 'true',
                    'entName': '',
                    # 'timeStamp': self.cur_time
                }
            else:
                params = {
                    'ent_id': self.entId,
                    'clear': '',
                    'pageNo': i,
                    'pageNos': i+1,
                    'pageSize': '5'
                }
            r = self.get_request(url =url, params=params)
            soup = BeautifulSoup(r.text, 'lxml')
            tr_list = soup.select('table tr')
            if len(tr_list) > 3:
                if i == 0:
                    if len(tr_list) < 2:
                        i = -1
                        continue
                    th_list = tr_list[1].find_all('th')
                values = {}
                for tr in tr_list[2:-1]:
                    idn += 1
                    td_list = tr.select('td')
                    for j in range(len(td_list)):
                        col_dec = th_list[j].text.strip().replace('\n','')
                        col = fenzhijigou_column_dict[col_dec]
                        td = td_list[j]
                        val = td.text.strip()
                        values[col] = val
                    values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, idn)
                    values[family + ':registrationno'] = self.cur_zch
                    values[family + ':enterprisename'] = self.cur_mc
                    values[family + ':id'] = str(idn)
                    # print json.dumps(values, ensure_ascii=False)
                    json_list.append(values)
                    idn += 1
                page_ele_list = tr_list[-1].select('th')[0].findChildren()
                last_page = '0'
                for page_ele in page_ele_list:
                    cur = page_ele.text.strip()
                    if cur == '>>':
                        break
                    else:
                        last_page = cur
                if str(i+1) == last_page:
                    break
            else:
                break
        self.release_lock_id()

    def get_qing_suan(self):
        """
        查询清算信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'liquidation_Information'
        table_id = '09'
        self.json_result[family] = []
        url = 'http://qyxy.baic.gov.cn/gjjbj/gjjQueryCreditAction!qsxxFrame.dhtml'
        if url not in self.tab_url_set:
            return
        params = {'ent_id': self.entId}
        r = self.post_request(url=url, params=params)
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
        values={}
        json_list=[]
        url = 'http://qyxy.baic.gov.cn/gjjbjTab/gjjTabQueryCreditAction!dcdyFrame.dhtml'
        if url not in self.tab_url_set:
            return
        params = {
            'entId': self.entId,
            'clear': 'true',
        }
        # print 'dongchandiya_url',self.cur_time,url
        r = self.get_request(url=url, params=params)
        # r.encoding = 'gbk'
        soup = BeautifulSoup(r.text, 'lxml')
        # print '*******dongchandiya*******',soup

        row_cnt = len(soup.find(class_="detailsList").find_all('tr'))

        self.dcdydj_list = []
        self.dyqrgk_list = []
        self.bdbzqgk_list = []
        self.dywgk_list = []
        self.dcdybg_list = []
        self.dcdyzx_list = []

        if row_cnt > 3:
            # print 'come_on_bb_not_OK'
            try:
                pages_counts = int(soup.find(id='pagescount').get('value'))
                # print '*****mmm*****', 'wach', pages_counts
            except:
                pages_counts = 1
            tr_element_list = soup.find(class_="detailsList").find_all('tr')
            th_element_list = soup.find(class_="detailsList").find_all('tr')[1].find_all('th')
            idn = 1
            for tr_element in tr_element_list[2:-1]:
                td_element_list = tr_element.find_all('td')
                col_nums = len(th_element_list)
                for j in range(col_nums):
                    col_dec = th_element_list[j].text.strip().replace('\n','')
                    col = dongchandiyadengji_column_dict[col_dec]
                    td = td_element_list[j]
                    val = td.text.strip()
                    if val == u'详情':
                        link = td.a.get('href')
                        link = self.domain + link
                        values[col] = link
                        # print 'dcdy_link', link
                        self.get_dongchandiya_detail(link)
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

            if pages_counts > 1:
                for p in range(2, pages_counts+1):
                    purl = 'http://qyxy.baic.gov.cn/gjjbjTab/gjjbjTab/gjjTabQueryCreditAction!dcdyFrame.dhtml'
                    params = dict(clear='', entId=self.entId, pageNo=p-1, pageNos=p, pageSize=10)
                    try:
                        r = self.post_request(url=purl, params=params)
                    except:
                        self.info(u'internal error')
                        continue
                    # print '2nd',r.text
                    soup = BeautifulSoup(r.text, 'lxml')

                    tr_element_list = soup.find(class_="detailsList").find_all('tr')
                    for tr_element in tr_element_list[2:-1]:
                        td_element_list = tr_element.find_all('td')
                        col_nums = len(th_element_list)
                        for j in range(col_nums):
                            col_dec = th_element_list[j].text.strip().replace('\n','')
                            col = dongchandiyadengji_column_dict[col_dec]
                            td = td_element_list[j]
                            val = td.text.strip()
                            if val == u'详情':
                                link = td.a.get('href')
                                link = self.domain + link
                                values[col] = link
                                # print 'dcdy_link', link
                                self.get_dongchandiya_detail(link)
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
            if self.dcdydj_list:
                self.json_result['dcdydj'] = self.dcdydj_list
            if self.dyqrgk_list:
                self.json_result['dyqrgk'] = self.dyqrgk_list
            if self.bdbzqgk_list:
                self.json_result['bdbzqgk'] = self.bdbzqgk_list
            if self.dywgk_list:
                self.json_result['dywgk'] = self.dywgk_list
            if self.dcdybg_list:
                self.json_result['dcdybg'] = self.dcdybg_list
            if self.dcdyzx_list:
                self.json_result['dcdyzx'] = self.dcdyzx_list

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
        url = 'http://qyxy.baic.gov.cn/gdczdj/gdczdjAction!gdczdjFrame.dhtml'
        # print 'gudongchuzhi_url',self.cur_time,url
        # print 'gqcz***', self.tab_url_set
        if url not in self.tab_url_set:
            return
        params = {
            'entId': self.entId,
            'clear': 'true',
        }
        r = self.get_request(url=url, params=params)
        # r.encoding = 'gbk'
        soup = BeautifulSoup(r.text, 'html5lib')
        # print '*******guquanchuzhi*******',soup

        self.gqczbg_list = []
        self.gqczzx_list = []

        table_element = soup.select("detailsList")
        row_cnt = len(soup.find(class_="detailsList").find_all('tr'))
        # print 'gqcz', row_cnt
        if row_cnt > 2:
            tr_element_list = soup.find(class_="detailsList").find_all('tr')
            th_element_list = soup.find(class_="detailsList").find_all('tr')[1].find_all('th')
            idn = 1
            for tr_element in tr_element_list[2:-1]:
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
                        link=td.a.get('href')
                        link = self.domain + link
                        values[col] = link
                        # print 'gqcz_link', link
                        self.get_guquanchuzhi_detail(link)
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
                # print 'json_guquanchuzhidengji', json_guquanchuzhidengji
                values = {}
                idn += 1
            if json_list:
                self.json_result[family] = json_list
            # print '-,-**guquanchuzhi_json_list**',len(json_list),json_list
            if self.gqczbg_list:
                self.json_result['gqczbg'] = self.gqczbg_list
            if self.gqczzx_list:
                self.json_result['gqczzx'] = self.gqczzx_list

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
        url = 'http://qyxy.baic.gov.cn/gsgs/gsxzcfAction!list.dhtml'
        # print 'xingzhengchufai_url',self.cur_time,url
        if url not in self.tab_url_set:
            return
        params = {
            'entId': self.entId,
            'clear': 'true',
        }
        r = self.get_request(url=url, params=params)
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
            try:
                turn_page = tr_element_list[-1].find_all('a')
                turn_page = len(turn_page)
            except:
                turn_page = 0
            if turn_page:
                for p in range(1,turn_page):
                    url = 'http://qyxy.baic.gov.cn/gsgs/gsxzcfAction!list.dhtml?entId='+self.entId
                    params = {'clear':'','pageNo':p+1,'pageSize':10}
                    r = self.post_request(url=url, params=params)
                    soup = BeautifulSoup(r.text,'html5lib')
                    # print '2p',soup
                    tr_element_list = soup.find(class_="detailsList").find_all('tr')
                    th_element_list = soup.find(class_="detailsList").find_all('tr')[1].find_all('th')

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
        url = 'http://qyxy.baic.gov.cn/gsgs/gsxzcfAction!list_jyycxx.dhtml'
        # print 'jingyingyichang_url',self.cur_time,url
        if url not in self.tab_url_set:
            return
        params = {
            'entId': self.entId,
            'clear': 'true',
            'timeStamp': get_cur_ts_mil()
        }
        r = self.get_request(url=url, params=params)
        # r.encoding = 'gbk'
        soup = BeautifulSoup(r.text, 'lxml')
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
        url = 'http://qyxy.baic.gov.cn/gsgs/gsxzcfAction!list_yzwfxx.dhtml'
        if url not in self.tab_url_set:
            return
        params = {
            'ent_id': self.entId,
            'clear': 'true',
        }
        # print 'yanzhongweifa_url',self.cur_time,url
        r = self.get_request(url=url, params=params)
        # r.encoding = 'gbk'
        soup = BeautifulSoup(r.text, 'lxml')
        # print '*******yanzhongweifa*******',soup

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
        url = 'http://qyxy.baic.gov.cn/gsgs/gsxzcfAction!list_ccjcxx.dhtml'
        # print 'chouchajiancha_url',self.cur_time,url
        if url not in self.tab_url_set:
            return
        params = {
            'ent_id': self.entId,
            'clear': 'true',
            'entName': '',
        }
        r = self.get_request(url=url, params=params)
        # r.encoding = 'gbk'
        soup = BeautifulSoup(r.text, 'lxml')
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

    def get_nian_bao(self):

        family = 'annual_report'
        table_id = '39'

        url = 'http://qyxy.baic.gov.cn/qynb/entinfoAction!qyxx.dhtml?entid='+self.entId+'&clear=true&timeStamp='+self.cur_time
        # print 'nianbaourl:', url
        self.get_lock_id()
        r = self.get_request(url=url)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'lxml')
        # print 'nianbao*soup:', soup
        nblist = soup.find(id='qiyenianbao').find_all('tr')
        json_list = []
        json_dict = {}
        link_list = []
        year_list = []
        cid_dict = {}
        if len(nblist) > 2:
            th_list = nblist[1].find_all('th')
            tr_list = nblist[2:]
            tr_recent = nblist[-1]

            for tr in tr_list:
                idn = 1
                if tr.text.strip():
                    td_list = tr.find_all('td')
                    for t in range(len(td_list)):
                        col_dec = th_list[t].text.strip()
                        col = qiyenianbao_column_dict[col_dec]
                        td = td_list[t].text.strip()
                        if col_dec == u'报送年度':
                            try:
                                href = td_list[t].a.get('href')
                            except AttributeError as e:
                                # print u'个体户年报不做处理', e
                                self.info(u'个体户年报不做处理')
                                return
                            link = 'http://qyxy.baic.gov.cn' + href
                            # print 'nianbao_link:', td, link
                            self.y = td[:4]
                            cid = re.search(r'(?<=cid=).*(?=&entid)', link).group()
                            # print '***cid***:', cid
                            cid_dict[td] = cid
                            year_list.append(td)
                            link_list.append(link)
                            json_dict[qiyenianbao_column_dict[u'详情']] = link
                        json_dict[col] = td
                    json_dict['rowkey'] = '%s_%s_%s_%d' %(self.cur_mc, self.y, table_id, idn)
                    json_dict[family + ':registrationno'] = self.cur_zch
                    json_dict[family + ':enterprisename'] = self.cur_mc
                    json_dict[family + ':id'] = str(idn)
                    json_list.append(json_dict)
                    json_dict = {}
                    idn += 1
            if json_list:
                # print 'json_list:', json_list
                self.json_result[family] = json_list

        # 年报详情解析
            if link_list:
                # print 'link_list:', link_list
                # 年报年份
                cnt = 0
                iyear_dict = {}  # 年份容器
                idata_dict = {}  # 年份数据容器

                self.nbjb_list = []  # 年报基本信息
                self.nbzczk_list = []  # 年报资产状况

                self.nbdwdb_list = []
                self.nbgdcz_list = []
                self.nbgqbg_list = []
                self.nbwz_list = []
                self.nbxg_list = []
                self.nbdwtz_list = []

                # 此部分需要锁定IP
                for l in link_list:
                    # print 'refer-link:', url
                    r = self.get_request(url=l)  #包含基本信息和企业资产状况信息
                    r.encoding = 'utf-8'
                    soup = BeautifulSoup(r.text, 'lxml')
                    # print '****-nianbaodetail--soup-****', soup
                    no_iframe = soup.find_all(id='qufenkuang')[0]#.find_all(class_='detailsList')
                    yes_iframe = soup.find_all('iframe')
                    # print '*'*100
                    self.info(u'获取年报基本信息**'+year_list[cnt])
                    self.get_nianbaojiben(no_iframe)  # 获取年报基本信息
                    self.info(u'获取年报资产状况信息**'+year_list[cnt])
                    self.get_nianbaozichanzhuangkuang(no_iframe)  # 获取年报资产状况信息
                    # print '*'*150

                    for i in range(len(yes_iframe)):
                        yes_id = yes_iframe[i].get('id')
                        yes_src = yes_iframe[i].get('src')
                        yes_link = self.domain + yes_src
                        # print '*'*50, i, year_list[cnt], yes_id, yes_src, yes_link
                        idata_dict[yes_id] = yes_link
                    iyear_dict[year_list[cnt]] = idata_dict
                    idata_dict = {}
                    cnt += 1

                # print '***---***', iyear_dict
                # 对不用锁定IP的iframe进行单独处理
                for y, d in iyear_dict.items():
                    # print 'show_me_the_data:', y, d  # y为年份，d为年份对应的iframe的id和url
                    self.y = y[:4]
                    self.cid = cid_dict[y]
                    for lid, lurl in d.items():
                        # print '*-'*50, lid, lurl

                        if lid == 'dwdbFrame':
                            # print u'对外提供保证担保信息', y
                            self.info(u'对外提供保证担保信息**' + y)
                            self.get_nianbaoduiwaidanbao(lurl)
                        elif lid == 'gdczFrame':
                            # print u'股东及出资信息', y
                            self.info(u'股东及出资信息**' + y)
                            self.get_nianbaogudongchuzi(lurl)
                        elif lid == 'gdzrFrame':
                            # print u'股权变更信息', y
                            self.info(u'股权变更信息**' + y)
                            self.get_nianbaoguquanbiangeng(lurl)
                        elif lid == 'wzFrame':
                            # print u'网站或网店信息', y
                            self.info(u'网站或网店信息**' + y)
                            self.get_nianbaowangzhan(lurl)
                        elif lid == 'xgFrame':
                            # print u'修改记录', y
                            self.info(u'修改记录**' + y)
                            self.get_nianbaoxiugai(lurl)
                        elif lid == 'dwtzFrame':
                            # print u'对外投资信息', y
                            self.info(u'对外投资信息**' + y)
                            self.get_nianbaoduiwaitouzi(lurl)
                        else:
                            # print '******$$$**unknown_iframe***', lid, lurl
                            self.info(u'******$$$**unknown_iframe***iframeID:' + lid + u'iframeURL:' + lurl)
                if self.nbjb_list:
                    self.json_result['report_base'] = self.nbjb_list  # 年报基本信息
                if self.nbzczk_list:
                    self.json_result['industry_status'] = self.nbzczk_list  # 年报资产状况

                if self.nbdwdb_list:
                    self.json_result['guarantee'] = self.nbdwdb_list
                if self.nbgdcz_list:
                    self.json_result['enterprise_shareholder'] = self.nbgdcz_list
                if self.nbgqbg_list:
                    self.json_result['equity_transfer'] = self.nbgqbg_list
                if self.nbwz_list:
                    self.json_result['web_site'] = self.nbwz_list
                if self.nbxg_list:
                    self.json_result['modify'] = self.nbxg_list
                if self.nbdwtz_list:
                    self.json_result['investment'] = self.nbdwtz_list


                    # for j in no_iframe:
                    #     print '******soup_basic:', j
                    # iframes = soup.find_all(id='qufenkuang')[0].find_all('iframe')
                    # for j in iframes:
                    #     print '))))))iframe_show:', j

#  基本页面加载成功包含基本信息和企业资产状况信息,网站结构为table，锁IP
    def get_nianbaojiben(self, soup):
        family = 'report_base'
        table_id = '40'
        table = soup.find_all(class_='detailsList')[0]
        tr_element_list = table.find_all("tr")
        values = {}
        json_list = []
        for tr_element in tr_element_list[2:]:
            th_element_list = tr_element.find_all('th')
            td_element_list = tr_element.find_all('td')
            if len(th_element_list) == len(td_element_list):
                col_nums = len(th_element_list)
                for i in range(col_nums):
                    col = th_element_list[i].get_text().strip().replace('\n','')
                    val = td_element_list[i].get_text().strip().replace('\n','')
                    if col != u'':
                        values[qiyenianbaojiben_column_dict[col]] = val
                        # print col,val
        values['rowkey'] = '%s_%s_%s_' %(self.cur_mc, self.y, table_id)
        values[family + ':registrationno'] = self.cur_zch
        values[family + ':enterprisename'] = self.cur_mc
        json_list.append(values)
        self.nbjb_list.append(values)
        # if json_list:
        #     # print 'nianbaojibenxinxi', json_list
        #     self.json_result[family] = json_list

    def get_nianbaozichanzhuangkuang(self, soup):
        family = 'industry_status'
        table_id = '43'

        table = soup.find_all(class_='detailsList')[1]
        tr_element_list = table.find_all("tr")
        values = {}
        json_list = []
        for tr_element in tr_element_list:
            th_element_list = tr_element.find_all('th')
            td_element_list = tr_element.find_all('td')
            if len(th_element_list) == len(td_element_list):
                col_nums = len(th_element_list)
                for i in range(col_nums):
                    col = th_element_list[i].get_text().strip().replace('\n','')
                    val = td_element_list[i].get_text().strip().replace('\n','')
                    if col != u'':
                        values[qiyenianbaozichanzhuangkuang_column_dict[col]] = val
#                     print col,val
#         values[u'注册号']=self.cur_code
#         values[u'省份']=self.province
#         values[u'报送年度']=self.nianbaotitle
        values['rowkey'] = '%s_%s_%s_' %(self.cur_mc, self.y, table_id)
        values[family + ':registrationno'] = self.cur_zch
        values[family + ':enterprisename'] = self.cur_mc
        json_list.append(values)
        self.nbzczk_list.append(values)
        # if json_list:
            # json_nianbaozichan=json.dumps(values,ensure_ascii=False)
            # print 'json_nianbaozichan', json_list
            # self.json_result[family] = json_list

    def get_nianbaoduiwaidanbao(self, url):
        family = 'guarantee'
        table_id = '44'
        values = {}
        json_list = []
        r = self.get_request(url=url)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'lxml')
        # print 'nianbaoduiwaidanbao', soup

        sp = soup.find(id='touziren').find_all('tr')
        # print 'lendwdbsp', len(sp)
        if len(sp) > 3:
            idn = 1
            tr_element_list = sp
            th_element_list = sp[1].find_all('th')
            for tr_element in tr_element_list[2:-1]:
                td_element_list = tr_element.find_all('td')
                col_nums = len(th_element_list)
                for j in range(col_nums):
                    col = th_element_list[j].text.strip().replace('\n','')
                    td = td_element_list[j]
                    val = td.text.strip()
                    values[qiyenianbaoduiwaidanbao_column_dict[col]] = val
                # values[u'注册号']=self.cur_code
                # values[u'省份']=self.province
                # values[u'报送年度']=self.nianbaotitle
                values['rowkey'] = '%s_%s_%s_%d' %(self.cur_mc, self.y, table_id, idn)
                values[family + ':registrationno'] = self.cur_zch
                values[family + ':enterprisename'] = self.cur_mc
                values[family + ':id'] = str(idn)
                json_list.append(values)
                self.nbdwdb_list.append(values)
                values = {}
                # print 'dwdb****'
                idn += 1

            page_tr = sp[-1].find_all('a')
            if page_tr:
                ncnt = len(page_tr)
                if ncnt > 3:
                    # print u'股东出资分页抓取'
                    for p in range(1, ncnt-1):
                        # url = 'http://qyxy.baic.gov.cn/entPub/entPubAction!dwtz_bj.dhtml'
                        url = 'http://qyxy.baic.gov.cn/entPub/entPubAction!qydwdb_bj.dhtml'
                        params = {
                            'cid': self.cid,
                            'clear': '',
                            'entid': '',
                            'pageNo': p,
                            'pageNos': p+1,
                            'pageSize': 5
                        }
                        # print 'params:', params
                        r = self.post_request(url=url, params=params)
                        r.encoding = 'utf-8'
                        soup = BeautifulSoup(r.text, 'lxml')
                        # print '***dwtzfenye***', p+1,
                        sp = soup.find(id='touziren').find_all('tr')
                        tr_element_list = sp
                        th_element_list = sp[1].find_all('th')
                        for tr_element in tr_element_list[2:-1]:
                            td_element_list = tr_element.find_all('td')
                            col_nums = len(th_element_list)
                            for j in range(col_nums):
                                col = th_element_list[j].text.strip().replace('\n','')
                                td = td_element_list[j]
                                val = td.text.strip()
                                # print 'dwdb', p+1, idn, val
                                values[qiyenianbaoduiwaidanbao_column_dict[col]] = val
                            # values[u'注册号']=self.cur_code
                            # values[u'省份']=self.province
                            # values[u'报送年度']=self.nianbaotitle
                            # values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, idn)
                            values['rowkey'] = '%s_%s_%s_%d' %(self.cur_mc, self.y, table_id, idn)
                            values[family + ':registrationno'] = self.cur_zch
                            values[family + ':enterprisename'] = self.cur_mc
                            values[family + ':id'] = str(idn)
                            json_list.append(values)
                            self.nbdwdb_list.append(values)
                            values = {}
                            idn += 1
            # if json_list:
            #     # print 'nianbaoduiwandanbao:', json_list
            #     self.json_result[family] = json_list

    def get_nianbaogudongchuzi(self, url):
        family = 'enterprise_shareholder'
        table_id = '42'
        values = {}
        json_list = []
        r = self.get_request(url=url)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'lxml')
        # print 'nianbaogudongchuzisoup', soup

        sp = soup.find(id='touziren').find_all('tr')
        # print 'lengdczsp', len(sp)
        if len(sp) > 3:
            idn = 1
            tr_element_list = sp
            th_element_list = sp[1].find_all('th')
            for tr_element in tr_element_list[2:-1]:
                td_element_list = tr_element.find_all('td')
                col_nums = len(th_element_list)
                for j in range(col_nums):
                    col = th_element_list[j].text.strip().replace('\n','')
                    td = td_element_list[j]
                    val = td.text.strip()
                    values[qiyenianbaogudong_column_dict[col]] = val
                values['rowkey'] = '%s_%s_%s_%d' %(self.cur_mc, self.y, table_id, idn)
                values[family + ':registrationno'] = self.cur_zch
                values[family + ':enterprisename'] = self.cur_mc
                values[family + ':id'] = str(idn)
                json_list.append(values)
                self.nbgdcz_list.append(values)
                values = {}
                # print 'wzwz****'
                idn += 1

            page_tr = sp[-1].find_all('a')
            if page_tr:
                ncnt = len(page_tr)
                if ncnt > 3:
                    # print u'股东出资分页抓取'
                    for p in range(1, ncnt-1):
                        # url = 'http://qyxy.baic.gov.cn/entPub/entPubAction!dwtz_bj.dhtml'
                        url = 'http://qyxy.baic.gov.cn/entPub/entPubAction!gdcz_bj.dhtml'
                        params = {
                            'cid': self.cid,
                            'clear': '',
                            'entid': '',
                            'pageNo': p,
                            'pageNos': p+1,
                            'pageSize': 5
                        }
                        # print 'params:', params
                        r = self.post_request(url=url, params=params)
                        r.encoding = 'utf-8'
                        soup = BeautifulSoup(r.text, 'lxml')
                        # print '***dwtzfenye***', p+1,
                        sp = soup.find(id='touziren').find_all('tr')
                        tr_element_list = sp
                        th_element_list = sp[1].find_all('th')
                        for tr_element in tr_element_list[2:-1]:
                            td_element_list = tr_element.find_all('td')
                            col_nums = len(th_element_list)
                            for j in range(col_nums):
                                col = th_element_list[j].text.strip().replace('\n','')
                                td = td_element_list[j]
                                val = td.text.strip()
                                # print 'gdcz', p+1, idn, val
                                values[qiyenianbaogudong_column_dict[col]] = val
                            # values[u'注册号']=self.cur_code
                            # values[u'省份']=self.province
                            # values[u'报送年度']=self.nianbaotitle
                            # values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, idn)
                            values['rowkey'] = '%s_%s_%s_%d' %(self.cur_mc, self.y, table_id, idn)
                            values[family + ':registrationno'] = self.cur_zch
                            values[family + ':enterprisename'] = self.cur_mc
                            values[family + ':id'] = str(idn)
                            json_list.append(values)
                            self.nbgdcz_list.append(values)
                            values = {}
                            idn += 1

            # if json_list:
            #     # print 'nianbaogudongchuzi:', json_list
            #     self.json_result[family] = json_list

    def get_nianbaoguquanbiangeng(self, url):
        family = 'equity_transfer'
        table_id = '45'
        values = {}
        json_list = []
        r = self.get_request(url=url)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'lxml')
        # print 'nianbaoguquanbiangeng', soup

        sp = soup.find(id='touziren').find_all('tr')
        # print 'lengqbgsp', len(sp)
        if len(sp) > 3:
            idn = 1
            tr_element_list = sp
            th_element_list = sp[1].find_all('th')
            for tr_element in tr_element_list[2:-1]:
                td_element_list = tr_element.find_all('td')
                col_nums = len(th_element_list)
                for j in range(col_nums):
                    col = th_element_list[j].text.strip().replace('\n','')
                    td = td_element_list[j]
                    val = td.text.strip()
                    values[qiyenianbaoguquanbiangeng_column_dict[col]] = val
                values['rowkey'] = '%s_%s_%s_%d' %(self.cur_mc, self.y, table_id, idn)
                values[family + ':registrationno'] = self.cur_zch
                values[family + ':enterprisename'] = self.cur_mc
                values[family + ':id'] = str(idn)
                json_list.append(values)
                self.nbgqbg_list.append(values)
                values = {}
                # print 'wzwz****'
                idn += 1

            page_tr = sp[-1].find_all('a')
            if page_tr:
                ncnt = len(page_tr)
                if ncnt > 3:
                    # print u'股权变更分页抓取'
                    for p in range(1, ncnt-1):
                        # url = 'http://qyxy.baic.gov.cn/entPub/entPubAction!dwtz_bj.dhtml'
                        url = 'http://qyxy.baic.gov.cn/entPub/entPubAction!gdzr_bj.dhtml'
                        params = {
                            'cid': self.cid,
                            'clear': '',
                            'entid': '',
                            'pageNo': p,
                            'pageNos': p+1,
                            'pageSize': 5
                        }
                        # print 'params:', params
                        r = self.post_request(url=url, params=params)
                        r.encoding = 'utf-8'
                        soup = BeautifulSoup(r.text, 'lxml')
                        # print '***dwtzfenye***', p+1,
                        sp = soup.find(id='touziren').find_all('tr')
                        tr_element_list = sp
                        th_element_list = sp[1].find_all('th')
                        for tr_element in tr_element_list[2:-1]:
                            td_element_list = tr_element.find_all('td')
                            col_nums = len(th_element_list)
                            for j in range(col_nums):
                                col = th_element_list[j].text.strip().replace('\n','')
                                td = td_element_list[j]
                                val = td.text.strip()
                                # print 'gqbg', p+1, idn, val
                                values[qiyenianbaoguquanbiangeng_column_dict[col]] = val
                            # values[u'注册号']=self.cur_code
                            # values[u'省份']=self.province
                            # values[u'报送年度']=self.nianbaotitle
                            # values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, idn)
                            values['rowkey'] = '%s_%s_%s_%d' %(self.cur_mc, self.y, table_id, idn)
                            values[family + ':registrationno'] = self.cur_zch
                            values[family + ':enterprisename'] = self.cur_mc
                            values[family + ':id'] = str(idn)
                            json_list.append(values)
                            self.nbgqbg_list.append(values)
                            values = {}
                            idn += 1

            # if json_list:
            #     # print 'nianbaoguquanbiangeng:', json_list
            #     self.json_result[family] = json_list

    def get_nianbaowangzhan(self, url):
        family = 'web_site'
        table_id = '41'
        values = {}
        json_list = []
        r = self.get_request(url=url)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'lxml')
        # print 'nianbaowangzhansoup', soup

        sp = soup.find(id='touziren').find_all('tr')
        # print 'lenwzsp', len(sp)
        if len(sp) > 3:
            idn = 1
            tr_element_list = sp
            th_element_list = sp[1].find_all('th')
            for tr_element in tr_element_list[2:-1]:
                td_element_list = tr_element.find_all('td')
                col_nums = len(th_element_list)
                for j in range(col_nums):
                    col = th_element_list[j].text.strip().replace('\n','')
                    td = td_element_list[j]
                    val = td.text.strip()
                    values[qiyenianbaowangzhan_column_dict[col]] = val
                values['rowkey'] = '%s_%s_%s_%d' %(self.cur_mc, self.y, table_id, idn)
                values[family + ':registrationno'] = self.cur_zch
                values[family + ':enterprisename'] = self.cur_mc
                values[family + ':id'] = str(idn)
                json_list.append(values)
                self.nbwz_list.append(values)
                values = {}
                idn += 1
                # print 'wzwz****'

            page_tr = sp[-1].find_all('a')
            if page_tr:
                ncnt = len(page_tr)
                if ncnt > 3:
                    # print u'网站或网店分页抓取'
                    for p in range(1, ncnt-1):
                        # url = 'http://qyxy.baic.gov.cn/entPub/entPubAction!dwtz_bj.dhtml'
                        url = 'http://qyxy.baic.gov.cn//entPub/entPubAction!wz_bj.dhtml'
                        params = {
                            'cid': self.cid,
                            'clear': '',
                            'entid': '',
                            'pageNo': p,
                            'pageNos': p+1,
                            'pageSize': 5
                        }
                        # print 'params:', params
                        r = self.post_request(url=url, params=params)
                        r.encoding = 'utf-8'
                        soup = BeautifulSoup(r.text, 'lxml')
                        # print '***dwtzfenye***', p+1,
                        sp = soup.find(id='touziren').find_all('tr')
                        tr_element_list = sp
                        th_element_list = sp[1].find_all('th')
                        for tr_element in tr_element_list[2:-1]:
                            td_element_list = tr_element.find_all('td')
                            col_nums = len(th_element_list)
                            for j in range(col_nums):
                                col = th_element_list[j].text.strip().replace('\n','')
                                td = td_element_list[j]
                                val = td.text.strip()
                                # print 'wz', p+1, idn, val
                                values[qiyenianbaowangzhan_column_dict[col]] = val
                            # values[u'注册号']=self.cur_code
                            # values[u'省份']=self.province
                            # values[u'报送年度']=self.nianbaotitle
                            # values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, idn)
                            values['rowkey'] = '%s_%s_%s_%d' %(self.cur_mc, self.y, table_id, idn)
                            values[family + ':registrationno'] = self.cur_zch
                            values[family + ':enterprisename'] = self.cur_mc
                            values[family + ':id'] = str(idn)
                            json_list.append(values)
                            self.nbwz_list.append(values)
                            values = {}
                            idn += 1

            # if json_list:
            #     # print 'nianbaowangzhan:', json_list
            #     self.json_result[family] = json_list

    def get_nianbaoxiugai(self, url):
        family = 'modify'
        table_id = '46'
        values = {}
        json_list = []
        r = self.get_request(url=url)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'lxml')
        # print 'nianbaowangzhansoup', soup

        sp = soup.find(id='touziren').find_all('tr')
        # print 'lenxgsp', len(sp)
        if len(sp) > 3:
            idn = 1
            tr_element_list = sp
            th_element_list = sp[1].find_all('th')
            for tr_element in tr_element_list[2:-1]:
                td_element_list = tr_element.find_all('td')
                col_nums = len(th_element_list)
                for j in range(col_nums):
                    col = th_element_list[j].text.strip().replace('\n','')
                    td = td_element_list[j]
                    val = td.text.strip()
                    values[qiyenianbaoxiugaijilu_column_dict[col]] = val
                values['rowkey'] = '%s_%s_%s_%d' %(self.cur_mc, self.y, table_id, idn)
                values[family + ':registrationno'] = self.cur_zch
                values[family + ':enterprisename'] = self.cur_mc
                values[family + ':id'] = str(idn)
                json_list.append(values)
                self.nbxg_list.append(values)
                values = {}
                idn += 1
                # print 'xg****'

            page_tr = sp[-1].find_all('a')
            if page_tr:
                ncnt = len(page_tr)
                if ncnt > 3:
                    # print u'修改分页抓取'
                    for p in range(1, ncnt-1):
                        # url = 'http://qyxy.baic.gov.cn/entPub/entPubAction!dwtz_bj.dhtml'
                        url = 'http://qyxy.baic.gov.cn/entPub/entPubAction!qybg_bj.dhtml'
                        params = {
                            'cid': self.cid,
                            'clear': '',
                            'entid': '',
                            'pageNo': p,
                            'pageNos': p+1,
                            'pageSize': 5
                        }
                        # print 'params:', params
                        r = self.post_request(url=url, params=params)
                        r.encoding = 'utf-8'
                        soup = BeautifulSoup(r.text, 'lxml')
                        # print '***dwtzfenye***', p+1,
                        sp = soup.find(id='touziren').find_all('tr')
                        tr_element_list = sp
                        th_element_list = sp[1].find_all('th')
                        for tr_element in tr_element_list[2:-1]:
                            td_element_list = tr_element.find_all('td')
                            col_nums = len(th_element_list)
                            for j in range(col_nums):
                                col = th_element_list[j].text.strip().replace('\n','')
                                td = td_element_list[j]
                                val = td.text.strip()
                                # print 'xg', p+1, idn, val
                                values[qiyenianbaoxiugaijilu_column_dict[col]] = val
                            # values[u'注册号']=self.cur_code
                            # values[u'省份']=self.province
                            # values[u'报送年度']=self.nianbaotitle
                            # values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, idn)
                            values['rowkey'] = '%s_%s_%s_%d' %(self.cur_mc, self.y, table_id, idn)
                            values[family + ':registrationno'] = self.cur_zch
                            values[family + ':enterprisename'] = self.cur_mc
                            values[family + ':id'] = str(idn)
                            json_list.append(values)
                            self.nbxg_list.append(values)
                            values = {}
                            idn += 1
            # if json_list:
            #     # print 'nianbaoxiugai:', json_list
            #     self.json_result[family] = json_list

    def get_nianbaoduiwaitouzi(self, url):
        family = 'investment'
        table_id = '47'
        values = {}
        json_list = []
        r = self.get_request(url=url)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'lxml')
        # print 'nianbaoduiwaitouzisoup', soup

        sp = soup.find(id='touziren').find_all('tr')
        # print 'lendwtzsp', len(sp)
        if len(sp) > 3:
            idn = 1
            tr_element_list = sp
            th_element_list = sp[1].find_all('th')
            for tr_element in tr_element_list[2:-1]:
                td_element_list = tr_element.find_all('td')
                col_nums = len(th_element_list)
                for j in range(col_nums):
                    col = th_element_list[j].text.strip().replace('\n','')
                    td = td_element_list[j]
                    val = td.text.strip()
                    values[qiyenianbaoduiwaitouzi_column_dict[col]] = val
                # values[u'注册号']=self.cur_code
                # values[u'省份']=self.province
                # values[u'报送年度']=self.nianbaotitle
                # json_list.append(values)
                # values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, idn)
                values['rowkey'] = '%s_%s_%s_%d' %(self.cur_mc, self.y, table_id, idn)
                values[family + ':id'] = str(idn)
                json_list.append(values)
                self.nbdwtz_list.append(values)
                values = {}
                idn += 1
                # print 'wzwz****'

            page_tr = sp[-1].find_all('a')
            if page_tr:
                ncnt = len(page_tr)
                if ncnt > 3:
                    # print u'对外投资分页抓取'
                    for p in range(1, ncnt-1):
                        url = 'http://qyxy.baic.gov.cn/entPub/entPubAction!dwtz_bj.dhtml'
                        params = {
                            'cid': self.cid,
                            'clear': '',
                            'entid': '',
                            'pageNo': p,
                            'pageNos': p+1,
                            'pageSize': 5
                        }
                        # print 'params:', params
                        r = self.post_request(url=url, params=params)
                        r.encoding = 'utf-8'
                        soup = BeautifulSoup(r.text, 'lxml')
                        # print '***dwtzfenye***', p+1,
                        sp = soup.find(id='touziren').find_all('tr')
                        tr_element_list = sp
                        th_element_list = sp[1].find_all('th')
                        for tr_element in tr_element_list[2:-1]:
                            td_element_list = tr_element.find_all('td')
                            col_nums = len(th_element_list)
                            for j in range(col_nums):
                                col = th_element_list[j].text.strip().replace('\n','')
                                td = td_element_list[j]
                                val = td.text.strip()
                                # print 'dwtz', p+1, idn, val
                                values[qiyenianbaoduiwaitouzi_column_dict[col]] = val
                            # values[u'注册号']=self.cur_code
                            # values[u'省份']=self.province
                            # values[u'报送年度']=self.nianbaotitle
                            # values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, idn)
                            values['rowkey'] = '%s_%s_%s_%d' %(self.cur_mc, self.y, table_id, idn)
                            values[family + ':registrationno'] = self.cur_zch
                            values[family + ':enterprisename'] = self.cur_mc
                            values[family + ':id'] = str(idn)
                            json_list.append(values)
                            self.nbdwtz_list.append(values)
                            values = {}
                            idn += 1
            # if json_list:
            #     # print 'nianbaoduiwaitouzi:', json_list
            #     self.json_result[family] = json_list

    def get_guquanchuzhi_detail(self, url):
        try:
            r = self.get_request(url=url)
        except Exception as e:
            # self.info(u'%s' %e)
            return
        soup = BeautifulSoup(r.text, 'lxml')
        table_list = soup.find_all('table')
        for tb in table_list:
            tig = tb.find_all('tr')[0].text
            if tig == u'变更':
                tr_list = tb.find_all('tr')
                th_list = tb.find_all('tr')[1].find_all('th')
                if len(tr_list) > 2:
                    dyn = 1

                    family = 'gqczbg'
                    tableID = '61'

                    json_list = []
                    values = {}
                    for tre in tr_list[2:-1]:
                        col_num = len(th_list)
                        td_list = tre.find_all('td')
                        for i in range(col_num):
                            col = th_list[i].text.strip()
                            val = td_list[i].text.strip()
                            # print u'gqbg', col, val
                            values[gqcz_biangeng_column_dict[col]] = val
                        values['rowkey'] = '%s_%s_%s_%s%d' %(self.cur_mc, self.djbh, self.djrq, tableID, dyn)
                        values[family + ':registrationno'] = self.cur_zch
                        values[family + ':enterprisename'] = self.cur_mc
                        values[family + ':id'] = str(dyn)
                        try:
                            values.pop(u'序号')
                        except KeyError as e:
                            # self.info(u'*%s' % e)
                            pass
                        json_list.append(values)
                        self.gqczbg_list.append(values)
                        values = {}
                        dyn += 1
                    # if json_list:
                    #     self.json_result[family] = json_list
            elif tig == u'注销':
                tr_list = tb.find_all('tr')
                th_list = tb.find_all('tr')[1].find_all('th')
                if len(tr_list) > 2:

                    family = 'gqczzx'
                    tableID = '60'

                    json_list = []
                    values = {}

                    dyn = 1
                    for tre in tr_list[2:-1]:
                        col_num = len(th_list)
                        td_list = tre.find_all('td')
                        for i in range(col_num):
                            col = th_list[i].text.strip()
                            val = td_list[i].text.strip()
                            # print u'gqzx', col, val
                            values[gqcz_zhuxiao_column_dict[col]] = val
                        values['rowkey'] = '%s_%s_%s_%s%d' %(self.cur_mc, self.djbh, self.djrq, tableID, dyn)
                        values[family + ':registrationno'] = self.cur_zch
                        values[family + ':enterprisename'] = self.cur_mc
                        values[family + ':id'] = str(dyn)
                        try:
                            values.pop(u'序号')
                        except KeyError as e:
                            # self.info(u'*%s' % e)
                            pass
                        json_list.append(values)
                        self.gqczzx_list.append(values)
                        values = {}
                        dyn += 1
                    # if json_list:
                    #     self.json_result[family] = json_list

    def get_dongchandiya_detail(self, url):
        zxb = {'dyqrgkFrame': u'抵押权人概况', 'dywgkFrame':u'抵押物概况', 'dcdybgFrame': u'变更'}  # iframe id参数
        try:
            r = self.get_request(url=url)
        except Exception as e:
            self.info(u'%s' %e)
            return
        chr = re.search(r'(?<=chr_id=).*', url).group()
        soup = BeautifulSoup(r.text, 'lxml')
        # print '**__**', soup
        table_list = soup.find_all('table')
        iframe_list = soup.find_all('iframe')
        dcnt = 0
        for tb in table_list:
            tig = tb.find_all('tr')[0].text
            # print 'dcdy**bb', tig
            if tig == u'动产抵押登记信息':

                family = 'dcdydj'
                tableID = '63'

                json_list = []
                values = {}
                djbh = u''
                djrq = u''
                tr_list = tb.find_all('tr')[1:]
                for tre in tr_list:
                    th_list = tre.find_all('th')
                    td_list = tre.find_all('td')
                    col_num = len(th_list)
                    for i in range(col_num):
                        col = th_list[i].text.strip()
                        val = td_list[i].text.strip()
                        # print 'dc**djxx', col, val
                        values[dcdy_dengji_column_dict[col]] = val
                        if col == u'登记编号':
                            djbh = val
                            self.djbh = djbh
                        if col == u'登记日期':
                            djrq = val
                            self.djrq = djrq
                values['rowkey'] = '%s_%s_%s_%s' %(self.cur_mc, self.djbh, self.djrq, tableID)
                values[family + ':registrationno'] = self.cur_zch
                values[family + ':enterprisename'] = self.cur_mc
                # json_list.append(values)
                self.dcdydj_list.append(values)

                # self.json_result[family] = json_list

            elif tig == u'被担保债权概况':
                family = 'bdbzqgk'
                tableID = '56'

                json_list = []
                values = {}

                tr_list = tb.find_all('tr')[1:]
                for tre in tr_list:
                    th_list = tre.find_all('th')
                    td_list = tre.find_all('td')
                    col_num = len(th_list)
                    for i in range(col_num):
                        col = th_list[i].text.strip()
                        val = td_list[i].text.strip()
                        # print 'dc**bdbrgk', col, val
                        values[dcdy_beidanbaozhaiquan_column_dict[col]] = val
                values['rowkey'] = '%s_%s_%s_%s' %(self.cur_mc, self.djbh, self.djrq, tableID)
                values[family + ':registrationno'] = self.cur_zch
                values[family + ':enterprisename'] = self.cur_mc
                # json_list.append(values)
                self.bdbzqgk_list.append(values)
                # self.json_result[family] = json_list

            elif tig == u'注销':
                family = 'dcdyzx'
                tableID = '59'

                json_list = []
                values = {}
                tr_list = tb.find_all('tr')[1:]
                for tre in tr_list:
                    th_list = tre.find_all('th')
                    td_list = tre.find_all('td')
                    col_num = len(th_list)
                    for i in range(col_num):
                        col = th_list[i].text.strip()
                        val = td_list[i].text.strip()
                        # print 'dc**zx', col, val
                        values[dcdy_zhuxiao_column_dict[col]] = val
                values['rowkey'] = '%s_%s_%s_%s' %(self.cur_mc, self.djbh, self.djrq, tableID)
                values[family + ':registrationno'] = self.cur_zch
                values[family + ':enterprisename'] = self.cur_mc
                # json_list.append(values)
                self.dcdyzx_list.append(values)
                # self.json_result[family] = json_list

            else:
                self.info('unknown_title:'+tig)


        for fm in iframe_list:
            # print '**'*100
            fid = fm.get('id')  # iframe对应id
            trg = zxb[fid]  # id对应表名
            # print 'dcdy**ff', fid, trg, '**',  self.entId, 'm', chr
            if trg == u'抵押权人概况':
                family = 'dyqrgk'
                tableID = '55'
                json_list = []
                values = {}

                url = 'http://qyxy.baic.gov.cn/gjjbjTab/gjjTabQueryCreditAction!dyqrgkFrame.dhtml?'\
                'ent_id='+self.entId+'&chr_id='+chr+'&clear=true&timeStamp='+self.cur_time
                # print u'抵押权人概况url', url
                r = self.get_request(url=url)
                soup = BeautifulSoup(r.text, 'lxml')
                # print 'dyqrgk', soup
                tb_list = soup.find_all(class_='detailsList')
                # print 'len@', len(tb_list)
                try:
                    tr_list = tb_list[0].find_all('tr')
                except:
                    self.info(u'抵押权人概况加载失败')
                    continue
                th_list = tb_list[0].find_all('tr')[1].find_all('th')
                gkn = 1  # 概况递增id
                if len(tr_list) > 3:
                    for tre in tr_list[2:-1]:
                        col_num = len(th_list)
                        td_list = tre.find_all('td')
                        for i in range(col_num):
                            col = th_list[i].text.strip()
                            val = td_list[i].text.strip()
                            # print u'@@', col, val
                            values[dcdy_diyaquanren_column_dict[col]] = val
                        values['rowkey'] = '%s_%s_%s_%s%d' %(self.cur_mc, self.djbh, self.djrq, tableID, gkn)
                        values[family + ':registrationno'] = self.cur_zch
                        values[family + ':enterprisename'] = self.cur_mc
                        values[family + ':id'] = str(gkn)
                        try:
                            values.pop(dcdy_diyaquanren_column_dict[u'序号'])
                        except KeyError as e:
                            # self.info(u'%s' % e)
                            pass
                        # json_list.append(values)
                        self.dyqrgk_list.append(values)
                        values = {}
                        gkn += 1
                    # if json_list:
                    #     self.json_result[family] = json_list

            elif trg == u'抵押物概况':
                family = 'dywgk'
                tableID = '57'

                json_list = []
                values = {}

                url = 'http://qyxy.baic.gov.cn/gjjbjTab/gjjTabQueryCreditAction!dywgkFrame.dhtml?'\
                'chr_id='+chr+'&chr_id='+chr+'&clear=true&timeStamp='+self.cur_time
                # print u'抵押物概况url', url
                r = self.get_request(url=url)
                soup = BeautifulSoup(r.text, 'lxml')
                # print 'dywgk', soup
                tb_list = soup.find_all(class_='detailsList')
                # print 'lenβ', len(tb_list)
                try:
                    tr_list = tb_list[0].find_all('tr')
                except:
                    self.info(u'抵押物概况table加载失败，访问频繁')
                    continue
                th_list = tb_list[0].find_all('tr')[1].find_all('th')
                pgn = tr_list[-1].find_all('a')
                try:
                    pagescnt = int(soup.find(id='pagescount').get('value'))
                    # print '@'*20, 'gk', pagescnt
                except:
                    pagescnt = 1
                # print 'pgn', len(pgn)

                dyn = 1
                if len(tr_list) > 3:
                    for tre in tr_list[2:-1]:
                        col_num = len(th_list)
                        td_list = tre.find_all('td')
                        for i in range(col_num):
                            col = th_list[i].text.strip()
                            val = td_list[i].text.strip()
                            # print u'ββ', col, val
                            values[dcdy_diyawu_column_dict[col]] = val
                        values['rowkey'] = '%s_%s_%s_%s%d' %(self.cur_mc, self.djbh, self.djrq, tableID, dyn)
                        values[family + ':registrationno'] = self.cur_zch
                        values[family + ':enterprisename'] = self.cur_mc
                        values[family + ':id'] = str(dyn)
                        try:
                            values.pop(dcdy_diyawu_column_dict[u'序号'])
                        except KeyError as e:
                            # self.info(u'%s' % e)
                            pass
                        # json_list.append(values)
                        self.dywgk_list.append(values)
                        values = {}
                        dyn += 1

                    # 有翻页情况
                    if len(pgn) > 2:

                        for p in range(2, pagescnt+1):
                            url = 'http://qyxy.baic.gov.cn/gjjbjTab/gjjbjTab/gjjTabQueryCreditAction!dywgkFrame.dhtml'
                            params = dict(chr_id=chr, clear='', ent_id='', pageNo=p-1, pageNos=p, pageSize=5)
                            # print 'wgk**', params
                            try:
                                r = self.post_request(url=url, params=params)
                            except:
                                # self.info(u'网站内部internal Error访问频繁')
                                continue
                            soup = BeautifulSoup(r.text, 'lxml')
                            # print 'dywgksub', soup
                            tb_list = soup.find_all(class_='detailsList')
                            try:
                                tr_list = tb_list[0].find_all('tr')
                            except:
                                # self.info(u'翻页太频繁,ip临时被封')
                                continue
                            pgn = tr_list[-1].find_all('a')

                            for tre in tr_list[2:-1]:
                                col_num = len(th_list)
                                td_list = tre.find_all('td')
                                for i in range(col_num):
                                    col = th_list[i].text.strip()
                                    val = td_list[i].text.strip()
                                    # print u'ββsub', p, col, val
                                    values[dcdy_diyawu_column_dict[col]] = val
                                values['rowkey'] = '%s_%s_%s_%s%d' %(self.cur_mc, self.djbh, self.djrq, tableID, dyn)
                                values[family + ':registrationno'] = self.cur_zch
                                values[family + ':enterprisename'] = self.cur_mc
                                values[family + ':id'] = str(dyn)
                                try:
                                    values.pop(dcdy_diyawu_column_dict[u'序号'])
                                except KeyError as e:
                                    # self.info(u'*%s' % e)
                                    pass
                                json_list.append(values)
                                self.dywgk_list.append(values)
                                values = {}
                                dyn += 1
                            # 下面跳出逻辑最多指定10页抓取，有1000多页 e.g.北京恒嘉国际融资租赁有限公司
                            if p == 10:
                                # print u'页数过多，只取前10页', pagescnt
                                self.info(u'页数过多，只取前10页')
                                break
                    # if json_list:
                    #     self.json_result[family] = json_list

            elif trg == u'变更':
                family = 'dcdybg'
                tableID = '58'

                json_list = []
                values = {}

                url = 'http://qyxy.baic.gov.cn/gjjbjTab/gjjTabQueryCreditAction!dcdybgFrame.dhtml?'\
                'chr_id='+chr+'&chr_id='+chr+'&clear=true&timeStamp='+self.cur_time
                # print u'变更url', url
                r = self.get_request(url=url)
                soup = BeautifulSoup(r.text, 'lxml')
                # print 'dybg', soup
                tb_list = soup.find_all(class_='detailsList')
                # print 'lenγ', len(tb_list)
                try:
                    tr_list = tb_list[0].find_all('tr')
                except:
                    self.info(u'动产抵押变更加载失败')
                    continue
                th_list = tb_list[0].find_all('tr')[1].find_all('th')
                if len(tr_list) > 2:
                    dyn = 1
                    for tre in tr_list[2:-1]:
                        col_num = len(th_list)
                        td_list = tre.find_all('td')
                        for i in range(col_num):
                            col = th_list[i].text.strip()
                            val = td_list[i].text.strip()
                            # print u'γγ', col, val
                            values[dcdy_biangeng_column_dict[col]] = val
                        values['rowkey'] = '%s_%s_%s_%s%d' %(self.cur_mc, self.djbh, self.djrq, tableID, dyn)
                        values[family + ':registrationno'] = self.cur_zch
                        values[family + ':enterprisename'] = self.cur_mc
                        values[family + ':id'] = str(dyn)
                        try:
                            values.pop(dcdy_biangeng_column_dict[u'序号'])
                        except KeyError as e:
                            # self.info(u'*%s' % e)
                            pass
                        json_list.append(values)
                        self.dcdybg_list.append(values)
                        values = {}
                        dyn += 1
                    # if json_list:
                    #     self.json_result[family] = json_list
            else:
                # print u'未知表格', trg
                self.info(u'未知表格'+trg)

        dcnt += 1

if __name__ == '__main__':
    searcher = BeiJing()
    searcher.submit_search_request(u"北京众旺达汽车租赁有限公司")#北京京东尚科信息技术有限公司")  # 阿里巴巴（北京）软件服务有限公司")
    # 北京幻想纵横网络技术有限公司")#北京百代彩虹激光技术有限责任公司")#北京北斗兴业信息技术股份有限公司") # 北京中益优胜投资管理有限公司
    # 北京三宝阁图书销售中心")#北京百度网讯科技有限公司")# 北京一搏星徽商贸中心")#北京链家房地产经纪有限公司")#北斗中科卫士物联科技（北京）有限公司")#北京兴盛建业机电设备有限公司")
    # 乐视网信息技术（北京）股份有限公司")#北京中视乾元文化发展有限公司")中国机械工业集团有限公司
    # 北京链家房地产经纪有限公司")#中信国安黄金有限责任公司")  # 北京正北经贸有限公司 本草汇（北京）环境治理有限公司"))
    # print json.dumps(searcher.json_result, ensure_ascii=False)
