# coding: utf-8
import copy
import datetime
import math

import pymongo
from scipy.interpolate import CubicSpline
import hoshino
from hoshino.res import R
from nonebot import MessageSegment
from hoshino.modules.priconne import chara
from hoshino.util import concat_pic, pic2b64


class Argot:
    def __init__(self):
        self.argot_map = {}
        self.nickname_map = {}
        self.chara_map = {}
        self.load_argots('/etc/hoshino/pcr.csv')

    def load_argots(self, filepath):
        with open(filepath, encoding='gbk') as fp:
            lines = fp.readlines()
            for line in lines:
                parts = line.split(',')
                if len(set(parts)) == 1:
                    continue
                argots = parts[1:]
                name = parts[2].strip()
                self.argot_map[name] = list(i.strip() for i in filter(lambda x: x, set(argots)))
                self.nickname_map[name] = argots[3] or argots[0] or argots[1]
                self.nickname_map[name] = self.nickname_map[name].strip()
                self.chara_map[name] = chara.Chara(parts[0])

    def find(self, keyword):
        result = {
                    1: list(),
                    2: list(),
                    3: list()
        }
        for name, argots in self.argot_map.items():
            for argot in argots:
                if argot == keyword:
                    result[1].append((name, argot))
                elif argot.startswith(keyword):
                    result[2].append((name, argot))
                elif keyword in argot:
                    result[3].append((name, argot))

        def clean(argot_list):
            new_list = []
            for i in range(len(argot_list)):
                for j in range(len(new_list)):
                    if new_list[j][0] == argot_list[i][0]:
                        new_list[j] = (new_list[j][0], '{}/{}'.format(new_list[j][1], argot_list[i][1]))
                        break
                else:
                    new_list.append(argot_list[i])
            return new_list
        result[1] = clean(result[1])
        result[2] = clean(result[2])
        result[3] = clean(result[3])
        def merge(from_list, to_list):
            new_from_list = []
            new_to_list = copy.copy(to_list)
            for n, a in from_list:
                for i in range(len(new_to_list)):
                    if new_to_list[i][0] == n:
                        new_to_list[i] = (new_to_list[i][0], '{}/{}'.format(new_to_list[i][1], a))
                        break
                else:
                    new_from_list.append((n, a))
            return new_from_list, new_to_list

        result[3], result[2] = merge(result[3], result[2])
        result[2], result[1] = merge(result[2], result[1])
        result[3], result[1] = merge(result[3], result[1])
        return result[1] + result[2] + result[3]

    def get_nickname(self, name):
        return self.nickname_map.get(name, name)

    def get_chara(self, name):
        c = self.chara_map.get(name)
        return c

argots = Argot()

def find_chars(character_names):
    db = pymongo.MongoClient()['arenadb']
    collection = db['arena']
    # print(character_names)
    result = collection.find({'defense.characters': {'$all': character_names}})
    result = list(result)
    result = list(filter(lambda battle: battle['good'] + battle['bad'] >= 5, result))
    return result


def elapse_rate(days):
    x = [0, 1, 7, 14, 30, 90, 180, 365, 730, 1000, 2000]
    y = [1, 0.999, 0.998, 0.995, 0.99, 0.9, 0.4, 0.2, 0.12, 0.06, 0.03]
    s = CubicSpline(x, y)
    return math.pow(s(days), 2)


def rate(good, bad, updated):
    rate_factor = (good + 1) / (bad + 1)
    count_factor = max(math.sqrt(math.log(good + bad, 10)), 1)
    elapse_factor = elapse_rate((datetime.date.today() - updated.date()).days)
    return rate_factor * count_factor * elapse_factor


def format_battles(battles, argots):
    charas = [chara.Chara.gen_team_pic([argots.get_chara(c) for c in battle['attack']['characters']] + [argots.get_chara(c) for c in battle['defense']['characters']], extra='↑{}/{}↓ {}'.format(battle['good'], battle['bad'], battle['updated'].date())) for battle in battles]
    charas = concat_pic(charas)
    charas = pic2b64(charas)
    charas = str(MessageSegment.image(charas))
    return charas

def print_battle(battle, argots):
    result = '{} {} {} {} {} -> {} {} {} {} {}  ↑{}/{}↓ {}'.format(
        argots.get_nickname(battle['attack']['characters'][0]),
        argots.get_nickname(battle['attack']['characters'][1]),
        argots.get_nickname(battle['attack']['characters'][2]),
        argots.get_nickname(battle['attack']['characters'][3]),
        argots.get_nickname(battle['attack']['characters'][4]),
        argots.get_nickname(battle['defense']['characters'][0]),
        argots.get_nickname(battle['defense']['characters'][1]),
        argots.get_nickname(battle['defense']['characters'][2]),
        argots.get_nickname(battle['defense']['characters'][3]),
        argots.get_nickname(battle['defense']['characters'][4]),
        battle['good'],
        battle['bad'],
        battle['updated'].date(),
        # rate(battle['good'], battle['bad'], battle['updated']),
        # battle['note']
        )
    return result


def execute(character_argots):
    character_names = []
    msg = []
    for argot in character_argots:
        character = argots.find(argot)
        if not character:
            return ['找不到对应角色：{}'.format(argot)]
        character_names.append(character[0][0])
    if character_names:
        msg.append('查询角色: {}'.format([argots.get_nickname(i) for i in character_names]))

        battles = find_chars(character_names)
        if battles:
            battles.sort(
                key=lambda battle: rate(battle['good'], battle['bad'], battle['updated']), reverse=True)
            battles = battles[:5]
            msg.append(format_battles(battles, argots))
            #for battle in battles[:5]:
            #    msg.append('{}'.format(print_battle(battle, argots)))
        else:
            msg.append('找不到对应的竞技场防守队伍')
    return msg
#
#
#
#
# def run():
#     character_names = []
#     argots = Argot()
#     while True:
#         print('Chosen characters: {}'.format([argots.get_nickname(i) for i in character_names]))
#         print('Character keyword: '),
#         keyword = input().strip()
#         print(keyword)
#         if keyword == '$':
#             return
#         if keyword == '#':
#             break
#         if not keyword:
#             continue
#         results = argots.find(keyword)
#         if len(results) == 0:
#             print('{} not found, try other keywords.'.format(keyword))
#         else:
#             i = 1
#             for name, argot in results:
#                 print('{}: {} ({})'.format(i, argot, name))
#                 i += 1
#             if len(results) == 1:
#                 character_names.append(results[0][0])
#             else:
#                 print('Which: '),
#                 chosen = input()
#                 if not chosen.strip():
#                     chosen = '1'
#
#                 if chosen.isdigit() and 0 < int(chosen) <= len(results):
#                     chosen_char = results[int(chosen)-1][0]
#                     if chosen_char in character_names:
#                         print('{} already in chosen list'.format(chosen_char))
#                     else:
#                         character_names.append(chosen_char)
#                 else:
#                     print('Unknown chosen {}'.format(chosen))
#     if character_names:
#         battles = find_chars(character_names)
#         battles.sort(
#             key=lambda battle: rate(battle['good'], battle['bad'], battle['updated']), reverse=True)
#         for battle in battles[:50]:
#             print_battle(battle, argots)
#
if __name__ == '__main__':
    print('\n'.join(execute(['吃货', '黄骑', '老师'])))
