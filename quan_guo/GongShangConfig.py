# coding=utf-8
ji_ben_dict = {
    u'注册号': 'zch',
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
    u'经营状态': 'entstatus',
    u'统一社会信用代码/注册号':'',
}

tou_zi_ren_dict = {
    u'投资人类型': 'investor_type',
    u'投资人': 'investor_name',
    u'证照类型': 'investor_certificationtype',
    u'证照号码': 'investor_certificationno',
    u'详情': 'investor_details',
    u'股东': 'investor_name',
    u'认缴额（万元）': 'ivt_subscripted_capital',
    u'实缴额（万元）': 'ivt_actualpaid_capital',
    u'认缴出资方式': 'ivt_subscripted_method',
    u'认缴出资额（万元）': 'ivt_subscripted_amount',
    u'认缴出资日期': 'ivt_subscripted_time',
    u'实缴出资方式': 'ivt_actualpaid_method',
    u'实缴出资额（万元）': 'ivt_actualpaid_amount',
    u'实缴出资日期': 'ivt_actualpaid_time',
}
gu_dong_dict = {
    'invtypeName': 'shareholder_type',  # 股东类型
    'inv': 'shareholder_name',  # 股东
    'blictypeName': 'shareholder_certificationtype',  # 证照/证件类型
    'blicno': 'shareholder_certificationno',  # 证件号码
    'lisubconam': 'subscripted_capital',  # 认缴额
    'liacconam': 'actualpaid_capital',  # 实缴额
    'subConformName': 'subscripted_method',  # 认缴出资方式
    'subconam': 'subscripted_amount',  # 认缴出资额（万元）
    'subCondateStr': 'subscripted_time',  # 认缴出资日期
    'accConformName': 'actualpaid_method',  # 实缴出资方式
    'acconam': 'actualpaid_amount',  # 实缴出资额（万元）
    'accCondateStr': 'actualpaid_time'  # 实缴出资日期
}

bian_geng_dict = {
    u'变更后内容': 'changedannouncement_after',  # 变更后
    u'变更前内容': 'changedannouncement_before',  # 变更前
    u'变更事项': 'changedannouncement_events',  # 变更事项
    u'变更日期': 'changedannouncement_date',  # 变更日期
}

zhu_yao_ren_yuan_dict = {
    u'姓名': 'keyperson_name',  # 姓名
    u'职务': 'keyperson_position',  # 职务
    u'序号': 'keyperson_no'
}

fen_zhi_ji_gou_dict = {
    u'名称': 'branch_registrationname',  # 名称
    u'注册号': 'branch_registrationno',  # 统一社会信用代码/注册号
    u'登记机关': 'branch_registrationinstitution',  # 登记机关
    u'序号': 'branch_no'
}

qing_suan_dict = {

}

dong_chan_di_ya_dict = {
    u'登记编号': 'chattelmortgage_registrationno',  # 登记编号
    u'登记日期': 'chattelmortgage_registrationdate',  # 登记日期
    u'登记机关': 'chattelmortgage_registrationinstitution',  # 登记机关
    u'被担保债权数额': 'chattelmortgage_guaranteedamount',  # 被担保债权数额
    u'状态': 'chattelmortgage_status',  # 状态
    u'序号': 'chattelmortgage_no',
    u'详情': 'chattelmortgage_details',
    #'gstimeStr': 'chattelmortgage_announcedate'  # 公示时间
}

gu_quan_chu_zhi_dict = {
    u'序号': 'equitypledge_no',
    u'登记编号': 'equitypledge_registrationno',  # 登记编号
    u'出质人': 'equitypledge_pledgor',  # 出质人
    u'证照/证件号码(出质人)': 'equitypledge_pledgorid',  # 证照/证件号码(出质人)
    u'出质股权数额': 'equitypledge_amount',
    u'质权人': 'equitypledge_pawnee',  # 质权人
    u'证照/证件号码(质权人)': 'equitypledge_pawneeid',  # 证照/证件号码(质权人)
    u'股权出质设立登记日期': 'equitypledge_registrationdate',  # 股权出质设立登记日期
    u'状态': 'equitypledge_status',  # 状态
    u'详情': 'equitypledge_detail',  #
    u'变化情况': 'equitypledge_change'

}

xing_zheng_chu_fa_dict = {
    u'行政处罚决定书文号': 'penalty_code',  # 行政处罚决定书文号
    u'违法行为类型': 'penalty_illegaltype',  # 违法行为类型
    u'行政处罚内容': 'penalty_decisioncontent',  # 行政处罚内容
    u'作出行政处罚决定机关名称': 'penalty_decisioninsititution',  # 作出行政处罚决定机关名称
    u'作出行政处罚决定日期': 'penalty_decisiondate',  # 作出行政处罚决定日期
    u'详情': 'penalty_details',
    u'序号': 'penalty_no'
}

