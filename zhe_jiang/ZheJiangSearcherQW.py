# coding=utf-8
import PackageTool
from gs.Searcher import Searcher
from gs.Searcher import get_args
import os
import sys
from bs4 import BeautifulSoup
from TableConfig import *
from gs.KafkaAPI import KafkaAPI
from gs.TimeUtils import get_cur_time
import json
import subprocess
import traceback


class ZheJiangSearcherQW(Searcher):
    load_func_dict = {}

    def __init__(self):
        super(ZheJiangSearcherQW, self).__init__(use_proxy=True)
        self.load_func_dict[u'登记信息'] = self.get_deng_ji
        self.load_func_dict[u'基本信息'] = self.get_ji_ben
        self.load_func_dict[u'股东信息'] = self.get_gu_dong
        self.load_func_dict[u'变更信息'] = self.get_bian_geng
        self.load_func_dict[u'备案信息'] = self.get_bei_an
        self.load_func_dict[u'主要人员信息'] = self.get_zhu_yao_ren_yuan
        self.load_func_dict[u'分支机构信息'] = self.get_fen_zhi_ji_gou
        self.load_func_dict[u'清算信息'] = self.get_qing_suan
        self.load_func_dict[u'投资人信息'] = self.get_tou_zi_ren
        # self.load_func_dict[u'主管部门（出资人）信息'] = self.get_zhu_guan_bu_men     #Modified by Jing
        # self.load_func_dict[u'参加经营的家庭成员姓名'] = self.load_jiatingchengyuan     # Modified by Jing
        # self.load_func_dict[u'合伙人信息'] = self.load_hehuoren     #Modified by Jing
        # self.load_func_dict[u'成员名册'] = self.load_chengyuanmingce     #Modified by Jing
        # self.load_func_dict[u'撤销信息'] = self.load_chexiao     #Modified by Jing
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:45.0) Gecko/20100101 Firefox/45.0",
                        "Host": "gsxt.zjaic.gov.cn",
                        "Accept": "*/*",
                        "Accept-Encoding": "gzip, deflate",
                        "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
                        "Referer": "http://gsxt.zjaic.gov.cn/search/doGetAppSearchResult.do",
                        "Connection": "keep-alive"
                        }
        self.set_config()

    def set_config(self):
        # self.plugin_path = os.path.join(sys.path[0], '../zhe_jiang/ocr/jisuan/zhejiang.bat')
        self.plugin_path = os.path.join(sys.path[0], '../zhe_jiang/ocr/new/zhejiang.bat')
        # self.group = 'Crawler'  # 正式
        # self.kafka = KafkaAPI("GSCrawlerResult")  # 正式
        self.group = 'CrawlerTest'  # 测试
        self.kafka = KafkaAPI("GSCrawlerTest")  # 测试
        self.topic = 'GsSrc33'
        self.province = u'浙江省'
        self.kafka.init_producer()
        self.set_request_timeout(10)
    # def recognize_yzm(self, yzm_path):
    #     image = Image.open(yzm_path)
    #     image.show()
    #     print '请输入验证码:'
    #     yzm = raw_input()
    #     image.close()
    #     return yzm

    def download_yzm(self):
        # print 'lock_id -> %d' % self.lock_id
        image_url = 'http://gsxt.zjaic.gov.cn/common/captcha/doReadKaptcha.do'
        r = self.get_request_qw(image_url)
        # self.update_lock_time()
        yzm_path = self.get_yzm_path().replace('/', '\\')
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
        print cmd
        process = subprocess.Popen(cmd.encode('GBK', 'ignore'), stdout=subprocess.PIPE)
        process_out = process.stdout.read()
        process_out = process_out.strip()
        answer = process_out.split('\r\n')[-1].strip()
        if answer.endswith(yzm_path):
            answer = u''
        print 'answer: ' + answer.decode('gbk', 'ignore')
        return answer.decode('gbk', 'ignore')

    def save_tag_a_to_db(self, tag_a):
        pass

    def get_tag_a_from_db(self, keyword):
        return None

    def get_tag_a_from_page(self, keyword):
        self.reset_proxy_qw(force_change=False)
        url = 'http://gsxt.zjaic.gov.cn/search/doGetAppSearchResult.do'
        for t in range(20):
            yzm = self.get_yzm()
            if len(yzm) == 0:
                print u'非数字、成语验证码'
                continue
            # if not str.isdigit(yzm.encode('utf-8')):
            #     print u'非数字验证码'
            #     continue
            print yzm
            params = {'clickType': '1', 'name': keyword, 'verifyCode': yzm.encode('utf-8')}
            print u'提交验证码...'
            r = self.post_request_qw(url=url, params=params)
            print u'提交成功'
            # print r.text
            if u'验证码输入错误' in r.text:
                continue
            elif u'您搜索的条件无查询结果' in r.text:
                return None
            else:
                search_result_json = {}
                soup = BeautifulSoup(r.text, 'lxml')
                search_result_text = soup.select('html body div div dl dt a')[0].attrs['href']
                if search_result_text != u'':
                    self.cur_mc = soup.select('html body div div dl dt a')[0].text.strip()
                    self.cur_zch = soup.select('html body div div dl dt span')[0].text.strip()
                    search_result_json['entname'] = self.cur_mc
                    search_result_json['regno'] = self.cur_zch
                    search_result_json['corpid'] = search_result_text.split("=")[1]
                    # search_result_json['corpid']=search_result_text[search_result_text.index('corpid=')+len('corpid='):len('search_result_text')]
                    tag_a = json.dumps(search_result_json, ensure_ascii=False)
                    return tag_a

    def get_search_args(self, tag_a, keyword):
        search_result_json = json.loads(tag_a)
        if search_result_json.get('entname', None) == keyword:
            corpid = search_result_json['corpid']
            self.cur_mc = search_result_json['entname'].replace('(', u'（').replace(')', u'）')  # 公司名称括号统一转成全角
            self.cur_zch = search_result_json['regno']
            return [corpid, keyword]
        else:
            return []

    def parse_detail(self, kwargs):
        """
        解析公司详情信息
        :param kwargs:
        :return:
        """
        print u'登记信息'
        self.get_deng_ji(*kwargs)
        print u'备案信息'
        self.get_bei_an(*kwargs)
        print u'动产抵押'
        self.get_dong_chan_di_ya(*kwargs)
        print u'股权出质'
        self.get_gu_quan_chu_zhi(*kwargs)
        print u'行政处罚'
        self.get_xing_zheng_chu_fa(*kwargs)
        print u'经营异常'
        self.get_jing_ying_yi_chang(*kwargs)
        # print u'严重违法'
        # self.get_yan_zhong_wei_fa(*kwargs)
        print u'抽查检查'
        self.get_chou_cha_jian_cha(*kwargs)

    def get_deng_ji(self, param_corpid, param_orgno):
        for i in range(5):
            url = 'http://gsxt.zjaic.gov.cn/appbasicinfo/doReadAppBasicInfo.do'
            params = {'corpid': param_corpid}
            r = self.get_request(url=url, params=params)
            if u'系统警告' in r.text and i < 4:
                continue
            elif u'系统警告' in r.text and i == 4:
                break
            else:
                soup = BeautifulSoup(r.text, 'lxml')
                table_elements = soup.find_all("table")
                for table_element in table_elements:
                    table_name = table_element.find("th").get_text().strip()  # 表格名称
                    if u'股东信息' in table_name:
                        self.get_gu_dong(param_corpid, table_element)
                    elif table_name in self.load_func_dict:
                        self.load_func_dict[table_name](param_corpid, table_element)
                    else:
                        print u'未知表名'

    def get_ji_ben(self, param_corpid, table_element):
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
        for i in range(len(td_list)):
            th = th_list[i]
            td = td_list[i]
            desc = self.pattern.sub('', th.text)
            val = self.pattern.sub('', td.text)
            # print desc,val
            if len(desc) > 0:
                if desc == u'统一社会信用代码/注册号' and len(val) == 18:
                    result_json[0][u'社会信用代码'] = val
                    result_json[0][u'注册号码'] = ''
                if desc == u'统一社会信用代码/注册号' and len(val) != 18:
                    result_json[0][u'社会信用代码'] = ''
                    result_json[0][u'注册号码'] = val
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

    def get_gu_dong(self, param_corpid, table_element):
        """
        查询股东信息
        :param param_corpid:
        :param table_element:
        :return:
        """
        family = 'Shareholder_Info'
        table_id = '04'
        self.json_result[family] = []
        if u'下一页' in table_element.text:
            th_element_list = table_element.select('th')[1:-1]
            tr_element_list = table_element.select('tr')[2:-1]
            pages = self.pattern.sub('', table_element.select('th')[-1].text.strip())
            page_nums = pages[1:pages.index(u'页')]
        else:
            th_element_list = table_element.select('th')[1:]
            tr_element_list = table_element.select('tr')[2:]
            page_nums = 1
        for i in range(int(page_nums)):
            if i > 0:
                url = 'http://gsxt.zjaic.gov.cn/appbasicinfo/doReadAppBasicInfo.do'
                params = {'corpid': param_corpid, 'entInvestorPagination.currentPage': '%s' % (i+1), 'entInvestorPagination.pageSize': '5'}
                r = self.get_request(url = url, params = params)
                soup = BeautifulSoup(r.text, 'lxml')
                table_element = soup.select('table')[1]
                th_element_list = table_element.select('th')[1:-1]
                tr_element_list = table_element.select('tr')[2:-1]
            for tr_element in tr_element_list:
                td_element_list = tr_element.select('td')
                col_nums = len(th_element_list)
                self.json_result[family].append({})
                for j in range(col_nums):
                    col_dec = th_element_list[j].text.strip().replace('\n', '')
                    col = gudong_column_dict[col_dec]
                    td = td_element_list[j]
                    val = td.text.strip()
                    self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
        # print json.dumps(self.json_result[family], ensure_ascii=False)

    def get_tou_zi_ren(self, param_corpid, table_element):
        pass

    def get_bian_geng(self, param_corpid, table_element):
        """
        查询变更信息
        :param param_corpid:
        :param table_element:
        :return:
        """
        family = 'Changed_Announcement'
        table_id = '05'
        self.json_result[family] = []
        if u'下一页' in table_element.text:
            th_element_list = table_element.select('th')[1:-1]
            tr_element_list = table_element.select('tr')[2:-1]
            pages = self.pattern.sub('', table_element.select('th')[-1].text.strip())
            page_nums = pages[1:pages.index(u'页')]
        else:
            th_element_list = table_element.select('th')[1:]
            tr_element_list = table_element.select('tr')[2:]
            page_nums = 1
        for i in range(int(page_nums)):
            if i > 0:
                url = 'http://gsxt.zjaic.gov.cn/appbasicinfo/doReadAppBasicInfo.do'
                params = {'corpid': param_corpid, 'checkAlterPagination.currentPage': '%s' % (i+1), 'checkAlterPagination.pageSize': '5'}
                r = self.get_request(url=url, params=params)
                soup = BeautifulSoup(r.text, 'lxml')
                table_element = soup.select('table')[-1]
                th_element_list = table_element.select('th')[1:-1]
                tr_element_list = table_element.select('tr')[2:-1]
            # print table_element
            for tr_element in tr_element_list:
                td_element_list = tr_element.select('td')
                col_nums = len(th_element_list)
                self.json_result[family].append({})
                for j in range(col_nums):
                    col_dec = th_element_list[j].text.strip().replace('\n', '')
                    col = biangeng_column_dict[col_dec]
                    td = td_element_list[j]
                    val = self.pattern.sub('', td.text)
                    if val.endswith(u'更多'):
                        val = val[val.index(u'更多')+2:val.index(u'收起更多')]
                    self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family][i], ensure_ascii=False)

    def get_bei_an(self, param_corpid, param_orgno):
        for i in range(5):
            url = 'http://gsxt.zjaic.gov.cn/filinginfo/doViewFilingInfo.do'
            params = {'corpid': param_corpid}
            r = self.get_request(url=url, params=params)
            if u'系统警告' in r.text and i < 4:
                continue
            elif u'系统警告' in r.text and i == 4:
                break
            else:
                soup = BeautifulSoup(r.text, 'lxml')
                table_elements = soup.find_all("table")
                for table_element in table_elements:
                    table_name = table_element.find("th").get_text().strip()  # 表格名称
                    if table_name in self.load_func_dict:
                        self.load_func_dict[table_name](param_corpid, table_element)
                    else:
                        print u'未知表名'
                break

    def get_zhu_yao_ren_yuan(self, param_corpid, table_element):
        """
        查询主要人员信息
        :param param_coripid:
        :param table_element:
        :return:
        """
        family = 'KeyPerson_Info'
        table_id = '06'
        self.json_result[family] = []
        if u'下一页' in table_element.text:
            th_element_list = table_element.select('th')[1:]
            tr_element_list = table_element.select('tr')[2:-1]
            pages = self.pattern.sub('', table_element.select('th')[-1].text.strip())
            page_nums = pages[1:pages.index(u'页')]
        else:
            th_element_list = table_element.select('th')[1:]
            tr_element_list = table_element.select('tr')[2:]
            page_nums = 1
        for i in range(int(page_nums)):
            if i > 0:
                url = 'http://gsxt.zjaic.gov.cn/filinginfo/doViewFilingInfo.do'
                params = {'corpid': param_corpid, 'entMemberPagination.currentPage': '%s' % (i+1), 'entMemberPagination.pageSize': '10'}
                r = self.get_request(url=url, params=params)
                soup = BeautifulSoup(r.text, 'lxml')
                table_element = soup.select('table')[0]
                th_element_list = table_element.select('th')[1:]
                tr_element_list = table_element.select('tr')[2:-1]
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
        # print json.dumps(self.json_result[family], ensure_ascii=False)

    def get_fen_zhi_ji_gou(self, param_corpid, table_element):
        """
        查询分支机构信息
        :param param_corpid:
        :param table_element:
        :return:
        """
        family = 'Branches'
        table_id = '08'
        self.json_result[family] = []
        th_element_list = table_element.select('th')[1:]
        tr_element_list = table_element.select('tr')[2:]
        for tr_element in tr_element_list:
            td_element_list = tr_element.select('td')
            col_nums = len(th_element_list)
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
            # print json.dumps(self.json_result[family], ensure_ascii=False)

    def get_qing_suan(self, param_corpid, table_element):
        """
        查询清算信息
        :param param_corpid:
        :param table_element:
        :return:
        """
        family = 'liquidation_Information'
        table_id = '09'
        self.json_result[family] = []
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
        print cheng_yuan,fu_ze_ren
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

    def get_dong_chan_di_ya(self, param_corpid, table_element):
        """
        查询动产抵押信息
        :param param_corpid:
        :param table_element:
        :return:
        """
        family = 'Chattel_Mortgage'
        table_id = '11'
        self.json_result[family] = []
        url = 'http://gsxt.zjaic.gov.cn/dcdyapplyinfo/doReadDcdyApplyinfoList.do'
        params = {'corpid': param_corpid}
        r = self.get_request(url=url, params=params)
        if u'系统警告' not in r.text:
            soup = BeautifulSoup(r.text, 'lxml')
            table_element = soup.find("table")
            if u'此企业暂无动产抵押登记信息' not in table_element.text:
                th_element_list = table_element.select('th')[1:]
                tr_element_list = table_element.select('tr')[2:]
                for tr_element in tr_element_list:
                    td_element_list = tr_element.select('td')
                    col_nums = len(th_element_list)
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
            # print json.dumps(self.json_result[family], ensure_ascii=False)

    def get_gu_quan_chu_zhi(self, param_corpid, table_element):
        """
        查询动产抵押信息
        :param param_corpid:
        :param table_element:
        :return:
        """
        family = 'Equity_Pledge'
        table_id = '13'
        self.json_result[family] = []
        url = 'http://gsxt.zjaic.gov.cn/equityall/doReadEquityAllListFromPV.do'
        params = {'corpid': param_corpid}
        r = self.get_request(url=url, params=params)
        if u'系统警告' not in r.text:
            soup = BeautifulSoup(r.text, 'lxml')
            table_element = soup.find("table")
            if u'此企业暂无股权出质信息' not in table_element.text:
                th_element_list = table_element.select('th')[1:]
                tr_element_list = table_element.select('tr')[2:]
                for tr_element in tr_element_list:
                    td_element_list = tr_element.select('td')
                    col_nums = len(th_element_list)
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
            # print json.dumps(self.json_result[family], ensure_ascii=False)

    def get_xing_zheng_chu_fa(self, param_corpid, table_element):
        """
        查询行政处罚信息
        :param param_corpid:
        :param table_element:
        :return:
        """
        family = 'Administrative_Penalty'
        table_id = '13'
        self.json_result[family] = []
        url = 'http://gsxt.zjaic.gov.cn/punishment/doViewPunishmentFromPV.do'
        params = {'corpid': param_corpid}
        r = self.get_request(url=url, params=params)
        if u'系统警告' not in r.text:
            soup = BeautifulSoup(r.text, 'lxml')
            table_element = soup.find("table")
            if u'此企业暂无行政处罚信息' not in table_element.text:
                th_element_list = table_element.select('th')[1:]
                tr_element_list = table_element.select('tr')[2:]
                for tr_element in tr_element_list:
                    td_element_list = tr_element.select('td')
                    col_nums = len(th_element_list)
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
            # print json.dumps(self.json_result[family][i], ensure_ascii=False)

    def get_jing_ying_yi_chang(self, param_corpid, table_element):
        """
        查询经营异常信息
        :param param_corpid:
        :param table_element:
        :return:
        """
        family = 'Business_Abnormal'
        table_id = '14'
        self.json_result[family] = []
        url = 'http://gsxt.zjaic.gov.cn/catalogapply/doReadCatalogApplyList.do'
        params = {'corpid': param_corpid}
        r = self.get_request(url=url, params=params)
        if u'系统警告' not in r.text:
            soup = BeautifulSoup(r.text, 'lxml')
            table_element = soup.find("table")
            if u'此企业暂无经营异常信息' not in table_element.text:
                th_element_list = table_element.select('th')[1:]
                tr_element_list = table_element.select('tr')[2:]
                for tr_element in tr_element_list:
                    td_element_list = tr_element.select('td')
                    col_nums = len(th_element_list)
                    self.json_result[family].append({})
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n', '')
                        col =jingyingyichang_column_dict[col_dec]
                        td = td_element_list[j]
                        val = self.pattern.sub('', td.text)
                        self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps( self.json_result[family], ensure_ascii=False)

    def get_yan_zhong_wei_fa(self, param_corpid, table_element):
        """
        查询严重违法信息
        :param param_corpid:
        :param table_element:
        :return:
        """
        family = 'Serious_Violations'
        table_id = '15'
        self.json_result[family] = []
        url = 'http://gsxt.zjaic.gov.cn/blacklist/doViewBlackListInfo.do'
        params = {'corpid': param_corpid}
        r = self.get_request(url=url, params=params)
        if u'系统警告' not in r.text:
            soup = BeautifulSoup(r.text, 'lxml')
            table_element = soup.find("table")
            if u'此企业暂无严重违法信息' not in table_element.text:
                th_element_list = table_element.select('th')[1:]
                tr_element_list = table_element.select('tr')[2:]
                for tr_element in tr_element_list:
                    td_element_list = tr_element.select('td')
                    col_nums = len(th_element_list)
                    self.json_result[family].append({})
                    for j in range(col_nums):
                        col_dec = th_element_list[j].text.strip().replace('\n', '')
                        col =yanzhongweifa_column_dict[col_dec]
                        td = td_element_list[j]
                        val = self.pattern.sub('', td.text)
                        self.json_result[family][-1][col] = val
        for i in range(len(self.json_result[family])):
            self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
            self.json_result[family][i][family + ':registrationno'] = self.cur_zch
            self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
            self.json_result[family][i][family + ':id'] = i+1
            # print json.dumps(self.json_result[family], ensure_ascii=False)

    def get_chou_cha_jian_cha(self, param_corpid, table_element):
        """
        查询抽查检查信息
        :param param_corpid:
        :param table_element:
        :return:
        """
        family = 'Spot_Check'
        table_id = '16'
        self.json_result[family] = []
        url = 'http://gsxt.zjaic.gov.cn/pubcheckresult/doViewPubCheckResultList.do'
        params = {'corpid': param_corpid}
        r = self.get_request(url=url, params=params)
        if u'系统警告' not in r.text:
            soup = BeautifulSoup(r.text, 'lxml')
            table_element = soup.find("table")
            if u'此企业无抽查检查信息' not in table_element.text:
                th_element_list = table_element.select('th')[1:]
                tr_element_list = table_element.select('tr')[2:]
                for tr_element in tr_element_list:
                    td_element_list = tr_element.select('td')
                    col_nums = len(th_element_list)
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
            # print json.dumps(self.json_result[family], ensure_ascii=False)

if __name__ == '__main__':
    args_dict = get_args()
    args_dict = {'companyName': u'杭州绿城东友房产开发有限公司', 'accountId': '123', 'taskId': '456'}
    searcher = ZheJiangSearcherQW()
    # searcher.recognize_yzm(r"C:\Users\kai.li\pycharmprojects\GsClawlerV2\temp\935597444795.jpg")
    # for i in range(10):
    #     print searcher.download_yzm()
    # searcher.submit_search_request(keyword=args_dict['companyName'], account_id=args_dict['accountId'], task_id=args_dict['taskId'])