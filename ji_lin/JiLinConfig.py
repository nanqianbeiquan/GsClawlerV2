# coding=utf-8
ji_ben_dict = {
    u'统一社会信用代码/注册号': 'registrationno',
    u'注册号/统一社会信用代码': 'registrationno',
    u'名称': 'enterprisename',
    u'省份': 'province',
    u'法定代表人': 'legalrepresentative',
    u'类型': 'enterprisetype',
    u'注册日期': 'establishmentdate',
    u'成立日期': 'establishmentdate',
    u'注册资本': 'registeredcapital',
    u'注册资金': 'registeredcapital',
    u'住所': 'residenceaddress',
    u'营业期限自': 'validityfrom',
    u'营业期限至': 'validityto',
    u'经营期限自': 'validityfrom',
    u'经营期限至': 'validityto',
    u'经营范围': 'businessscope',
    u'登记机关': 'registrationinstitution',
    u'核准日期': 'approvaldate',
    u'登记状态': 'registrationstatus',
    u'负责人': 'principal',
    u'经营场所': 'businessplace',
    u'营业场所': 'businessplace',
    u'修改日期': 'lastupdatetime',
    u'吊销日期': 'revocationdate',
    u'投资人': 'investor',
    u'主要经营场所': 'mianbusinessplace',
    u'合伙期限自': 'partnershipfrom',
    u'合伙期限至': 'partnershipto',
    u'执行事务合伙人': 'executivepartner',
    u'组成形式': 'compositionform',
    u'经营者': 'operator',
    u'首席代表': 'chiefrepresentative',
    u'派出企业名称': 'enterpriseassigning',
    u'成员出资总额': 'totalcontributionofmembers',
    u'统一社会信用代码': 'tyshxy_code',
    u'省份': 'province',
    u'迁入地工商局': 'qrdgsj',
    u'社会信用代码': 'tyshxy_code',
    u'注册号': 'zch',                                           # add zch
    u'详情页url':'detailpageurl'}       


gu_dong_dict = {
    'invtype': 'shareholder_type',  # 股东类型
    'inv': 'shareholder_name',  # 股东
    'blictype': 'shareholder_certificationtype',  # 证照/证件类型
    'blicno': 'shareholder_certificationno',  # 证件号码
    'lisubconam': 'subscripted_capital',  # 认缴额
    'liacconam': 'actualpaid_capital',  # 实缴额
    'subconform': 'subscripted_method',  # 认缴出资方式modify by guan
    'subconam': 'subscripted_amount',  # 认缴出资额（万元）modify by guan
#     'condate': 'subscripted_time',  # 认缴出资日期  山东
    'subtime': 'subscripted_time',  # 认缴出资日期 modify by guan
    'actconform': 'actualpaid_method',  # 实缴出资方式 modify by guan
    'actconam': 'actualpaid_amount',  # 实缴出资额（万元）
    'acttime': 'actualpaid_time'  # 实缴出资日期 modify by guan
}

bian_geng_dict = {
    'altaf': 'changedannouncement_after',  # 变更后
    'altbe': 'changedannouncement_before',  # 变更前
    'altitem': 'changedannouncement_events',  # 变更事项
    'altdate': 'changedannouncement_date',  # 变更日期
}

zhu_yao_ren_yuan_dict = {
    'name': 'keyperson_name',  # 姓名
    'position': 'keyperson_position',  # 职务
}

DICInfo_column_dict = {'xzqh': 'dic_no',             #序号
                        'invtype': 'dic_sponsortype',#出资人类型
                        'inv': 'dic_sponsorname',    #出资人
                        'blictype': 'dic_idtype',    #证照/证件类型
                        'blicno': 'dic_idno'}        #证照/证件号码

fen_zhi_ji_gou_dict = {
    'brname': 'branch_registrationname',  # 名称
    'regno': 'branch_registrationno',  # 统一社会信用代码/注册号
    'regorg': 'branch_registrationinstitution'  # 登记机关
    
}

qing_suan_dict = {

}

dong_chan_di_ya_dict = {
    'morregcno': 'chattelmortgage_registrationno',  # 登记编号
    'regidate': 'chattelmortgage_registrationdate',  # 登记日期
    'regorg': 'chattelmortgage_registrationinstitution',  # 登记机关
    'priclasecam': 'chattelmortgage_guaranteedamount',  # 被担保债权数额
    'type': 'chattelmortgage_status',  # 状态  modify by guan  1 代表【有效】 2 代表【无效】
#     'gstimeStr': 'chattelmortgage_announcedate'  # 公示时间
}

gu_quan_chu_zhi_dict = {
    'equityno': 'equitypledge_registrationno',  # 登记编号
    'pledgor': 'equitypledge_pledgor',  # 出质人
    'blicno': 'equitypledge_pledgorid',  # 证照/证件号码(出质人)
    'impam': 'equitypledge_amount',  # 出质股权数额 modify by guan  
    'imporg': 'equitypledge_pawnee',  # 质权人
    'impmorblicno': 'equitypledge_pawneeid',  # 证照/证件号码(质权人)
    'equpledate': 'equitypledge_registrationdate',  # 股权出质设立登记日期
    'type': 'equitypledge_status',  # 状态 modify by guan  1 代表【有效】
    'gstimeStr': 'equitypledge_announcedate',  # 公示时间

}

xing_zheng_chu_fa_dict = {
    'pendecno': 'penalty_code',  # 行政处罚决定书文号
    'illegacttype': 'penalty_illegaltype',  # 违法行为类型
    'pencontent': 'penalty_decisioncontent',  # 行政处罚内容
    'penauthName': 'penalty_decisioninsititution',  # 作出行政处罚决定机关名称
    'pendecissdateStr': 'penalty_decisiondate',  # 作出行政处罚决定日期
}

jing_ying_yi_chang_dict = {
    'specause': 'abnormal_events',  # 列入经营异常名录原因
    'abntime': 'abnormal_datesin',  # 列入日期
    'remexcpres': 'abnormal_moveoutreason',  # 移出经营异常名录原因
    'remdate': 'abnormal_datesout',  # 移出日期
    'decorg': 'abnormal_decisioninstitution'  # 作出决定机关
}

yan_zhong_wei_fa_dict = {
    'serillreaName': 'serious_events',  # 列入严重违法企业名单原因
    'abntimeStr': 'serious_datesin',  # 列入日期
    'remexcpresName': 'serious_moveoutreason',  # 移出严重违法企业名单原因
    'remdateStr': 'serious_datesout',  # 移出日期
    'decorgName': 'serious_decisioninstitution'  # 作出决定机关

}

chou_cha_jian_cha_dict = {
    'insauth': 'check_institution',  # 检查实施机关
    'instype': 'check_type',  # 类型
    'insdate': 'check_date',  # 日期
    'insres': 'check_result',  # 结果
}
