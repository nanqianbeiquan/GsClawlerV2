# coding=utf-8
ji_ben_dict = {
    'zch': 'registrationno',
    'qymc': 'enterprisename',      #企业名称
    'province': 'province',
    'fddbr': 'legalrepresentative',   # 法人代表
    'optypemc': 'enterprisetype',     # 企业类型
    'clrq': 'establishmentdate',      # 成立日期
    'zczb': 'registeredcapital',      # 注册资本
    'zs': 'residenceaddress',         # 地址
    'yyrq1': 'validityfrom',          # 营业日期自
    'yyrq2': 'validityto',            # 营业日期至
    'jyfw': 'businessscope',        # 经营范围
    'djjgmc': 'registrationinstitution',   # 登记机构
    'hzrq': 'approvaldate',           # 核准日期
    'mclxmc': 'registrationstatus',  # 状态
    'pril': 'principal',
    'oploc': 'businessplace',
    'revdate': 'revocationdate',
    'tyshxy_code': 'tyshxy_code',
    'zch' : 'zch'
}

gu_dong_dict = {
    'tzrlxmc': 'shareholder_type',  # 股东类型
    'czmc': 'shareholder_name',  # 股东
    'zzlxmc': 'shareholder_certificationtype',  # 证照/证件类型
    'zzbh': 'shareholder_certificationno',  # 证件号码
    'rjcze': 'subscripted_capital',  # 认缴额
    'sjcze': 'actualpaid_capital',  # 实缴额
    'rjczfsmc': 'subscripted_method',  # 认缴出资方式
    'rjcze1': 'subscripted_amount',  # 认缴出资额（万元）
    'condate': 'subscripted_time',  # 认缴出资日期
    'sjczfsmc': 'actualpaid_method',  # 实缴出资方式
    'sjcze1': 'actualpaid_amount',  # 实缴出资额（万元）
    'sjczrq': 'actualpaid_time',  # 实缴出资日期
}

gu_dong_detail_dict = {
    'rjcze': 'subscripted_capital',  # 认缴额
    'sjcze': 'actualpaid_capital',  # 实缴额
    'rjczfsmc': 'subscripted_method',  # 认缴出资方式
    'rjcze1': 'subscripted_amount',  # 认缴出资额（万元）
    'condate': 'subscripted_time',  # 认缴出资日期
    'sjczfsmc': 'actualpaid_method',  # 实缴出资方式
    'sjcze1': 'actualpaid_amount',  # 实缴出资额（万元）
    'sjczrq': 'actualpaid_time',  # 实缴出资日期
}


bian_geng_dict = {
    'bghnr': 'changedannouncement_after',  # 变更后
    'bcnr': 'changedannouncement_before',  # 变更前
    'bcsxmc': 'changedannouncement_events',  # 变更事项
    'hzrq': 'changedannouncement_date',  # 变更日期
}

zhu_yao_ren_yuan_dict = {
    'xm': 'keyperson_name',  # 姓名
    'zwmc': 'keyperson_position',  # 职务
}

fen_zhi_ji_gou_dict = {
    'fgsmc': 'branch_registrationname',  # 名称
    'fgszch': 'branch_registrationno',  # 统一社会信用代码/注册号
    'fgsdjjgmc': 'branch_registrationinstitution'  # 登记机关
}

qing_suan_dict = {

}

dong_chan_di_ya_dict = {
    'djbh': 'chattelmortgage_registrationno',  # 登记编号
    'djrq': 'chattelmortgage_registrationdate',  # 登记日期
    'djjgmc': 'chattelmortgage_registrationinstitution',  # 登记机关
    'bdbse': 'chattelmortgage_guaranteedamount',  # 被担保债权数额
    'zt': 'chattelmortgage_status',  # 状态
    'gsrq': 'chattelmortgage_announcedate'  # 公示时间
}

gu_quan_chu_zhi_dict = {
    'djbh': 'equitypledge_registrationno',  # 登记编号
    'czr': 'equitypledge_pledgor',  # 出质人
    'czgqse': 'equitypledge_amount',  # 出质股权数额
    'czzjhm': 'equitypledge_pledgorid',  # 证照/证件号码(出质人)
    'zqr': 'equitypledge_pawnee',  # 质权人
    'zqzjhm': 'equitypledge_pawneeid',  # 证照/证件号码(质权人)
    'czrq': 'equitypledge_registrationdate',  # 股权出质设立登记日期
    'zt': 'equitypledge_status',  # 状态
    'gsrq': 'equitypledge_announcedate',  # 公示时间

}

xing_zheng_chu_fa_dict = {
    'cfjdsh': 'penalty_code',  # 行政处罚决定书文号
    'wfxwlx': 'penalty_illegaltype',  # 违法行为类型
    'xzcfnr': 'penalty_decisioncontent',  # 行政处罚内容
    'cfjg': 'penalty_decisioninsititution',  # 作出行政处罚决定机关名称
    'cfrq': 'penalty_decisiondate',  # 作出行政处罚决定日期
    'gsrq': 'penalty_publicationdate',  # 行政处罚公式日期
}

jing_ying_yi_chang_dict = {
    'lryy': 'abnormal_events',  # 列入经营异常名录原因
    'lrrq': 'abnormal_datesin',  # 列入日期
    'ycyy': 'abnormal_moveoutreason',  # 移出经营异常名录原因
    'ycrq': 'abnormal_datesout',  # 移出日期
    'zcjdjg': 'abnormal_decisioninstitution'  # 作出决定机关
}

yan_zhong_wei_fa_dict = {
    'serillrea': 'serious_events',  # 列入严重违法企业名单原因
    'abntime': 'serious_datesin',  # 列入日期
    'remexcpres': 'serious_moveoutreason',  # 移出严重违法企业名单原因
    'remdate': 'serious_datesout',  # 移出日期
    'decorg': 'serious_decisioninstitution'  # 作出决定机关

}

chou_cha_jian_cha_dict = {
    'insauth': 'check_institution',  # 检查实施机关
    'instype': 'check_type',  # 类型
    'insdate': 'check_date',  # 日期
    'insresdesc': 'check_result',  # 结果
    'insresname': 'check_remark'  # 备注
}
