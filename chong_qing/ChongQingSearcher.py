# coding=utf-8
import PackageTool
from gs.Searcher import Searcher
from gs.Searcher import get_args
from gs import MSSQL
import requests
from PIL import Image
import time
import os
import sys
import re
import random
import subprocess
from bs4 import BeautifulSoup
from TableConfig import *
from gs.KafkaAPI import KafkaAPI
from gs.TimeUtils import get_cur_time
import json
from requests.exceptions import RequestException
import uuid
reload(sys)
sys.setdefaultencoding('utf-8')

class ChongQingSearcher(Searcher):
	load_func_dict = {}
	load_yearreport_dict = {}
	lock_id = 0
	year = []
	entid = None
	dataid = None
	datatype = None
	search_type = None

	def __init__(self):
		super(ChongQingSearcher, self).__init__(use_proxy=False)
		self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:45.0) Gecko/20100101 Firefox/45.0",
						"Host": "cq.gsxt.gov.cn",
						"Accept": "*/*",
						"Accept-Encoding": "gzip, deflate",
						"Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
						# "Referer": "http://gsxt.cqgs.gov.cn/search_research.action",
						"Cache-Control": "no-cache",
						"Pragma": "no-cache",
						"X-Requested-With": "XMLHttpRequest",
						"Connection": "keep-alive",
                        "appkey": "8dc7959eeee2792ac2eebb490e60deed"
						}
		self.set_config()
		self.log_name = self.topic + "_" + str(uuid.uuid1())

	def set_config(self):
		self.plugin_path = os.path.join(sys.path[0], '../chong_qing/ocr/chongqing/chongqing.bat')
		# self.group = 'Crawler'  # 正式
		# self.kafka = KafkaAPI("GSCrawlerResult")  # 正式
		self.group = 'CrawlerTest'  # 测试
		self.kafka = KafkaAPI("GSCrawlerTest")  # 测试
		self.topic = 'GsSrc50'
		self.province = u'重庆市'
		self.kafka.init_producer()

	def download_yzm(self):
		image_url = 'http://gsxt.cqgs.gov.cn/sc.action'
		params = {'fs': '23', 'height': '40', 'width': '130'}
		r = self.get_request(url=image_url,params=params)
		yzm_path = self.get_yzm_path()
		with open(yzm_path, 'wb') as f:
			for chunk in r.iter_content(chunk_size=1024):
				if chunk:  # filter out keep-alive new chunks
					f.write(chunk)
					f.flush()
			f.close()
		return yzm_path

	def get_tag_a_from_page(self, keyword):
		url = 'http://gsxt.cqgs.gov.cn/search_research.action'
		for t in range(20):
			yzm = self.get_yzm()
			params = {'key': keyword, 'code': yzm}
			r = self.post_request(url=url, params=params)
			if u'验证码不正确' in r.text:
				continue
			elif u'您搜索的条件无查询结果' in r.text:
				return None
			else:
				search_result_json = {}
				html_list = r.text.split('<html>')
				html_text = '<html>' + html_list[2]
				soup = BeautifulSoup(html_text, 'lxml')
				# print '*** %d' % r.status_code
				search_result_text = soup.select('div#result > div > a')[0].attrs['data-entid']
				if search_result_text != u'':
					self.cur_mc = soup.select('div#result > div > a')[0].text.strip()
					self.cur_zch = soup.select('div#result > div > span > span')[0].text.strip()
					dataid = soup.select('div#result > div > a')[0].attrs['data-id']
					datatype = soup.select('div#result > div > a')[0].attrs['data-type']
					search_result_json['entname'] = self.cur_mc
					search_result_json['regno'] = self.cur_zch
					search_result_json['entid'] = search_result_text
					search_result_json['dataid'] = dataid
					search_result_json['datatype'] = datatype
					tag_a = json.dumps(search_result_json, ensure_ascii=False)
					return tag_a

	def get_search_args(self, tag_a, keyword):
		# print 'tag_a:', type(tag_a), tag_a
		tag = json.loads(tag_a)
		if tag['datatype'].encode('utf-8') != '1001':
			self.ent_type = '/1'
		elif tag['datatype'].encode('utf-8') == '1001':
			self.ent_type = '/8'
		self.entid = tag['entid']
		self.dataid = None
		self.datatype = None
		search_result_json = json.loads(tag_a)
		if search_result_json.get('entname', None) == keyword:
			self.entid = search_result_json['entid']
			self.dataid = search_result_json['dataid']
			self.datatype = search_result_json['datatype']
			self.cur_mc = search_result_json['entname'].replace('(', u'（').replace(')', u'）')  # 公司名称括号统一转成全角
			self.cur_zch = search_result_json['regno']
			return 1
		else:
			return 0

	def get_search_type(self):
		ur = 'http://gsxt.cqgs.gov.cn/search_ent'
		para = {'entId': self.entid,'id':self.dataid,'type':self.datatype,'name':self.cur_mc}
		rq = self.get_request(url=ur, params=para)
		search_ent = rq.text
		self.search_type = search_ent[search_ent.index('type=')+len('type='):search_ent.index('name')].replace('\'','').replace(';','')

	def parse_detail(self):
		"""
		解析公司详情信息
		:param kwargs:
		:return:
		"""
		# self.get_ji_ben()
		self.get_gu_dong()
		self.get_bian_geng()
		self.get_zhu_yao_ren_yuan()
		# self.get_fen_zhi_ji_gou()
		self.get_dong_chan_di_ya()
		self.get_gu_quan_chu_zhi()
		self.get_chou_cha_jian_cha()
		self.get_xing_zheng_chu_fa()
		self.get_jing_ying_yi_chang()

	def get_ji_ben(self):
		"""
		查询基本信息
		:return: 基本信息结果
		"""
		self.info(u'解析基本信息...')
		family = 'Registered_Info'
		table_id = '01'
		self.json_result[family] = []
		self.json_result[family].append({})
		# host = 'http://cq.gsxt.gov.cn/gsxt/api/ebaseindex/queryForm/'
		# url = host + self.tag_a['entid'] + str(long(time.time()*1000))
		# print "url:", url
		host = 'http://cq.gsxt.gov.cn/gsxt/api/ebaseindex/queryForm/'
		entid = self.entid
		other ='?currentpage=1&pagesize=5&t='
		sj = str(long(time.time()*1000))
		url = host+entid+self.ent_type+other+sj
		r = requests.get(url, headers=self.headers)
		jiben_detail = r.text
		content = jiben_detail.encode('utf-8').replace("\n", '').replace("\r\n", '').replace("\r\n", '')
		# print "content", content
		result_text = json.loads(content)
		result_json = result_text[0]['form1']
		# print "result_json", result_json
		for j in result_json:
			if j in ji_ben_dict:
				col = family + ':' + ji_ben_dict[j]
				val = result_json[j]
				self.json_result[family][-1][col] = val
			if j =='entname':
				self.cur_mc = result_json[j]
			if j == 'uniscid':
				self.cur_zch = result_json[j]
		host = 'http://cq.gsxt.gov.cn/gsxt/api/ebaseinfo/queryForm/'
		entid = self.entid
		other ='?currentpage=1&pagesize=5&t='
		sj = str(long(time.time()*1000))
		url_2 = host+entid+self.ent_type+other+sj
		r = requests.get(url_2, headers=self.headers)
		jiben_comtent = r.text
		content = jiben_comtent.encode('utf-8').replace("\n", '').replace("\r\n", '').replace("\r\n", '')
		# print "content", content
		result_text = json.loads(content)
		result_json = result_text[0]['form']
		# print "result_json", result_json
		for j in result_json:
			if j in ji_ben_dict:
				col = family + ':' + ji_ben_dict[j]
				val = result_json[j]
				self.json_result[family][-1][col] = val
			if result_json['regcap']:
				self.json_result[family][-1]['Registered_Info:registeredcapital'] = result_json['regcap'] + u'(万元)'
		self.json_result[family][-1]['rowkey'] = '%s_%s_%s_' % (self.cur_mc, table_id, self.cur_zch)
		self.json_result[family][-1][family + ':registrationno'] = self.cur_zch
		self.json_result[family][-1][family + ':enterprisename'] = self.cur_mc
		self.json_result[family][-1][family + ':province'] = self.province
		self.json_result[family][-1][family + ':lastupdatetime'] = get_cur_time()
		# print json.dumps(self.json_result[family], ensure_ascii=False)

	def get_gu_dong(self):
		"""
		查询股东信息
		:param table_element:
		:return:
		"""
		self.info(u'解析股东信息...')
		family = 'Shareholder_Info'
		table_id = '04'
		self.json_result[family] = []
		host = 'http://cq.gsxt.gov.cn/gsxt/api/einv/gdjczxxList/'
		entid = self.entid
		other ='?currentpage=1&pagesize=5&t='
		sj = str(long(time.time()*1000))
		url = host+entid+self.ent_type+other+sj
		r = requests.get(url, headers=self.headers)
		gudong_detail = r.text
		start_idx = gudong_detail.index('st":')
		stop_idx = gudong_detail.index(']')
		result_text = gudong_detail[start_idx+4:stop_idx+1]
		result_text = result_text.encode("utf-8").replace("  ", '').replace("\n", '').replace("\r\n", '').replace("\r", '')
		# print 'result_text:', result_text
		result_json = json.loads(result_text.decode('utf-8'))
		for j in result_json:
			self.json_result[family].append({})
			for k in j:
				if k in gu_dong_dict:
					col = family + ':' + gu_dong_dict[k]
					val = j[k]
					self.json_result[family][-1][col] = val
			if j['invid']:
				detail_host = 'http://cq.gsxt.gov.cn/gsxt/api/einv/gdxx/'
				detail_entid = j['invid']
				detail_other = '?currentpage=1&pagesize=5&t='
				detail_sj = str(long(time.time()*1000))
				url = detail_host+detail_entid+detail_other+detail_sj
				# print "url", url
				r = requests.get(url, headers=self.headers)
				gudong_detail = r.text
				# print "gudong_detail", gudong_detail
				start_idx = gudong_detail.index('rm":')
				stop_idx = gudong_detail.index('}')
				result_text = gudong_detail[start_idx+4:stop_idx+1]
				result_json = json.loads(result_text.decode('utf-8'))
				for p in result_json:
					col = family + ':' + gu_dong_dict[p]
					val = result_json[p]
					self.json_result[family][-1][col] = val
					if result_json['lisubconam']:
						self.json_result[family][-1]['Shareholder_Info:subscripted_capital'] = \
							result_json['lisubconam'] + u'(万元)'
					if result_json['liacconam']:
						self.json_result[family][-1]['Shareholder_Info:actualpaid_capital'] = \
							result_json['liacconam'] + u'(万元)'
				renjiao_host = 'http://cq.gsxt.gov.cn/gsxt/api/einvpaidin/queryList/'
				renjiao_entid = j['invid']
				renjiao_other = '?currentpage=1&pagesize=5&t='
				renjiao_sj = str(long(time.time()*1000))
				url = renjiao_host+renjiao_entid+renjiao_other+renjiao_sj
				r = requests.get(url, headers=self.headers)
				renjiao_detail = r.text
				renjiao_list = []
				renjiao_dict = {}
				start_idx = renjiao_detail.index('st":')
				stop_idx = renjiao_detail.index(']')
				result_text = renjiao_detail[start_idx+4:stop_idx+1]
				result_text = result_text.encode("utf-8").replace("  ", '').replace("\n", '').replace("\r\n", '').replace("\r", '')
				result_json = json.loads(result_text)
				for f in result_json:
					renjiao_list.append({})
					for g in f:
						if g in gu_dong_renjiao_dict:
							col = family + ':' + gu_dong_renjiao_dict[g]
							val = f[g]
							# self.json_result[family][-1][col] = val
							renjiao_dict[col] = val
							if f['subconam']:
								renjiao_dict['Shareholder_Info:subscripted_amount'] = f['subconam'] + u'(万元)'
				# print "renjiao_dict:", renjiao_dict
				self.json_result[family][-1].update(renjiao_dict)
				shijiao_host = 'http://cq.gsxt.gov.cn/gsxt/api/efactcontribution/queryList/'
				shijiao_entid = j['invid']
				shijiao_other ='?currentpage=1&pagesize=5&t='
				shijiao_sj = str(long(time.time()*1000))
				url = shijiao_host+shijiao_entid+shijiao_other+shijiao_sj
				r = requests.get(url, headers=self.headers)
				shijiao_detail = r.text
				shijiao_list = []
				shijiao_dict = {}
				start_idx = shijiao_detail.index('st":')
				stop_idx = shijiao_detail.index(']')
				result_text = shijiao_detail[start_idx+4:stop_idx+1]
				result_text = result_text.encode("utf-8").replace("  ", '').replace("\n", '').replace("\r\n", '').replace("\r", '')
				result_json = json.loads(result_text)
				for n in result_json:
					shijiao_list.append({})
					for m in n:
						if m in gu_dong_shijiao_dict:
							col = family + ':' + gu_dong_shijiao_dict[m]
							val = n[m]
							shijiao_dict[col] = val
							if n['acconam']:
								shijiao_dict['Shareholder_Info:actualpaid_amount'] = n['acconam'] + u'(万元)'
				# print "shijiao_dict:", shijiao_dict
				self.json_result[family][-1].update(shijiao_dict)
		for i in range(len(self.json_result[family])):
			self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
			self.json_result[family][i][family + ':registrationno'] = self.cur_zch
			self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
			self.json_result[family][i][family + ':id'] = self.today+str(i+1)
			# print json.dumps(self.json_result[family][i], ensure_ascii=False)
		# print json.dumps(self.json_result[family], ensure_ascii=False)

	def get_gu_dong_detail(self, id,table_element):
		detail_dict_list = []
		url = 'http://222.143.24.157/queryInvDetailAction.jspx'
		params = {'id': id, 'ad_cheak': '1'}
		r = self.get_request(url=url, params=params)
		soup = BeautifulSoup(r.text, 'lxml')
		table_element=soup.find('table')
		th_element_list=table_element.select('th')[2:]
		tr_element_list=table_element.select('tr')[3:]
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
					j = j-2
				col = gu_dong_dict[col_dec]
				td = td_element_list[j]
				val = td.text.strip()
				detail_dict_list[-1][col] = val
		# print json.dumps(detail_dict_list, ensure_ascii=False)
		return detail_dict_list

	def get_tou_zi_ren(self, param_corpid, table_element):
		pass

	def get_bian_geng(self):
		"""
		查询变更信息
		:param param_entid:
		:return:
		"""
		family = 'Changed_Announcement'
		table_id = '05'
		self.json_result[family] = []
		bg_host = 'http://cq.gsxt.gov.cn/gsxt/api/ealterrecoder/queryList/'
		bg_entid = self.entid
		bg_other ='?currentpage=1&pagesize=5&t='
		bg_sj = str(long(time.time()*1000))
		url = bg_host+bg_entid+self.ent_type+bg_other+bg_sj
		r = requests.get(url, headers=self.headers)
		bg_detail = r.text
		start_idx = bg_detail.index('st":')
		stop_idx = bg_detail.index(']')
		result_text = bg_detail[start_idx+4:stop_idx+1]
		result_text = result_text.encode("utf-8").replace("  ", '').replace("\n", '').replace("\r\n", '').replace("\r", '')
		# print 'result_text:', result_text
		result_json = json.loads(result_text.decode('utf-8'))
		for j in result_json:
			self.json_result[family].append({})
			for k in j:
				if k in bian_geng_dict:
					col = family + ':' + bian_geng_dict[k]
					val = j[k]
					self.json_result[family][-1][col] = val
		for i in range(len(self.json_result[family])):
			self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
			self.json_result[family][i][family + ':registrationno'] = self.cur_zch
			self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
			self.json_result[family][i][family + ':id'] = i+1
			# print json.dumps(self.json_result[family][i], ensure_ascii=False)

	def get_zhu_yao_ren_yuan(self):
		"""
		查询主要人员信息
		:param param_id:
		:return:
		"""
		self.info(u'解析主要人员信息...')
		family = 'KeyPerson_Info'
		table_id = '06'
		self.json_result[family] = []
		zzyr_host = 'http://cq.gsxt.gov.cn/gsxt/api/epriperson/queryList/'
		zzyr_entid = self.entid
		zzyr_other ='?currentpage=1&pagesize=5&t='
		zzyr_sj = str(long(time.time()*1000))
		url = zzyr_host+zzyr_entid+self.ent_type+zzyr_other+zzyr_sj
		r = requests.get(url, headers=self.headers)
		# print 'url:',url
		zzyr_detail = r.text
		start_idx = zzyr_detail.index(':[')
		stop_idx = zzyr_detail.index(']')
		result_text = zzyr_detail[start_idx+2:stop_idx+1]
		result_text = result_text.encode("utf-8").replace("  ", '').replace("\n", '').replace("\r\n", '').replace("\r", '')
		# print 'result_text:', type(result_text), result_text
		result_json = json.loads(result_text.decode('utf-8'))
		for j in result_json:
			self.json_result[family].append({})
			for k in j:
				if k in zhu_yao_ren_yuan_dict:
					col = family + ':' + zhu_yao_ren_yuan_dict[k]
					val = j[k]
					self.json_result[family][-1][col] = val
		for i in range(len(self.json_result[family])):
			self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
			self.json_result[family][i][family + ':registrationno'] = self.cur_zch
			self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
			self.json_result[family][i][family + ':id'] = i+1
			# print json.dumps(self.json_result[family][i], ensure_ascii=False)

	def get_fen_zhi_ji_gou(self):
		"""
		查询分支机构信息
		:param param_id:
		:return:
		"""
		family = 'Branches'
		table_id = '08'
		self.json_result[family] = []
		for j in table_detail:
			self.json_result[family].append({})
			for k in j:
				if k in fen_zhi_ji_gou_dict:
					col = family + ':' + fen_zhi_ji_gou_dict[k]
					val = j[k]
					self.json_result[family][-1][col] = val
		for i in range(len(self.json_result[family])):
			self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
			self.json_result[family][i][family + ':registrationno'] = self.cur_zch
			self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
			self.json_result[family][i][family + ':id'] = i+1
			# print json.dumps(self.json_result[family][i], ensure_ascii=False)

	def get_qing_suan(self, table_detail):
		"""
		查询清算信息
		:param param_entid:
		:param table_detail:
		:return:
		"""
		family = 'liquidation_Information'
		table_id = '09'
		self.json_result[family] = []
		for j in table_detail:
			self.json_result[family].append({})
			for k in j:
				if k in qing_suan_dict:
					col = family + ':' + qing_suan_dict[k]
					val = j[k]
					self.json_result[family][-1][col] = val
		for i in range(len(self.json_result[family])):
			self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
			self.json_result[family][i][family + ':registrationno'] = self.cur_zch
			self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
			self.json_result[family][i][family + ':id'] = i+1
			# print json.dumps(self.json_result[family][i], ensure_ascii=False)

	def get_dong_chan_di_ya(self):
		"""
		查询动产抵押信息
		:param param_corpid:
		:return:
		"""
		self.info(u'解析动产抵押信息...')
		family = 'Chattel_Mortgage'
		table_id = '11'
		self.json_result[family] = []
		dcdy_host = 'http://cq.gsxt.gov.cn/gsxt/api/mortreginfo/queryList/'
		dcdy_entid = self.entid
		dcdy_other = '?currentpage=1&pagesize=5&t='
		dcdy_sj = str(long(time.time()*1000))
		url = dcdy_host+dcdy_entid+self.ent_type+dcdy_other+dcdy_sj
		r = requests.get(url, headers=self.headers)
		dcdy_detail = r.text
		start_idx = dcdy_detail.index('st":')
		stop_idx = dcdy_detail.index(']')
		result_text = dcdy_detail[start_idx+4:stop_idx+1]
		result_text = result_text.encode("utf-8").replace("  ", '').replace("\n", '').replace("\r\n", '').replace("\r", '')
		# print 'result_text:', result_text
		result_json = json.loads(result_text.decode('utf-8'))
		for j in result_json:
			self.json_result[family].append({})
			for k in j:
				if k in dong_chan_di_ya_dict:
					col = family + ':' + dong_chan_di_ya_dict[k]
					val = j[k]
					self.json_result[family][-1][col] = val
				if j['priclasecam']:
					self.json_result[family][-1]['Chattel_Mortgage:chattelmortgage_guaranteedamount'] = \
					j['priclasecam'] + u'万元'
				if j['type'] == '1':
					self.json_result[family][-1]['Chattel_Mortgage:chattelmortgage_status'] = u'有效'
				elif j['type'] == '2':
					self.json_result[family][-1]['Chattel_Mortgage:chattelmortgage_status'] = u'无效'
		for i in range(len(self.json_result[family])):
			self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
			self.json_result[family][i][family + ':registrationno'] = self.cur_zch
			self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
			self.json_result[family][i][family + ':id'] = i+1
			# print json.dumps(self.json_result[family][i], ensure_ascii=False)

	def get_gu_quan_chu_zhi(self):
		"""
		查询动产抵押信息
		:param param_entid:
		:return:
		"""
		self.info(u'解析股权出质信息...')
		family = 'Equity_Pledge'
		table_id = '13'
		self.json_result[family] = []
		gqcz_host = 'http://cq.gsxt.gov.cn/gsxt/api/esppledge/queryList/'
		gqcz_entid = self.entid
		gqcz_other ='?currentpage=1&pagesize=5&t='
		gqcz_sj = str(long(time.time()*1000))
		url = gqcz_host+gqcz_entid+self.ent_type+gqcz_other+gqcz_sj
		r = requests.get(url, headers=self.headers)
		gqcz_detail = r.text
		start_idx = gqcz_detail.index('st":')
		stop_idx = gqcz_detail.index(']')
		result_text = gqcz_detail[start_idx+4:stop_idx+1]
		result_text = result_text.encode("utf-8").replace("  ", '').replace("\n", '').replace("\r\n", '').replace("\r", '')
		# print 'result_text:', result_text
		result_json = json.loads(result_text.decode('utf-8'))
		for j in result_json:
			self.json_result[family].append({})
			for k in j:
				if k in gu_quan_chu_zhi_dict:
					col = family + ':' + gu_quan_chu_zhi_dict[k]
					val = j[k]
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
		:param param_corpid:
		:return:
		"""
		family = 'Administrative_Penalty'
		table_id = '13'
		self.json_result[family] = []
		xzcf_host = 'http://cq.gsxt.gov.cn/gsxt/api/casepubbaseinfo/queryList/'
		xzcf_entid = self.entid
		xzcf_other ='?currentpage=1&pagesize=5&t='
		xzcf_sj = str(long(time.time()*1000))
		url = xzcf_host+xzcf_entid+self.ent_type+xzcf_other+xzcf_sj
		r = requests.get(url, headers=self.headers)
		xzcf_detail = r.text
		start_idx = xzcf_detail.index('st":')
		stop_idx = xzcf_detail.index(']')
		result_text = xzcf_detail[start_idx+4:stop_idx+1]
		result_text = result_text.encode("utf-8").replace("  ", '').replace("\n", '').replace("\r\n", '').replace("\r", '')
		# print 'result_text:', result_text
		result_json = json.loads(result_text.decode('utf-8'))
		for j in result_json:
			self.json_result[family].append({})
			for k in j:
				if k in xing_zheng_chu_fa_dict:
					col = family + ':' + xing_zheng_chu_fa_dict[k]
					val = j[k]
					# print "val:", type(val), val
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
		:param param_entid:
		:return:
		"""
		family = 'Business_Abnormal'
		table_id = '14'
		self.json_result[family] = []
		jyyc_host = 'http://cq.gsxt.gov.cn/gsxt/api/aoopadetail/queryList/'
		jyyc_entid = self.entid
		jyyc_other ='?currentpage=1&pagesize=5&t='
		jyyc_sj = str(long(time.time()*1000))
		url = jyyc_host+jyyc_entid+self.ent_type+jyyc_other+jyyc_sj
		r = requests.get(url, headers=self.headers)
		jyyc_detail = r.text
		start_idx = jyyc_detail.index('st":')
		stop_idx = jyyc_detail.index(']')
		result_text = jyyc_detail[start_idx+4:stop_idx+1]
		result_text = result_text.encode("utf-8").replace("  ", '').replace("\n", '').replace("\r\n", '').replace("\r", '')
		# print 'result_text:', result_text
		result_json = json.loads(result_text.decode('utf-8'))
		for j in result_json:
			self.json_result[family].append({})
			for k in j:
				if k in jing_ying_yi_chang_dict:
					col = family + ':' + jing_ying_yi_chang_dict[k]
					val = j[k]
					self.json_result[family][-1][col] = val
		for i in range(len(self.json_result[family])):
			self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
			self.json_result[family][i][family + ':registrationno'] = self.cur_zch
			self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
			self.json_result[family][i][family + ':id'] = i+1
			# print json.dumps( self.json_result[family][i], ensure_ascii=False)

	def get_yan_zhong_wei_fa(self, table_detail):
		"""
		查询严重违法信息
		:param param_corpid:
		:param table_element:
		:return:
		"""
		family = 'Serious_Violations'
		table_id = '15'
		self.json_result[family] = []
		for j in table_detail:
			self.json_result[family].append({})
			for k in j:
				if k in yan_zhong_wei_fa_dict:
					col = family + ':' + yan_zhong_wei_fa_dict[k]
					val = j[k]
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
		:param param_entid:
		:return:
		"""
		family = 'Spot_Check'
		table_id = '16'
		self.json_result[family] = []
		ccjc_host = 'http://cq.gsxt.gov.cn/gsxt/api/epubspotcheck/queryList/'
		ccjc_entid = self.entid
		ccjc_other ='?currentpage=1&pagesize=5&t='
		ccjc_sj = str(long(time.time()*1000))
		url = ccjc_host+ccjc_entid+self.ent_type+ccjc_other+ccjc_sj
		r = requests.get(url, headers=self.headers)
		ccjc_detail = r.text
		start_idx = ccjc_detail.index('st":')
		stop_idx = ccjc_detail.index(']')
		result_text = ccjc_detail[start_idx+4:stop_idx+1]
		result_text = result_text.encode("utf-8").replace("  ", '').replace("\n", '').replace("\r\n", '').replace("\r", '')
		# print 'result_text:', result_text
		result_json = json.loads(result_text.decode('utf-8'))
		for j in result_json:
			self.json_result[family].append({})
			for k in j:
				if k in chou_cha_jian_cha_dict:
					col = family + ':' + chou_cha_jian_cha_dict[k]
					val = j[k]
					self.json_result[family][-1][col] = val
		for i in range(len(self.json_result[family])):
			self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
			self.json_result[family][i][family + ':registrationno'] = self.cur_zch
			self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
			self.json_result[family][i][family + ':id'] = i+1
			# print json.dumps(self.json_result[family][i], ensure_ascii=False)


if __name__ == '__main__':
	args_dict = get_args()
	# args_dict = {'companyName': u'重庆浅墨贸易有限公司', 'accountId': '123', 'taskId': '456'}
	searcher = ChongQingSearcher()
	searcher.submit_search_request(u'重庆山象胶业有限公司')
# 	print json.dumps(searcher.json_result, ensure_ascii=False)
