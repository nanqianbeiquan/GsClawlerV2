import re

s = '"session.token": "a44a485a-35dd-4039-9ce4-4bb916fef32d"'

print re.findall('"session\.token":\s"(.*?)"', s)[0]