import cv2
import tesseract
import os
import os.path
from uuid import uuid1
import sys


api = tesseract.TessBaseAPI()
api.Init(os.path.dirname(__file__) + r'\tessdata', 'eng', tesseract.OEM_DEFAULT)
api.SetVariable('tesseract_char_whitelist', '1234567890+-xX')
# api.SetVariable('tesseract_char_blacklist', 'abcdefghijklmnopqrstuvwtzABCDEFGHIJKLMNOPQRSTUVWYZ')

black_set = set(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'])


def img_denoise(src):
    gray = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
    (t, thresh) = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    # cv2.imshow("0",thresh)
    # cv2.waitKey(0)
    return thresh


def recognize_yzm(yzm_path):
    global api, black_set
    img = cv2.imread(yzm_path, 1)
    try:
        b, g, r = cv2.split(img)
    except Exception, e:
        return ""
    for i in range(8, 26):
        for j in range(20, 85):
            if g[i][j] > 100 and r[i][j] > 100:
                b[i][j] = 255
                g[i][j] = 255
                r[i][j] = 255
    merged = cv2.merge([b, g, r])
    img_1 = merged[8:26, 21:34]  # first number
    img_2 = merged[12:26, 47:61]  # operator
    img_3 = merged[8:26, 71:84]  # second number

    img_list = [img_1, img_2, img_3]
    numbers = []
    tmp_file = str(uuid1()) + '.jpg'
    try:
        for i in range(0, 3):
            im = img_denoise(img_list[i])
            cv2.imwrite(tmp_file, im)
            tmp_buffer = open(tmp_file, "rb").read()
            result = tesseract.ProcessPagesBuffer(tmp_buffer, len(tmp_buffer), api)
            # result = result.decode("UTF-8", 'ignore')
            # result = result.encode("GBK", "ignore")
            # res = result.rstrip()
            res = result.split('\n')[0].strip()
            numbers.append(res)
    except Exception:
        if os.path.exists(tmp_file):
            os.remove(tmp_file)
    if os.path.exists(tmp_file):
        os.remove(tmp_file)
    else:
        print 'no such file:%s' % tmp_file
    # print numbers
    if numbers[0] in black_set or numbers[2] in black_set:
        return ""
    else:
        if numbers[1] in ('X', 'x'):
            return int(numbers[0]) * int(numbers[2])
        elif numbers[1] == '+':
            return int(numbers[0]) + int(numbers[2])
        elif numbers[1] == '-':
            return int(numbers[0]) - int(numbers[2])
        else:
            return ""


if __name__ == '__main__':
    path = sys.argv[1]
    print recognize_yzm(path)
