# coding=utf-8

jiben_column_dict = {
    u'统一社会信用代码/注册号': 'Registered_Info:registrationno',
    u'注册号/统一社会信用代码': 'Registered_Info:registrationno',             # modified by jing
    u'注册号': 'Registered_Info:zch',
    u'统一社会信用代码': 'Registered_Info:tyshxy_code',                  # modified by jing
    u'名称': 'Registered_Info:enterprisename',
    u'省份': 'Registered_Info:province',
    u'法定代表人': 'Registered_Info:legalrepresentative',
    u'经营者': 'Registered_Info:operator',                              # modified by jing
    u'类型': 'Registered_Info:enterprisetype',
    u'组成形式': 'Registered_Info:compositionform',                       # modified by jing
    u'成立日期': 'Registered_Info:establishmentdate',
    u'注册日期': 'Registered_Info:establishmentdate',                    # modified by jing
    u'注册资本': 'Registered_Info:registeredcapital',
    u'注册资金': 'Registered_Info:registeredcapital',                    # modified by jing
    u'住所': 'Registered_Info:residenceaddress',
    u'营业期限自': 'Registered_Info:validityfrom',
    u'营业期限至': 'Registered_Info:validityto',
    u'经营期限自': 'Registered_Info:validityfrom',
    u'经营期限至': 'Registered_Info:validityto',
    u'经营范围': 'Registered_Info:businessscope',
    u'业务范围': 'Registered_Info:businessscope',
    u'登记机关': 'Registered_Info:registrationinstitution',
    u'核准日期': 'Registered_Info:approvaldate',
    u'登记状态': 'Registered_Info:registrationstatus',
    u'经营状态': 'Registered_Info:entstatus',
    u'负责人': 'Registered_Info:principal',
    u'营业场所': 'Registered_Info:businessplace',
    u'住所/经营场所': 'Registered_Info:businessplace',
    u'经营场所': 'Registered_Info:businessplace',                        # modified by jing
    u'吊销日期': 'Registered_Info:revocationdate',
    u'吊销时间': 'Registered_Info:revocationdate',
    u'投资人': 'Registered_Info:investor',
    u'股东': 'Registered_Info:investor',
    u'执行事务合伙人': 'Registered_Info:executivepartner',
    u'主要经营场所': 'Registered_Info:mianbusinessplace',
    u'合伙期限自': 'Registered_Info:partnershipfrom',
    u'合伙期限至': 'Registered_Info:partnershipto',
    u'成员出资总额':'Registered_Info:totalcontributionofmembers',
    u'社会信用代码': 'Registered_Info:tyshxy_code',
    u'注册号码': 'Registered_Info:zch',                                           # add zch
    u'详情页url':'Registered_Info:detailpageurl'
}                               # modified by jing

gu_dong_dict = {
    'invType': 'shareholder_type',  # 股东类型
    'inv': 'shareholder_name',  # 股东
    'certName': 'shareholder_certificationtype',  # 证照/证件类型
    'certNo': 'shareholder_certificationno',  # 证件号码
    'lisubconam': 'subscripted_capital',  # 认缴额
    'liacconam': 'actualpaid_capital',  # 实缴额
    'conForm': 'subscripted_method',  # 认缴出资方式
    'subConAm': 'subscripted_amount',  # 认缴出资额（万元）
    'conDate': 'subscripted_time',  # 认缴出资日期
    'conForm': 'actualpaid_method',  # 实缴出资方式
    'acConAm': 'actualpaid_amount',  # 实缴出资额（万元）
    'acConDate': 'actualpaid_time'  # 实缴出资日期
}

bian_geng_dict = {
    'altAf': 'changedannouncement_after',  # 变更后
    'altBe': 'changedannouncement_before',  # 变更前
    'altFiledName': 'changedannouncement_events',  # 变更事项
    'altDate': 'changedannouncement_date',  # 变更日期
}

zhuyaorenyuan_column_dict={u'序号':'KeyPerson_Info:keyperson_no',
                           u'姓名':'KeyPerson_Info:keyperson_name',
                           u'职务':'KeyPerson_Info:keyperson_position'}

fenzhijigou_column_dict = {u'序号':'Branches:branch_no',
                            u'注册号/统一社会信用代码':'Branches:branch_registrationno',
                           u'注册号':'Branches:branch_registrationno',
                            u'名称':'Branches:branch_registrationname',
                            u'登记机关':'Branches:branch_registrationinstitution'}

