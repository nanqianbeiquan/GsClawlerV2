%~d0
cd %~dp0
for /l %%i in (1,1,10) do start python ../zhe_jiang/ZheJiangUpdateJobQW.py
for /l %%i in (1,1,10) do start python ../guangdong/GuangdongUpdateJob.py
for /l %%i in (1,1,5) do start python ../ning_xia/NingXiaUpdateJob.py