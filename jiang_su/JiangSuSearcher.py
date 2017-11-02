# coding=utf-8

import PackageTool
import sys
from gs.KafkaAPI import KafkaAPI
import os
import uuid
import subprocess
from gs.Searcher import Searcher
from gs.Searcher import get_args
import json
from gs.TimeUtils import get_cur_time_jiangsu
from gs.TimeUtils import get_cur_time
from lxml import html

reload(sys)
sys.setdefaultencoding('utf8')

'''developer  liuwenhai'''

class JiangSuSearcher(Searcher):

    def __init__(self):
        super(JiangSuSearcher, self).__init__(True)
        self.error_judge = False  # 判断网站是否出错，False正常，True错误
        self.tag_a = ''
        self.id = ''
        self.org = ''
        self.seqId = ''
        self.reg_no = ''
        self.set_config()
        self.headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:47.0) Gecko/20100101 Firefox/47.0",
                        "Host": "www.jsgsj.gov.cn:58888",
                        "Accept": "*/*",
                        "Accept-Encoding": "gzip, deflate",
                        "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
                        "Connection": "keep-alive",
                        }
        self.log_name = 'jiang_su_'+str(uuid.uuid1())
        self.lock_ip = ''

    def set_config(self):
        self.plugin_path = os.path.join(sys.path[0],  r'..\jiang_su\ocr\jiangsuocr.exe')
        self.group = 'Crawler'  # 正式
        self.kafka = KafkaAPI("GSCrawlerResult")  # 正式
        # self.group = 'CrawlerTest'  # 测试
        # self.kafka = KafkaAPI("GSCrawlerTest")  # 测试
        self.topic = 'GsSrc32'
        self.province = u'江苏省'
        self.kafka.init_producer()

    def get_tag_a_from_page(self, keyword, flags=True):
        headers = {
            "Host": 'www.jsgsj.gov.cn:58888',
            "Referer": "http://www.jsgsj.gov.cn:58888/province/jiangsu.jsp",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0",
            # 'Proxy-Authorization': self.proxy_config.get_auth_header()
        }
        for t in range(10):
            yzm = self.get_yzm()
            params = {'name': keyword, 'verifyCode': yzm}
            url = 'http://www.jsgsj.gov.cn:58888/province/infoQueryServlet.json?checkCode=true'
            r = self.post_request(url, data=params, headers=headers)
            result_dict = json.loads(r.text)
            if result_dict.get('bean', '').get('name', ''):
                self.info(u'验证成功')
                coded_name = result_dict['bean']['name']
                break
        for j in range(10):
            try:
                params = {'name': coded_name, 'pageNo': 1, "pageSize": 50, "searchType": "qyxx"}
                url = 'http://www.jsgsj.gov.cn:58888/province/infoQueryServlet.json?queryCinfo=true'  # 此处验证ip
                r = self.post_request(url, data=params, headers=headers)
                result_dict = json.loads(r.text)
                result_list = result_dict['items']
                break
            except Exception, e:
                if j == 9:
                    raise  e
        for result in result_list:
            name = result['CORP_NAME'].replace('(', u'（').replace(')', u'）')
            if name != keyword:
                self.save_mc_to_db(name)
        for result in result_list:
            name = result['CORP_NAME'].replace('(', u'（').replace(')', u'）')
            if flags:
                if name == keyword:
                    self.id = result["ID"]
                    self.org = result["ORG"]
                    self.seqId = result["SEQ_ID"]
                    self.tag_a = self.id+";"+self.org+";"+self.seqId
                    return self.tag_a
            else:
                self.id = result["ID"]
                self.org = result["ORG"]
                self.seqId = result["SEQ_ID"]
                self.tag_a = self.id+";"+self.org+";"+self.seqId
                return self.tag_a

    def recognize_yzm(self, yzm_path):
        """
        识别验证码
        :param yzm_path: 验证码保存路径
        :return: 验证码识别结果
        """
        cmd = self.plugin_path + " " + yzm_path
        self.info(cmd)
        process = subprocess.Popen(cmd.encode('GBK', 'ignore'), stdout=subprocess.PIPE)
        process_out = process.stdout.read()
        # self.info('process_out', process_out
        answer = process_out.split('\r\n')[0].strip()
        # self.info('answer: ' + answer
        return answer.decode('gbk', 'ignore')

    def get_search_args(self, tag_a, keyword):
        self.info(u'解析查询参数')
        # print tag_a
        self.cur_mc = keyword
        self.id = tag_a.split(";")[0]
        self.org = tag_a.split(";")[1]
        self.seqId = tag_a.split(";")[2]
        return 1

    def download_yzm(self):
        time_url = get_cur_time_jiangsu()
        image_url = 'http://www.jsgsj.gov.cn:58888/province/rand_img.jsp?type=7&temp=' + time_url[:-6].replace(" ", "%20")
        r = self.get_request(image_url)
        yzm_path = self.get_yzm_path()
        with open(yzm_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    f.flush()
            f.close()
        return yzm_path

    def parse_detail(self):
        """
        解析公司详情信息
        :param kwargs:
        :return:
        """
        self.get_ji_ben()
        self.get_gu_dong()
        self.get_bian_geng()
        self.get_zhu_yao_ren_yuan()
        self.get_fen_zhi_ji_gou()
        self.get_qing_suan()
        self.get_dong_chan_di_ya()
        self.get_gu_quan_chu_zhi()
        self.get_xing_zheng_chu_fa()
        self.get_jing_ying_yi_chang()
        self.get_yan_zhong_wei_fa()
        self.get_chou_cha_jian_cha()
        self.get_si_fa_xie_zhu()  # 苏州融创科技担保投资有限公司

    def get_ji_ben(self):
        """
        查询基本信息
        :return: 基本信息结果
        """
        family = 'Registered_Info'
        table_id = '01'
        result_values = dict()
        url = 'http://www.jsgsj.gov.cn:58888/ecipplatform/publicInfoQueryServlet.json?pageView=true'  #http://www.jsgsj.gov.cn:58888/ecipplatform/inner_ci/ci_queryCorpInfor_gsRelease.jsp
        params = {'id': self.id, 'org': self.org, 'seqId': self.seqId}
        r = self.get_request(url=url, params=params)
        self.info(u'基本信息')
        # print r.text
        ji_ben_xinxi = json.loads(r.text)
        if not ji_ben_xinxi:
            self.error_judge = True
            self.info(r.text)
            raise ValueError('!!!!!!!!!!!!website is wrong!!!!!!!!!!!!!')
        self.cur_zch = ji_ben_xinxi.get('REG_NO', '')
        if self.cur_zch:
            if len(self.cur_zch) == 18:
                result_values[family + ':tyshxy_code'] = self.cur_zch
            else:
                result_values[family + ':zch'] = self.cur_zch
        result_values[family + ':registrationno'] = self.cur_zch
        result_values[family + ':enterprisename'] = ji_ben_xinxi.get('CORP_NAME', '')
        result_values[family + ':enterprisetype'] = ji_ben_xinxi.get('ZJ_ECON_KIND', '')
        result_values[family + ':residenceaddress'] = ji_ben_xinxi.get('ADDR', '')
        result_values[family + ':registeredcapital'] = ji_ben_xinxi.get('REG_CAPI', '')
        result_values[family + ':legalrepresentative'] = ji_ben_xinxi.get('OPER_MAN_NAME', '')
        result_values[family + ':validityfrom'] = ji_ben_xinxi.get('FARE_TERM_START', '')
        result_values[family + ':validityto'] = ji_ben_xinxi.get('FARE_TERM_END', '')
        result_values[family + ':businessscope'] = ji_ben_xinxi.get('FARE_SCOPE', '')
        result_values[family + ':registrationinstitution'] = ji_ben_xinxi.get('BELONG_ORG', '')
        result_values[family + ':registrationstatus'] = ji_ben_xinxi.get('CORP_STATUS', '')
        result_values[family + ':establishmentdate'] = ji_ben_xinxi.get('START_DATE', '')
        result_values[family + ':approvaldate'] = ji_ben_xinxi.get('CHECK_DATE', '')

        result_values['rowkey'] = '%s_%s_%s_' % (self.cur_mc, table_id, self.cur_zch)
        result_values[family + ':province'] = u'江苏省'
        result_values[family + ':lastupdatetime'] = get_cur_time()
        self.json_result["Registered_Info"] = [result_values]

    def get_gu_dong(self):
        """
        查询股东信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Shareholder_Info'
        table_id = '04'
        result_list = []
        j = 1
        url = 'http://www.jsgsj.gov.cn:58888/ecipplatform/publicInfoQueryServlet.json?queryGdcz=true'
        params = {'id': self.id, 'org': self.org, 'seqId': self.seqId, 'curPage': 1, 'pageSize': 1000}
        r = self.post_request(url, data=params)
        self.info(u'股东信息')
        result_values = dict()
        investmentinfo = json.loads(r.text)["data"]
        for invest_dict in investmentinfo:
            result_values[family + ':shareholder_type'] = invest_dict.get('STOCK_TYPE', '')
            result_values[family + ':shareholder_name'] = invest_dict.get('STOCK_NAME', '')
            result_values[family + ':shareholder_certificationtype'] = invest_dict.get('IDENT_TYPE_NAME', '')
            result_values[family + ':shareholder_certificationno'] = invest_dict.get('IDENT_NO', '')
            invest_detail = self.get_investor_detail(invest_dict)
            result_values.update(invest_detail)
            result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
            result_values[family + ':registrationno'] = self.cur_zch
            result_values[family + ':enterprisename'] = self.cur_mc
            result_values[family + ':id'] = j
            result_list.append(result_values)
            result_values = {}
            j += 1
        self.json_result["Shareholder_Info"] = result_list

    def get_investor_detail(self, inv_dict):
        family = 'Shareholder_Info'
        params = {
            'seqId': inv_dict["SEQ_ID"],
            'org': inv_dict["ORG"],
            'id': inv_dict["ID"],
        }
        url = "http://www.jsgsj.gov.cn:58888/ecipplatform/publicInfoQueryServlet.json?queryGdczGdxx=true"
        r = self.get_request(url, params=params)
        detail = json.loads(r.text)
        detail_values = dict()
        detail_values[family + ':subscripted_capital'] = detail.get("SHOULD_CAPI", '') # 认缴额
        detail_values[family + ':actualpaid_capital'] = detail.get("REAL_CAPI", '') # 实缴额

        params = {"curPage": 1, "id": inv_dict["ID"], 'org': inv_dict["ORG"], "type": 'rj'}
        url = "http://www.jsgsj.gov.cn:58888/ecipplatform/publicInfoQueryServlet.json?queryGdczGdxx=true"
        r = self.post_request(url, data=params)
        detail_1 = json.loads(r.text)
        if detail_1["data"]:
            detail_values[family + ':subscripted_time'] = detail_1["data"][0].get("SHOULD_CAPI_DATE", '')
            detail_values[family + ':subscripted_method'] = detail_1["data"][0].get("INVEST_TYPE_NAME", '')

        params = {"curPage": 1, "id": inv_dict["ID"], 'org': inv_dict["ORG"], "type": 'sj'}
        url = "http://www.jsgsj.gov.cn:58888/ecipplatform/publicInfoQueryServlet.json?queryGdczGdxx=true"
        r = self.post_request(url, data=params)
        detail_2 = json.loads(r.text)
        if detail_2['data']:
            detail_values[family + ':actualpaid_time'] = detail_2["data"][0].get("REAL_CAPI_DATE", '')
            detail_values[family + ':actualpaid_method'] = detail_2["data"][0].get("INVEST_TYPE_NAME", '')

        return detail_values

    def get_bian_geng(self):
        """
        查询变更信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Changed_Announcement'
        table_id = '05'
        result_list = []
        j = 1
        # self.json_result[family] = []
        url = 'http://www.jsgsj.gov.cn:58888/ecipplatform/publicInfoQueryServlet.json?queryBgxx=true'
        params = {'id': self.id, 'org': self.org, 'seqId': self.seqId, 'curPage': 1, 'pageSize': 1000}
        r = self.post_request(url, data=params)
        self.info(u'变更信息')
        result_values = dict()
        change_info = json.loads(r.text)["data"]
        for change_dict in change_info:
            result_values[family + ':changedannouncement_events'] = change_dict.get('CHANGE_ITEM_NAME', '')
            result_values[family + ':changedannouncement_before'] = change_dict.get('OLD_CONTENT', ' ')
            result_values[family + ':changedannouncement_after'] = change_dict.get('NEW_CONTENT', ' ')
            result_values[family + ':changedannouncement_date'] = change_dict.get('CHANGE_DATE', '')
            result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
            result_values[family + ':registrationno'] = self.cur_zch
            result_values[family + ':enterprisename'] = self.cur_mc
            result_values[family + ':id'] = j
            result_list.append(result_values)
            result_values = {}
            j += 1
        self.json_result["Changed_Announcement"] = result_list

    def get_zhu_yao_ren_yuan(self):
        """
        查询主要人员信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'KeyPerson_Info'
        table_id = '06'
        result_list = []
        j = 1
        # self.json_result[family] = []
        url = 'http://www.jsgsj.gov.cn:58888/ecipplatform/publicInfoQueryServlet.json?queryZyry=true'
        params = {'id': self.id, 'org': self.org, 'seqId': self.seqId}
        r = self.get_request(url, params=params)
        self.info(u'主要人员信息')
        result_values = dict()
        keyperson_info = json.loads(r.text)
        for keyperson_dict in keyperson_info:
            result_values[family + ':keyperson_name'] = keyperson_dict['PERSON_NAME']
            result_values[family + ':keyperson_position'] = keyperson_dict['POSITION_NAME']
            result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
            result_values[family + ':registrationno'] = self.cur_zch
            result_values[family + ':enterprisename'] = self.cur_mc
            result_values[family + ':id'] = j
            result_list.append(result_values)
            result_values = {}
            j += 1
        self.json_result["KeyPerson_Info"] = result_list

    def get_fen_zhi_ji_gou(self):
        """
        查询分支机构信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Branches'
        table_id = '08'
        result_list = []
        j = 1
        # self.json_result[family] = []
        url = 'http://www.jsgsj.gov.cn:58888/ecipplatform/publicInfoQueryServlet.json?queryFzjg=true'
        params = {'id': self.id, 'org': self.org, 'seqId': self.seqId}
        r = self.get_request(url, params=params)
        self.info(u'分支机构')
        result_values = dict()
        branch_info = json.loads(r.text)
        for branch_dict in branch_info:
            result_values[family + ':branch_registrationname'] = branch_dict.get('DIST_NAME', '')
            result_values[family + ':branch_registrationinstitution'] = branch_dict.get('DIST_BELONG_ORG', '')
            result_values[family + ':branch_registrationno'] = branch_dict.get('DIST_REG_NO', '')
            result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
            result_values[family + ':registrationno'] = self.cur_zch
            result_values[family + ':enterprisename'] = self.cur_mc
            result_values[family + ':id'] = j
            result_list.append(result_values)
            result_values = {}
            j += 1
        self.json_result["Branches"] = result_list

    def get_qing_suan(self):
        pass

    def get_dong_chan_di_ya(self):
        """
        查询动产抵押信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Chattel_Mortgage'
        table_id = '11'
        result_list = []
        j = 1
        # self.json_result[family] = []
        url = 'http://www.jsgsj.gov.cn:58888/ecipplatform/publicInfoQueryServlet.json?queryDcdy=true'
        params = {'id': self.id, 'org': self.org, 'seqId': self.seqId, 'curPage': 1, 'pageSize': 1000}
        r = self.post_request(url, data=params)
        self.info(u'动产抵押信息')
        result_values = dict()
        mortgage_info = json.loads(r.text)["data"]
        for mortgage_dict in mortgage_info:
            result_values[family + ':chattelmortgage_registrationno'] = mortgage_dict.get('GUARANTY_REG_NO', '')
            result_values[family + ':chattelmortgage_registrationdate'] = mortgage_dict.get('START_DATE', '')
            result_values[family + ':chattelmortgage_registrationinstitution'] = mortgage_dict.get('CREATE_ORG', '')
            result_values[family + ':chattelmortgage_guaranteedamount'] = mortgage_dict.get('ASSURE_CAPI', '')
            result_values[family + ':chattelmortgage_status'] = mortgage_dict.get('STATUS', '')
            result_values[family + ':priclaseckind'] = mortgage_dict.get('ASSURE_KIND', '')  # 被担保主债权种类
            # result_values[family + ':priclaseckind'] = mortgage_dict.get('ASSURE_KIND', '')  # 被担保主债权种类
            mortgage_params = dict()
            mortgage_params['id'] = mortgage_dict['ID']
            mortgage_params['org'] = mortgage_dict['ORG']
            mortgage_params['seqId'] = mortgage_dict['SEQ_ID']
            diya_detail = self.get_diya_detail(mortgage_params, mortgage_dict.get('GUARANTY_REG_NO', ''),mortgage_dict.get('START_DATE', ''))
            result_values.update(diya_detail)

            result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
            result_values[family + ':registrationno'] = self.cur_zch
            result_values[family + ':enterprisename'] = self.cur_mc
            result_values[family + ':id'] = j
            result_list.append(result_values)
            result_values = {}
            j += 1
        self.json_result["Chattel_Mortgage"] = result_list
        # self.info(json.dumps(result_json_2, ensure_ascii=False)

    def get_diya_detail(self, mortgage_params, mot_no, mot_date):
        values = dict()
        if not mot_date: mot_date = ''
        mot_date = mot_date.replace(u'年', '-').replace(u'月', '-').replace(u'日', '')

        """被担保债券概况"""
        family = 'bdbzqgk'
        bdbzqgk = list()
        bdbzqgk_table_id = '56'
        r_1 = self.post_request('http://www.jsgsj.gov.cn:58888/ecipplatform/publicInfoQueryServlet.json?queryDcdyDetail=true', data=mortgage_params)
        result = r_1.json()
        bdbzqgk_dict = dict()
        bdbzqgk_dict[family + ':dbzq_fw'] = result[0]['ASSURE_SCOPE']
        bdbzqgk_dict[family + ':dbzq_zl'] = result[0]['ASSURE_KIND']
        bdbzqgk_dict[family + ':dbzq_qx'] = result[0]['ASSURE_START_DATE']
        bdbzqgk_dict[family + ':dbzq_bz'] = result[0]['REMARK']
        bdbzqgk_dict[family + ':dbzq_sl'] = result[0]['ASSURE_CAPI']
        bdbzqgk_dict['rowkey'] = '%s_%s_%s_%s' % (self.cur_mc, mot_no,mot_date, bdbzqgk_table_id)
        bdbzqgk_dict[family + ':registrationno'] = self.cur_zch
        bdbzqgk_dict[family + ':enterprisename'] = self.cur_mc
        bdbzqgk.append(bdbzqgk_dict)
        values['Chattel_Mortgage:bdbzqgk'] = bdbzqgk # 被担保债券概况

        """动产抵押登记信息"""
        dcdydj = list()
        dcdydj_table_id = '63'
        family = 'dcdydj'
        dcdydj_dict = dict()
        dcdydj_dict[family + ':dcdy_djbh'] = result[0]['GUARANTY_REG_NO']
        if not result[0]['START_DATE']: result[0]['START_DATE'] = ''
        dcdydj_dict[family + ':dcdy_djrq'] = result[0]['START_DATE'].replace(u'年', '-').replace(u'月', '-').replace(u'日', '')
        dcdydj_dict[family + ':dcdy_djjg'] = result[0]['CREATE_ORG']
        dcdydj_dict['rowkey'] = '%s_%s_%s_%s' % (self.cur_mc, mot_no,mot_date, dcdydj_table_id)
        dcdydj_dict[family + ':registrationno'] = self.cur_zch
        dcdydj_dict[family + ':enterprisename'] = self.cur_mc
        dcdydj.append(dcdydj_dict)
        values['Chattel_Mortgage:dcdydj'] = dcdydj # 动产抵押登记信息

        """抵押权人概况"""
        r_2 = self.post_request('http://www.jsgsj.gov.cn:58888/ecipplatform/publicInfoQueryServlet.json?queryDcdyDyqrgk=true', data=mortgage_params)
        result = r_2.json()['data']
        family = 'dyqrgk'
        dyqrgk = list()
        dyqrgk_table_id = '55' # 抵押权人概况表格
        k = 1
        for dyqrgk_dict in result:
            dyqrgk_values = dict()
            dyqrgk_values[family + ':dyqr_mc'] = dyqrgk_dict.get('AU_NAME', '')
            dyqrgk_values[family + ':dyqr_zzlx'] = dyqrgk_dict.get('AU_CER_TYPE', '')
            dyqrgk_values[family + ':dyqr_zzhm'] = dyqrgk_dict.get('AU_CER_NO', '')
            dyqrgk_values['rowkey'] = '%s_%s_%s_%s_%d' % (self.cur_mc, mot_no,mot_date, dyqrgk_table_id, k)
            dyqrgk_values[family + ':registrationno'] = self.cur_zch
            dyqrgk_values[family + ':enterprisename'] = self.cur_mc
            dyqrgk_values[family + ':id'] = k
            dyqrgk.append(dyqrgk_values)
            k += 1
        values['Chattel_Mortgage:dyqrgk'] = dyqrgk # 抵押权人概况

        """抵押物概况"""
        family = 'dywgk'
        dywgk = list()
        dywgk_table_id = '57'
        r_2 = self.post_request('http://www.jsgsj.gov.cn:58888/ecipplatform/publicInfoQueryServlet.json?queryDcdyDywgk=true', data=mortgage_params)
        result = r_2.json()['data']
        k = 1
        for dyqrgk_dict in result:
            dyqrgk_values = dict()
            dyqrgk_values[family + ':dyw_mc'] = dyqrgk_dict.get('NAME', '')
            dyqrgk_values[family + ':dyw_gs'] = dyqrgk_dict.get('BELONG_KIND', '')
            dyqrgk_values[family + ':dyw_xq'] = dyqrgk_dict.get('PA_DETAIL', '')
            dyqrgk_values[family + ':dyw_bz'] = dyqrgk_dict.get('REMARK', '')
            dyqrgk_values['rowkey'] = '%s_%s_%s_%s_%d' % (self.cur_mc, mot_no,mot_date, dywgk_table_id, k)
            dyqrgk_values[family + ':registrationno'] = self.cur_zch
            dyqrgk_values[family + ':enterprisename'] = self.cur_mc
            dyqrgk_values[family + ':id'] = k
            dywgk.append(dyqrgk_values)
            k += 1
        values[family + ':dywgk'] = dywgk # 抵押物概况
        return values

    def get_gu_quan_chu_zhi(self):  # finished
        """
        查询股权出置信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Equity_Pledge'
        table_id = '12'
        result_list = []
        j = 1
        url = 'http://www.jsgsj.gov.cn:58888/ecipplatform/publicInfoQueryServlet.json?queryGqcz=true'
        params = {'id': self.id, 'org': self.org, 'seqId': self.seqId, 'curPage': 1, 'pageSize': 1000}
        r = self.post_request(url, data=params)
        self.info(u'股权出质')
        result_values = dict()
        pledge_info = json.loads(r.text)["data"]
        for pledge_dict in pledge_info:
            pledge_text = pledge_dict.get('D1', '')
            tree = html.fromstring(pledge_text)
            td_list = tree.xpath(".//td")
            result_values[family + ':equitypledge_registrationno'] = td_list[1].text
            result_values[family + ':equitypledge_pledgor'] = td_list[2].text
            result_values[family + ':equitypledge_pledgorid'] = td_list[3].text
            result_values[family + ':equitypledge_amount'] = td_list[4].text
            result_values[family + ':equitypledge_pawnee'] = td_list[5].text
            result_values[family + ':equitypledge_pawneeid'] = td_list[6].text
            result_values[family + ':equitypledge_registrationdate'] = td_list[7].text.replace(u'年', '-').replace(u'月', '-').replace(u'日', '')
            result_values[family + ':equitypledge_status'] = td_list[8].text
            result_values[family + ':equitypledge_announcedate'] = td_list[9].text.replace(u'年', '-').replace(u'月', '-').replace(u'日', '')
            if pledge_dict.get('CHANGESITUATION', '') == u'详情':
                pledge_params = dict()
                pledge_params['id'] = pledge_dict['ID']
                pledge_params['org'] = pledge_dict['ORG']
                pledge_params['seqId'] = pledge_dict['SEQ_ID']
                pledge_detail = self.get_pledge_detail(pledge_params,td_list[1].text,td_list[7].text)
                result_values.update(pledge_detail)
            # result_values[family + ':equitypledge_pawnee'] = pledge_dict.get('C5', '')

            result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
            result_values[family + ':registrationno'] = self.cur_zch
            result_values[family + ':enterprisename'] = self.cur_mc
            result_values[family + ':id'] = j
            result_list.append(result_values)
            result_values = {}
            j += 1
        self.json_result["Equity_Pledge"] = result_list
        # print result_list

    def get_pledge_detail(self, pledge_params, equity_no, equity_date):
        equity_date = equity_date.replace(u'年', '-').replace(u'月', '-').replace(u'日', '')

        family = 'gqczzx'
        table_id = '60'
        result_values = dict()
        pledge_list = list()
        values = dict()

        r = self.post_request('http://www.jsgsj.gov.cn:58888/ecipplatform/publicInfoQueryServlet.json?queryGqczDetail=true', data=pledge_params)
        # print r.text
        result = json.loads(r.text)
        values[family + ':gqcz_zxrq'] = result.get('CREATE_DATE', '').replace(u'年', '-').replace(u'月', '-').replace(u'日', '')  #
        values[family + ':gqcz_zxyy'] = result.get('WRITEOFF_REASON', '') #
        values['rowkey'] = '%s_%s_%s_%s' % (self.cur_mc,equity_no,equity_date, table_id)
        values[family + ':registrationno'] = self.cur_zch
        values[family + ':enterprisename'] = self.cur_mc
        pledge_list.append(values)
        result_values['Equity_Pledge:gqczzx'] = pledge_list
        return result_values

    def get_xing_zheng_chu_fa(self):
        """
        查询行政处罚信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Administrative_Penalty'
        table_id = '13'
        result_list = []
        j = 1
        # self.json_result[family] = []
        url = 'http://www.jsgsj.gov.cn:58888/ecipplatform/publicInfoQueryServlet.json?queryXzcf=true'
        params = {'id': self.id, 'org': self.org, 'seqId': self.seqId, 'curPage': 1, 'pageSize': 1000}
        r = self.post_request(url, data=params)
        self.info(u'行政处罚')
        result_values = dict()
        penalty_info = json.loads(r.text)["data"]
        for penalty_dict in penalty_info:
            result_values[family + ':penalty_code'] = penalty_dict.get('PEN_DEC_NO', '')
            result_values[family + ':penalty_illegaltype'] = penalty_dict.get('ILLEG_ACT_TYPE', '')
            result_values[family + ':penalty_decisioncontent'] = penalty_dict.get('PEN_TYPE', '')
            result_values[family + ':penalty_decisioninsititution'] = penalty_dict.get('PUNISH_ORG_NAME', '')
            result_values[family + ':penalty_decisiondate'] = penalty_dict.get('PUNISH_DATE', '')
            result_values[family + ':penalty_publicationdate'] = penalty_dict.get('CREATE_DATE', '')

            result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
            result_values[family + ':registrationno'] = self.cur_zch
            result_values[family + ':enterprisename'] = self.cur_mc
            result_values[family + ':id'] = j
            result_list.append(result_values)
            result_values = {}
            j += 1
        self.json_result["Administrative_Penalty"] = result_list
        # self.info(json.dumps(result_json_2, ensure_ascii=False)

    def get_jing_ying_yi_chang(self):
        """
        查询经营异常信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Business_Abnormal'
        table_id = '14'
        result_list = []
        j = 1
        # self.json_result[family] = []
        url = 'http://www.jsgsj.gov.cn:58888/ecipplatform/publicInfoQueryServlet.json?queryJyyc=true'
        params = {'id': self.id, 'org': self.org, 'seqId': self.seqId, 'curPage': 1, 'pageSize': 1000}
        r = self.post_request(url, data=params)
        self.info(u'经营异常')
        result_values = dict()
        abnormal_info = json.loads(r.text)["data"]
        for abnormal_dict in abnormal_info:
            result_values[family + ':abnormal_events'] = abnormal_dict.get('FACT_REASON', '')
            result_values[family + ':abnormal_datesin'] = abnormal_dict.get('MARK_DATE', '')
            result_values[family + ':abnormal_moveoutreason'] = abnormal_dict.get('REMOVE_REASON', '')
            result_values[family + ':abnormal_datesout'] = abnormal_dict.get('CREATE_DATE', '')
            result_values[family + ':abnormal_decisioninstitution'] = abnormal_dict.get('CREATE_ORG', '')

            result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
            result_values[family + ':registrationno'] = self.cur_zch
            result_values[family + ':enterprisename'] = self.cur_mc
            result_values[family + ':id'] = j
            result_list.append(result_values)
            result_values = {}
            j += 1
        self.json_result["Business_Abnormal"] = result_list
        # self.info(json.dumps(result_json_2, ensure_ascii=False)

    def get_yan_zhong_wei_fa(self):
        """
        查询严重违法信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        pass

    def get_chou_cha_jian_cha(self):
        """
        查询抽查检查信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        family = 'Spot_Check'
        table_id = '16'
        result_list = []
        j = 1
        # self.json_result[family] = []
        url = 'http://www.jsgsj.gov.cn:58888/ecipplatform/publicInfoQueryServlet.json?queryCcjc=true'
        params = {'id': self.id, 'org': self.org, 'seqId': self.seqId, 'curPage': 1, 'pageSize': 1000}
        r = self.post_request(url, data=params)
        self.info(u'抽查检查信息')
        result_values = dict()
        spot_info = json.loads(r.text)["data"]
        for spot_dict in spot_info:
            result_values[family + ':check_institution'] = spot_dict.get('CHECK_ORG', '')
            result_values[family + ':check_type'] = spot_dict.get('CHECK_TYPE', '')
            result_values[family + ':check_date'] = spot_dict.get('CHECK_DATE', '')
            result_values[family + ':check_result'] = spot_dict.get('CHECK_RESULT', '')

            result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
            result_values[family + ':registrationno'] = self.cur_zch
            result_values[family + ':enterprisename'] = self.cur_mc
            result_values[family + ':id'] = j
            result_list.append(result_values)
            result_values = {}
            j += 1
        self.json_result["Spot_Check"] = result_list
        # self.info(self.json_result
        # self.info(json.dumps(result_json_2, ensure_ascii=False)

        # self.info(json.dumps(result_json, ensure_ascii=False)

    def get_si_fa_xie_zhu(self):
        self.info(u'司法协助')
        family = 'sharesfrost'
        table_id = '25'
        result_list = []
        j = 1
        # self.json_result[family] = []
        url = 'http://www.jsgsj.gov.cn:58888/ecipplatform/publicInfoQueryServlet.json?querySfxz=true'
        params = {'id': self.id, 'org': self.org, 'seqId': self.seqId, 'curPage': 1, 'pageSize': 1000}
        r = self.post_request(url, data=params)
        result_values = dict()
        result_data = r.json()["data"]
        for result_dict in result_data:
            result_values[family + ':fro_bzxr'] = result_dict.get('ASSIST_NAME', '')
            result_values[family + ':fro_zxfy'] = result_dict.get('EXECUTE_COURT', '')
            result_values[family + ':fro_zxtzswh'] = result_dict.get('NOTICE_NO', '')
            result_values[family + ':fro_lx'] = result_dict.get('FREEZE_STATUS', '').split('|')[0]
            result_values[family + ':fro_zt'] = result_dict.get('FREEZE_STATUS', '').split('|')[-1]
            result_values[family + ':froam'] = result_dict.get('FREEZE_AMOUNT', '')
            # result_values[family + ':shareholder_name'] = result_dict.get('STOCK_NAME', '')
            # result_values[family + ':shareholder_certificationtype'] = result_dict.get('IDENT_TYPE_NAME', '')
            # result_values[family + ':shareholder_certificationno'] = result_dict.get('IDENT_NO', '')
            if result_values[family + ':fro_lx'] == u'股东变更':
                params = {'id':result_dict['ID'], 'org': result_dict['ORG'], 'seqId':result_dict['SEQ_ID']}
                sharefrost_detail = self.get_sharefrost_detail_gd(params)
            else:
                params = {'id':result_dict['ID'], 'org': result_dict['ORG']}
                sharefrost_detail = self.get_sharefrost_detail(params)
            result_values.update(sharefrost_detail)
            result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
            result_values[family + ':registrationno'] = self.cur_zch
            result_values[family + ':enterprisename'] = self.cur_mc
            result_values[family + ':id'] = j
            result_list.append(result_values)
            result_values = {}
            j += 1
        self.json_result["sharesfrost"] = result_list

    def get_sharefrost_detail(self, params):
        family = 'sharesfrost'
        url = "http://www.jsgsj.gov.cn:58888/ecipplatform/publicInfoQueryServlet.json?querySfxzGqdjDetail=true"
        r = self.get_request(url, params=params)
        detail = r.json()['djInfo'][0]
        detail_values = dict()
        detail_values[family + ':fro_zxsx'] = detail.get("ASSIST_ITEM", '')
        detail_values[family + ':fro_zxcdswh'] = detail.get("ADJUDICATE_NO", '')
        detail_values[family + ':fro_cyse'] = detail.get("FREEZE_AMOUNT", '')
        detail_values[family + ':fro_bzxrzzzl'] = detail.get("ASSIST_IDENT_TYPE", '')
        detail_values[family + ':fro_bzxrzzhm'] = detail.get("ASSIST_IDENT_NO", '')
        detail_values[family + ':frofrom'] = detail.get("FREEZE_START_DATE", '')
        detail_values[family + ':fro_djqx_to'] = detail.get("FREEZE_END_DATE", '')
        detail_values[family + ':fro_djqx'] = detail.get("FREEZE_YEAR_MONTH", '')
        detail_values[family + ':fro_gsrq'] = detail.get("PUBLIC_DATE", '')
        # detail_values[family + ':fro_djqx'] = detail.get("FREEZE_YEAR_MONTH", '')
        # detail_values[family + ':fro_djqx'] = detail.get("FREEZE_YEAR_MONTH", '')
        return detail_values

    def get_sharefrost_detail_gd(self, params):
        family = 'sharesfrost'
        url = "http://www.jsgsj.gov.cn:58888/ecipplatform/publicInfoQueryServlet.json?querySfxzGdbgDetail=true"
        r = self.get_request(url, params=params)
        detail = r.json()[0]
        detail_values = dict()
        detail_values[family + ':fro_zxsx'] = detail.get("ASSIST_ITEM", '')
        detail_values[family + ':fro_zxcdswh'] = detail.get("ADJUDICATE_NO", '')
        detail_values[family + ':fro_cyse'] = detail.get("FREEZE_AMOUNT", '')
        detail_values[family + ':fro_bzxrzzzl'] = detail.get("ASSIST_IDENT_TYPE", '')
        detail_values[family + ':fro_bzxrzzhm'] = detail.get("ASSIST_IDENT_NO", '')
        detail_values[family + ':frofrom'] = detail.get("FREEZE_START_DATE", '')
        detail_values[family + ':fro_djqx_to'] = detail.get("FREEZE_END_DATE", '')
        detail_values[family + ':fro_djqx'] = detail.get("FREEZE_YEAR_MONTH", '')
        detail_values[family + ':fro_gsrq'] = detail.get("PUBLIC_DATE", '')
        detail_values[family + ':fro_xzzxrq'] = detail.get("ASSIST_DATE", '')
        detail_values[family + ':fro_srr'] = detail.get("ACCEPT_NAME", '')
        detail_values[family + ':fro_srrzjzl'] = detail.get("ACCEPT_IDENT_TYPE", '')
        detail_values[family + ':fro_srrzjhm'] = detail.get("ACCEPT_IDENT_NO", '')
        detail_values[family + ':fro_gqszgs'] = detail.get("CORP_NAME", '')
        return detail_values


    def get_nian_bao_link(self):
        """
        获取年报url
        :param param_pripid:
        :param param_type:
        :return:
        """
        pass
        # params = {"REG_NO": "913201002496827567",
        #   "propertiesName": "query_report_list",
        #   "showRecordLine": "0",
        #   "specificQuery": "gs_pb",
        #   }
        # url = "http://www.jsgsj.gov.cn:58888/ecipplatform/nbServlet.json?nbEnter=true"
        # r = self.post_request(url, params=params)
        # nianbao_list = json.loads(r.text)
        # for nianbao in nianbao_list:

    # def get_request(self, url, params={}, t=0):
    #     try:
    #         return self.session.get(url=url, headers=self.headers, params=params)
    #     except RequestException, e:
    #         if t == 5:
    #             raise e
    #         else:
    #             return self.get_request(url, params, t+1)
    #
    # def post_request(self, url, params, t=0):
    #     try:
    #         return self.session.post(url=url, headers=self.headers, data=params)
    #     except RequestException, e:
    #         if t == 5:
    #             raise e
    #         else:
    #             return self.post_request(url, params, t+1)


if __name__ == '__main__':
    searcher = JiangSuSearcher()
    args_dict = get_args()
    if args_dict:
        searcher.submit_search_request(keyword=args_dict['companyName'], account_id=args_dict['accountId'], task_id=args_dict['taskId'])
    else:
        searcher.submit_search_request(u"金红叶纸业集团有限公司")
        searcher.info(json.dumps(searcher.json_result, ensure_ascii=False))