jing_ying_yi_chang_dict = {
    u'列入经营异常名录原因': 'abnormal_events',  # 列入经营异常名录原因
    u'列入日期': 'abnormal_datesin',  # 列入日期
    u'移出经营异常名录原因': 'abnormal_moveoutreason',  # 移出经营异常名录原因
    u'移出日期': 'abnormal_datesout',  # 移出日期
    u'作出决定机关': 'abnormal_decisioninstitution',  # 作出决定机关
    u'序号': 'abnormal_no'
}

yan_zhong_wei_fa_dict = {
    u'列入严重违法企业名单原因': 'serious_events',  # 列入严重违法企业名单原因
    u'列入严重违法失信企业名单原因': 'serious_events',
    u'列入日期': 'serious_datesin',  # 列入日期
    u'移出严重违法企业名单原因': 'serious_moveoutreason',  # 移出严重违法企业名单原因
    u'移出严重违法失信企业名单原因': 'serious_moveoutreason',
    u'移出日期': 'serious_datesout',  # 移出日期
    u'作出决定机关': 'serious_decisioninstitution',  # 作出决定机关
    u'序号': 'serious_no'

}

chou_cha_jian_cha_dict = {
    u'序号': 'check_no',
    u'检查实施机关': 'check_institution',  # 检查实施机关
    u'类型': 'check_type',  # 类型
    u'日期': 'check_date',  # 日期
    u'结果': 'check_result',  # 结果
    u'备注': 'check_remark'  # 备注
}

nian_bao_dict = {
    u'序号': 'xh',
    u'报送年度': 'bsrq',  # 需要修改！！！！！！！！！！！！！！！！！！！！！！！！
    u'发布日期': 'fbrq',
    u'详情': 'xq'
}


nian_bao_ji_ben_dict = {
    u'统一社会信用代码': 'tyshxydm',
    u'注册号': 'zch',
    u'企业联系电话': 'lxdh',
    u'邮政编码': 'yzbm',
    u'企业通信地址': 'txdz',
    u'电子邮箱': 'dzyx',
    u'有限责任公司本年度是否发生股东股权转让': 'gqzr',
    u'企业是否有对外投资设立企业信息': 'qtgq',
    u'从业人数': 'cyrs',
    u'是否有网站或网店': 'sfwd',
    u'公司名称': 'enterprisename',
    u'企业经营状态': 'jyzt',
    }
nian_bao_wang_zhan_dict = {
    u'类型': 'lx',
    u'名称': 'mc',
    u'网址': 'wz'
    }
nian_bao_chu_zi_dict = {
    u'股东': 'gd',
    u'认缴出资额（万元）': 'rjcze',
    u'认缴出资时间': 'rjczrq',
    u'认缴出资方式': 'rjczfs',
    u'实缴出资额（万元）': 'sjcze',
    u'出资时间': 'sjczrq',
    u'出资方式': 'sjczfs'
}
nian_bao_tou_zi_dict = {
    u'投资设立企业或购买股权企业名称': 'qymc',
    u'注册号': 'zch'
}
nian_bao_zi_chan_dict = {
    u'资产总额': 'zcze',
    u'负债总额': 'fzze',
    u'营业总收入': 'yyzsr',
    u'其中：主营业务收入': 'zyyw',
    u'利润总额': 'lrze',
    u'净利润': 'jlr',
    u'纳税总额': 'nsze',
    u'所有者权益合计': 'qyhj'
}
nian_bao_dan_bao_dict = {
    u'债权人': 'zqr',
    u'债务人': 'zwr',
    u'主债权种类': 'zzqzl',
    u'主债权数额': 'zzqse',
    u'履行债务的期限': 'zwqx',
    u'保证的期间': 'bzqj',
    u'保证的方式': 'bzfs',
    u'保证担保的范围': 'dbfw'
}
nian_bao_gu_quan_bian_geng_dict = {
    u'股东': 'gd',
    u'变更前股权比例': 'bgq',
    u'变更后股权比例': 'bgh',
    u'股权变更日期': 'bgrq',
}
nian_bao_xiu_gai_dict = {
    u'序号': 'xhxh',
    u'修改事项': 'xgsx',
    u'修改前': 'xgq',
    u'修改后': 'xgh',
    u'修改日期': 'xgrq'
}

