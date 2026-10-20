#!/usr/bin/env python3
from pdf2image import convert_from_path
from PIL import Image
import gc
import os
import sys
import shutil
import traceback
from glob import glob
from tqdm import tqdm
from getopt import gnu_getopt as getopt

def usage():
    USAGE = """
把pdf转成图像，再存成pdf。专治那些矢量笔迹过多、文件又大导致很难打开的pdf
使用前请安装两项依赖：
(1) pip install pdf2image
(2) poppler
 -- mac: conda install -c conda-forge poppler 或者 brew install poppler
 -- linux 一般不用额外安装，除非提示错误，安装 poppler-utils
 -- win需要 https://github.com/oschwartz10612/poppler-windows/releases/ 并按要求添加到环境变量

用法：
(1) python3 pdf_to_png_to_pdf.py -d "dir_of_pdfs" 将优化所给目录下所有大于10M的PDF。生成的文件命名为 原文件名+_TOPNGTOPDF，放在原来的目录下
(2) python3 pdf_to_png_to_pdf.py -f "path_of_pdf" 将优化单个PDF
(3) 以上两种用法，加上 --clean 或 -c 参数，会把优化前的原pdf自动清理（移动）到原目录下的compressed文件夹里


注意事项：
  极个别PDF会在转换后丢失矢量笔迹。如果转换后发现是空白的作业（只有题目而没有做），需要double check原文件

    """
    print(USAGE)
    sys.exit(0)


# def size_large_10M(path):
#     if os.stat(path).st_size > maxsize_MB*1024*1024:
#         return True
#     else:
#         return False

def size_large_XM(maxsize_MB):
    def fun(path):
        if os.stat(path).st_size > maxsize_MB*1024*1024:
            return True
        else:
            return False
    return fun


if __name__ == '__main__':
    big_files = []
    maxsize_MB = 10
    CLEAN = False

    opts, args = getopt(sys.argv[1:], 'd:f:s:ch', ['dir=', 'file=', 'clean', 'help', 'size'])
    for opt_name, opt_value in opts:
        if opt_name in ('-h', '--help'):
            usage()
        if opt_name in ('-f', '--file'):
            file = opt_value
            if file[0] == "'" or file[0] == '"':
                file = file[1:-1]
            big_files = [file,]
        if opt_name in ('-d', '--dir'):
            searchdir = opt_value
            if searchdir[0] == "'" or searchdir[0] == '"':
                searchdir = searchdir[1:-1]
            if searchdir[-1] == os.sep:
                searchdir = searchdir[:-1]
            list_of_files = filter(os.path.isfile, glob(searchdir + os.sep +'*'))
            # big_files = list(filter(size_large_XM(maxsize_MB), list_of_files))
            big_files = list(list_of_files)
        if opt_name in ('-c', '--clean'):
            CLEAN = True
        if opt_name in ('-s', '--size'):
            maxsize_MB = int(opt_value)

    if len(big_files) == 0:
        usage()

    print(f"Optimizing {len(big_files)} files")

    for pdfin in tqdm(big_files):
        try:
            images = convert_from_path(pdfin)

            # check size
            max_long_size_px = 2224 # ipad pro 10.5 = 2224*1668
            if images[0].size[0] > max_long_size_px: 
                for i in range(len(images)):
                    images[i] = images[i].resize(
                        (max_long_size_px, int(images[i].size[1]/images[i].size[0] * max_long_size_px)), 
                        Image.ANTIALIAS)

            pdfout = os.path.splitext(pdfin)[0] + \
                "_TOPNGTOPDF" + os.path.splitext(pdfin)[1]
            images[0].save(
                pdfout, "PDF", resolution=100.0, save_all=True, append_images=images[1:], optimize=True, quality=75)
            del images
            gc.collect()

        except Exception as e:
            print(f"Exception of {pdfin}:")
            print(traceback.format_exc())

    if CLEAN:
        collectfolder = os.path.dirname(pdfin) + os.sep + "compressed"
        if not os.path.isdir(collectfolder):
            os.mkdir(collectfolder)
        for pdfin in big_files:
            shutil.move(pdfin, collectfolder + os.sep + os.path.basename(pdfin))

