# clean up entries in postgres with api

# import stuff
from configparser import ConfigParser
import suji
import regex as re
from pprint import pprint
import requests

# get necessary info for using api
parser = ConfigParser()
parser.read('api_config.txt')
api = parser.get('api', 'address')
api_user = parser.get('api', 'user')
api_user_pw = parser.get('api', 'pw')

# basic Japanese processing info
FULL2HALF = dict((i + 0xFEE0, i) for i in range(0x21, 0x7F))
FULL2HALF[0x3000] = 0x20
katakana_chart = "ァアィイゥウェエォオカガキギクグケゲコゴサザシジスズセゼソゾタダチヂッツヅテデトドナニヌネノハバパヒビピフブプヘベペホボポマミムメモャヤュユョヨラリルレロヮワヰヱヲンヴヵヶヽヾ"
hiragana_chart = "ぁあぃいぅうぇえぉおかがきぎくぐけげこごさざしじすずせぜそぞただちぢっつづてでとどなにぬねのはばぱひびぴふぶぷへべぺほぼぽまみむめもゃやゅゆょよらりるれろゎわゐゑをんゔゕゖゝゞ"
hir2kat = str.maketrans(hiragana_chart, katakana_chart)
kat2hir = str.maketrans(katakana_chart, hiragana_chart)


def add_fullstops(txt, lang="jp"):
    if lang == "jp":
        txt += "。"
        one_fullstop = re.compile(r"[。\\.\s\\？\\！\\?\\!\\…\\｡]+$").sub("。", txt)
    else:
        txt += "."
        one_fullstop = re.compile(r"[。\\.\s\\？\\！\\?\\!\\…\\｡]+$").sub(".", txt)
    return one_fullstop


def fix_watashi(txt):
    replace_txt = re.compile(r"私").sub("わたし", txt)
    return replace_txt


def fix_watakushi(txt):
    replace_txt = re.compile(r"わたくし").sub("わたし", txt)
    return replace_txt


def no_spaces(txt, lang="jp"):
    if lang == "jp":
        no_space = re.compile(r"\s+").sub("", txt)
    else:
        no_space = re.compile(r"\s+").sub(" ", txt)
    return no_space


def no_punctuation(txt):
    no_punct = re.compile(r"[…\[\]\\?\\!\\.\\,、「」？！]*").sub("", txt)
    return no_punct


def clean_kanji(txt):
    txt1 = no_spaces(txt, lang="jp")
    txt2 = add_fullstops(txt1, lang="jp")
    return txt2


def clean_reading(txt):
    txt1 = no_punctuation(txt)
    txt2 = no_spaces(txt1, lang="jp")
    txt3 = add_fullstops(txt2, lang="jp")
    txt4 = fix_watakushi(txt3)
    return txt4


def clean_english(txt):
    txt1 = no_spaces(txt, lang="en")
    txt2 = add_fullstops(txt1, lang="en")
    return txt2


def update_array(old_list, new_list, col_name, sid, params):
    for i, old in enumerate(old_list):
        if old != new_list[i]:
            this_param = params.copy()
            this_param["sentence_id"] = sid
            this_param["edit_type"] = "edit"
            if col_name not in ["reading", "ginza_str"]:
                this_param["prev"] = old
            this_param[col_name] = new_list[i]
            update = requests.get(api + "/sentence/edit", params=this_param)
            update_msg = update.json()
            update_msg["from"] = old
            update_msg["new"] = new_list[i]
            print(update_msg)
    return None


# get list of ids from db
api_params = {"user_display": api_user, "user_key": api_user_pw}
response = requests.get(api+"/sentence/list", params=api_params)
sentence_list = response.json()['sentence_id']


for sentence_id in sentence_list:
    sentence_params = api_params.copy()
    sentence_params['id'] = sentence_id
    response = requests.get(api + "/sentence/get", params=sentence_params)
    json_response = response.json()
    for key in json_response.keys():
        print("Checking "+str(key)+"...")
        s = json_response[key]
        new_display = [clean_kanji(d) for d in s["display"]]
        new_ginza_str = clean_kanji(s["ginza_str"])
        new_reading = clean_reading(s["reading"])
        new_english = [clean_english(d) for d in s["english"]]
        if set(new_display) != set(s["display"]):
            print("Updating display")
            update_array(s["display"], new_display, "display", sentence_id, api_params)
        if new_ginza_str != s["ginza_str"]:
            print("Updating ginza_str")
            update_array([s["ginza_str"]], [new_ginza_str], "ginza_str", sentence_id, api_params)
        if new_reading != s["reading"]:
            print("Updating reading")
            update_array([s["reading"]], [new_reading], "reading", sentence_id, api_params)
        if set(new_english) != set(s["english"]):
            print("Updating english")
            update_array(s["english"], new_english, "english", sentence_id, api_params)
        if set(new_display) != set(s["display"]) or new_ginza_str != s["ginza_str"] or set(new_english) != set(s["english"]):
            input("Manual Check Please...")


