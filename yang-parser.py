import string
import re
import json 
import collections
import sys

def delete_pipes(line):
    line = list(line)
    for i in range(0,len(line)):
        if line[i] == '|':
            line[i] = " "
    line = "".join(line)
    return line

def dict_merge(di1, di2):
    for k, _ in di2.items():
        if k in di1:
            if (isinstance(di1[k], dict) and isinstance(di2[k], dict)):
                dict_merge(di1[k], di2[k])
            elif (isinstance(di1[k], list) and isinstance(di2[k], list)):
                dict_merge(di1[k][0], di2[k][0])
        else:
            di1[k] = di2[k]

def check_dict_is_leaf(path):
    if len(path) > 1:
        if path[-1][1] == "is_dict":
            if path[-2][1] == "is_list":
                if path[-1][0] in path[-2][2]:
                    path_elem = path.pop()[0]
                    path.append((path_elem, "is_leaf"))
                    return path
                else:
                    return path
            else:
                return path
        else:
            return path
    else:
        return path

def find_path_for_offset(li, offset):
    for index in range(len(li)-1, -1, -1):
        if li[index]["offset"] == offset:
            return li[index]["path"] 

def find_anchor_offset(offset, offsets):
    return offsets[offsets.index(offset) - 1]

def process(offset, offsets, path_elem, li):
    if offset not in offsets:
        offsets.append(offset)

    path = []
    anchor_offset = find_anchor_offset(offset, offsets)
    path_add = find_path_for_offset(li, anchor_offset)
    path = path_add + path_elem
    temp_di = {}
    temp_di["offset"] = offset
    temp_di["path"] = path
    path = check_dict_is_leaf(path)
    if temp_di["path"][-1][1] == 'is_leaf' or temp_di["path"][-1][1] == 'is_leaflist':
        temp_di["is_leaf_element"] = "true"
    else:
        temp_di["is_leaf_element"] = "false"
    li.append(temp_di)

def parse(file):
    li = []
    di = {}

    offsets = []
    offsets.append(0)

    initial_di = {}
    initial_di["offset"] = 0
    initial_di["path"] = []

    li.append(initial_di)

    with open(file) as f:
        while True:
            line = f.readline().rstrip()
            if not line:
                break
            line = delete_pipes(line)
            
            offset = 0
            for i in line:
                if i != '+':
                    offset +=1
                else:
                    break
            if "*" in line and "[" in line and "]" in line:
                matchObj = re.search(r'^.*\+\-\-rw\s([a-zA-Z0-9.\-_]+)\*\s(.*)$', line)

                if matchObj:
                    keys = matchObj.group(2).strip('][').split(' ')
                    path_elem = [(matchObj.group(1), "is_list", keys)]
                    process(offset, offsets, path_elem, li)

            elif "*" in line:
                matchObj = re.search(r'^.*\+\-\-rw\s([a-zA-Z0-9.\-_]+)\*', line)

                if matchObj:
                    path_elem = [(matchObj.group(1), "is_leaflist")]
                    process(offset, offsets, path_elem, li)
                    
            elif "?" in line:
                matchObj = re.search(r'.*\+\-\-rw\s([a-zA-Z0-9.\-_]+)\?', line)
                
                if matchObj:
                    path_elem = [(matchObj.group(1), "is_leaf")]
                    process(offset, offsets, path_elem, li)
            
            else:
                matchObj = re.search(r'.*\+\-\-rw\s([a-zA-Z0-9.\-_]+)', line)
                
                if matchObj:
                    path_elem = [(matchObj.group(1), "is_dict")]
                    process(offset, offsets, path_elem, li)

    return li

def construct(di, pointer, current_line):
    if len(di) == 0 and pointer != 0:
        if current_line[pointer][1] == 'is_list':
            di[current_line[pointer][0]] = []
        elif current_line[pointer][1] == 'is_dict':
            di[current_line[pointer][0]] = {}
        elif current_line[pointer][1] == 'is_leaflist':
            di[current_line[pointer][0]] = ['leaflist_data']
        elif current_line[pointer][1] == 'is_leaf':
            di[current_line[pointer][0]] = 'leaf_data'

        pointer -= 1
        return construct(di, pointer, current_line)

    elif len(di) != 0 and pointer != 0:
        new_di = {}
        if current_line[pointer][1] == 'is_list':
            new_di[current_line[pointer][0]] = [di]
        elif current_line[pointer][1] == 'is_dict':
            new_di[current_line[pointer][0]] = di
        pointer -= 1
        return construct(new_di, pointer, current_line)

    elif pointer == 0 and current_line[pointer][1] == 'is_list':
        new_di = {}
        new_di[current_line[pointer][0]] = [di]
        return new_di

    elif pointer == 0 and current_line[pointer][1] == 'is_dict':
        new_di = {}
        new_di[current_line[pointer][0]] = di
        return new_di

def construct_all_elements(li, dst):
    for i in li:
        di = {}
        pointer = len(i["path"]) - 1
        elem = construct(di, pointer, i["path"])
        dst.append(elem)

def merge(li):
    if len(li) > 2:
        dict_merge(li[0],li[1])
        li.pop(1)
        return merge(li)
    else:
        return li[0]

def main():
    li = parse(sys.argv[1])[1:]

    leafs_only = [ i for i in li if i['is_leaf_element']=='true' ]

    dicts = []
    construct_all_elements(leafs_only, dicts)

    res = merge(dicts)

    print(json.dumps(res)) 

if __name__ == "__main__":
    main()