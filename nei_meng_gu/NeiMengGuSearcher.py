# coding=utf-8

import PackageTool
from gs.Searcher import Searcher
from gs.Searcher import get_args
import os
import sys
from bs4 import BeautifulSoup
from TableConfig import *
from gs.KafkaAPI import KafkaAPI
import json
from gs.TimeUtils import *
import uuid
from gs.MyException import NotFoundException


class NeiMengGuSearcher(Searcher):
    load_func_dict = {}
    lock_id = 0
    service = None
    tab_set = set()

    def __init__(self):
        super(NeiMengGuSearcher, self).__init__(use_proxy=False)
        self.load_func_dict[u'基本信息'] = self.get_ji_ben
        self.load_func_dict[u'股东信息'] = self.get_gu_dong
        self.load_func_dict[u'变更信息'] = self.get_bian_geng
        self.load_func_dict[u'主要人员信息'] = self.get_zhu_yao_ren_yuan
        self.load_func_dict[u'分支机构信息'] = self.get_fen_zhi_ji_gou
        self.load_func_dict[u'清算信息'] = self.get_qing_suan
        self.load_func_dict[u'投资人信息'] = self.get_tou_zi_ren
        self.load_func_dict[u'动产抵押登记信息'] = self.get_dong_chan_di_ya
        self.load_func_dict[u'股权出质登记信息'] = self.get_gu_quan_chu_zhi
        self.load_func_dict[u'行政处罚信息'] = self.get_xing_zheng_chu_fa
        self.load_func_dict[u'经营异常信息'] = self.get_jing_ying_yi_chang
        self.load_func_dict[u'严重违法信息'] = self.get_yan_zhong_wei_fa
        self.load_func_dict[u'严重违法失信信息'] = self.get_yan_zhong_wei_fa
        self.load_func_dict[u'抽查检查信息'] = self.get_chou_cha_jian_cha
        # self.load_func_dict[u'主管部门（出资人）信息'] = self.get_zhu_guan_bu_men     #Modified by Jing
        # self.load_func_dict[u'参加经营的家庭成员姓名'] = self.load_jiatingchengyuan     # Modified by Jing
        # self.load_func_dict[u'合伙人信息'] = self.load_hehuoren     #Modified by Jing
        # self.load_func_dict[u'成员名册'] = self.load_chengyuanmingce     # Modified by Jing
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:45.0) Gecko/20100101 Firefox/45.0",
                        "Host": "www.nmgs.gov.cn:7001",
                        "Accept": "*/*",
                        "Accept-Encoding": "gzip, deflate",
                        "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
                        # "Referer": "http://www.nmgs.gov.cn:7001/aiccips/CheckEntContext/showInfo.html",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1"
                        }
        self.set_config()
        self.log_name = self.topic + "_" + str(uuid.uuid1())
        self.entNo = ''
        self.regOrg = ''
        self.ent_type = ''

    def set_config(self):
        self.plugin_path = os.path.join(sys.path[0], '../nei_meng_gu/ocr/neimenggu/neimenggu.bat')
        self.group = 'Crawler'  # 正式
        self.kafka = KafkaAPI("GSCrawlerResult")  # 正式
        # self.group = 'CrawlerTest'  # 测试
        # self.kafka = KafkaAPI("GSCrawlerTest")  # 测试
        self.topic = 'GsSrc15'
        self.province = u'内蒙古自治区'
        self.kafka.init_producer()
        self.set_request_timeout(30)

    def download_yzm(self):
        image_url = 'http://www.nmgs.gov.cn:7001/aiccips//verify.html?random=0.26959788688170283'
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
        ur = 'http://www.nmgs.gov.cn:7001/aiccips/CheckEntContext/checkCode.html'
        url = 'http://www.nmgs.gov.cn:7001/aiccips/CheckEntContext/showInfo.html'
        textfield = None
        for t in range(50):
            yzm = self.get_yzm()
            if not textfield:
                para = {'textfield': keyword, 'code': yzm}
                rq = self.post_request(url=ur, params=para)
                if u'验证码不正确' in rq.text:
                    continue
                else:
                    # text_field = rq.text
                    # print rq.text
                    # textfield = text_field[text_field.index('textfield')+12:text_field.index('}')-1].replace('\\n', '').replace('\u003d','=')
                    textfield_dict = json.loads(rq.text)
                    if 'textfield' not in textfield_dict:
                        continue
                    else:
                        textfield = textfield_dict['textfield']
                params = {'textfield': textfield, 'code': yzm}
                r = self.post_request(url=url, params=params)
                search_result_json = {}
                soup = BeautifulSoup(r.text, 'lxml')
                if u'暂未查询到相关记录' in r.text:
                    return None
                elif u'验证码不正确' in r.text:
                    continue
                else:
                    # print '*** %d' % r.status_code
                    # print soup
                    search_result_text = soup.select('html > body > div > div > div > ul > li > a')[0].attrs['href']
                    if search_result_text != u'':
                        self.cur_mc = soup.select('html > body > div > div > div > ul > li > a')[0].text.strip()
                        if flags:
                            if keyword == self.cur_mc :
                                self.cur_zch = soup.select('html > body > div > div > div > ul > li > span')[0].text.strip()
                                search_result_json['entname'] = self.cur_mc
                                search_result_json['regno'] = self.cur_zch
                                search_result_json['textfield'] = textfield
                                search_result_json['service'] = search_result_text.split("=")[1]
                                tag_a = json.dumps(search_result_json, ensure_ascii=False)
                        else:
                            self.cur_mc = keyword
                            self.cur_zch = soup.select('html > body > div > div > div > ul > li > span')[0].text.strip()
                            search_result_json['entname'] = self.cur_mc
                            search_result_json['regno'] = self.cur_zch
                            search_result_json['textfield'] = textfield
                            search_result_json['service'] = search_result_text.split("=")[1]
                            tag_a = json.dumps(search_result_json, ensure_ascii=False)
                        return tag_a

    def get_search_args(self, tag_a, keyword):
        self.service = None
        search_result_json = json.loads(tag_a)
        if search_result_json.get('entname', None) == keyword:
            self.service = search_result_json['service']
            self.cur_mc = search_result_json['entname'].replace('(', u'（').replace(')', u'）')  # 公司名称括号统一转成全角
            self.cur_zch = search_result_json['regno']
            return 1
        else:
            return 0

    def parse_detail(self):
        """
        解析公司详情信息
        :return:
        """
        self.get_deng_ji()
        self.get_bei_an()
        self.get_dong_chan_di_ya()
        self.get_gu_quan_chu_zhi()
        self.get_xing_zheng_chu_fa()
        self.get_jing_ying_yi_chang()
        #  网站接口一直500错误
        # self.get_yan_zhong_wei_fa(*kwargs) 
        self.get_chou_cha_jian_cha()

    def get_deng_ji(self):
        self.tab_set.clear()
        url = 'http://www.nmgs.gov.cn:7001/aiccips/GSpublicity/GSpublicityList.html'
        nmgservice = self.service+'=='
        # print nmgservice
        params = {'service': nmgservice}
        r = self.get_request(url=url, params=params)
        soup = BeautifulSoup(r.text, 'lxml')
        tab_ele_list = soup.select('div.tabs li')
        for tab in tab_ele_list:
            self.tab_set.add(tab.text)
        # print '>>', json.dumps(list(self.tab_set), ensure_ascii=False)
        if len(soup.select('img[src=http://www.nmgs.gov.cn:7001/aiccips//images/errorinfo_new2.gif]')) > 0:
            return NotFoundException()
        # public_detail = soup.select("div#details > script")[2].text.strip()
        # public_detail = public_detail.split('goIndex')[1]
        # entNo = public_detail.split('\n')[2]
        # regOrg = public_detail.split('\n')[3]
        # self.entNo = entNo[entNo.index('entNo = encodeURI')+len('entNo = encodeURI')+2:len(entNo)-4]
        # self.regOrg = regOrg[regOrg.index('regOrg = encodeURI')+len('regOrg = encodeURI')+2:len(regOrg)-4]
        self.entNo = soup.select("input#entNo")[0].attrs['value']
        self.regOrg = soup.select("input#regOrg")[0].attrs['value']
        self.ent_type = soup.select("input#entType")[0].attrs['value']
        jiben_table = soup.select('table#baseinfo')[0]
        self.get_ji_ben(jiben_table)
        if len(soup.select('table#touziren')) > 0:
            gudong_table = soup.select('table#touziren')[0]
            if u'暂无数据' not in gudong_table.text:
                self.get_gu_dong()
        if len(soup.select('div#biangeng table')) > 0:
            biangeng_table = soup.select('div#biangeng table')[0]
            if u'暂无数据' not in biangeng_table.text:
                self.get_bian_geng()
        # for table_element in table_elements:
        #     table_name = table_element.find("th").text.strip().split('\n')[0]  # 表格名称
        #     if u'股东信息' in table_name:
        #         table_name = u'股东信息'
        #     table_name=table_name.replace(u'股东（发起人）信息',u'股东信息')
        #     table_name=self.pattern.sub('', table_name)
        #     if u'<<' in table_name:
        #         continue
        #     elif table_name in self.load_func_dict:
        #         self.load_func_dict[table_name](table_element)
        #     else:
        #         self.info(u'未知表名....')

    def get_ji_ben(self, table_element):
        """
        查询基本信息
        :return: 基本信息结果
        """
        family = 'Registered_Info'
        table_id = '01'
        self.json_result[family] = []
        td_list = table_element.select('tr > td')
        th_list = table_element.select('tr > th')[1:]
        result_json = [{}]
        if len(self.cur_zch) == 18:
            result_json[0][u'统一社会信用代码'] = self.cur_zch
            result_json[0][u'注册号'] = ''
        if len(self.cur_zch) != 18:
            result_json[0][u'统一社会信用代码'] = ''
            result_json[0][u'注册号'] = self.cur_zch
        for i in range(len(td_list)):
            th = th_list[i]
            td = td_list[i]
            desc = self.pattern.sub('', th.text)
            val = self.pattern.sub('', td.text)
            # print desc,val
            if len(desc) > 0:
                result_json[0][desc] = val
        for j in result_json:
            self.json_result[family].append({})
            for k in j:
                col = jiben_column_dict[k]
                val = j[k]
                self.json_result[family][-1][col] = val
        self.json_result[family][-1]['rowkey'] = '%s_%s_%s_' % (self.cur_mc, table_id, self.cur_zch)
        self.json_result[family][-1][family + ':registrationno'] = self.cur_zch
        self.json_result[family][-1][family + ':enterprisename'] = self.cur_mc
        self.json_result[family][-1][family + ':province'] = self.province
        self.json_result[family][-1][family + ':lastupdatetime'] = get_cur_time()
        # print json.dumps(self.json_result[family], ensure_ascii=False)

    def get_gu_dong(self):
        """
        查询股东信息
        :return:
        """
        family = 'Shareholder_Info'
        table_id = '04'
        self.json_result[family] = []
        url = 'http://www.nmgs.gov.cn:7001/aiccips/GSpublicity/invInfoPage.html'
        params = {'entNo': self.entNo, 'regOrg': self.regOrg, 'pageNo': '100'}
        r = self.post_request(url=url, params=params)
        table_detail = json.loads(r.text)[u'list']
        for j in table_detail:
            self.json_result[family].append({})
            for k in j:
                if k in gu_dong_dict:
                    col = family + ':' + gu_dong_dict[k]
                    val = j[k]
                    if k == 'conDate' or k == 'acConDate':
                        val = format_nei_meng_gu(val).split(' ')[0]
                    self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family][i], ensure_ascii=False)

    def get_gu_dong_detail(self, id,table_element):
        detail_dict_list = []
        url = 'http://www.nmgs.gov.cn:7001/aiccips/GSpublicity/invInfoPage.html'
        params = {'id': id, 'ad_cheak': '1'}
        r = self.post_request(url = url, params = params)
        soup = BeautifulSoup(r.text, 'lxml')
        table_element=soup.find('table')
        th_element_list=table_element.select('th')[2:]
        tr_element_list=table_element.select('tr')[3:4]
        for tr_element in tr_element_list:
            # detail_dict_list.append({})
            td_element_list = tr_element.select('td')[1:]
            col_nums = len(th_element_list)
            detail_dict_list.append({})
            for j in range(col_nums):
                col_dec = th_element_list[j].text.strip().replace('\n', '')
                if u'明细' in col_dec:
                    continue
                if j > 3:
                    j -= 2
                col = gu_dong_dict[col_dec]
                td = td_element_list[j]
                val = td.text.strip()
                detail_dict_list[-1][col] = val
        # print 'detail_dict_list:',detail_dict_list
        return detail_dict_list

    def get_tou_zi_ren(self, table_element):
        pass

    def get_bian_geng(self):
        """
        查询变更信息
        :return:
        """
        family = 'Changed_Announcement'
        table_id = '05'
        self.json_result[family] = []
        url = 'http://www.nmgs.gov.cn:7001/aiccips/GSpublicity/entChaPage'
        params = {'entNo': self.entNo, 'regOrg': self.regOrg, 'pageNo': '100','entType': self.ent_type}
        r = self.post_request(url=url, params=params)
        if u'暂无数据' not in r.text:
            table_detail = json.loads(r.text)[u'list']
            for j in table_detail:
                self.json_result[family].append({})
                for k in j:
                    if k in bian_geng_dict:
                        col = family + ':' + bian_geng_dict[k]
                        val = j[k]
                        if k == 'altDate':
                            val = format_nei_meng_gu(val).split(' ')[0]
                        self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
        # print json.dumps(self.json_result[family], ensure_ascii=False)

    def get_bei_an(self):
        if u'备案信息' not in self.tab_set:
            return
        url = 'http://www.nmgs.gov.cn:7001/aiccips/GSpublicity/GSpublicityList.html?service=entCheckInfo'
        params = {'entNo': self.entNo, 'regOrg': self.regOrg,'entType':self.ent_type}
        r = self.get_request(url = url, params = params)
        soup = BeautifulSoup(r.text, 'lxml')

        zyry_th_list = None
        fzjg_th_list = None
        qs_table = None

        table_list = soup.select('table')
        for table_ele in table_list:
            if u'主要人员信息' in table_ele.text:
                zyry_th_list = table_ele.select('tr')[1].select('th')
            elif u'分支机构信息' in table_ele.text:
                fzjg_th_list = table_ele.select('tr')[1].select('th')
            if u'清算信息' in table_ele.text:
                if u'暂无数据' not in table_ele.text:
                    qs_table = table_ele

        if len(soup.select('div#zyry table')) > 0:
            zyry_table = soup.select('div#zyry table')[0]
            if u'暂无数据' not in zyry_table and zyry_th_list:
                self.get_zhu_yao_ren_yuan(zyry_th_list, zyry_table)
        if len(soup.select('div#branch table')) > 0:
            fzjg_table = soup.select('div#branch table')[0]
            if u'暂无数据' not in fzjg_table and fzjg_th_list:
                self.get_fen_zhi_ji_gou(fzjg_th_list, fzjg_table)
        if qs_table:
            self.get_qing_suan(qs_table)

    def get_zhu_yao_ren_yuan(self, th_element_list, table_element):
        """
        查询主要人员信息
        :param th_element_list: 表头
        :param table_element: 表格内容
        :return:
        """
        family = 'KeyPerson_Info'
        table_id = '06'
        self.json_result[family] = []

        tr_element_list = table_element.select('tr')
        for tr_element in tr_element_list:
            td_element_list = tr_element.select('td')
            list_length = len(td_element_list)
            fixed_length = list_length - list_length % 3
            self.json_result[family].append({})
            for j in range(fixed_length):
                col_dec = th_element_list[j].text.strip().replace('\n', '')
                col = zhuyaorenyuan_column_dict[col_dec]
                td = td_element_list[j]
                val = self.pattern.sub('', td.text)
                self.json_result[family][-1][col] = val
                if j == 2 and fixed_length == 6:
                    self.json_result[family].append({})
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family][i], ensure_ascii=False)

    def get_fen_zhi_ji_gou(self, th_element_list, table_element):
        """
        查询分支机构信息
        :param th_element_list: 表头
        :param table_element: 表内容
        :return:
        """
        family = 'Branches'
        table_id = '08'
        self.json_result[family] = []
        tr_element_list = table_element.select('tr')
        for tr_element in tr_element_list[1:]:
            td_element_list = tr_element.select('td')
            col_nums = len(td_element_list)
            self.json_result[family].append({})
            for j in range(col_nums):
                col_dec = th_element_list[j].text.strip().replace('\n', '')
                col = fenzhijigou_column_dict[col_dec]
                td = td_element_list[j]
                val = self.pattern.sub('', td.text)
                self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family][i], ensure_ascii=False)

    def get_qing_suan(self, table_element):
        """
        查询清算信息
        :param table_element:
        :return:
        """
        family = 'liquidation_Information'
        table_id = '09'
        self.json_result[family] = []
        cheng_yuan = ''
        fu_ze_ren = ''
        if u'暂无数据' not in table_element.text.strip():
            tr_element_list = table_element.select('tr')[1:]
            # self.json_result[family].append({})
            for tr_element in tr_element_list:
                td_element = tr_element.select('td')
                th_element = tr_element.select('th')
                col_dec = th_element[0].text.strip()
                col = qingsuan_column_dict[col_dec]
                val = self.pattern.sub('', td_element[0].text)
                # self.json_result[family][-1][col] = val
                if col_dec == u'清算组负责人':
                    cheng_yuan = val
                else:
                    fu_ze_ren = val
            # print cheng_yuan,fu_ze_ren
            result_json = []
        if cheng_yuan != '' and fu_ze_ren != '':
            result_json.append({'rowkey': '%s_%s_%s_' % (self.cur_mc, table_id, self.cur_zch),
                                family + ':' + 'liquidation_member': 'cheng_yuan',
                                family + ':' + 'liquidation_pic': 'fu_ze_ren',
                                family + ':registrationno': self.cur_zch,
                                family + ':enterprisename': self.cur_mc
                                })
            self.json_result[family].extend(result_json)
            # print json.dumps(self.json_result[family], ensure_ascii=False)

    def get_dong_chan_di_ya(self):
        """
        查询动产抵押信息
        :param param_param_service:
        :param table_element:
        :return:
        """
        if u'动产抵押登记信息' not in self.tab_set:
            return
        family = 'Chattel_Mortgage'
        table_id = '11'
        self.json_result[family] = []
        url = 'http://www.nmgs.gov.cn:7001/aiccips/GSpublicity/GSpublicityList.html?service=pleInfo'
        params = {'entNo': self.entNo, 'regOrg': self.regOrg,'entType':self.ent_type}
        r = self.post_request(url=url, params=params)
        soup = BeautifulSoup(r.text, 'lxml')
        if u'动产抵押登记信息' in r.text:
            table_element = soup.select('div#dongchandiya > table')[0]
            if u'暂无数据' not in table_element.text.strip():
                th_element_list = table_element.select('th')[1:]
                tr_element_list = table_element.select('tr')[2:]
                for tr_element in tr_element_list:
                    td_element_list = tr_element.select('td')
                    if len(td_element_list)<6:
                        break
                    col_nums = len(td_element_list)
                    self.json_result[family].append({})
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n', '')
                        col = dongchandiyadengji_column_dict[col_dec]
                        td = td_element_list[j]
                        val = self.pattern.sub('', td.text)
                        self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family][i], ensure_ascii=False)

    def get_gu_quan_chu_zhi(self):
        """
        查询股权出质信息
        :return:
        """
        if u'股权出质登记信息' not in self.tab_set:
            return
        family = 'Equity_Pledge'
        table_id = '13'
        self.json_result[family] = []
        url = 'http://www.nmgs.gov.cn:7001/aiccips/GSpublicity/GSpublicityList.html?service=curStoPleInfo'
        params = {'entNo': self.entNo, 'regOrg': self.regOrg,'entType':self.ent_type}
        r = self.post_request(url=url, params=params)
        if u'股权出质登记信息' in r.text:
            soup = BeautifulSoup(r.text, 'lxml')
            table_element = soup.select('div#guquanchuzhi > div > table')[0]
            if u'暂无数据' not in table_element.text.strip():
                th_element_list = table_element.select('th')[1:]
                tr_element_list = table_element.select('tr')[2:]
                for tr_element in tr_element_list:
                    td_element_list = tr_element.select('td')
                    col_nums = len(td_element_list)
                    self.json_result[family].append({})
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n', '')
                        col = guquanchuzhidengji_column_dict[col_dec]
                        td = td_element_list[j]
                        val = self.pattern.sub('', td.text)
                        self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family][i], ensure_ascii=False)

    def get_xing_zheng_chu_fa(self):
        """
        查询行政处罚信息
        :return:
        """
        if u'行政处罚信息' not in self.tab_set:
            return
        family = 'Administrative_Penalty'
        table_id = '13'
        self.json_result[family] = []
        url = 'http://www.nmgs.gov.cn:7001/aiccips/GSpublicity/GSpublicityList.html?service=cipPenaltyInfo'
        params = {'entNo': self.entNo, 'regOrg': self.regOrg,'entType':self.ent_type}
        r = self.post_request(url=url, params=params)
        if u'行政处罚信息' in r.text:
            soup = BeautifulSoup(r.text, 'lxml')
            table_element = soup.select('div#xingzhengchufa > table')[0]
            if u'暂无数据' not in table_element.text.strip():
                th_element_list = table_element.select('th')[1:]
                tr_element_list = table_element.select('tr')[2:]
                for tr_element in tr_element_list:
                    td_element_list = tr_element.select('td')
                    col_nums = len(td_element_list)
                    self.json_result[family].append({})
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n', '')
                        col = xingzhengchufa_column_dict[col_dec]
                        td = td_element_list[j]
                        val = self.pattern.sub('', td.text)
                        self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family], ensure_ascii=False)

    def get_jing_ying_yi_chang(self):
        """
        查询经营异常信息
        :return:
        """
        if u'经营异常信息' not in self.tab_set:
            return
        family = 'Business_Abnormal'
        table_id = '14'
        self.json_result[family] = []
        url = 'http://www.nmgs.gov.cn:7001/aiccips/GSpublicity/GSpublicityList.html?service=cipUnuDirInfo'
        params = {'entNo': self.entNo, 'regOrg': self.regOrg,'entType':self.ent_type}
        r = self.post_request(url=url, params=params)
        if u'经营异常信息' in r.text:
            soup = BeautifulSoup(r.text, 'lxml')
            table_element = soup.select('div#yichangminglu > table')[0]
            if u'暂无数据' not in table_element.text.strip():
                th_element_list = table_element.select('th')[1:]
                tr_element_list = table_element.select('tr')[2:]
                for tr_element in tr_element_list:
                    td_element_list = tr_element.select('td')
                    col_nums = len(td_element_list)
                    self.json_result[family].append({})
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n', '')
                        col = jingyingyichang_column_dict[col_dec]
                        td = td_element_list[j]
                        val = self.pattern.sub('', td.text)
                        self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps( self.json_result[family][i], ensure_ascii=False)

    def get_yan_zhong_wei_fa(self):
        """
        查询严重违法信息
        :return:
        """
        if u'严重违法信息' not in self.tab_set:
            return
        family = 'Serious_Violations'
        table_id = '15'
        self.json_result[family] = []
        url = 'http://www.nmgs.gov.cn:7001/aiccips/GSpublicity/GSpublicityList.html?service=cipBlackInfo'
        params = {'entNo': self.entNo, 'regOrg': self.regOrg,'entType': self.ent_type}
        r = self.post_request(url=url, params=params)
        if u'严重违法' in r.text:
            soup = BeautifulSoup(r.text, 'lxml')
            table_element = soup.select('div#heimingdan > table')[0]
            if u'暂无数据' not in table_element.text.strip():
                th_element_list = table_element.select('th')[1:]
                tr_element_list = table_element.select('tr')[2:]
                for tr_element in tr_element_list:
                    td_element_list = tr_element.select('td')
                    col_nums = len(td_element_list)
                    self.json_result[family].append({})
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n', '')
                        col = yanzhongweifa_column_dict[col_dec]
                        td = td_element_list[j]
                        val = self.pattern.sub('', td.text)
                        self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family], ensure_ascii=False)

    def get_chou_cha_jian_cha(self):
        """
        查询抽查检查信息
        :param param_param_service:
        :param table_element:
        :return:
        """
        if u'抽查检查信息' not in self.tab_set:
            return
        family = 'Spot_Check'
        table_id = '16'
        self.json_result[family] = []
        url = 'http://www.nmgs.gov.cn:7001/aiccips/GSpublicity/GSpublicityList.html?service=cipSpotCheInfo'
        params = {'entNo': self.entNo, 'regOrg': self.regOrg,'entType':self.ent_type}
        r = self.post_request(url=url, params=params)
        if u'抽查检查信息' in r.text:
            soup = BeautifulSoup(r.text, 'lxml')
            table_element = soup.select('div#chouchajiancha > table')[0]
            if u'暂无数据' not in table_element.text.strip():
                th_element_list = table_element.select('th')[1:]
                tr_element_list = table_element.select('tr')[2:]
                for tr_element in tr_element_list:
                    td_element_list = tr_element.select('td')
                    col_nums = len(td_element_list)
                    self.json_result[family].append({})
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n', '')
                        col = chouchajiancha_column_dict[col_dec]
                        td = td_element_list[j]
                        val = self.pattern.sub('', td.text)
                        self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family][i], ensure_ascii=False)

if __name__ == '__main__':
    args_dict = get_args()
    args_dict = {'companyName': u'金杰新能源股份有限公司', 'accountId': '123', 'taskId': '456'}
    searcher = NeiMengGuSearcher()
    # searcher.submit_search_request(u'内蒙古大鲜卑酒店集团有限公司')
    searcher.submit_search_request(keyword=args_dict['companyName'], flags=True, account_id=args_dict['accountId'], task_id=args_dict['taskId'])
    searcher.info(json.dumps(searcher.json_result, ensure_ascii=False))