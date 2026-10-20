#!/usr/bin/env python3
import os
import sys
from glob import glob
from zipfile import ZipFile
from getopt import gnu_getopt as getopt

def usage():
    USAGE = '''
用法：
python3 zip_in_100M.py -d "path_to_the_homework_dir"
会把文件夹和子文件夹下的所有文件打包成一堆不超过95M的压缩包
    '''
    print(USAGE)
    sys.exit(0)


def sizeof_MB(path):
    return os.stat(path).st_size/1024/1024


if __name__ == '__main__':
    list_of_files = [] 
    opts, args = getopt(sys.argv[1:], 'd:h', ['dir=', 'help'])
    for opt_name, opt_value in opts:
        if opt_name in ('-h', '--help'):
            usage()
        if opt_name in ('-d', '--dir'):
            searchdir = opt_value
            if searchdir[0] == "'" or searchdir[0] == '"':
                searchdir = searchdir[1:-1]
            if searchdir[-1] == os.sep:
                searchdir = searchdir[:-1]
            list_of_files = list(filter(os.path.isfile, glob(searchdir + os.sep+ '**', recursive=True)))

    if len(list_of_files) == 0:
        usage()

    i = 0
    nzip = 0
    while i < len(list_of_files):
        zipf = ZipFile(f'{searchdir}{os.sep}{nzip}.zip', 'w')
        print(f"Creating zip #{nzip}")
        total_size_this = 0
        while i < len(list_of_files) and sizeof_MB(list_of_files[i]) + total_size_this < 95:
            zipf.write(list_of_files[i])
            total_size_this += sizeof_MB(list_of_files[i])
            i += 1
        zipf.close()
        nzip += 1

