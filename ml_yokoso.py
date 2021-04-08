# parse mailing list sentences from Yokoso and input into database
# make sure to have the grammar ID ready

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

# basic functions for Japanese strings
def is_japanese(string):
    jp_match = re.search(r'[\p{Hiragana}\p{Katakana}\p{Han}]+', string)
    eng_match = re.search(r'[a-zA-Z]+', string)
    if jp_match and not eng_match:
        return True
    else:
        return False

def jpstring_clean(txt):
    # convert any full width numbers etc to half-width
    half_txt = txt.translate(FULL2HALF)
    # remove multiple spaces and replace with standard space
    one_space = re.compile(r"\s+").sub(" ", half_txt)
    # remove all punctuation
    no_punctuation = re.compile(r"[…\[\]\\?\\!\\.\\,]*").sub("", one_space)
    # roman numerals to japanese
    roman_nums = suji.kansuji(no_punctuation, False)
    return roman_nums

def engstring_clean(txt):
    # remove multiple spaces and replace with standard space
    one_space = re.compile(r"\s+").sub(" ", txt)
    # remove all punctuation
    no_punctuation = re.compile(r"[\\\"\[\]\\.]*").sub("", one_space)
    return no_punctuation

# get necessary info to use on api
jp_eng = {}
with open('ml_yokoso.txt', 'r', encoding='utf8') as reader:
    key_val = ""
    for line in reader:
        if is_japanese(line):
            jpstr = line.strip()  # remove new line
            jpstr = jpstring_clean(jpstr)  # only text
            key_val = jpstr
        elif line.startswith("— contributed by:"):
            key_val = ""
        elif len(key_val) > 0:
            jp_eng[key_val] = engstring_clean(line.strip())
            key_val = ""
pprint(jp_eng)  # confirmation
input("Press Enter to continue...")

# insert into api
grammar_id = 75
api_params = {"user_display": api_user, "user_key": api_user_pw}
for jpstr in jp_eng.keys():
    sentence_params = api_params
    sentence_params['display'] = jpstr
    sentence_params['english'] = engstring_clean(jp_eng[jpstr])
    response = requests.get(api+"/sentence/new", params=sentence_params)
    print(response.json())
    if response.status_code != 200:
        print("Manual check on ", jpstr)
        continue
    if "error" in response.json().keys() > 0:
        print("Manual check on ", jpstr)
        continue
    response_txt = response.json()['message']
    pattern = re.compile('id (.*)\\.')
    sentence_id = pattern.search(response_txt).group(1)
    join_params = api_params
    join_params['grammar_id'] = str(grammar_id)
    join_params['sentence_id'] = str(sentence_id)
    response = requests.get(api + "/grammar/add_sentence", params=join_params)
    print(response.json())
