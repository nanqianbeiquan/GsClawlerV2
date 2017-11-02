# coding=utf-8

from bs4 import BeautifulSoup
import requests

prov_dict = {
    '10': u'工商总局',
    '11': u'北京市',
    '12': u'天津市',
    '13': u'河北省',
    '14': u'山西省',
    '15': u'内蒙古自治区',
    '21': u'辽宁省',
    '22': u'吉林省',
    '23': u'黑龙江省',
    '31': u'上海市',
    '32': u'江苏省',
    '33': u'浙江省',
    '34': u'安徽省',
    '35': u'福建省',
    '36': u'江西省',
    '37': u'山东省',
    '41': u'河南省',
    '42': u'湖北省',
    '43': u'湖南省',
    '44': u'广东省',
    '45': u'广西壮族自治区',
    '46': u'海南省',
    '50': u'重庆市',
    '51': u'四川省',
    '52': u'贵州省',
    '53': u'云南省',
    '54': u'西藏自治区',
    '61': u'陕西省',
    '62': u'甘肃省',
    '63': u'青海省',
    '64': u'宁夏回族自治区',
    '65': u'新疆维吾尔自治区'
}


class TopicConsumingInfo(object):

    desc = 'null'

    def __init__(self, group, topic, desc=None):
        self.group = group
        self.topic = topic
        self.desc = desc
        self.offset_info = None

    def load_info(self):
        url = "http://hadoop10:9010/clusters/kafka/consumers/%s/topic/%s/type/KF" % (self.group, self.topic)
        r = requests.get(url)
        soup = BeautifulSoup(r.text, 'lxml')
        tr_list = soup.select("html body div.container div.col-md-12.un-pad-me div.panel.panel-default "
                              "div.row div.col-md-12 div.panel.panel-default table.table tbody tr")
        self.offset_info = []
        for tr in tr_list:
            self.offset_info.append({})
            td_list = tr.select('td')
            p = int(td_list[0].text)
            s = int(td_list[1].text)
            o = int(td_list[2].text)
            l = int(td_list[3].text)

            self.offset_info[p]['size'] = s
            self.offset_info[p]['offset'] = o
            self.offset_info[p]['lag'] = l

        # print self.offset_info

    def get_progress(self):
        t_s, t_o, t_l = (0, 0, 0)
        for p in range(len(self.offset_info)):
            s = self.offset_info[p]['size']
            o = self.offset_info[p]['offset']
            l = self.offset_info[p]['lag']
            # print '%d\t%d\t%d\t%d\t%f' % (p, s, o, l, (o + 0.0)/s)
            t_s += s
            t_o += o
            t_l += l
        print '%s\t%d\t%d\t%d\t%f' % (self.desc, t_s, t_o, t_l, (t_o + 0.0) / t_s)


if __name__ == '__main__':

    for prov_id in prov_dict:
        topic_name = 'GsSrc'+prov_id
        group = 'Crawler'
        topic_info = TopicConsumingInfo(group, topic_name, prov_dict[prov_id])
        # topic_info = TopicConsumingInfo('Crawler', 'NewRegisteredCompany')
        topic_info.load_info()
        # print topic_info.offset_info
        topic_info.get_progress()

