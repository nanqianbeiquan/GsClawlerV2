# coding=utf-8
import PackageTool
from gs.Searcher import Searcher
from gs.Searcher import get_args
from gs import MSSQL
import requests
from PIL import Image
import os
import sys
import re
import uuid
import random
import subprocess
from bs4 import BeautifulSoup
from TableConfig import *
from gs.KafkaAPI import KafkaAPI
from gs.TimeUtils import get_cur_time
import json
from requests.exceptions import RequestException


class HeNanSearcher(Searcher):
	load_func_dict = {}
	lock_id = 0

	def __init__(self):

		super(HeNanSearcher, self).__init__(use_proxy=False)
		self.headers = {"Accept": "*/*",
						"Accept-Encoding": "gzip, deflate",
						"Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
						"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
						"Referer": "http://222.143.24.157/searchList.jspx",
						"Host": "222.143.24.157",
						"Connection": "keep-alive",
						"User-Agent":"Mozilla/5.0 (Windows NT 6.3; WOW64; rv:45.0) Gecko/20100101 Firefox/45.0",
						"X-Requested-With": "XMLHttpRequest"
						}
		self.set_config()
		self.log_name = self.topic + "_" + str(uuid.uuid1())

	def set_config(self):
		self.plugin_path = os.path.join(sys.path[0], '../he_nan/ocr/pinyin/pinyin.bat')
		self.list_path = os.path.join(sys.path[0], '../he_nan/Data/company')
		self.group = 'Crawler'  # 正式
		self.kafka = KafkaAPI("GSCrawlerResult")  # 正式
		# self.group = 'CrawlerTest'  # 测试
		# self.kafka = KafkaAPI("GSCrawlerTest")  # 测试
		self.topic = 'GsSrc41'
		self.province = u'河南省'
		self.kafka.init_producer()
		self.session = requests.session()

	def download_yzm(self):
		image_url = 'http://222.143.24.157/validateCode.jspx'
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
		url = 'http://222.143.24.157/queryListData.jspx'
		params = {'currentPageIndex': '1', 'entName': keyword, 'searchType': '1'}
		r = self.session.post(url=url, data=params)
		# print '&&&r.text&&&', r.text
		soup = BeautifulSoup(r.text, 'lxml')
		try:
			tag_a = soup.find('div').attrs['data-label']
			regno_1 = soup.find(class_='tongyi').text.strip()
			regno = regno_1.encode("utf-8").split('：')[1]
			self.cur_mc = soup.find(class_='gggscpnametitle').contents[0].replace('(', u'（').replace(')', u'）').strip()
			if flags:
				if keyword == self.cur_mc:
					self.cur_zch = soup.find(class_='tongyi').text.strip()
					return tag_a
			elif keyword == regno:
				self.cur_mc = keyword
				self.cur_zch = soup.find(class_='tongyi').text.strip()
				return tag_a
		except:
			return None

	def get_search_args(self, tag_a, keyword):
		"""
		:param tag_a:
		:param keyword:
		:return:
		"""
		self.tag_a = tag_a
		if tag_a:
			return 1
		else:
			return 0
		self.parse_detail(self)

	def parse_detail(self):
		"""
		解析公司详情信息
		:param tag_a:
		:return:
		"""
		tag_a = self.tag_a
		self.get_ji_ben(tag_a)
		# result = self.get_ji_ben(tag_a)
		if self.json_result['Registered_Info']:
			self.get_gu_dong(tag_a)
			self.get_bian_geng(tag_a)
			self.get_qing_suan(tag_a)
			self.get_zhu_yao_ren_yuan(tag_a)
			self.get_fen_zhi_ji_gou(tag_a)
			self.get_dong_chan_di_ya(tag_a)
			self.get_xing_zheng_chu_fa(tag_a)
			self.get_gu_quan_chu_zhi(tag_a)
			self.get_jing_ying_yi_chang(tag_a)
			self.get_chou_cha_jian_cha(tag_a)
		else:
			return None

	def get_ji_ben(self, tag_a):
		"""
		查询基本信息
		:param tag_a:
		:return: 基本信息结果
		"""
		self.info(u'解析基本信息...')
		family = 'Registered_Info'
		table_id = '01'
		self.json_result[family] = []
		result_json = [{}]
		url = 'http://222.143.24.157/business/YYZZ.jspx?id='+tag_a
		params = {'id': tag_a}
		r = self.get_request(url, data=params, headers=self.headers)
		r.encoding = 'utf-8'
		soup = BeautifulSoup(r.text, 'lxml')
		table_element = soup.find(id='zhizhao')
		tr_list = table_element.find_all('tr')
		if tr_list:
			for tr in tr_list:
				td_list = tr.find_all('td')
				for td in td_list:
					col_1 = td.text.replace(u'·', '').strip()
					col = col_1.split(u'：')[0].strip()
					val = td.find('span').text.strip()
					# print 'col', col, val
					if u'统一社会信用代码' in col and len(val) == 18:
						result_json[0][u'社会信用代码'] = val
						result_json[0][u'注册号码'] = ''
					if u'统一社会信用代码' in col and len(val) != 18:
						result_json[0][u'社会信用代码'] = ''
						result_json[0][u'注册号码'] = val
					result_json[0][col] = val
			for j in result_json:
				self.json_result[family].append({})
				for k in j:
					col = jiben_column_dict[k]
					val = j[k]
					self.json_result[family][-1][col] = val
		else:
			return None
		self.cur_mc = self.json_result[family][-1]['Registered_Info:enterprisename']
		self.cur_zch = self.json_result[family][-1]['Registered_Info:registrationno']
		self.json_result[family][-1]['rowkey'] = '%s_%s_%s_' % (self.cur_mc, table_id, self.cur_zch)
		self.json_result[family][-1][family + ':registrationno'] = self.cur_zch
		self.json_result[family][-1][family + ':enterprisename'] = self.cur_mc
		self.json_result[family][-1][family + ':province'] = self.province
		self.json_result[family][-1][family + ':lastupdatetime'] = get_cur_time()
		# print json.dumps(self.json_result[family], ensure_ascii=False)

	def get_gu_dong(self, tag_a):
		"""
		查询股东信息
		:param tag_a:
		:return:
		"""
		self.info(u'解析股东信息...')
		url = 'http://222.143.24.157/business/GDCZ.jspx?id='+tag_a+'&ad_check=1'
		r = self.get_request(url=url)
		# print r.text
		soup = BeautifulSoup(r.text, 'lxml')
		th_element_list = soup.find_all(class_='detailsList')[0].find_all('th')
		pages = soup.find(id='paging').find(class_='ax_image fenye').find_all('li')[1].text.strip()
		page = int(re.search(r'\d', pages).group())
		nums = soup.find(id='paging').find(class_='ax_image fenye').find_all('li')[0].text.strip()
		num = int(re.search(r'\d', nums).group())
		table_describ = soup.find(class_='text mainPerText').find('span').text.strip().replace('\n','')
		table_des = table_describ.split('&')[0]
		if table_des == u'股东及出资信息' or table_des == u'发起人及出资信息':
			family = 'Shareholder_Info'
			table_id = '04'
		elif table_des == u'合伙人及出资信息':
			family = 'Partner_Info'
			table_id = '03'
		elif table_des == u'主管部门(出资人)信息':
			family = 'DIC_Info'
			table_id = '10'
		self.json_result[family] = []
		if num == 0:
			pass
		else:
			for i in range(page):
				url = 'http://222.143.24.157/business/QueryInvList.jspx'
				params = {'mainId': tag_a, 'order': 0, 'pno': '%s' % (i+1)}
				r = self.get_request(url=url, params=params)
				soup = BeautifulSoup(r.text, 'lxml')
				table_element = soup.find_all(class_='detailsList')[1]
				tr_element_list = table_element.find_all('tr')
				for tr_element in tr_element_list:
					td_element_list = tr_element.find_all('td')
					col_nums = len(td_element_list)
					self.json_result[family].append({})
					for j in range(col_nums):
						col_dec = th_element_list[j].text.strip().replace('\n', '')
						# print 'col_dec', col_dec
						if table_des == u'股东及出资信息' or table_des == u'发起人及出资信息':
							col = gudong_column_dict[col_dec]
						elif table_des == u'合伙人及出资信息':
							col = hehuoren_column_dict[col_dec]
						elif table_des == u'主管部门(出资人)信息':
							col = DICInfo_column_dict[col_dec]
						td = td_element_list[j]
						val = td.text.strip()
						if val == u'详情' or val == u'查看' :
							id_1 = td.find('a').attrs['onclick']
							id = re.search(r'\d{3,}', id_1).group()
							detail_list = self.get_gu_dong_detail(id)
							for detail_json in detail_list:
								for k in detail_json:
									col = k
									val = detail_json[k]
									self.json_result[family][-1][col] = val
						else:
							self.json_result[family][-1][col] = val
		for i in range(len(self.json_result[family])):
			self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
			self.json_result[family][i][family + ':registrationno'] = self.cur_zch
			self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
			self.json_result[family][i][family + ':id'] = i+1
			# print json.dumps(self.json_result[family][i], ensure_ascii=False)

	def get_gu_dong_detail(self, id):
		"""
		查询股东详情信息
		:param id:
		:return:
		"""
		detail_dict_list = []
		url = 'http://222.143.24.157/queryInvDetailAction.jspx?invId='+id
		r = self.get_request(url=url)
		soup = BeautifulSoup(r.text, 'lxml')
		gudong_table = soup.find_all(class_='detailsList')[0]
		gudong_tr_element_list = gudong_table.find_all('tr')
		for tr_element in gudong_tr_element_list:
			detail_dict_list.append({})
			col_dec = tr_element.find('th').text.strip().replace('\n', '')
			col = gudong_column_dict[col_dec]
			val = tr_element.find('td').text.strip().replace('\n', '')
			detail_dict_list[-1][col] = val
		renjiao_table = soup.find_all(class_='detailsList')[1]
		renjiao_tr_element_list = renjiao_table.find_all('tr')
		renjiao_th_element_list = renjiao_table.find_all('th')
		for tr_element in renjiao_tr_element_list:
			detail_dict_list.append({})
			td_element_list = tr_element.find_all('td')
			col_nums = len(td_element_list)
			for j in range(col_nums):
				col_dec = renjiao_th_element_list[j].text.strip().replace('\n', '')
				col = gudong_column_dict[col_dec]
				val = td_element_list[j].text.strip().replace('\n', '')
				detail_dict_list[-1][col] = val
		shijiao_table = soup.find_all(class_='detailsList')[2]
		shijiao_tr_element_list = shijiao_table.find_all('tr')
		shijiao_th_element_list = shijiao_table.find_all('th')
		for tr_element in shijiao_tr_element_list:
			detail_dict_list.append({})
			td_element_list = tr_element.find_all('td')
			col_nums = len(td_element_list)
			for j in range(col_nums):
				col_dec = shijiao_th_element_list[j].text.strip().replace('\n', '')
				col = gudong_column_dict[col_dec]
				val = td_element_list[j].text.strip().replace('\n', '')
				detail_dict_list[-1][col] = val
		return detail_dict_list

	def get_tou_zi_ren(self, param_corpid, table_element):
		pass

	def get_bian_geng(self, tag_a):
		"""
		查询变更信息
		:param tag_a:
		:return:
		"""
		self.info(u'解析变更信息...')
		family = 'Changed_Announcement'
		table_id = '05'
		self.json_result[family] = []
		url = 'http://222.143.24.157/business/BGXX.jspx?id='+tag_a
		r = self.get_request(url=url)
		# print r.text
		soup_1 = BeautifulSoup(r.text, 'lxml')
		pages = soup_1.find(id='altDiv2').find(class_='ax_image fenye').find_all('li')[1].text.strip()
		page = int(re.search(r'\d', pages).group())
		nums = soup_1.find(id='altDiv2').find(class_='ax_image fenye').find_all('li')[0].text.strip()
		num = int(re.search(r'\d', nums).group())
		# print 'page', pages, nums
		if num == 0:
			pass
		elif num != 0:
			for i in range(page):
				url = 'http://222.143.24.157/business/QueryAltList.jspx?pno='+ str(i+1)+'&order=0&mainId='+tag_a
				# print 'get_bian_geng', url
				r = self.get_request(url=url)
				soup = BeautifulSoup(r.text, 'lxml')
				table_element = soup.find_all(class_='detailsList')[1]
				th_element_list = soup.find_all(class_='detailsList')[0].find_all('th')
				tr_element_list = table_element.find_all('tr')
				for tr_element in tr_element_list:
					td_element_list = tr_element.find_all('td')
					col_nums = len(td_element_list)
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

	def get_zhu_yao_ren_yuan(self, tag_a):
		"""
		查询主要人员信息
		:param tag_a:
		:return:
		"""
		self.info(u'解析主要人员信息...')

		url = 'http://222.143.24.157/business/ZYRY.jspx?id='+tag_a
		# print url
		r = self.get_request(url=url)
		# print r.text
		soup = BeautifulSoup(r.text, 'lxml')
		table_describ = soup.find(class_='text mainPerText').find('span').text.strip().replace('\n','')
		table_des = table_describ.split('&')[0]
		tr_element_list = soup.find_all(class_='keyPerInfo')
		# print 'table_des', table_des
		if table_des == u'主要人员信息':
			family = 'KeyPerson_Info'
			table_id = '06'
			self.json_result[family] = []
			for tr_element in tr_element_list:
				self.json_result[family].append({})
				td_element_list = tr_element.find_all('p')
				# if td_element_list:
				name = td_element_list[0].text.strip().replace('\n', '')
				self.json_result[family][-1]['KeyPerson_Info:keyperson_name'] = name
				positon = td_element_list[1].text.strip().replace('\n', '')
				self.json_result[family][-1]['KeyPerson_Info:keyperson_position'] = positon
		elif table_des == u'成员名册':
			# print u'这是成员名册表，数据库没这个table_id'
			# raise Exception
			family = 'Members_Info'
			table_id = '54'         # 记得修改这个id
			self.json_result[family] = []
			for tr_element in tr_element_list:
				self.json_result[family].append({})
				td_element_list = tr_element.find_all('span')
				# if td_element_list:
				name = td_element_list[0].text.strip().replace('\n', '')
				self.json_result[family][-1]['Members_Info:members_name'] = name
		elif table_des == u'参加经营的家庭成员姓名':
			family = 'Family_Info'
			table_id = '07'
			self.json_result[family] = []
			for tr_element in tr_element_list:
				self.json_result[family].append({})
				td_element_list = tr_element.find_all('span')
				# if td_element_list:
				name = td_element_list[0].text.strip().replace('\n', '')
				self.json_result[family][-1]['Family_Info:familymember_name'] = name
		for i in range(len(self.json_result[family])):
			self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
			self.json_result[family][i][family + ':registrationno'] = self.cur_zch
			self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
			self.json_result[family][i][family + ':id'] = i+1
			# print json.dumps(self.json_result[family][i], ensure_ascii=False)

	def get_fen_zhi_ji_gou(self, tag_a):
		"""
		查询分支机构信息
		:param tag_a:
		:return:
		"""
		self.info(u'解析分支机构信息...')
		family = 'Branches'
		table_id = '08'
		self.json_result[family] = []
		url = 'http://222.143.24.157/business/FZJG.jspx?id='+tag_a
		# print url
		r = self.get_request(url=url)
		soup = BeautifulSoup(r.text, 'lxml')
		tr_element_list = soup.find_all(class_='fenzhixinxin')
		for tr_element in tr_element_list:
			td_element_list = tr_element.find_all('p')
			self.json_result[family].append({})
			# for td_element in td_element_list:
			mc = td_element_list[0].text.strip().replace('\n', '')
			self.json_result[family][-1]['Branches:branch_registrationname'] = mc
			zch_1 = td_element_list[1].text.strip().replace('\n', '')
			zch = zch_1.split(u'：')[1].strip()
			self.json_result[family][-1]['Branches:branch_registrationno'] = zch
			jiguan_1 = td_element_list[2].text.strip().replace('\n', '')
			jiguan = jiguan_1.split(u'：')[1].strip()
			self.json_result[family][-1]['Branches:branch_registrationinstitution'] = jiguan
		for i in range(len(self.json_result[family])):
			self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
			self.json_result[family][i][family + ':registrationno'] = self.cur_zch
			self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
			self.json_result[family][i][family + ':id'] = i+1
			# print json.dumps(self.json_result[family][i], ensure_ascii=False)

	def get_qing_suan(self, tag_a):
		"""
		查询清算信息
		:param tag_a:
		:return:
		"""
		self.info(u'解析清算信息...')
		family = 'liquidation_Information'
		table_id = '09'
		self.json_result[family] = []
		url = 'http://222.143.24.157/business/QSXX.jspx?id='+tag_a
		# print url
		r = self.get_request(url=url)
		soup = BeautifulSoup(r.text, 'lxml')
		table_element = soup.find(class_='details')
		tr_element_list = table_element.find_all('tr')
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

	def get_dong_chan_di_ya(self, tag_a):
		"""
		查询动产抵押信息
		:param tag_a:
		:return:
		"""
		self.info(u'解析动产抵押信息...')
		family = 'Chattel_Mortgage'
		table_id = '11'
		self.json_result[family] = []
		url = 'http://222.143.24.157/business/DCDY.jspx?id='+tag_a
		# print 'url_1',url
		r = self.get_request(url=url)
		soup = BeautifulSoup(r.text, 'lxml')
		pages = soup.find(id='mortDiv2').find(class_='ax_image fenye').find_all('li')[1].text.strip()
		page = int(re.search(r'\d', pages).group())
		nums = soup.find(id='mortDiv2').find(class_='ax_image fenye').find_all('li')[0].text.strip()
		num = int(re.search(r'\d', nums).group())
		# print 'page', pages, nums
		if num == 0:
			pass
		# print 'dong_chan_page', pages
		# for i in range(page):   #此处多页待优化，未找到多页的例子
			# url = 'http://222.143.24.157/business/DCDY.jspx?pno='+str(i+1)+'&order=0&mainId='+tag_a
			# print 'url_2',url
			# r = self.get_request(url = url)
			# soup = BeautifulSoup(r.text, 'lxml')
		elif num != 0 and page == 1:
			table_element = soup.find_all(class_='detailsList')[1]
			th_element_list = soup.find_all(class_='detailsList')[0].find_all('th')
			tr_element_list = table_element.find_all('tr')
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
		elif page > 1:
			print u'动产抵押********多页'
			raise Exception("unknown pages!")
		for i in range(len(self.json_result[family])):
			self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
			self.json_result[family][i][family + ':registrationno'] = self.cur_zch
			self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
			self.json_result[family][i][family + ':id'] = i+1
			# print json.dumps(self.json_result[family], ensure_ascii=False)

	def get_gu_quan_chu_zhi(self, tag_a):
		"""
		查询股权出质信息
		:param tag_a:
		:return:
		"""
		self.info(u'解析股权出质信息...')
		family = 'Equity_Pledge'
		table_id = '13'
		self.json_result[family] = []
		url = 'http://222.143.24.157/business/GQCZ.jspx?id='+tag_a+'&ad_check=1'
		r = self.get_request(url=url)
		soup = BeautifulSoup(r.text, 'lxml')
		pages = soup.find(id='pledgeDiv2').find(class_='ax_image fenye').find_all('li')[1].text.strip()
		page = int(re.search(r'\d', pages).group())
		nums = soup.find(id='pledgeDiv2').find(class_='ax_image fenye').find_all('li')[0].text.strip()
		num = int(re.search(r'\d', nums).group())
		# print 'gu_quan_chu_zhi_page', pages, nums
		if num == 0:
			pass
		# elif num != 0 and page == 1:
		else:
			for i in range(page):
				url = 'http://222.143.24.157/business/QueryPledgeList.jspx'
				params = {'mainId': tag_a, 'order': 0, 'ad_check': 1, 'pno': '%s' % (i+1)}
				r = self.get_request(url=url, params=params)
				# print r.text
				soup = BeautifulSoup(r.text, 'lxml')
				table_element = soup.find_all(class_='detailsList')[1]
				th_element_list = soup.find_all(class_='detailsList')[0].find_all('th')
				# print 'th_element_list', th_element_list
				tr_element_list = table_element.find_all('tr')
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
		# elif page > 1:
		# 	print u'股权出资********多页'
		# 	raise Exception("unknown pages!")
		for i in range(len(self.json_result[family])):
			self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
			self.json_result[family][i][family + ':registrationno'] = self.cur_zch
			self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
			self.json_result[family][i][family + ':id'] = i+1
			# print json.dumps(self.json_result[family][i], ensure_ascii=False)

	def get_xing_zheng_chu_fa(self, tag_a):
		"""
		查询行政处罚信息
		:param tag_a:
		:return:
		"""
		self.info(u'解析行政处罚信息...')
		family = 'Administrative_Penalty'
		table_id = '13'
		self.json_result[family] = []
		url = 'http://222.143.24.157/business/XZCF.jspx?id='+tag_a
		r = self.get_request(url=url)
		soup = BeautifulSoup(r.text, 'lxml')
		pages = soup.find(id='punDiv2').find(class_='ax_image fenye').find_all('li')[1].text.strip()
		page = int(re.search(r'\d', pages).group())
		nums = soup.find(id='punDiv2').find(class_='ax_image fenye').find_all('li')[0].text.strip()
		num = int(re.search(r'\d', nums).group())
		# print 'dong_chan_page', pages,nums
		if num == 0:
			pass
		else:
			for i in range(page):
				url = 'http://222.143.24.157/business/QueryPunList.jspx'
				params = {'mainId': tag_a, 'order': 0, 'ad_check': 1, 'pno': '%s' % (i+1)}
				r = self.get_request(url=url, params=params)
				# print r.text
				soup = BeautifulSoup(r.text, 'lxml')
				table_element = soup.find_all(class_='detailsList')[1]
				th_element_list = soup.find_all(class_='detailsList')[0].find_all('th')
				# print 'th_element_list', th_element_list
				tr_element_list = table_element.find_all('tr')
				for tr_element in tr_element_list[:-1]:
					td_element_list = tr_element.select('td')
					col_nums = len(th_element_list)
					self.json_result[family].append({})
					for j in range(col_nums):
						col_dec = th_element_list[j].text.strip().replace('\n', '')
						col = xingzhengchufa_column_dict[col_dec]
						td = td_element_list[j]
						val = self.pattern.sub('', td.text)
						self.json_result[family][-1][col] = val
						if val == u'详情' or val == u'查看':
							id_1 = td.find('a').attrs['onclick']
							id = re.search(r'\d{3,}', id_1).group()
							self.json_result[family][-1]['Administrative_Penalty:penalty_details'] = \
								'http://222.143.24.157/business/punishInfoDetail.jspx?id='+id
		for i in range(len(self.json_result[family])):
			self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
			self.json_result[family][i][family + ':registrationno'] = self.cur_zch
			self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
			self.json_result[family][i][family + ':id'] = i+1
			# print json.dumps(self.json_result[family][i], ensure_ascii=False)

	def get_jing_ying_yi_chang(self, tag_a):
		"""
		查询经营异常信息
		:param tag_a:
		:return:
		"""
		self.info(u'解析经营异常信息...')
		family = 'Business_Abnormal'
		table_id = '14'
		self.json_result[family] = []
		url = 'http://222.143.24.157/business/JYYC.jspx?id='+ tag_a
		r = self.get_request(url=url)
		soup = BeautifulSoup(r.text, 'lxml')
		pages = soup.find(id='excDiv2').find(class_='ax_image fenye').find_all('li')[1].text.strip()
		page = int(re.search(r'\d', pages).group())
		nums = soup.find(id='excDiv2').find(class_='ax_image fenye').find_all('li')[0].text.strip()
		num = int(re.search(r'\d', nums).group())
		# print 'jing_ying_yi_chang', pages, nums
		if num == 0:
			pass
		elif num != 0 and page == 1:
			table_element = soup.find_all(class_='detailsList')[1]
			th_element_list = soup.find_all(class_='detailsList')[0].find_all('th')
			tr_element_list = table_element.find_all('tr')
			for tr_element in tr_element_list:
				td_element_list = tr_element.select('td')
				col_nums = len(th_element_list)
				self.json_result[family].append({})
				for j in range(col_nums):
					col_dec = th_element_list[j].text.strip().replace('\n', '').replace(' ', '')
					# print col_dec
					col = jingyingyichang_column_dict[col_dec]
					td = td_element_list[j]
					val = self.pattern.sub('', td.text)
					self.json_result[family][-1][col] = val
		elif page > 1:
			print u'经营异常多页'
			raise Exception("unknown pages!")
		for i in range(len(self.json_result[family])):
			self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
			self.json_result[family][i][family + ':registrationno'] = self.cur_zch
			self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
			self.json_result[family][i][family + ':id'] = i+1
			# print json.dumps( self.json_result[family][i], ensure_ascii=False)

	def get_yan_zhong_wei_fa(self, tag_a):
		"""
		查询严重违法信息
		:param tag_a:
		:return:
		"""
		self.info(u'解析严重违法信息...')
		family = 'Serious_Violations'
		table_id = '15'
		self.json_result[family] = []
		url = 'http://222.143.24.157/business/YZWF.jspx?id='+tag_a
		r = self.get_request(url=url)
		soup = BeautifulSoup(r.text, 'lxml')
		pages = soup.find(id='serillDiv2').find(class_='ax_image fenye').find_all('li')[1].text.strip()
		page = int(re.search(r'\d', pages).group())
		nums = soup.find(id='serillDiv2').find(class_='ax_image fenye').find_all('li')[0].text.strip()
		num = int(re.search(r'\d', nums).group())
		# print 'page', pages, nums
		if num == 0:
			pass
		elif num != 0 and page == 1:
			table_element = soup.find_all(class_='detailsList')[1]
			th_element_list = soup.find_all(class_='detailsList')[0].find_all('th')
			tr_element_list = table_element.find_all('tr')
			for tr_element in tr_element_list:
				td_element_list = tr_element.select('td')
				col_nums = len(th_element_list)
				self.json_result[family].append({})
				for j in range(col_nums):
					col_dec = th_element_list[j].text.strip().replace('\n', '')
					col = yanzhongweifa_column_dict[col_dec]
					td = td_element_list[j]
					val = self.pattern.sub('', td.text)
					self.json_result[family][-1][col] = val
		elif page > 1:
			print u'严重违法********多页'
			raise Exception("unknown pages!")
		for i in range(len(self.json_result[family])):
			self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
			self.json_result[family][i][family + ':registrationno'] = self.cur_zch
			self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
			self.json_result[family][i][family + ':id'] = i+1
			# print json.dumps(self.json_result[family], ensure_ascii=False)

	def get_chou_cha_jian_cha(self, tag_a):
		"""
		查询抽查检查信息
		:param tag_a:
		:return:
		"""
		self.info(u'解析抽查检查信息...')
		family = 'Spot_Check'
		table_id = '16'
		self.json_result[family] = []
		url = 'http://222.143.24.157/business/CCJC.jspx?id='+ tag_a
		r = self.get_request(url=url)
		soup = BeautifulSoup(r.text, 'lxml')
		pages = soup.find(id='spotCheck2').find(class_='ax_image fenye').find_all('li')[1].text.strip()
		page = int(re.search(r'\d', pages).group())
		nums = soup.find(id='spotCheck2').find(class_='ax_image fenye').find_all('li')[0].text.strip()
		num = int(re.search(r'\d', nums).group())
		# print 'page', pages, nums
		if num == 0:
			pass
		elif num != 0 and page == 1:
			table_element = soup.find_all(class_='detailsList')[1]
			th_element_list = soup.find_all(class_='detailsList')[0].find_all('th')
			tr_element_list = table_element.find_all('tr')
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
		elif page > 1:
			print u'抽查检查多页'
			raise Exception("unknown pages!")
		for i in range(len(self.json_result[family])):
			self.json_result[family][i]['rowkey'] = '%s_%s_%s_%s%d' % (self.cur_mc, table_id, self.cur_zch, self.today, i+1)
			self.json_result[family][i][family + ':registrationno'] = self.cur_zch
			self.json_result[family][i][family + ':enterprisename'] = self.cur_mc
			self.json_result[family][i][family + ':id'] = i+1
			# print json.dumps(self.json_result[family][i], ensure_ascii=False)

