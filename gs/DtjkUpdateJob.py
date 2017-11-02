# coding=utf-8

from UpdateFromTable import UpdateFromTable
from Crawler import GsCrawler
import MSSQL
from MyException import NotFoundException, StatusCodeException
import traceback
import uuid
import Logger
import time
import sys


class DtjkUpdateJob(UpdateFromTable):

    ignore_province = (
        u'河北省',  # 待开发
        u'吉林省',  # 待开发
        u'广西壮族自治区',  # 待开发
        u'云南省',  # 待开发
        u'西藏自治区', # 网站出错
        'HK',
        'CHINA',
        u'黑龙江省', # 网站出错
        u'内蒙古自治区', # 网站出错
        u'青海省', # 网站出错
    )
    update_status_meaning = {
        0: u'未查询到结果',
        1: u'查询有结果',
        3: u'未知异常',
        5: u'网站响应码错误',
        9: u'特殊字符',
        7: u'数据源省份错误',
        4: u'ip被封'
    }

    def __init__(self):
        self.set_config()
        self.src_table = 'GsSrc.dbo.DtjkSrc'
        self.pk_name = 'mc'
        self.log_name = u"动态监控_"+str(uuid.uuid1())

    def set_config(self):
        self.searcher = GsCrawler()

    info = lambda self, msg: Logger.write(msg, self.log_name, print_msg=True)

    def run(self):
        sql_0 = "update %s set update_status=2 where province in ('%s') and data_type='%s'" %(self.src_table, "','".join(self.ignore_province), u'工商')  # 暂不需更新的省份状态设为2
        MSSQL.execute_update(sql_0)
        # cnt_0 = 0
        # cnt_1 = 0
        # cnt_2 = 0
        # cnt_3 = 0
        result_dict = {}
        while True:
            sql_1 = "select top 1 mc,province from " \
                    "(" \
                    "select top 30 * from %s where update_status=-1 " \
                    "and data_type='%s' " \
                    ") t " \
                    "order by newid()" % (self.src_table, u'工商')
            res_1 = MSSQL.execute_query(sql_1)
            if len(res_1) > 0:
                print u'取到公司'
                mc = res_1[0][0]
                province = res_1[0][1]
                sql_2 = "update %s set update_status=-2 where %s='%s' and data_type='%s'" \
                        % (self.src_table, self.pk_name, mc, u'工商')
                MSSQL.execute_update(sql_2)
                self.info(mc+'|'+province)
                if self.ignore_pattern.search(mc):
                    print '*', mc
                    update_status = 9  # 公司名有特殊字符
                else:
                    try:
                        update_status = self.searcher.crawl(company_name=mc, province=province)
                    except NotFoundException:
                        update_status = 8
                    except StatusCodeException:
                        update_status = 5
                    except Exception, e:
                        err = traceback.format_exc(e)
                        if type(err) != unicode:
                            err = err.decode('utf-8', 'ignore')
                        self.info(err)
                        update_status = 3  # 未知异常
                        self.searcher.delete_tag_a_from_db(mc, province)
                sql_3 = "update %s set update_status=%d,last_update_time=getDate() where %s='%s' " \
                        "and data_type='%s'" % (self.src_table, update_status, self.pk_name, mc, u'工商')
                self.searcher.release_lock_id(province)
                MSSQL.execute_update(sql_3)

                result_dict[update_status] = result_dict.get(update_status,0) + 1
                res = ''
                for key in result_dict:
                    res = res + self.update_status_meaning[key] + ':' + str(result_dict[key]) + ' '
                self.info(res)
                # if update_status == 0:
                #     cnt_0 += 1
                # elif update_status == 1:
                #     self.info(u'更新成功')
                #     cnt_1 += 1
                # elif update_status == 9:
                #     cnt_3 += 1
                # else:
                #     cnt_2 += 1
                # self.info(u'查询有结果: %d, 查询无结果: %d, 查询失败:%d, 特殊字符:%d' % (cnt_1, cnt_0, cnt_2, cnt_3))
            else:
                self.info(u'未取得公司')
                time.sleep(300)
                sql_4 = "update %s set update_status=-1 where update_status in (-2,3,5) and " \
                        "(DATEDIFF(SECOND, last_update_time, GETDATE())>300 or last_update_time is null) " \
                        "and data_type='%s'" % (self.src_table, u'工商')
                MSSQL.execute_update_without_commit(sql_4)  # 在未commit情况下，才可以查询rowcount
                sql_5 = "select @@ROWCOUNT"
                res_5 = MSSQL.execute_query(sql_5)
                MSSQL.commit()
                print res_5
                if res_5[0][0] == 0:
                    self.info(u'更新完毕')
                    sys.exit(1)



if __name__ == '__main__':
    job = DtjkUpdateJob()
    job.run()
    # sql_4 = "update %s set update_status=3 where update_status in (-1,3,5) and " \
    #                     "(DATEDIFF(SECOND, last_update_time, GETDATE())>30 or last_update_time is null) " \
    #                     "and data_type='%s'" % ('GsSrc.dbo.DtjkSrc', u'工商')
    # MSSQL.execute_update_without_commit(sql_4)
    # sql_5 = "select @@ROWCOUNT"
    # res_5 = MSSQL.execute_query(sql_5)
    # MSSQL.commit()
    # print res_5
