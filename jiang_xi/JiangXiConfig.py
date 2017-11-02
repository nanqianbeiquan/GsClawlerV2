# coding=utf-8

jiben_column_dict = {
    'REGNO': 'zch',
    'UNISCID': 'tyshxy_code',
    'ENTNAME': 'enterprisename',
    'PROVINCE': 'province',
    'NAME': 'legalrepresentative',                              # modified by jing
    'ENTTYPE_CN': 'enterprisetype',
    'ESTDATE': 'establishmentdate',
    'REGCAP': 'registeredcapital',
    'REGCAPCUR_CN':'',
    'DOM': 'residenceaddress',
    'OPFROM': 'validityfrom',
    'OPTO': 'validityto',
    'OPSCOPE': 'businessscope',
    'REGORG_CN': 'registrationinstitution',
    'APPRDATE': 'approvaldate',
    'REGSTATE_CN': 'registrationstatus',
    'REVDATE':'revocationdate'
    }

gu_dong_dict = {
    'INVTYPE_CN': 'shareholder_type',  # 股东类型
    'INV': 'shareholder_name',  # 股东
    'CERTYPE_CN': 'shareholder_certificationtype',  # 证照/证件类型
    'CERNO': 'shareholder_certificationno',  # 证件号码
    u'认缴额（万元）': 'subscripted_capital',  # 认缴额
    u'实缴额（万元）': 'actualpaid_capital',  # 实缴额
    'SUBCONFROM': 'subscripted_method',  # 认缴出资方式
    u'认缴出资方式': 'subscripted_method',  # 认缴出资方式
    u'认缴出资额（万元）': 'subscripted_amount',  # 认缴出资额（万元）
    u'认缴出资日期': 'subscripted_time',  # 认缴出资日期
    u'实缴出资方式': 'actualpaid_method',  # 实缴出资方式
    u'实缴出资额（万元）': 'actualpaid_amount',  # 实缴出资额（万元）
    u'实缴出资日期': 'actualpaid_time',  # 实缴出资日期
    'ROWNUM_': 'id',
    'DOM': 'dom',  # 股东地址   modified
    'COUNTRY_CN': 'shareholder_country' # 股东国籍  modified
}

bian_geng_dict = {
    'ALTAF': 'changedannouncement_after',  # 变更后
    'ALTBE': 'changedannouncement_before',  # 变更前
    'ALTITEM_CN': 'changedannouncement_events',  # 变更事项
    'ALTDATE': 'changedannouncement_date',  # 变更日期
    'ROWNUM_': 'id'
}

zhu_yao_ren_yuan_dict = {
    'NAME': 'keyperson_name',  # 姓名
    'POSITION_CN': 'keyperson_position',  # 职务
}

fen_zhi_ji_gou_dict = {
    'BRNAME': 'branch_registrationname',  # 名称
    'REGNO': 'branch_registrationno',  # 注册号
    'UNISCID': 'branch_tyshxy_code',  # 统一社会信用代码
    'REGORG_CN': 'branch_registrationinstitution',  # 登记机关
    'ROWNUM_': 'id'
}

qing_suan_dict = {

}

dong_chan_di_ya_dict = {
    'MORREGCNO': 'chattelmortgage_registrationno',  # 登记编号
    'REGIDATE': 'chattelmortgage_registrationdate',  # 登记日期
    'REGORG_CN': 'chattelmortgage_registrationinstitution',  # 登记机关
    'PRICLASECAM': 'chattelmortgage_guaranteedamount',  # 被担保债权数额
    'TYPE': 'chattelmortgage_status',  # 状态
    'PUBLICDATE': 'chattelmortgage_announcedate',  # 公示时间
    'MORREG_ID': 'chattelmortgage_details',
    'ROWNUM_':  'id'
}

gu_quan_chu_zhi_dict = {
    'EQUITYNO': 'equitypledge_registrationno',  # 登记编号
    'PLEDGOR': 'equitypledge_pledgor',  # 出质人
    'PLEDBLICNO': 'equitypledge_pledgorid',  # 证照/证件号码(出质人)
    'IMPAM': 'equitypledge_amount',  # 出质股权数额
    'IMPORG': 'equitypledge_pawnee',  # 质权人
    'IMPORGBLICNO': 'equitypledge_pawneeid',  # 证照/证件号码(质权人)
    'EQUPLEDATE': 'equitypledge_registrationdate',  # 股权出质设立登记日期
    'TYPE': 'equitypledge_status',  # 状态
    'IMPORGID': 'equitypledge_change',
    'ROWNUM_': 'id'
}
#状态：有效，1
#状态：无效，2


xing_zheng_chu_fa_dict = {
    'PENDECNO': 'penalty_code',  # 行政处罚决定书文号
    'ILLEGACTTYPE': 'penalty_illegaltype',  # 违法行为类型
    'PENCONTENT': 'penalty_decisioncontent',  # 行政处罚内容
    'PENAUTH_CN': 'penalty_decisioninsititution',  # 作出行政处罚决定机关名称
    'PENDECISSDATE': 'penalty_decisiondate',  # 作出行政处罚决定日期，
    'PUBLICDATE': 'penalty_announcedate',  # 公示日期
    'CASEID': 'Administrative_Penalty:penalty_details',  #详情 钱大师所做
    'REMARK': 'Administrative_Penalty:penalty_details',  #详情  modify by guan
    'ROWNUM_': 'id'
}

jing_ying_yi_chang_dict = {
    'SPECAUSE_CN': 'abnormal_events',  # 列入经营异常名录原因
    'ABNTIME': 'abnormal_datesin',  # 列入日期
    'REMEXCPRES_CN': 'abnormal_moveoutreason',  # 移出经营异常名录原因
    'REMDATE': 'abnormal_datesout',  # 移出日期
    'DECORG_CN': 'abnormal_decisioninstitution(in)',  # 作出决定机关(列入)
    'REDECORG_CN': 'abnormal_decisioninstitution(out)',  # 作出决定机关(移出)
    'ROWNUM_': 'id'
}

yan_zhong_wei_fa_dict = {
    'serillreaName': 'serious_events',  # 列入严重违法企业名单原因
    'abntimeStr': 'serious_datesin',  # 列入日期
    'remexcpresName': 'serious_moveoutreason',  # 移出严重违法企业名单原因
    'remdateStr': 'serious_datesout',  # 移出日期
    'decorgName': 'serious_decisioninstitution'  # 作出决定机关

}

chou_cha_jian_cha_dict = {
    'INSAUTH': 'check_institution',  # 检查实施机关
    'INSTYPE': 'check_type',  # 类型
    'INSDATE': 'check_date',  # 日期
    'INSRES_CN': 'check_result',  # 结果
    'ROWNUM_': 'id'
}
# 即时信息定向	1
# 即时信息不定向	2
# 年报不定向	3
# 年报定向	4
# 专项	5