qingsuan_column_dict = {u'清算组成员':'liquidation_member',
                            u'清算组负责人':'liquidation_pic'}

dongchandiyadengji_column_dict = {u'序号':'Chattel_Mortgage:chattelmortgage_no',
                                  u'登记编号':'Chattel_Mortgage:chattelmortgage_registrationno',
                                  u'登记日期':'Chattel_Mortgage:chattelmortgage_registrationdate',
                                  u'登记机关':'Chattel_Mortgage:chattelmortgage_registrationinstitution',
                                  u'被担保债权数额':'Chattel_Mortgage:chattelmortgage_guaranteedamount',
                                  u'状态':'Chattel_Mortgage:chattelmortgage_status',
                                  u'公示日期':'Chattel_Mortgage:chattelmortgage_announcedate',
                                  u'详情':'Chattel_Mortgage:chattelmortgage_details'}

guquanchuzhidengji_column_dict = {u'序号':'Equity_Pledge:equitypledge_no',
                                  u'登记编号':'Equity_Pledge:equitypledge_registrationno',
                                  u'出质人':'Equity_Pledge:equitypledge_pledgor',
                                  u'证照/证件号码1':'Equity_Pledge:equitypledge_pledgorid',
                                  u'证照/证件号码（类型）':'Equity_Pledge:equitypledge_pledgorid',
                                  u'证照/证件号码':'Equity_Pledge:equitypledge_pledgorid',   #tian
                                  u'出质股权数额':'Equity_Pledge:equitypledge_amount',
                                  u'质权人':'Equity_Pledge:equitypledge_pawnee',
                                  u'证照/证件号码1':'Equity_Pledge:equitypledge_pawneeid',
                                  u'证照/证件号码（类型）':'Equity_Pledge:equitypledge_pledgorid',
                                  u'证照/证件号码':'Equity_Pledge:equitypledge_pawneeid',  #tian
                                  u'股权出质设立登记日期':'Equity_Pledge:equitypledge_registrationdate',
                                  u'状态':'Equity_Pledge:equitypledge_status',
                                  u'公示日期':'Equity_Pledge:equitypledge_announcedate',
                                  u'变化情况':'Equity_Pledge:equitypledge_change'}

xingzhengchufa_column_dict = {u'序号':'Administrative_Penalty:penalty_no',
                              u'行政处罚决定书文号':'Administrative_Penalty:penalty_code',
                              u'违法行为类型':'Administrative_Penalty:penalty_illegaltype',
                              u'行政处罚内容':'Administrative_Penalty:penalty_decisioncontent',
                              u'作出行政处罚决定机关名称':'Administrative_Penalty:penalty_decisioninsititution',
                              u'作出行政处罚决定日期':'Administrative_Penalty:penalty_decisiondate',
                              u'公示日期':'Administrative_Penalty:penalty_announcedate',
                              u'详情':'Administrative_Penalty:penalty_details'}

jingyingyichang_column_dict = {u'序号':'Business_Abnormal:abnormal_no',
                               u'列入经营异常名录原因':'Business_Abnormal:abnormal_events',
                               u'列入日期':'Business_Abnormal:abnormal_datesin',
                               u'移出经营异常名录原因':'Business_Abnormal:abnormal_moveoutreason',
                               u'移出日期':'Business_Abnormal:abnormal_datesout',
                               u'作出决定机关':'Business_Abnormal:abnormal_decisioninstitution',
                               u'作出决定机关(列入)':'Business_Abnormal:abnormal_decisioninstitution(in)',
                               u'作出决定机关(移出)':'Business_Abnormal:abnormal_decisioninstitution(out)'
                               }

yanzhongweifa_column_dict = {u'序号':'Serious_Violations:serious_no',
                             u'列入严重违法企业名单原因':'Serious_Violations:serious_events',
                             u'列入日期':'Serious_Violations:serious_datesin',
                             u'移出严重违法企业名单原因':'Serious_Violations:serious_moveoutreason',
                             u'移出日期':'Serious_Violations:serious_datesout',
                             u'作出决定机关':'Serious_Violations:serious_decisioninstitution'}

chouchajiancha_column_dict = {u'序号':'Spot_Check:check_no',
                              u'检查实施机关':'Spot_Check:check_institution',
                              u'类型':'Spot_Check:check_type',
                              u'日期':'Spot_Check:check_date',
                              u'结果':'Spot_Check:check_result',
                              u'备注':'Spot_Check:check_remark'}