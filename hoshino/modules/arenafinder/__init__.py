import random
import re

from hoshino import aiorequests
from nonebot import NoneBot
from nonebot import CommandSession, MessageSegment, get_bot
from hoshino import util
from hoshino.modules.arenafinder import finder
from hoshino.service import Service, Privilege
from hoshino.util import FreqLimiter

sv = Service('arenafinder', manage_priv=Privilege.SUPERUSER)

conf = util.load_config(__file__)['arenafinder']
lmt = FreqLimiter(5)

DISABLE_NOTICE = '本群日服竞技场查询功能已禁用\n如欲开启，请与维护组联系'

# aliases = ('怎么拆', '怎么解', '怎么打', '如何拆', '如何解', '如何打', '怎麼拆', '怎麼解', '怎麼打', 'jjc查询', 'jjc查詢')
aliases = ()
@sv.on_command('.af', aliases=aliases, deny_tip=DISABLE_NOTICE, only_to_me=False)
async def arena_query_jp(session:CommandSession):
    await _arena_query(session, region=4)


async def _arena_query(session:CommandSession, region:int):

    uid = session.ctx['user_id']

    if not lmt.check(uid):
        session.finish('您查询得过于频繁，请稍等片刻', at_sender=True)
    lmt.start_cd(uid)

    # 处理输入数据
    argv = session.current_arg_text.strip()
    argv = re.sub(r'[?？，,_]', ' ', argv)
    argv = argv.split()
    if 2 >= len(argv):
        session.finish('请输入防守方角色（至少三名），用空格隔开', at_sender=True)
    if 5 < len(argv):
        session.finish('编队不能多于5名角色', at_sender=True)

    msg = finder.execute(argv)

    sv.logger.debug('Arena sending result...')
    await session.send('\n'.join(msg))
    sv.logger.debug('Arena result sent!')