if __name__ == '__main__':
	args_dict = get_args()
	searcher = HeNanSearcher()
	# searcher.delete_tag_a_from_db(u'河南郑缆电缆有限公司')
	# searcher.submit_search_request(u'河南郑缆电缆有限公司')
	searcher.submit_search_request('91410700785060889M', False)
	searcher.info(json.dumps(searcher.json_result, ensure_ascii=False))
	# print json.dumps(searcher.json_result, ensure_ascii=False)

	# args_dict = {'companyName': u'信阳申通货运集团有限公司', 'accountId': '123', 'taskId': '456'}
	# searcher.submit_search_request(keyword=args_dict['companyName'], account_id=args_dict['accountId'], task_id=args_dict['taskId'])
	# print json.dumps(searcher.json_result, ensure_ascii=False)
	# company_path = os.path.join(sys.path[0], '../he_nan/Data/list')
	# patt = re.compile("\s")
	# companies = open(company_path)
	# for keyword in companies.xreadlines():
	# 	# keyword = u'河南乾诚实业有限公司'
	# 	keyword = keyword.decode('gbk')
	# 	keyword = patt.sub('',keyword)
	# 	args_dict = get_args()
	# 	args_dict = {'companyName': keyword, 'accountId': '123', 'taskId': '456'}
	# 	searcher =HeNanSearcher()
	# 	searcher.submit_search_request(keyword=args_dict['companyName'], account_id=args_dict['accountId'], task_id=args_dict['taskId'])
