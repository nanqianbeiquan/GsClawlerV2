# coding=utf-8
import re

x = '''
ProgrammingError: ('42000', "[42000] [Microsoft][ODBC SQL Server Driver][SQL Server]'Opx5m4WBYJnFe2TtLD0N0DgSjSF60hHp' \xb8\xbd\xbd\xfc\xd3\xd0\xd3\xef\xb7\xa8\xb4\xed\xce\xf3\xa1\xa3 (102) (SQLExecDirectW)")
'''.decode('gbk')
print x