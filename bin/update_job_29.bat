%~d0
cd %~dp0
for /l %%i in (1,1,10) do start python ../bei_jing/BeiJingUpdateQWJob.py
for /l %%i in (1,1,5) do start python ../jiang_xi/JiangXiUpdateJob.py
for /l %%i in (1,1,10) do start python ../shanghai/ShangHaiUpdateJob.py
