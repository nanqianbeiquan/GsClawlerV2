# coding=utf-8
import time
import requests
from lxml import html
import re
from gs.Searcher import Searcher

# for i in range(10):
#     time_url = long(time.time()*1000)
#     params = {'maent.entname': u'西安曲江大明宫置业有限公司'.encode('gbk')}
#     # print params
#     url = 'http://xygs.snaic.gov.cn/ztxy.do?method=sslist&djjg=&random=%s' % time_url
#     r = requests.post(url, data=params)
#     print 'fine'
#     tree = html.fromstring(r.text)
#     tag_a = tree.xpath(".//*[@class='result_item']")[0].get('onclick')
#     print re.findall("\(.*?(\d+).*,", tag_a)[0]
#     time.sleep(0.5)
#
# # print '!!!', r.text, '!!!'
#
#
# tag_a = "openView('0133100003185','11','K','1')"
# print re.findall("\(.*?(\d+).*,", tag_a)[0]
# # 0133100003185

if __name__ == '__main__':
    searcher = Searcher()
    print searcher.get_yzm_path()
