# coding=utf-8

import PackageTool
import os
import json
import re
from requests.exceptions import RequestException
from gs.KafkaAPI import KafkaAPI
import sys
import uuid
import random
from lxml import html
from GuangdongConfig import *
from GuangdongShenzhen import parse_detail_shenzhen
from GuangdongGuangzhou import parse_detail_guangzhou
from gs.Searcher import Searcher, save_dead_company
from gs.TimeUtils import *
import urllib
from requests.exceptions import ReadTimeout
import requests
from selenium import webdriver

class Guangdong(Searcher):

    search_result_json = None
    pattern = re.compile("\s")
    cur_mc = ''
    cur_zch = ''
    json_result_data = {}
    json_result_nianbao = dict()  # 年报json数据
    nian_bao_year = ''  # 年报年份
    today = None
    credit_ticket = None
    cur_time = None
    ent_url = ''
    params = dict()
    tag_a = ""
    error_judge = ''

    def __init__(self):
        super(Guangdong, self).__init__(True)
        self.today = str(datetime.date.today()).replace('-', '')
        self.headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:47.0) Gecko/20100101 Firefox/47.0",
                        "Host": "gsxt.gdgs.gov.cn",
                        }
        self.set_config()
        self.log_name = 'guang_dong_'+str(uuid.uuid1())
        self.dengji_tree = ''

    def get_yzm(self):
        """
        获取验证码结果
        :return: 验证码
        """
        self.cur_time = '%d' % (time.time() * 1000)
        params = dict()
        params['random'] = ('%.18f' % random.random())
        image_url = 'http://gsxt.gdgs.gov.cn/aiccips//verify.html'
        r = self.get_request(image_url, params=params)
        yzm_path = self.get_yzm_path()
        with open(yzm_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    f.flush()
            f.close()
        yzm = self.recognize_yzm(yzm_path)
        os.remove(yzm_path)
        return yzm

    def set_config(self):
        self.plugin_path = os.path.join(sys.path[0], '../guangdong/ocr/huadongjuli.exe')
        self.group = 'Crawler'  # 正式
        self.kafka = KafkaAPI("GSCrawlerResult")  # 正式
        # self.group = 'CrawlerTest'  # 测试
        # self.kafka = KafkaAPI("GSCrawlerTest")  # 测试
        self.topic = 'GsSrc44'
        self.province = u'广东省'
        self.kafka.init_producer()

    def submit_search_request(self, keyword, flags=True, account_id='null', task_id='null'):
        """
        提交查询请求
        :param keyword: 查询关键词(公司名称或者注册号)
        :param flags: True表示keyword代表公司名，False表示keyword代表注册号
        :param account_id: 在线更新,kafka所需参数
        :param task_id: 在线更新kafka所需参数
        :return:
        """
        self.session = requests.session()  # 初始化session
        self.add_proxy(self.app_key)  # 为session添加代理
        res = 0
        self.cur_mc = ''  # 当前查询公司名称
        self.cur_zch = ''  # 当前查询公司注册号
        self.today = str(datetime.date.today()).replace('-', '')
        self.json_result.clear()

        self.json_result['inputCompanyName'] = keyword
        self.json_result['accountId'] = account_id
        self.json_result['taskId'] = task_id
        self.save_tag_a = True
        keyword = keyword.replace('(', u'（').replace(')', u'）')  # 公司名称括号统一转成全角
        self.info(u'keyword: %s' % keyword)
        tag_a = self.get_tag_a_from_db(keyword)
        if not tag_a:
            if not flags:
                tag_a = self.get_tag_a_from_page(keyword, flags) # flags False:不需校验公司名称是否匹配
            else:
                tag_a = self.get_tag_a_from_page(keyword)
        # if not tag_a:  # 等所有省份都修改结束，使用此段代码代替以上代码
        #     tag_a = self.get_tag_a_from_page(keyword, flags)
        if tag_a:
            if self.get_search_args(tag_a, keyword):
                if self.save_tag_a:  # 查询结果与所输入公司名称一致时,将其写入数据库
                    self.save_tag_a_to_db(tag_a)
                self.info(u'解析详情信息')
                if tag_a.startswith('http://www.szcredit'):
                    parse_detail_shenzhen(tag_a)
                elif tag_a.startswith('http://gsxt.gzaic'):
                    parse_detail_guangzhou(tag_a)
                else:
                    self.parse_detail(tag_a)
                res = 1
            # else:
            #     self.info(u'查询结果不一致')
            #     save_dead_company(keyword)
        else:
            if self.use_proxy and self.lock_id != '0':
                self.proxy_config.release_lock_id(self.lock_id)
            self.info(u'查询无结果')
            # save_dead_company(keyword)
        self.info(u'消息写入kafka')
        self.kafka.send(json.dumps(self.json_result, ensure_ascii=False))
        # self.info(json.dumps(self.json_result, ensure_ascii=False))
        return res

    def get_tag_a_from_page(self, keyword, flags=True):
        """
        从页面上通过提交验证码获取tag_a
        :param keyword: 查询关键词
        :param flags
        :rtype: str
        :return: tag_a列表
        """
        self.driver = webdriver.PhantomJS()
        self.driver.get("http://gsxt.gdgs.gov.cn/aiccips/")
        name_in = self.driver.find_element_by_xpath(".//*[@id='content']")
        name_in.clear()
        name_in.send_keys(keyword)
        but1 = self.driver.find_element_by_xpath(".//*[@id='search']")
        but1.click()
        self.info(u'正在查询%s' % keyword)
        self.geetest_verify(".//*[@class='textStyle']")

        tree = self.driver.find_element_by_xpath('html').get_attribute('outerHTML')
        tree = html.fromstring(tree)
        self.driver.quit() # 退出浏览器
        result_name_list = tree.xpath(".//div[@class='mianBodyStyle']/div[@class='clickStyle']")
        for i in range(len(result_name_list)):
            name = result_name_list[i].xpath("string(.//span[@class='rsfont'])").replace('(', u'（').replace(')', u'）').strip()
            if name != keyword:
                self.save_mc_to_db(name)
        for i in range(len(result_name_list)):
            name = result_name_list[i].xpath("string(.//span[@class='rsfont'])").replace('(', u'（').replace(')', u'）').strip()
            if flags:
                if name == keyword:
                    self.info(u'查询到指定公司')
                    self.tag_a = result_name_list[i].xpath('.//a/@href')[0].strip()
                    if not self.tag_a.startswith("http"):
                        self.tag_a = "http://gsxt.gdgs.gov.cn/aiccips/" + self.tag_a[3:]
                    return self.tag_a
            else:
                self.info(u'查询到指定公司')
                self.tag_a = result_name_list[i].xpath('.//a/@href')[0].strip()
                if not self.tag_a.startswith("http"):
                    self.tag_a = "http://gsxt.gdgs.gov.cn/aiccips/" + self.tag_a[3:]  # 美的集团股份有限公司
                return self.tag_a

    def get_search_args(self, tag_a, keyword):
        self.cur_mc = keyword
        return 1

    def parse_detail(self, ent_url):
        self.get_ji_ben(ent_url)
        self.get_gu_dong()
        self.get_bian_geng()
        self.get_zhu_yao_ren_yuan()
        self.get_fen_zhi_ji_gou()
        self.get_qing_suan()
        # self.get_dong_chan_di_ya()
        # self.get_gu_quan_chu_zhi()
        # self.get_xing_zheng_chu_fa()
        # self.get_jing_ying_yi_chang()
        # self.get_yan_zhong_wei_fa()
        # self.get_chou_cha_jian_cha()

    def get_ji_ben(self, ent_url):
        """
        查询基本信息
        :param: ent_url link
        :return: 基本信息结果
        """
        self.info(u'基本信息')
        r = self.get_request(ent_url)
        r.encoding = 'utf-8'
        # print r.text
        if "http://gsxt.gdgs.gov.cn/aiccips//images/errorinfo_new2.gif" in r.text:
            raise Exception('tag_a is useless!!!!')
        self.dengji_tree = html.fromstring(r.text)
        td_list = self.dengji_tree.xpath(".//span[@class='content']")
        th_list = self.dengji_tree.xpath(".//span[@class='label']")
        # print len(td_list)
        # print len(th_list)
        assert len(td_list) > 0 , 'error: ji_ben_xin_xi is wrong'  # 判断是否查询到基本信息
        ent_no = self.dengji_tree.xpath(".//*[@id='entNo']")[0].get('value')
        ent_type = self.dengji_tree.xpath(".//*[@id='entType']")[0].get('value')
        reg_org = self.dengji_tree.xpath(".//*[@id='regOrg']")[0].get('value')
        self.params = {
            'entNo': ent_no,
            'entType': ent_type,
            'regOrg': reg_org
            }
        family = 'Registered_Info'
        table_id = '01'
        result_values = {}
        if len(td_list) == 0:
            self.error_judge = True
        for i in range(len(td_list)):
            th = th_list[i]
            td = td_list[i]
            desc = th.xpath('string(.)').strip(u'：')
            val = td.xpath("string(.)")
            if desc and desc in ji_ben_dict:
                desc = desc.strip()
                desc = family + ':' + ji_ben_dict[desc]
                if val:
                    val = val.strip().replace('\n', '')
                if desc == u'统一社会信用代码/注册号':
                    if len(val) == 18:
                        desc = family + ':' + ji_ben_dict[u'统一社会信用代码']
                    else:
                        desc = family + ':' + ji_ben_dict[u'注册号']
                result_values[desc] = val
        if result_values.get(family + ":" + 'tyshxy_code', ''):
            self.cur_zch = result_values[family + ":" + 'tyshxy_code']
        else:
            self.cur_zch = result_values.get(family + ":" + 'zch', '')
        result_values['rowkey'] = '%s_%s_%s_' % (self.cur_mc, table_id, self.cur_zch)
        result_values[family + ':registrationno'] = self.cur_zch
        result_values[family + ':enterprisename'] = self.cur_mc
        result_values[family + ':province'] = u'广东省'
        result_values[family + ':lastupdatetime'] = get_cur_time()
        self.json_result_data["Registered_Info"] = [result_values]

    def get_gu_dong(self):
        """
        查询股东信息
        :param param_pripid:
        :param param_type:
        :return:
        """
        self.info(u'查询股东信息')
        family = 'Shareholder_Info'
        table_id = '04'
        result_list = []
        result_values = {}
        j = 1
        params = self.params.copy()
        params['pageNo'] = '2'
        del params['entType']
        for i in range(5):
            try:
                r = self.post_request("http://gsxt.gdgs.gov.cn/aiccips//invInfo/invInfoList?pageNo=1", params=params)
                r.encoding = 'utf-8'
                inv_list = r.json()['list']['list']
                break
            except ValueError:
                pass
            except AttributeError:
                self.info(u'重新加载股东信息')
                pass
        for inv_dic in inv_list:
            result_values[family + ":" + 'shareholder_type'] = inv_dic.get('invType', '')
            result_values[family + ":" + 'shareholder_name'] = inv_dic.get('inv', '')
            result_values[family + ":" + 'shareholder_certificationno'] = inv_dic.get('certNo', '')
            result_values[family + ":" + 'subscripted_amount'] = inv_dic.get('subConAm', '')
            result_values[family + ":" + 'actualpaid_amount'] = inv_dic.get('acConAm', '')
            """
            出资详情在json中解析得到
            """
            result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
            result_values[family + ':registrationno'] = self.cur_zch
            result_values[family + ':enterprisename'] = self.cur_mc
            result_values[family + ':id'] = j
            result_list.append(result_values)
            result_values = {}
            j += 1
        self.json_result_data["Shareholder_Info"] = result_list
        # self.info(json.dumps(self.json_result_data, ensure_ascii=False)

    def get_bian_geng(self):
        """
        查询变更信息
        :return: 基本信息结果
        """
        pass
        # self.info(u'查询变更信息')
        # family = 'Changed_Announcement'
        # table_id = '05'
        # result_list = []
        # result_values = {}
        # j = 1
        # params = self.params.copy()
        # params['pageNo'] = '2'
        # r = self.post_request('http://gsxt.gdgs.gov.cn/aiccips/GSpublicity/entChaPage', params=params)
        # r.encoding = 'utf-8'
        # biangeng_list = json.loads(r.text).get('list', '')
        # for biangeng_dic in biangeng_list:
        #     result_values[family + ":" + 'changedannouncement_events'] = biangeng_dic.get('altFiledName', '')
        #     result_values[family + ":" + 'changedannouncement_before'] = biangeng_dic.get('altBe', '')
        #     result_values[family + ":" + 'changedannouncement_after'] = biangeng_dic.get('altAf', '')
        #     if biangeng_dic.get('altDate', ''):
        #         result_values[family + ":" + 'changedannouncement_date'] = format_nei_meng_gu(biangeng_dic.get('altDate', ''))[:10]
        #     result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
        #     result_values[family + ':registrationno'] = self.cur_zch
        #     result_values[family + ':enterprisename'] = self.cur_mc
        #     result_values[family + ':id'] = j
        #     result_list.append(result_values)
        #     result_values = {}
        #     j += 1
        # self.json_result_data["Changed_Announcement"] = result_list

    def get_zhu_yao_ren_yuan(self):
        """
        查询主要人员信息
        :return: 主要人员信息结果
        """
        self.info(u'查询主要人员信息')
        family = 'KeyPerson_Info'
        table_id = '06'
        result_list = []
        result_values = {}
        j = 1
        zhuyaorenyuan_list = self.dengji_tree.xpath(".//div[@class='twoLine']")
        for zhu_yao_ren_yuan in zhuyaorenyuan_list:
            result_values[family + ":" + 'keyperson_name'] = zhu_yao_ren_yuan.xpath('string(.//span[1])')
            result_values[family + ":" + 'keyperson_position'] = zhu_yao_ren_yuan.xpath('string(.//span[2])')
            result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
            result_values[family + ':registrationno'] = self.cur_zch
            result_values[family + ':enterprisename'] = self.cur_mc
            result_values[family + ':id'] = j
            result_list.append(result_values)
            result_values = {}
            j += 1
        self.json_result_data["KeyPerson_Info"] = result_list
        # self.info(json.dumps(self.json_result_data, ensure_ascii=False)

    def get_fen_zhi_ji_gou(self):
        """
        查询分支机构信息
        :return:分支机构信息结果
        """
        self.info(u'查询分支机构信息')
        family = 'Branches'
        table_id = '08'
        result_list = []
        result_values = {}
        j = 1

        brach_list = self.dengji_tree.xpath(".//div[@class='brabox']")
        for branch in brach_list:
            result_values[family + ":" + 'branch_registrationname'] = branch.xpath('string(.//span[1])')
            if branch.xpath('string(.//span[2]/span)'):branch_no = branch.xpath('string(.//span[2])/span').strip(u'（分）')
            result_values[family + ":" + 'branch_registrationno'] = branch_no
            result_values[family + ":" + 'branch_registrationinstitution'] = branch.xpath('string(.//span[3]/span)')
            result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
            result_values[family + ':registrationno'] = self.cur_zch
            result_values[family + ':enterprisename'] = self.cur_mc
            result_values[family + ':id'] = j
            result_list.append(result_values)
            result_values = {}
            j += 1
        self.json_result_data[family] = result_list

    def get_qing_suan(self):
        pass

    def get_dong_chan_di_ya(self):
        """
        查询动产抵押信息
        :return: 动产抵押信息结果
        """
        self.info(u'查询动产抵押信息')
        family = 'Chattel_Mortgage'
        table_id = '11'
        result_list = []
        result_values = {}
        j = 1
        r = self.post_request("http://gsxt.gdgs.gov.cn/aiccips/GSpublicity/GSpublicityList.html?service=pleInfo", params=self.params)
        r.encoding = 'utf-8'
        tree = html.fromstring(r.text)
        th_list = tree.xpath(".//*[@id='dongchandiya']//th")[1:-1]
        tr_list = tree.xpath(".//*[@id='dongchandiya']//tr")[2:-3]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                if len(td_list) > 1:
                    for i in range(len(th_list)):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th.text.strip()
                        val = td.text
                        if td.xpath('a'):
                            url = td.xpath('a')[0].get('onclick')
                            mot_no = re.findall("\('(.*?)'\)", url)[0]
                            dcdy_detail = self.get_dcdy_detail(mot_no, result_values[family + ":chattelmortgage_registrationdate"])
                            result_values.update(dcdy_detail)
                        result_values[family + ":" + dong_chan_di_ya_dict[desc]] = val
                    result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                    result_values[family + ':registrationno'] = self.cur_zch
                    result_values[family + ':enterprisename'] = self.cur_mc
                    result_values[family + ':id'] = j
                    result_list.append(result_values)
                    result_values = {}
                    j += 1
        self.json_result_data["Chattel_Mortgage"] = result_list

    def get_dcdy_detail(self, mot_no, mot_date):
        """
        :param mot_no: 登记编号
        :param mot_date: reg_no
        :return: 动产抵押登记详情
        """
        self.info(u'动产抵押登记详情')
        params = self.params.copy()
        params['service'] = 'pleInfoData'
        params['pleNo'] = mot_no
        r = self.get_request('http://gsxt.gdgs.gov.cn/aiccips/GSpublicity/GSpublicityList.html', params=params)
        r.encoding = 'utf-8'
        tree = html.fromstring(r.text)

        values = dict()
        mot_date = mot_date.replace(u'年', '-').replace(u'月', '-').replace(u'日', '')

        """被担保债券概况"""
        family = 'bdbzqgk'
        bdbzqgk = list()
        bdbzqgk_table_id = '56'
        bdbzqgk_dict = dict()
        bdbzqgk_dict[family + ':dbzq_fw'] = tree.xpath(".//table[3]//td")[2].text
        bdbzqgk_dict[family + ':dbzq_zl'] = tree.xpath(".//table[3]//td")[0].text
        bdbzqgk_dict[family + ':dbzq_qx'] = tree.xpath(".//table[3]//td")[3].text
        bdbzqgk_dict[family + ':dbzq_bz'] = tree.xpath(".//table[3]//td")[-1].text
        bdbzqgk_dict[family + ':dbzq_sl'] = tree.xpath(".//table[3]//td")[1].text
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
        dcdydj_dict[family + ':dcdy_djbh'] = tree.xpath(".//table[1]//td")[0].text
        dcdydj_dict[family + ':dcdy_djrq'] = tree.xpath(".//table[1]//td")[1].text.replace(u'年', '-').replace(u'月', '-').replace(u'日', '')
        dcdydj_dict[family + ':dcdy_djjg'] = tree.xpath(".//table[1]//td")[2].text
        dcdydj_dict[family + ':dcdy_bdbzqzl'] = tree.xpath(".//table[1]//td")[3].text
        dcdydj_dict[family + ':dcdy_bdbzqsl'] = tree.xpath(".//table[1]//td")[4].text
        dcdydj_dict[family + ':dcdy_lxqx'] = tree.xpath(".//table[1]//td")[5].text
        dcdydj_dict[family + ':dcdy_dbfw'] = tree.xpath(".//table[1]//td")[6].text
        dcdydj_dict[family + ':dcdy_bz'] = tree.xpath(".//table[1]//td")[7].text
        dcdydj_dict['rowkey'] = '%s_%s_%s_%s' % (self.cur_mc, mot_no,mot_date, dcdydj_table_id)
        dcdydj_dict[family + ':registrationno'] = self.cur_zch
        dcdydj_dict[family + ':enterprisename'] = self.cur_mc
        dcdydj.append(dcdydj_dict)
        values['Chattel_Mortgage:dcdydj'] = dcdydj # 动产抵押登记信息

        """抵押权人概况"""
        family = 'dyqrgk'
        dyqrgk = list()
        dyqrgk_table_id = '55' # 抵押权人概况表格
        k = 1
        for result_row in tree.xpath(".//table[2]//tr")[3:]:
            dyqrgk_values = dict()
            dyqrgk_values[family + ':dyqr_mc'] = result_row.xpath("td")[1].text.strip() if result_row.xpath("td")[1].text else ''
            dyqrgk_values[family + ':dyqr_zzlx'] = result_row.xpath("td")[2].text.strip() if result_row.xpath("td")[2].text else ''
            dyqrgk_values[family + ':dyqr_zzhm'] = result_row.xpath("td")[3].text.strip() if result_row.xpath("td")[3].text else ''
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
        k = 1
        for result_row in tree.xpath(".//table[4]//tr")[3:]:
            dyqrgk_values = dict()
            dyqrgk_values[family + ':dyw_mc'] = result_row.xpath('td')[1].text.strip() if result_row.xpath('td')[1].text else ''
            dyqrgk_values[family + ':dyw_gs'] = result_row.xpath('td')[2].text.strip() if result_row.xpath('td')[2].text else ''
            dyqrgk_values[family + ':dyw_xq'] = result_row.xpath('td')[3].text.strip() if result_row.xpath('td')[3].text else ''
            dyqrgk_values[family + ':dyw_bz'] = result_row.xpath('td')[4].text.strip() if result_row.xpath('td')[4].text else ''
            dyqrgk_values['rowkey'] = '%s_%s_%s_%s_%d' % (self.cur_mc, mot_no,mot_date, dywgk_table_id, k)
            dyqrgk_values[family + ':registrationno'] = self.cur_zch
            dyqrgk_values[family + ':enterprisename'] = self.cur_mc
            dyqrgk_values[family + ':id'] = k
            dywgk.append(dyqrgk_values)
            k += 1
        values[family + ':dywgk'] = dywgk # 抵押物概况
        return values

    def get_gu_quan_chu_zhi(self):
        """
        查询股权出质信息
        :return: 股权出质信息结果
        """
        self.info(u'查询股权出质信息')
        family = 'Equity_Pledge'
        table_id = '12'
        result_list = []
        result_values = {}
        j = 1
        r = self.post_request("http://gsxt.gdgs.gov.cn/aiccips/GSpublicity/GSpublicityList.html?service=curStoPleInfo", params=self.params)
        r.encoding = 'utf-8'
        tree = html.fromstring(r.text)
        th_list = tree.xpath(".//*[@id='guquanchuzhi']//th")[1:]
        tr_list = tree.xpath(".//*[@id='guquanchuzhi']//tr")
        if tr_list and len(tr_list) > 2:
            for tr in tr_list[2:]:
                td_list = tr.xpath("td")
                if len(td_list) > 1:
                    for i in range(len(th_list)):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th.text.strip()
                        if desc == u'证照/证件号码' or desc == u'证照/证件号码（类型）':
                            if i == 3:
                                desc = u'证照/证件号码(出质人)'
                            else:
                                desc = u'证照/证件号码(质权人)'
                        val = td.text
                        if td.xpath("a"):
                            val = td.xpath("a")[0].get("href")
                        result_values[family + ":" + gu_quan_chu_zhi_dict[desc]] = val
                    result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                    result_values[family + ':registrationno'] = self.cur_zch
                    result_values[family + ':enterprisename'] = self.cur_mc
                    result_values[family + ':id'] = j
                    result_list.append(result_values)
                    result_values = {}
                    j += 1
        self.json_result_data["Equity_Pledge"] = result_list
        # self.info(json.dumps(self.json_result_data, ensure_ascii=False)

    def get_xing_zheng_chu_fa(self):
        """
        查询行政处罚信息
        :return: 行政处罚信息结果
        """
        self.info(u'查询行政处罚信息')
        family = 'Administrative_Penalty'
        table_id = '13'
        result_list = []
        result_values = {}
        j = 1
        r = self.post_request("http://gsxt.gdgs.gov.cn/aiccips/GSpublicity/GSpublicityList.html?service=cipPenaltyInfo", params=self.params)
        r.encoding = 'utf-8'
        tree = html.fromstring(r.text)
        th_list = tree.xpath(".//*[@id='xingzhengchufa']//th")[1:]
        tr_list = tree.xpath(".//*[@id='xingzhengchufa']//tr")
        if tr_list and len(tr_list) > 2:
            for tr in tr_list[2:]:
                td_list = tr.xpath("td")
                if len(td_list) > 1:
                    for i in range(len(th_list)):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th.xpath("string(.)").strip()
                        val = td.text
                        if td.xpath("a"):
                            val = td.xpath("a")[0].get("href")
                        result_values[family + ":" + xing_zheng_chu_fa_dict[desc]] = val
                    result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                    result_values[family + ':registrationno'] = self.cur_zch
                    result_values[family + ':enterprisename'] = self.cur_mc
                    result_values[family + ':id'] = j
                    result_list.append(result_values)
                    result_values = {}
                    j += 1
        self.json_result_data["Administrative_Penalty"] = result_list
        # self.info(json.dumps(self.json_result_data, ensure_ascii=False)

    def get_jing_ying_yi_chang(self):
        """
        查询经营异常信息
        :return: 经营异常信息结果
        """
        self.info(u'查询经营异常信息')
        family = 'Business_Abnormal'
        table_id = '14'
        result_list = []
        result_values = {}
        j = 1
        r = self.post_request("http://gsxt.gdgs.gov.cn/aiccips/GSpublicity/GSpublicityList.html?service=cipUnuDirInfo", params=self.params)
        r.encoding = 'utf-8'
        tree = html.fromstring(r.text)
        th_list = tree.xpath(".//*[@id='yichangminglu']//th")[1:]
        tr_list = tree.xpath(".//*[@id='yichangminglu']//tr")
        if tr_list and len(tr_list) > 2:
            for tr in tr_list[2:]:
                td_list = tr.xpath("td")
                if len(td_list) > 1:
                    for i in range(len(th_list)):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th.text.strip()
                        val = td.text
                        if td.xpath("a"):
                            val = td.xpath("a")[0].get("href")
                        result_values[family + ":" + jing_ying_yi_chang_dict[desc]] = val
                    result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                    result_values[family + ':registrationno'] = self.cur_zch
                    result_values[family + ':enterprisename'] = self.cur_mc
                    result_values[family + ':id'] = j
                    result_list.append(result_values)
                    result_values = {}
                    j += 1
        self.json_result_data["Business_Abnormal"] = result_list
        # self.info(json.dumps(self.json_result_data, ensure_ascii=False)

    def get_yan_zhong_wei_fa(self):
        """
        查询严重违法信息
        :return: 信息结果
        """
        self.info(u'查询严重违法信息')
        family = 'Serious_Violations'
        table_id = '15'
        result_list = []
        result_values = {}
        j = 1
        r = self.post_request("http://gsxt.gdgs.gov.cn/aiccips/GSpublicity/GSpublicityList.html?service=cipUnuDirInfo", params=self.params)
        r.encoding = 'utf-8'
        tree = html.fromstring(r.text)
        th_list = tree.xpath(".//*[@id='heimingdan']//th")[1:]
        tr_list = tree.xpath(".//*[@id='heimingdan']//tr")
        if tr_list and len(tr_list) > 2:
            for tr in tr_list[2:]:
                td_list = tr.xpath("td")
                if len(td_list) > 1:
                    for i in range(len(th_list)):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th.text.strip()
                        val = td.text
                        if td.xpath("a"):
                            val = td.xpath("a")[0].get("href")
                        result_values[family + ":" + yan_zhong_wei_fa_dict[desc]] = val
                    result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                    result_values[family + ':registrationno'] = self.cur_zch
                    result_values[family + ':enterprisename'] = self.cur_mc
                    result_values[family + ':id'] = j
                    result_list.append(result_values)
                    result_values = {}
                    j += 1
        self.json_result_data["Serious_Violations"] = result_list
        # self.info(json.dumps(self.json_result_data, ensure_ascii=False)

    def get_chou_cha_jian_cha(self):
        """
        查询抽查检查信息
        :return: 抽查检查信息结果
        """
        self.info(u'查询抽查检查信息')
        family = 'Spot_Check'
        table_id = '16'
        result_list = []
        result_values = {}
        j = 1
        r = self.post_request("http://gsxt.gdgs.gov.cn/aiccips/GSpublicity/GSpublicityList.html?service=cipUnuDirInfo", params=self.params)
        r.encoding = 'utf-8'
        tree = html.fromstring(r.text)
        th_list = tree.xpath(".//*[@id='chouchajiancha']//th")[1:]
        tr_list = tree.xpath(".//*[@id='chouchajiancha']//tr")
        if tr_list and len(tr_list) > 3:
            for tr in tr_list[2:-1]:
                td_list = tr.xpath("td")
                if len(td_list) > 1:
                    for i in range(len(th_list)):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th.text.strip()
                        val = td.text
                        if td.xpath("a"):
                            val = td.xpath("a")[0].get("href")
                        result_values[family + ":" + chou_cha_jian_cha_dict[desc]] = val
                    result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                    result_values[family + ':registrationno'] = self.cur_zch
                    result_values[family + ':enterprisename'] = self.cur_mc
                    result_values[family + ':id'] = j
                    result_list.append(result_values)
                    result_values = {}
                    j += 1
        self.json_result_data["Spot_Check"] = result_list
        # self.info(json.dumps(self.json_result_data, ensure_ascii=False)
        # self.info(json.dumps(result_json, ensure_ascii=False)

    def get_nian_bao(self):
        """
        获取年报
        :param param_pripid:
        :param param_typ
        :return:
        """
        family = 'annual_report'
        table_id = '16'
        result_list = []
        result_values = {}
        self.json_result_data['nian_bao'] = list()
        self.json_result_nianbao.clear()
        j = 1
        for k in range(1, 5):
            url = 'http://gsxt.gdgs.gov.cn/aiccips/BusinessAnnals/BusinessAnnalsList.html?pageNo=%s&entNo=%s&entType=%s&regOrg=%s' % (k, self.params['entNo'], self.params['entType'],
                                                                                                                                      self.params['regOrg'])
            r = self.get_request(url)
            r.encoding = 'utf-8'
            tree = html.fromstring(r.text.replace('<<', '').replace('>>', ''))
            if u'暂无数据' in r.text:
                self.json_result_data[family] = result_list
                break
            else:
                page_no = int(tree.xpath(".//*[@id='qiyenianbao']/table[2]//th")[0].xpath('string(.)').strip().split(u'/')[1])
                self.info(page_no)
                th_list = tree.xpath(".//*[@id='qiyenianbao']/table[1]//th")[1:]
                tr_list = tree.xpath(".//*[@id='qiyenianbao']/table[1]//tr")[2:]
                for tr in tr_list:
                    td_list = tr.xpath("td")
                    if len(td_list) > 1:
                        for i in range(len(th_list)):
                            th = th_list[i]
                            td = td_list[i]
                            desc = th.text.strip()
                            val = td.text
                            if td.xpath("a"):
                                val = td.xpath("a")[0].text
                                self.nian_bao_year = td.xpath('a')[0].text[:4]
                                self.info(self.nian_bao_year)
                                self.get_nian_bao_detail(td.xpath("a")[0].get("href"))
                                self.json_result_data['nian_bao'].append(self.json_result_nianbao.copy())  # 将年报详情加入json数据中！！！！！！！！！！！！！
                            if desc in nian_bao_dict:
                                result_values[family + ":" + nian_bao_dict[desc]] = val
                        result_values['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, j)
                        result_values[family + ':registrationno'] = self.cur_zch
                        result_values[family + ':enterprisename'] = self.cur_mc
                        result_values[family + ':id'] = j
                        result_list.append(result_values)
                        result_values = {}
                        j += 1
            if page_no == k:
                break
        self.json_result_data[family] = result_list

    def get_nian_bao_detail(self, url):
        """
        :param url: 年报url地址
        :return: 返回年报中多个表格组成的dict详情{table_name:[table_info]}
        """
        self.json_result_nianbao.clear()
        r = self.get_request(url)
        r.encoding = 'utf-8'
        tree = html.fromstring(r.text)
        self.get_nianbao_jiben(tree)
        self.get_nianbao_wangzhan(tree)
        self.get_nianbao_gudong(tree)
        self.get_nianbao_touzi(tree)
        self.get_nianbao_zichan(tree)
        self.get_nianbao_danbao(tree)
        self.get_nianbao_guquan(tree)
        self.get_nianbao_xiugai(tree)
        # self.info(json.dumps(self.json_result_data['nian_bao'], ensure_ascii=False)

    def get_nianbao_jiben(self, tree):
        family = 't_pl_public_org_report_base'
        table_id = '40'
        th_list = tree.xpath(".//*[@id='detailsCon']/table[2]//th")
        td_list = tree.xpath(".//*[@id='detailsCon']/table[2]//td")
        result_values = {}
        for i in range(len(td_list)):
            th = th_list[i]
            td = td_list[i]
            desc = th.xpath('string(.)')
            if td.xpath("span"):
                val = td.xpath("span")[0].text
            else:
                val = td.text
            if desc:
                desc = desc.strip()
                if desc in nian_bao_ji_ben_dict:
                    desc = family + ':' + nian_bao_ji_ben_dict[desc]
                    if val:
                        val = val.strip().replace('\n', '')
                    result_values[desc] = val
        result_values['rowkey'] = '%s_%s_%s_' % (self.cur_mc, self.nian_bao_year, table_id)
        result_values[family + ':registrationno'] = self.cur_zch
        result_values[family + ':enterprisename'] = self.cur_mc
        result_values[family + ':province'] = u'广东省'
        result_values[family + ':lastupdatetime'] = get_cur_time()
        self.json_result_nianbao[family] = [result_values]
        # self.info(json.dumps(self.json_result_data['nian_bao'], ensure_ascii=False)

    def get_nianbao_wangzhan(self, tree):
        family = 't_pl_public_org_web_site'
        table_id = '41'
        result_list = []
        result_values = {}
        j = 1
        th_list = tree.xpath(".//*[@id='t02']//th")[1:]
        tr_list = tree.xpath(".//*[@id='t02']//tr")[2:]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                if len(td_list) > 1:
                    for i in range(len(th_list)):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th.text.strip()
                        val = td.text
                        result_values[family + ":" + nian_bao_wang_zhan_dict[desc]] = val
                    result_values['rowkey'] = '%s_%s_%s_%d' % (self.cur_mc, self.nian_bao_year, table_id, j)
                    result_values[family + ':registrationno'] = self.cur_zch
                    result_values[family + ':enterprisename'] = self.cur_mc
                    result_values[family + ':id'] = j
                    result_list.append(result_values)
                    result_values = {}
                    j += 1
        self.json_result_nianbao[family] = result_list

    def get_nianbao_gudong(self, tree):
        family = 't_pl_public_org_enterprise_shareholder'
        table_id = '42'
        result_list = []
        result_values = {}
        j = 1
        th_list = tree.xpath(".//*[@id='t03']//th")[1:]
        tr_list = tree.xpath(".//*[@id='t03']//tr")[2:]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                if len(td_list) > 1:
                    for i in range(len(th_list)):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th.text.strip()
                        val = td.text
                        if val:
                            val = val.replace('\r\n', '').strip()
                        result_values[family + ":" + nian_bao_chu_zi_dict[desc]] = val
                    result_values['rowkey'] = '%s_%s_%s_%d' % (self.cur_mc, self.nian_bao_year, table_id, j)
                    result_values[family + ':registrationno'] = self.cur_zch
                    result_values[family + ':enterprisename'] = self.cur_mc
                    result_values[family + ':id'] = j
                    result_list.append(result_values)
                    result_values = {}
                    j += 1
        self.json_result_nianbao[family] = result_list

    def get_nianbao_touzi(self, tree):
        family = 't_pl_public_org_investment'
        table_id = '47'
        result_list = []
        result_values = {}
        j = 1
        th_list = tree.xpath(".//*[@id='t04']//th")[1:]
        tr_list = tree.xpath(".//*[@id='t04']//tr")[2:]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                if len(td_list) > 1:
                    for i in range(len(th_list)):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th.text.strip()
                        val = td.text
                        result_values[family + ":" + nian_bao_tou_zi_dict[desc]] = val
                    result_values['rowkey'] = '%s_%s_%s_%d' % (self.cur_mc, self.nian_bao_year, table_id, j)
                    result_values[family + ':registrationno'] = self.cur_zch
                    result_values[family + ':enterprisename'] = self.cur_mc
                    result_values[family + ':id'] = j
                    result_list.append(result_values)
                    result_values = {}
                    j += 1
        self.json_result_nianbao[family] = result_list

    def get_nianbao_zichan(self, tree):
        family = 't_pl_public_org_industry_status'
        table_id = '43'
        th_list = tree.xpath(".//*[@id='t05']//th")[1:]
        td_list = tree.xpath(".//*[@id='t05']//td")
        result_values = {}
        for i in range(len(td_list)):
            th = th_list[i]
            td = td_list[i]
            desc = th.xpath('string(.)')
            if td.xpath("span"):
                val = td.xpath("span")[0].text
            else:
                val = td.text
            if desc:
                desc = desc.strip()
                if desc in nian_bao_zi_chan_dict:
                    desc = family + ':' + nian_bao_zi_chan_dict[desc]
                    if val:
                        val = val.strip().replace('\n', '')
                    result_values[desc] = val
        result_values['rowkey'] = '%s_%s_%s_' % (self.cur_mc, self.nian_bao_year, table_id)
        result_values[family + ':registrationno'] = self.cur_zch
        result_values[family + ':enterprisename'] = self.cur_mc
        self.json_result_nianbao[family] = [result_values]

    def get_nianbao_danbao(self, tree):
        family = 't_pl_public_org_guarantee'
        table_id = '44'
        result_list = []
        result_values = {}
        j = 1
        th_list = tree.xpath(".//table[7]//th")[1:]
        tr_list = tree.xpath(".//table[7]//tr")[2:]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                if len(td_list) > 1:
                    for i in range(len(th_list)):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th.text.strip()
                        val = td.text
                        result_values[family + ":" + nian_bao_dan_bao_dict[desc]] = val
                    result_values['rowkey'] = '%s_%s_%s_%d' % (self.cur_mc, self.nian_bao_year, table_id, j)
                    result_values[family + ':registrationno'] = self.cur_zch
                    result_values[family + ':enterprisename'] = self.cur_mc
                    result_values[family + ':id'] = j
                    result_list.append(result_values)
                    result_values = {}
                    j += 1
        self.json_result_nianbao[family] = result_list

    def get_nianbao_guquan(self, tree):
        family = 't_pl_public_org_equity_transfer'
        table_id = '45'
        result_list = []
        result_values = {}
        j = 1
        th_list = tree.xpath(".//table[8]//th")[1:]
        tr_list = tree.xpath(".//table[8]//tr")[2:]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                if len(td_list) > 1:
                    for i in range(len(th_list)):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th.text.strip()
                        val = td.text
                        result_values[family + ":" + nian_bao_gu_quan_bian_geng_dict[desc]] = val
                    result_values['rowkey'] = '%s_%s_%s_%d' % (self.cur_mc, self.nian_bao_year, table_id, j)
                    result_values[family + ':registrationno'] = self.cur_zch
                    result_values[family + ':enterprisename'] = self.cur_mc
                    result_values[family + ':id'] = j
                    result_list.append(result_values)
                    result_values = {}
                    j += 1
        self.json_result_nianbao[family] = result_list

    def get_nianbao_xiugai(self, tree):
        family = 't_pl_public_org_modify'
        table_id = '46'
        result_list = []
        result_values = {}
        j = 1
        th_list = tree.xpath(".//*[@id='table_1NA']//th")[1:]
        tr_list = tree.xpath(".//*[@id='table_1NA']//tr")[2:]
        if tr_list:
            for tr in tr_list:
                td_list = tr.xpath("td")
                if len(td_list) > 1:
                    for i in range(len(th_list)):
                        th = th_list[i]
                        td = td_list[i]
                        desc = th.text.strip()
                        val = td.text
                        if val:
                            val = val.replace('\r\n', '').strip()
                        result_values[family + ":" + nian_bao_xiu_gai_dict[desc]] = val
                    result_values['rowkey'] = '%s_%s_%s_%d' % (self.cur_mc, self.nian_bao_year, table_id, j)
                    result_values[family + ':registrationno'] = self.cur_zch
                    result_values[family + ':enterprisename'] = self.cur_mc
                    result_values[family + ':id'] = j
                    result_list.append(result_values)
                    result_values = {}
                    j += 1
        self.json_result_nianbao[family] = result_list

    def get_request_302(self, url, t=0):
        """
        手动处理包含302的请求
        :param url:
        :param params:
        :param lock_ip:
        :param t:
        :return:
        """
        try:
            for i in range(10):
                if self.use_proxy:
                    self.headers['Proxy-Authorization'] = self.proxy_conf.get_auth_header()
                r = self.session.get(url=url, headers=self.headers, proxies=self.proxy_conf.get_proxy(), allow_redirects=False)
                if r.status_code == 302:
                    protocal, addr = urllib.splittype(url)
                    url = protocal + '://' + urllib.splithost(addr)[0] + r.headers['Location']
                else:
                    return r
        except (RequestException, ReadTimeout) as e:
            if t == 5:
                raise e
            else:
                self.info(u'重试')
                return self.get_request_302(url, t + 1)


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
    reload(sys)
    sys.setdefaultencoding('utf8')
    searcher = Guangdong()
    args_dict = get_args()
    if args_dict:
        searcher.submit_search_request(keyword=args_dict['companyName'], account_id=args_dict['accountId'], task_id=args_dict['taskId'])
    else:
        searcher.delete_tag_a_from_db(u'珠海格力集团有限公司')
        searcher.submit_search_request(u"珠海格力集团有限公司")
        searcher.info(json.dumps(searcher.json_result_data, ensure_ascii=False))
