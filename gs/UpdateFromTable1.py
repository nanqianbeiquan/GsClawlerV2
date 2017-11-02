# coding=utf-8

import traceback
import MSSQL
import re
from MyException import NotFoundException


class UpdateFromTable1(object):

    src_table = None  #
    searcher = None  #
    pk_name = 'mc'
    pk_mc = 'mc'
    pk_zch = 'zch'
    pk_xydm = 'xydm'
    ignore_pattern = re.compile(u'[\d ~`@$%\^&*_\-+=\[\]\{\}\|:;"\',\.<>\?/，。？、：；“”‘’【】．《》１２３４５６７８９０ｑｗｅｒｔｙｕｉｏｐａｓｄｆｇｈｊｋｌｚｘｃｖｂｎｍＱＷＥＲＴＹＵＩＯＰＡＳＤＦＧＨＪＫＬＺＸＣＶＢＮＭ]')

    def __init__(self):
        self.set_config()
        self.searcher.turn_off_print()
        self.log_name = self.searcher.log_name
        self.src_table = self.searcher.topic

    def set_config(self):
        """
        设置查询器和kafka队列参数
        示例
        self.searcher = LiaoNing()  # 因为kakfa 客户端需要从searcher中读取group和topic,因此一定要先生成searcher再生成kafka 客户端
        :return:
        """
        pass

    def info(self, msg):
        self.searcher.info(msg)

    def run(self):
        cnt_0 = 0
        cnt_1 = 0
        cnt_2 = 0
        cnt_3 = 0
        while True:
            sql_1 = "select top 1 %s ,%s ,%s  from " \
                    "(" \
                    "select top 30 * from %s where update_status=-1" \
                    ") t " \
                    "order by newid()" % (self.pk_name, self.pk_xydm, self.pk_zch, self.src_table)
            res_1 = MSSQL.execute_query(sql_1)
            print 'kdfn', res_1
            # print 'kdfn1_mc',res_1[0][0]
            # print 'kdfn2_xydm', res_1[0][1]
            # print 'kdfn3_zch', res_1[0][2]

            if len(res_1) > 0:
                if res_1[0][2] and res_1[0][2] != 'null':
                    self.pk_name = self.pk_zch
                    pk = res_1[0][2]
                else:
                    if res_1[0][1] and res_1[0][1] != 'null':
                        self.pk_name = self.pk_xydm
                        pk = res_1[0][1]
                    else:
                        self.pk_name = self.pk_mc
                        pk = res_1[0][0]
                        # if pk == 'null':

                print 'coltype:', self.pk_name, 'tent:', pk
                sql_2 = "update %s set update_status=-2 where %s='%s'" % (self.src_table, self.pk_name, pk)
                print 'sql_2b',sql_2
                MSSQL.execute_update(sql_2)
                print 'sql_2a',sql_2
                try:
                    if self.pk_name == 'mc':
                        if self.ignore_pattern.search(pk):
                            update_status = 9
                        else:
                            print 'downmc'
                            update_status = self.searcher.submit_search_request(pk)
                    else:
                        print 'xydmorzch'
                        update_status = self.searcher.submit_search_request(pk)
                except NotFoundException:
                    update_status = 8
                except Exception, e:
                    err = traceback.format_exc(e)
                    if type(err) != unicode:
                        err = err.decode('utf-8', 'ignore')
                    self.info(err)
                    update_status = -1
                    self.searcher.delete_tag_a_from_db(pk)
                sql_3 = "update %s set update_status=%d,last_update_time=getDate() where %s='%s'" % (self.src_table, update_status, self.pk_name, pk)
                print 'sql_3', sql_3
                self.searcher.release_lock_id()
                MSSQL.execute_update(sql_3)
                if update_status == 0:
                    cnt_0 += 1
                elif update_status == 1:
                    cnt_1 += 1
                elif update_status == 9:
                    cnt_3 += 1
                else:
                    cnt_2 += 1
                self.info(u'查询有结果: %d, 查询无结果: %d, 查询失败:%d, 特殊字符:%d' % (cnt_1, cnt_0, cnt_2, cnt_3))
            else:
                sql_4 = "update %s set update_status=-1 where update_status=-2 and " \
                        "(DATEDIFF(SECOND, last_update_time, GETDATE())>300 or last_update_time is null)" % self.src_table
                MSSQL.execute_update(sql_4)
                # sql_5 = "select @@ROWCOUNT"
                # res_5 = MSSQL.execute_query(sql_5)
                # if res_5[0][0] == 0:
                #     time.sleep(300)
                #     self.info(u'更新完毕')




