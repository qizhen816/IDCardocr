import time
import re
import numpy as np
import cv2
import threading
import pytesseract

FLANN_INDEX_KDTREE = 0
MIN_MATCH_COUNT = 10
MASK_IMG_NAME = 'img/idcard_mask.jpg'
x = 1280.00 / 3840.00
pixel_x = int(x * 3840)


class Ocr(object):
    def find_id_number(self, crop_gray, crop_org):
        template = cv2.UMat(cv2.imread('img/id_number_mask_%s.jpg' % pixel_x, 0))
        w, h = cv2.UMat.get(template).shape[::-1]
        res = cv2.matchTemplate(crop_gray, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        top_left = (max_loc[0] + w, max_loc[1] - int(20 * x))
        bottom_right = (top_left[0] + int(2300 * x), top_left[1] + int(300 * x))
        result = cv2.UMat.get(crop_org)[top_left[1] - 10:bottom_right[1], top_left[0] - 10:bottom_right[0]]
        cv2.rectangle(crop_gray, top_left, bottom_right, 255, 2)

        _, _, red = cv2.split(cv2.UMat(result))
        red = cv2.UMat(red)

        return self.get_result_vary_length(red, 'eng', '--psm 8 ')

    def find_sex(self, crop_gray, crop_org):
        template = cv2.UMat(cv2.imread('img/sex_mask_%s.jpg' % pixel_x, 0))
        w, h = cv2.UMat.get(template).shape[::-1]
        res = cv2.matchTemplate(crop_gray, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        top_left = (max_loc[0] + w, max_loc[1] - int(20 * x))
        bottom_right = (top_left[0] + int(300 * x), top_left[1] + int(300 * x))
        result = cv2.UMat.get(crop_org)[top_left[1] - 10:bottom_right[1], top_left[0] - 10:bottom_right[0]]
        cv2.rectangle(crop_gray, top_left, bottom_right, 255, 2)

        _, _, red = cv2.split(cv2.UMat(result))
        red = cv2.UMat(red)
        red = cv2.adaptiveThreshold(red, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 151, 50)
        red = img_resize(red, 150)

        return self.get_result_vary_length(red, 'chi_sim', config='--psm 10')

    def find_address(self, crop_gray, crop_org):
        template = cv2.UMat(cv2.imread('img/address_mask_%s.jpg' % pixel_x, 0))
        w, h = cv2.UMat.get(template).shape[::-1]
        res = cv2.matchTemplate(crop_gray, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        top_left = (max_loc[0] + w, max_loc[1] - int(20 * x))
        bottom_right = (top_left[0] + int(1700 * x), top_left[1] + int(650 * x))
        result = cv2.UMat.get(crop_org)[top_left[1] - 10:bottom_right[1], top_left[0] - 10:bottom_right[0]]
        cv2.rectangle(crop_gray, top_left, bottom_right, 255, 2)

        return self.get_address(cv2.UMat(result))

    def get_address(self, img):
        _, _, red = cv2.split(img)
        red = cv2.UMat(red)
        red = cv2.adaptiveThreshold(red, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 151, 50)
        red = img_resize(red, 450)

        return self.punc_filter(self.get_result_vary_length(red, 'chi_sim'))

    def get_name(self, img):
        _, _, red = cv2.split(img)
        red = cv2.UMat(red)
        red = cv2.adaptiveThreshold(red, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 151, 50)
        red = img_resize(red, 150)

        return self.punc_filter(self.get_result_vary_length(red, 'chi_sim'))

    def get_result_vary_length(self, red, langset, config='--psm 6'):
        red_org = red
        rec, red = cv2.threshold(red, 127, 255, cv2.THRESH_BINARY_INV)

        image, contours, hierarchy = cv2.findContours(red, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(red, contours, -1, (255, 255, 255), 1)
        numset_contours = []
        height_list = []
        width_list = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            height_list.append(h)
            width_list.append(w)
        height_list.remove(max(height_list))
        width_list.remove(max(width_list))
        height_threshold = 0.70 * max(height_list)
        width_threshold = 1.4 * max(width_list)
        big_rect = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if h > height_threshold and w < width_threshold:
                numset_contours.append((x, y, w, h))
                big_rect.append((x, y))
                big_rect.append((x + w, y + h))

        result_string = ''
        result_string += pytesseract.image_to_string(cv2.UMat.get(red_org),
                                                     lang=langset,
                                                     config=config)
        return self.punc_filter(result_string)

    def punc_filter(self, context):
        xx = u"([\u4e00-\u9fff0-9A-Z]+)"
        pattern = re.compile(xx)
        results = pattern.findall(context)
        result = ""
        for _result in results:
            result += _result

        return result

    def show_img(self, img):
        cv2.namedWindow("contours", 0)
        cv2.resizeWindow("contours", 1600, 1200)
        cv2.imshow("contours", img)
        cv2.waitKey()

    def find_name(self, crop_gray, crop_org):
        template = cv2.UMat(cv2.imread('img/name_mask_%s.jpg' % pixel_x, 0))
        w, h = cv2.UMat.get(template).shape[::-1]
        res = cv2.matchTemplate(crop_gray, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        top_left = (max_loc[0] + w, max_loc[1] - int(20 * x))
        bottom_right = (top_left[0] + int(700 * x), top_left[1] + int(300 * x))

        result = cv2.UMat.get(crop_org)[top_left[1] - 10:bottom_right[1], top_left[0] - 10:bottom_right[0]]
        cv2.rectangle(crop_gray, top_left, bottom_right, 255, 2)

        return self.get_name(cv2.UMat(result))


class FindName(threading.Thread, Ocr):
    def __init__(self, crop_gray, crop_org):
        threading.Thread.__init__(self)
        self.crop_gray = crop_gray
        self.crop_org = crop_org
        self.name = ''

    def run(self):
        template = cv2.UMat(cv2.imread('img/name_mask_%s.jpg' % pixel_x, 0))
        w, h = cv2.UMat.get(template).shape[::-1]
        res = cv2.matchTemplate(self.crop_gray, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        top_left = (max_loc[0] + w, max_loc[1] - int(20 * x))
        bottom_right = (top_left[0] + int(700 * x), top_left[1] + int(300 * x))

        result = cv2.UMat.get(self.crop_org)[top_left[1] - 10:bottom_right[1], top_left[0] - 10:bottom_right[0]]
        cv2.rectangle(self.crop_gray, top_left, bottom_right, 255, 2)

        self.name = self.get_name(cv2.UMat(result))

    @property
    def result(self):
        return self.name


class FindIdNumber(threading.Thread):
    def __init__(self, crop_gray, crop_org):
        threading.Thread.__init__(self)
        self.crop_gray = crop_gray
        self.crop_org = crop_org
        self.id_number = ''

    def run(self):
        time.sleep(5)
        self.id_number = '测试一下id_number'

    @property
    def result(self):
        return self.id_number


class FindSex(threading.Thread):
    def __init__(self, crop_gray, crop_org):
        threading.Thread.__init__(self)
        self.crop_gray = crop_gray
        self.crop_org = crop_org
        self.id_number = ''

    def run(self):
        time.sleep(5)
        self.id_number = '测试一下id_number'

    @property
    def result(self):
        return self.id_number


class IDCard(object):
    def __init__(self, parse_img_name):
        self.parse_img_name = parse_img_name

    def get_result(self):
        id_card = self.find_idcard()
        gray_img, org_img = get_gray_img(id_card)

        find_name = FindName(gray_img, org_img)
        find_id_number = FindIdNumber(gray_img, org_img)
        find_sex = FindSex(gray_img, org_img)

        # 多线程
        data = [find_name, find_id_number, find_sex]
        for thread in data:
            thread.start()

        for thread in data:
            thread.join()

        id_card = {
            'name': find_name.result,
            'id_number': find_id_number.result,
            'sex': find_sex,
        }
        print(id_card)

        #
        # id_number = self.find_id_number(gray_img, org_img)
        # birthday = id_number[6:14]
        #
        # id_card = {
        #     'name': self.find_name(gray_img, org_img),
        #     'address': self.find_address(gray_img, org_img),
        #     'sex': self.find_sex(gray_img, org_img),
        #     'id_number': id_number,
        #     'birthday': birthday
        # }
        # print(id_card)

    def find_idcard(self):
        # imread 读取图片 格式为BGR  IMREAD_GRAYSCALE 以灰度读取一张图片
        mask_img = img_resize(cv2.UMat(cv2.imread(MASK_IMG_NAME, cv2.IMREAD_GRAYSCALE)), 640)

        parse_img = img_resize(cv2.UMat(cv2.imread(self.parse_img_name, cv2.IMREAD_GRAYSCALE)), 1920)
        img_org = img_resize(cv2.UMat(cv2.imread(self.parse_img_name)), 1920)

        sift = cv2.xfeatures2d.SIFT_create()
        # 特征点检测
        kp1, des1 = sift.detectAndCompute(mask_img, None)
        kp2, des2 = sift.detectAndCompute(parse_img, None)

        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=10)

        matches = cv2.FlannBasedMatcher(index_params, search_params).knnMatch(des1, des2, k=2)

        good_matches = [m for m, n in matches if m.distance < 0.7 * n.distance]
        if len(good_matches) < MIN_MATCH_COUNT:
            return

        src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        m, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        h, w = cv2.UMat.get(mask_img).shape
        m_r = np.linalg.inv(m)
        result_img = cv2.warpPerspective(img_org, m_r, (w, h))

        # 找到两幅图片特征点
        # draw_params = dict(matchColor=(0, 255, 0),
        #                    singlePointColor=None,
        #                    matchesMask=mask.ravel().tolist(),
        #                    flags=2)
        # img3 = cv2.drawMatches(mask_img, kp1, parse_img, kp2, good_matches, None, **draw_params)
        # self.show_img(img3)
        # plt.show()

        return result_img


def img_resize(imggray, dwidth):
    crop = imggray
    size = crop.get().shape
    height = size[0]
    width = size[1]
    height = height * dwidth / width
    crop = cv2.resize(src=crop, dsize=(dwidth, int(height)), interpolation=cv2.INTER_CUBIC)

    return crop


def get_gray_img(org_img):
    # 图片尺寸 (410, 640, 3)
    height, width, color = cv2.UMat.get(org_img).shape
    height = int(height * 3840 * x / width)

    # 拉伸原图尺寸与模板一致
    org_img = cv2.resize(src=org_img, dsize=(int(3840 * x), height), interpolation=cv2.INTER_CUBIC)
    _gray_img = cv2.cvtColor(org_img, cv2.COLOR_BGR2GRAY)

    return _gray_img, org_img
