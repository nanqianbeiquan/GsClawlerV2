# coding=utf-8

import re
import requests
import os
import sys
from PIL import Image
import pytesseract

imageobject = Image.open("D:\GsClawlerV2\\temp\\462082698189.jpg")
print imageobject
print pytesseract.image_to_string(imageobject, 'chi_sim')

