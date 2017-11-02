# coding=utf-8
import cv2
import proc
import tesseract
import sys
import os
import types

api = tesseract.TessBaseAPI()
tessdata_path = os.path.dirname(__file__) + r'\tessdata'
api.Init(tessdata_path, 'chi_sim', tesseract.OEM_DEFAULT)


def recognize(filename, target):
    global api
    api.SetVariable("tessedit_char_whitelist", target.encode("UTF-8", 'ignore'))
    img = cv2.imread(filename)
    try:
        height = img.shape[0]
    except:
        return u""
#     width = img.shape[1]
    img_1 = img[0:height, 9:29]  # first character
    img_2 = img[0:height, 46:66]  # seconde character
    img_3 = img[0:height, 83:103]  # third character
    img_4 = img[0:height, 120:140]  # fourth character
    img_list = [img_1, img_2, img_3, img_4]
    answer1 = u""
    answer2 = u""
    score_dict = dict.fromkeys(target.split(','), 0)
    for im in img_list:
        tmp_file, im_temp = proc.binary_character(im)
        if im_temp.shape[0] < 13:
            pass
        else:
            # tmp_file = '1.jpg'
            # tmp_file = str(uuid1())+".jpg"
            tmp_buffer = open(tmp_file, "rb").read()
            result = tesseract.ProcessPagesBuffer(tmp_buffer, len(tmp_buffer), api)
            if not isinstance(result, types.NoneType):
                result = result.decode("UTF-8", "ignore")
                # result = result.encode("GBK", "ignore")
                result = result.strip()
                result = result[:1]
            if not isinstance(result, types.NoneType):
                if result in target:
                    answer1 += result
                else:
                    answer1 += u"ĳ"
                for key in score_dict:
                    if result in key:
                        score_dict[key] += 1
            os.remove(tmp_file)
    max_score = 0
    for key in score_dict:
        score = score_dict.get(key)
        if score >= max_score:
            max_score = score
            answer2 = key
    word1 = [word for word in answer1 if word not in answer2]
    word2 = [word for word in answer2 if word not in answer1]
    if len(word1) == 0 and len(word2) == 0:
        answer = answer1
    elif len(word1) == 2 and len(word2) == 0:
        answer = answer1.replace(word1[0], [word for word in word2 if word2.count(word) > 1][0])
    elif len(word1) == 1 and len(word2) == 1:
        answer = answer1.replace(word1[0], word2[0])
    else:
        answer = u''
    return answer
