import numpy as np
import cv2
from uuid import uuid1


def clear_single_point(img_dilate):
    for i in range(img_dilate.shape[0]):
        for j in range(img_dilate.shape[1]):
            if i == 0 or i == img_dilate.shape[0]-1 or j == img_dilate.shape[1]-1 or j == 0:
                img_dilate[i][j] = 255
            else:
                if img_dilate[i-1][j-1] == 255 \
                        and img_dilate[i][j-1] == 255 \
                        and img_dilate[i+1][j-1] == 255 \
                        and img_dilate[i+1][j] == 255 \
                        and img_dilate[i+1][j+1] == 255 \
                        and img_dilate[i][j+1] == 255 \
                        and img_dilate[i][j+1] == 255 \
                        and img_dilate[i-1][j+1] == 255 \
                        and img_dilate[i-1][j] == 255:
                    img_dilate[i][j] = 255


def denoise(src):
    cv2.copyMakeBorder(src, 1, 1, 1, 1, cv2.BORDER_CONSTANT, 255)
    for i in range(1, src.shape[0]-1):
        for j in range(1, src.shape[1]-1):
            if src[i][j] == 0 \
                    and src[i-1][j-1] == 0 \
                    and src[i][j-1] == 255 \
                    and src[i+1][j-1] == 255 \
                    and src[i+1][j] == 255 \
                    and src[i+1][j+1] == 255 \
                    and src[i][j+1] == 255 \
                    and src[i-1][j+1] == 255 \
                    and src[i-1][j] == 255:
                src[i][j] = 255
                src[i-1][j-1] = 255
            if src[i][j] == 0 \
                    and src[i+1][j+1] == 0 \
                    and src[i][j-1] == 255 \
                    and src[i+1][j-1] == 255 \
                    and src[i+1][j] == 255 \
                    and src[i][j+1] == 255 \
                    and src[i-1][j+1] == 255 \
                    and src[i-1][j] == 255 \
                    and src[i-1][j-1] == 255:
                src[i][j] = 255
                src[i+1][j+1] = 255
            if src[i][j] == 0 \
                    and src[i+1][j-1] == 0 \
                    and src[i][j-1] == 255 \
                    and src[i+1][j] == 255 \
                    and src[i+1][j+1] == 255 \
                    and src[i][j+1] == 255 \
                    and src[i-1][j+1] == 255 \
                    and src[i-1][j] == 255 \
                    and src[i-1][j-1] == 255:
                src[i][j] = 255
                src[i+1][j-1] = 255
            if src[i][j] == 0 \
                    and src[i-1][j+1] == 0 \
                    and src[i][j-1] == 255 \
                    and src[i+1][j-1] == 255 \
                    and src[i+1][j] == 255 \
                    and src[i+1][j+1] == 255 \
                    and src[i][j+1] == 255 \
                    and src[i-1][j] == 255 \
                    and src[i-1][j-1] == 255:
                src[i][j] = 255
                src[i-1][j+1] = 255


def fill_small_blob(src):
    (cnt, h) = cv2.findContours(src.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    # sort in ascending order to find the smallest blob
    C = sorted(cnt, key=cv2.contourArea)[0]
    for i in range(0, len(cnt)-1):
        if len(cnt) == 1:
            return src
        else:
            area1 = cv2.contourArea(cnt[i])
            area2 = cv2.contourArea(cnt[i+1])
            if abs(area1 - area2) > 13:
                cv2.drawContours(src, C, -1, 0, 3)
                fill_small_blob(src)


def top_bottom(src):
    # RGB to Gray
    gray = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
    (t, thresh) = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    # thresh = cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,11,2)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 1))
    imgdilate = cv2.dilate(thresh, kernel)
    clear_single_point(imgdilate)
    gray_ero = cv2.bitwise_not(imgdilate)
    gray_ero = cv2.dilate(gray_ero, None, iterations=1)
    fill_small_blob(gray_ero)
    gray_ero = cv2.dilate(gray_ero, None, iterations=4)  # dilate target area run 3 times
    (cnts, hierarchy) = cv2.findContours(gray_ero.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # sort in descending order
    c = sorted(cnts, key=cv2.contourArea, reverse=True)[0]
    if (len(cnts)) == 1:
        x, y, w, h = cv2.boundingRect(c)
        bottom = y+h
        top = y 
        return bottom, top
    if (len(cnts)) == 2:
        x0, y0, w0, h0 = cv2.boundingRect(cnts[0])
        x1, y1, w1, h1 = cv2.boundingRect(cnts[1])
        a = [y0, y1, y0+h0, y1+h1]
        top = sorted(a)[0]  # the smallest value of list
        bottom = sorted(a)[-1]  # the biggest value of list
        return bottom, top
    if (len(cnts)) == 3:
        x0, y0, w0, h0 = cv2.boundingRect(cnts[0])
        x1, y1, w1, h1 = cv2.boundingRect(cnts[1])
        x2, y2, w2, h2 = cv2.boundingRect(cnts[2])
        a = [y0, y1, y2, y0+h0, y1+h1, y2+h2]
        top = sorted(a)[0] # the smallest value of list
        bottom = sorted(a)[-1] # the biggest value of list
        return bottom, top


def location_character(img):
    (y_bottom, y_top) = top_bottom(img)
    img_temp = img[y_top:y_bottom, 0:img.shape[1]]
    return img_temp


def binary_character(src):
    gray = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
    (t, thresh) = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    # thresh = cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,11,2)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 1))
    imgdilate = cv2.dilate(thresh, kernel)
    tmp_path = str(uuid1()) + '.jpg'
    cv2.imwrite(tmp_path, imgdilate)
    return tmp_path, imgdilate

