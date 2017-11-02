# coding=utf-8
import re
import os
import sys
import MSSQL
import json
from ProxyConf import ProxyConf, key1 as app_key
import urllib
from requests.exceptions import ReadTimeout
from requests.exceptions import ConnectTimeout
from requests.exceptions import ProxyError
from requests.exceptions import ConnectionError
from requests.exceptions import ChunkedEncodingError
import requests
from MyException import StatusCodeException
import datetime
import Logger
import pyodbc
import uuid
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from PIL import Image
import subprocess
import time
from selenium.webdriver.remote.command import Command
from selenium.common.exceptions import NoSuchElementException
import random
import traceback
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.wait import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC


class Searcher(object):

    pattern = re.compile("\s")
    cur_mc = ''  # 当前查询公司名称
    cur_zch = ''  # 当前查询公司注册号
    json_result = {}  # json输出结果
    plugin_path = None  # 验证码插件路径
    kafka = None  # kafka客户端
    save_tag_a = True  # 是否需要存储tag_a
    today = None  # 当天
    session = None  # 提交请求所用session
    province = None  # 省份
    topic = None  # 获取公司名称的队列
    group = None  # 获取公司名称的组
    use_proxy = False  # 是否需要用代理

    lock_id = '0'  # ip锁定标识
    release_id = '0'  # 要释放的ip
    proxy_config = None  # 代理浏览器头生成器
    timeout = 15  # request最大等待时间

    log_name = ''  # 日志文件名
    print_msg = True  # 是否打印日志
    headers = {}
    real_time = False
    crawler_id = str(uuid.uuid1())
    app_key = None  # 刘文海修改

    def __init__(self, use_proxy=False):
        self.session = requests.session()
        self.driver = '' # 极验火狐
        self.use_proxy = use_proxy
        self.add_proxy(app_key)

    def add_proxy(self, key):
        self.app_key = key  # 刘文海修改, 方便在submit中调用
        if self.use_proxy:
            self.proxy_config = ProxyConf(key)
            self.session.proxies = self.proxy_config.get_proxy()

    def turn_off_print(self):
        # print '>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>.'
        self.print_msg = False

    def info(self, msg):
        if self.real_time:
            name = self.province
        else:
            name = self.province + '_' + self.crawler_id
        Logger.write(msg, name=name, print_msg=self.print_msg)

    def set_request_timeout(self, t):
        self.timeout = t

    def set_real_time(self, real_time):
        self.real_time = real_time

    def set_config(self):
        """
        设置参数(self.plugin_path)
        :return:
        """
        pass

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
            # args = self.get_search_args(tag_a, keyword)
            if self.get_search_args(tag_a, keyword):
                if self.save_tag_a:  # 查询结果与所输入公司名称一致时,将其写入数据库
                    self.save_tag_a_to_db(tag_a)
                self.info(u'解析详情信息')
                self.parse_detail()
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

    def geetest_verify(self, success_flag):  # 极验PhantomJs验证函数
        """
        :param success_flag: 验证码成功通过的元素xpath
        :return:
        """
        while True:
            try:
                self.driver.set_window_size(1280,936)
                WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.XPATH, ".//*[@class='gt_slider_knob gt_show']")))
                but2 = self.driver.find_elements_by_xpath(".//*[@class='gt_slider_knob gt_show']")[-1]
                ActionChains(self.driver).click_and_hold(but2).perform()
                time.sleep(3)
                screenshot_file = self.get_yzm_path()
                self.driver.get_screenshot_as_file(screenshot_file)
                img_location = self.driver.find_elements_by_xpath(".//*[@class='gt_bg gt_show']")[-1]
                x, y = img_location.location['x'], img_location.location['y']
                rangle = (x+2, y+1, x+258, y+114)
                i = Image.open(screenshot_file)
                frame = i.crop(rangle)
                crop_file = self.get_yzm_path()
                frame.save(crop_file)
                cmd = self.plugin_path + " " + crop_file
                process = subprocess.Popen(cmd.encode('GBK', 'ignore'), stdout=subprocess.PIPE)
                for k in iter(process.stdout.readline,''):
                    result = int(k)
                os.remove(screenshot_file)
                os.remove(crop_file)
                old_location = 0
                new_location = result + 2
                while old_location < (new_location-1):
                    yoffset = random.choice([-1,0,0,0,0,0,1])
                    self.driver.execute(Command.MOVE_TO,{
                        'xoffset': 1,
                        'yoffset': yoffset})
                    old_location +=1
                    s = float(old_location)/new_location
                    dt = 0.001/(s*(1-s))
                    lt = [0.001,0.002,0.003,0.004,0.005,0.006,0.001,-0.001,-0.002,0.004,0.005,0.006,0.1,0.1,0.2,0.3]
                    dt = (dt + random.choice(lt))/100
                    if new_location - old_location < 2:
                        time.sleep(dt*100)
                    elif new_location - old_location < 10:
                        time.sleep(dt*50)
                    else:
                        time.sleep(dt)
                self.driver.execute(Command.MOVE_TO,{
                        'xoffset': -2,
                        'yoffset': 0})
                self.driver.execute(Command.MOUSE_UP, {})
                try:
                    WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.XPATH, success_flag)))
                    self.info(u'验证成功')
                    return
                except TimeoutException:
                    self.info(u'验证失败，正在重试')
                    try:
                        WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.XPATH, ".//*[@class='gt_refresh_button']"))).click()
                    except Exception, e:
                        raise e
                    time.sleep(0.5)
            except Exception,e:
                err = traceback.format_exc(e)
                if type(err) != unicode:
                    err = err.decode('utf-8', 'ignore')
                self.info(err)
                raise e

    def get_search_args(self, tag_a, keyword):
        """
        :param tag_a: tag_a
        :param keyword: 查询关键词
        根据tag_a解析查询所需参数, 如果查询结果和输入公司名不匹配返回空列表
        :rtype: list
        :return: 查询所需参数
        """
        pass

    def get_tag_a_from_db(self, keyword):
        """
        从数据库中查询tag_a, 如果数据库中存在tag_a,直接返回,否则需要提交验证码进行查询
        :param keyword: 查询关键词
        :rtype: str
        :return: 查询详情所需的tag_a
        """
        sql_1 = "select * from GsSrc.dbo.tag_a where mc='%s' and province='%s'" % (keyword, self.province)
        res_1 = MSSQL.execute_query(sql_1)
        if len(res_1) > 0:
            self.save_tag_a = False
            tag_a = res_1[0][1]
            return tag_a
        else:
            return None

    def get_tag_a_from_page(self, keyword, flags=True):
        """
        从页面上通过提交验证码获取tag_a
        :param keyword: 查询关键词
        :param flags:true需要校验公司名，false不需校验(使用注册号查询)
        :rtype: str
        :return: tag_a
        """
        pass

    def save_tag_a_to_db(self, tag_a):
        """
        将通过提交验证码获取到的tag_a存储到数据库中
        :param tag_a: 查询关键词
        :return:
        """
        sql = "insert into GsSrc.dbo.tag_a values ('%s','%s',getdate(),'%s')" % (self.cur_mc, tag_a, self.province)
        try:
            MSSQL.execute_update(sql)
        except pyodbc.IntegrityError:
            sql = "update GsSrc.dbo.tag_a " \
                  "set province='%s',tag_a='%s',last_update_time=getDate() where mc='%s'" \
                  % (self.province, tag_a, self.cur_mc)
            MSSQL.execute_update(sql)

    def save_mc_to_db(self, mc):
        """
        将查询衍生出的公司名称存入数据库
        :param mc: 公司名称
        :return:
        """
        mc = mc.replace("'", '"').replace(u"‘", '"')
        sql = "insert into %s(mc,update_status,last_update_time,province) values ('%s',-1,getdate(),'%s')" \
              % (self.topic, mc, self.province)
        try:
            MSSQL.execute_update(sql)
        except pyodbc.IntegrityError:
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

    def get_yzm_path(self):
        self
        return os.path.join(sys.path[0], '../temp/' + str(random.random())[2:] + '.jpg')

    def download_yzm(self):
        """
        下载验证码图片
        :rtype str
        :return 验证码保存路径
        """
        return ""

    def recognize_yzm(self, yzm_path):
        """
        识别验证码
        :param yzm_path: 验证码保存路径
        :return: 验证码识别结果
        """
        cmd = self.plugin_path + " " + yzm_path
        process = subprocess.Popen(cmd.encode('GBK', 'ignore'), stdout=subprocess.PIPE)
        process_out = process.stdout.read()
        answer = process_out.split('\r\n')[6].strip()
        return answer.decode('gbk', 'ignore')

    def parse_detail(self):
        """
        解析公司详情信息
        :param kwargs:
        :return:
        """
        self.info(u'解析基本信息...')
        self.get_ji_ben()
        self.info(u'解析股东信息...')
        self.get_gu_dong()
        self.info(u'解析变更信息...')
        self.get_bian_geng()
        self.info(u'解析主要人员信息...')
        self.get_zhu_yao_ren_yuan()
        self.info(u'解析分支机构信息...')
        self.get_fen_zhi_ji_gou()
        self.info(u'解析清算信息...')
        self.get_qing_suan()
        self.info(u'解析动产抵押信息...')
        self.get_dong_chan_di_ya()
        self.info(u'解析股权出质信息...')
        self.get_gu_quan_chu_zhi()
        self.info(u'解析行政处罚信息...')
        self.get_xing_zheng_chu_fa()
        self.info(u'解析经营异常信息...')
        self.get_jing_ying_yi_chang()
        self.info(u'解析严重违法信息...')
        self.get_yan_zhong_wei_fa()
        self.info(u'解析抽查检查信息...')
        self.get_chou_cha_jian_cha()
        # self.get_nian_bao_link(*kwargs)
        self.info(u'获取年报信息...')
        # self.get_nian_bao()

    def get_ji_ben(self):
        """
        获取基本信息
        :return:
        """
        pass

    def get_gu_dong(self):
        """
        获取股东信息
        :return:
        """
        pass

    def get_bian_geng(self):
        """
        获取变更信息
        :return:
        """
        pass

    def get_zhu_yao_ren_yuan(self):
        """
        获取主要人员信息
        :return:
        """
        pass

    def get_fen_zhi_ji_gou(self):
        """
        获取分支机构信息
        :return:
        """
        pass

    def get_qing_suan(self):
        """
        获取清算信息
        :return:
        """
        pass

    def get_dong_chan_di_ya(self):
        """
        获取动产抵押信息
        :return:
        """
        pass

    def get_gu_quan_chu_zhi(self):
        """
        获取股权出质信息
        :return:
        """
        pass

    def get_xing_zheng_chu_fa(self):
        """
        获取行政处罚信息
        :return:
        """
        pass

    def get_jing_ying_yi_chang(self):
        """
        获取经营异常信息
        :return:
        """
        pass

    def get_yan_zhong_wei_fa(self):
        """
        获取严重违法信息
        :return:
        """
        pass

    def get_chou_cha_jian_cha(self):
        """
        获取抽查检查信息
        :return:
        """
        pass

    def get_nian_bao_link(self):
        """
        获取年报信息
        :return:
        """
        pass

    def get_nian_bao(self):
        """
        获取年报信息
        :return:
        """
        pass

    def save_company_name_to_db(self, company_name):
        sql = "insert into %s(mc,update_status,province) values ('%s',-1,'%s')" % (self.topic, company_name, self.province)
        try:
            MSSQL.execute_update(sql)
        except pyodbc.IntegrityError:
            pass

    def delete_tag_a_from_db(self, keyword):
        """
        从数据库中删除现存的tag_a
        :param keyword: 查询关键词
        """
        sql_1 = "delete from GsSrc.dbo.tag_a where mc='%s' and province='%s'" % (keyword, self.province)
        MSSQL.execute_update(sql_1)

    def get_request(self, url, t=0, **kwargs):
        """
        发送get请求,包含添加代理,锁定ip与重试机制
        :param url: 请求的url
        :param t: 重试次数
        """
        try:
            if 'timeout' not in kwargs:
                kwargs['timeout'] = self.timeout
            if 'headers' not in kwargs:
                kwargs['headers'] = self.headers
            if self.use_proxy:
                kwargs['headers']['Proxy-Authorization'] = self.proxy_config.get_auth_header(lock_id=self.lock_id, release_id=self.release_id)
            r = self.session.get(url=url, **kwargs)
            if r.status_code != 200:
                # print r.status_code
                self.info(u'错误的响应代码 -> %d\n%s' % (r.status_code, url))
                if self.province == u'浙江省' and r.status_code == 504:
                    del self.session
                    self.session = requests.session()
                    self.session.proxies = self.proxy_config.get_proxy()
                    raise Exception(u'504错误')
                if r.status_code == 403:
                    if self.use_proxy:
                        if self.lock_id != '0':
                            self.proxy_config.release_lock_id(self.lock_id)
                            self.lock_id = self.proxy_config.get_lock_id()
                            self.release_id = self.lock_id
                    else:
                        raise Exception(u'IP被封')
                raise StatusCodeException(u'错误的响应代码 -> %d\n%s' % (r.status_code, url))
            else:
                if self.release_id != '0':
                    self.release_id = '0'
                return r
        except (ChunkedEncodingError, StatusCodeException, ReadTimeout, ConnectTimeout, ProxyError, ConnectionError) as e:
            if t == 15:
                raise e
            else:
                # print 't->', t
                return self.get_request(url, t+1, **kwargs)

    def post_request(self, url, t=0, **kwargs):
        """
        发送post请求,包含添加代理,锁定ip与重试机制
        :param url: 请求的url
        :param t: 重试次数
        :return:
        """
        try:
            if 'timeout' not in kwargs:
                kwargs['timeout'] = self.timeout
            if 'headers' not in kwargs:
                kwargs['headers'] = self.headers
            if self.use_proxy:
                kwargs['headers']['Proxy-Authorization'] = self.proxy_config.get_auth_header(lock_id=self.lock_id, release_id=self.release_id)
            r = self.session.post(url=url, **kwargs)
            if r.status_code != 200:
                self.info(u'错误的响应代码 -> %d\n%s' % (r.status_code, url))
                if self.province in (u'浙江省', u'北京市') and r.status_code == 504:
                    del self.session
                    self.session = requests.session()
                    self.session.proxies = self.proxy_config.get_proxy()
                    raise Exception(u'504错误')
                if r.status_code == 403:
                    if self.use_proxy:
                        if self.lock_id != '0':
                            self.proxy_config.release_lock_id(self.lock_id)
                            self.lock_id = self.proxy_config.get_lock_id()
                            self.release_id = self.lock_id
                    else:
                        raise Exception(u'IP被封')
                raise StatusCodeException(u'错误的响应代码 -> %d\n%s' % (r.status_code, url))
            else:
                if self.release_id != '0':
                    self.release_id = '0'
                return r
        except (ChunkedEncodingError, StatusCodeException, ReadTimeout, ConnectTimeout, ProxyError, ConnectionError) as e:
            if t == 15:
                raise e
            else:
                return self.post_request(url, t+1, **kwargs)

    def get_request_302(self, url, t=0, **kwargs):
        """
        手动处理包含302的请求
        :param url:
        :param t:
        :return:
        """
        try:
            self.get_lock_id()
            # print self.lock_id
            for i in range(10):
                if self.use_proxy:
                    self.headers['Proxy-Authorization'] = self.proxy_config.get_auth_header(lock_id=self.lock_id, release_id=self.release_id)
                r = self.session.get(url=url, headers=self.headers, allow_redirects=False, timeout=self.timeout, **kwargs)
                if r.status_code != 200:
                    if 300 <= r.status_code < 400:
                        self.release_id = '0'
                        protocal, addr = urllib.splittype(url)
                        url = protocal + '://' + urllib.splithost(addr)[0] + r.headers['Location']
                        continue
                    elif self.province in (u'浙江省', u'北京市') and r.status_code == 504:
                        del self.session
                        self.session = requests.session()
                        self.session.proxies = self.proxy_config.get_proxy()
                        raise Exception(u'504错误')
                    elif r.status_code == 403:
                        if self.use_proxy:
                            if self.lock_id != '0':
                                self.proxy_config.release_lock_id(self.lock_id)
                                self.lock_id = self.proxy_config.get_lock_id()
                                self.release_id = self.lock_id
                        else:
                            raise Exception(u'IP被封')
                    raise StatusCodeException(u'错误的响应代码 -> %d' % r.status_code)
                else:
                    if self.release_id != '0':
                        self.release_id = '0'
                    return r
        except (ChunkedEncodingError, StatusCodeException, ReadTimeout, ConnectTimeout, ProxyError, ConnectionError) as e:
            if t == 5:
                raise e
            else:
                return self.get_request_302(url, t+1, **kwargs)

    def post_request_302(self, url, t=0, **kwargs):
        """
        手动处理包含302的请求
        :param url:
        :param t:
        :return:
        """
        try:
            for i in range(10):
                if self.use_proxy:
                    self.headers['Proxy-Authorization'] = self.proxy_config.get_auth_header(lock_id=self.lock_id, release_id=self.release_id)
                r = self.session.post(url=url, headers=self.headers, allow_redirects=False, timeout=self.timeout, **kwargs)
                if r.status_code != 200:
                    if 300 <= r.status_code < 400:
                        protocal, addr = urllib.splittype(url)
                        url = protocal + '://' + urllib.splithost(addr)[0] + r.headers['Location']
                        # print '302 url', url
                        continue
                    elif self.province in (u'浙江省', u'北京市') and r.status_code == 504:
                        del self.session
                        self.session = requests.session()
                        self.session.proxies = self.proxy_config.get_proxy()
                        raise Exception(u'504错误')
                    elif r.status_code == 403:
                        if self.use_proxy:
                            if self.lock_id != '0':
                                self.proxy_config.release_lock_id(self.lock_id)
                                self.lock_id = self.proxy_config.get_lock_id()
                                self.release_id = self.lock_id
                        else:
                            raise Exception(u'IP被封')
                    raise StatusCodeException(u'错误的响应代码 -> %d' % r.status_code)
                else:
                    if self.release_id != '0':
                        self.release_id = '0'
                    return r
        except (ChunkedEncodingError, StatusCodeException, ReadTimeout, ConnectTimeout, ProxyError, ConnectionError) as e:
            if t == 5:
                raise e
            else:
                return self.post_request_302(url, t+1, **kwargs)

    def get_lock_id(self):
        if self.use_proxy:
            self.release_lock_id()
            self.lock_id = self.proxy_config.get_lock_id()
            self.release_id = self.lock_id

    def release_lock_id(self):
        if self.use_proxy and self.lock_id != '0':
            self.proxy_config.release_lock_id(self.lock_id)
            self.lock_id = '0'

    # def get_request_qw(self, url, t=0, **kwargs):
    #     try:
    #         self.session.proxies = self.proxy_qw
    #         r = self.session.get(url=url, headers=self.headers, timeout=self.timeout, **kwargs)
    #         self.session.proxies = {}
    #         if r.status_code != 200:
    #             if self.province == u'浙江省' and r.status_code == 504:
    #                 del self.session
    #                 self.session = requests.session()
    #                 raise ReadTimeout()
    #             if r.status_code == 403:
    #                 raise ReadTimeout()
    #             raise StatusCodeException(u'错误的响应代码 -> %d' % r.status_code)
    #         else:
    #             return r
    #     except StatusCodeException, e:
    #         if t == 15:
    #             raise e
    #         else:
    #             return self.get_request_qw(url, t+1, **kwargs)
    #     except (ReadTimeout, ConnectTimeout, ProxyError, ConnectionError) as e:
    #         if t == 15:
    #             raise e
    #         else:
    #             self.reset_proxy_qw()
    #             return self.get_request_qw(url, t+1, **kwargs)
    #
    # def post_request_qw(self, url, t=0, **kwargs):
    #     try:
    #         self.session.proxies = self.proxy_qw
    #         r = self.session.post(url=url, headers=self.headers, timeout=self.timeout, **kwargs)
    #         self.session.proxies = {}
    #         if r.status_code != 200:
    #             if self.province == u'浙江省' and r.status_code == 504:
    #                 del self.session
    #                 self.session = requests.session()
    #                 raise ReadTimeout()
    #             if r.status_code == 403:
    #                 raise ReadTimeout()
    #             raise StatusCodeException(u'错误的响应代码 -> %d' % r.status_code)
    #         else:
    #             return r
    #     except StatusCodeException, e:
    #         if t == 15:
    #             raise e
    #         else:
    #             return self.get_request_qw(url, t+1, **kwargs)
    #     except (ReadTimeout, ConnectTimeout, ProxyError, ConnectionError) as e:
    #         if t == 15:
    #             raise e
    #         else:
    #             self.reset_proxy_qw()
    #             return self.post_request_qw(url, t+1, **kwargs)
    #
    # def reset_proxy_qw(self, force_change=True):
    #     ts = long(time.time())
    #     if ts - self.proxy_last_update_ts > 50 or force_change:
    #         proxy = get_proxy()
    #         self.proxy_qw = {'http': proxy, 'https': proxy}
    #         # self.session.proxies = {'http': proxy, 'https': proxy}
    #         self.proxy_last_update_ts = long(time.time())


def save_dead_company(company_name):
    """
    将查询无结果的公司名保存, 下次不做更新
    :param company_name:
    :return:
    """
    sql_1 = "select * from GsSrc.dbo.dead_company where company_name='%s'" % company_name
    res_1 = MSSQL.execute_query(sql_1)
    if len(res_1) == 0:
        sql_2 = "insert into GsSrc.dbo.dead_company values('%s',getdate())" % company_name
        MSSQL.execute_update(sql_2)


def get_args():
    args = dict()
    for arg in sys.argv:
        kv = arg.split('=')
        if kv[0] == 'companyName':
            args['companyName'] = kv[1].decode(sys.stdin.encoding, 'ignore')
        elif kv[0] == 'taskId':
            args['taskId'] = kv[1].decode(sys.stdin.encoding, 'ignore')
        elif kv[0] == 'accountId':
            args['accountId'] = kv[1].decode(sys.stdin.encoding, 'ignore')
    return args


if __name__ == '__main__':
    # s = Searcher(True)
    # s.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:45.0) Gecko/20100101 Firefox/45.0",
    #                     "Host": "gxqyxygs.gov.cn",
    #                     "Accept": "*/*",
    #                     "Accept-Encoding": "gzip, deflate",
    #                     "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
    #                     "Referer": "http://gxqyxygs.gov.cn/search.jspx",
    #                     "Connection": "keep-alive",
    #                     "Cache-Control": "max-age=0",
    #                     }
    # # params = {'service': 'entInfo_oLH5KpqW8lj+tLzyGDoJ78OiZSSMvqUtEi13CAadOu8OV9SV9DvKUE9IxHt1Fll/-RMXe+ha3MQ6iGFT4oBCmPA=='}
    # r = s.get_request('http://wenshu.court.gov.cn/')
    # print r.status_code
    # # print r.text
    a = """GsSrc10
    GsSrc11
    GsSrc12
    GsSrc13
    GsSrc14
    GsSrc15
    GsSrc21
    GsSrc22
    GsSrc23
    GsSrc31
    GsSrc32
    GsSrc33
    GsSrc34
    GsSrc35
    GsSrc36
    GsSrc37
    GsSrc41
    GsSrc42
    GsSrc43
    GsSrc44
    GsSrc45
    GsSrc46
    GsSrc50
    GsSrc51
    GsSrc52
    GsSrc53
    GsSrc54
    GsSrc61
    GsSrc62
    GsSrc63
    GsSrc64
    GsSrc65
    """
    for i in (a.split('\n')):
        i = i.strip()
        sql = "select count(*) from %s where update_status='-1'" % i
        # print sql
        res = MSSQL.execute_query(sql)
        print i, res[0][0]
