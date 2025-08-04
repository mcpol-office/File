import os
import re
import asyncio
from typing import Set, Dict, List
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register("qq_group_crawler", "Mcpol", "QQ群成员信息爬取插件", "1.0.0", "https://github.com/your-repo")
class QQGroupCrawlerPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.target_group_id = "335881164"
        self.report_qq_id = "3097818372"
        # 保存到本地服务器
        self.save_dir = "./风纪小组名单/"
        self.save_file = os.path.join(self.save_dir, "txt.txt")
        self.processed_members: Set[str] = set()
        
        os.makedirs(self.save_dir, exist_ok=True)
        asyncio.create_task(self.periodic_crawl())
        logger.info("QQ群成员爬取插件已启动")

    async def periodic_crawl(self):
        while True:
            try:
                await self.crawl_group_members()
                await asyncio.sleep(300)
            except Exception as e:
                logger.error(f"定期爬取失败: {e}")
                await asyncio.sleep(60)

    async def crawl_group_members(self):
        try:
            platforms = self.context.platform_manager.get_insts()
            
            for platform in platforms:
                if hasattr(platform, 'get_group_member_list'):
                    try:
                        members = await platform.get_group_member_list(self.target_group_id)
                        if members:
                            await self.process_members(members)
                            logger.info(f"成功爬取到 {len(members)} 个群成员")
                            return
                    except Exception as e:
                        logger.warning(f"平台 {platform.__class__.__name__} 获取群成员失败: {e}")
                        continue
            
            logger.warning("所有平台都无法获取群成员信息")
            
        except Exception as e:
            logger.error(f"爬取群成员信息失败: {e}")

    async def process_members(self, members: List[Dict]):
        for member in members:
            try:
                user_id = str(member.get('user_id', ''))
                nickname = member.get('nickname', '')
                card = member.get('card', '') or nickname
                
                if not user_id or user_id in self.processed_members:
                    continue
                
                parsed_info = self.parse_nickname_format(card)
                
                if parsed_info:
                    await self.save_member_info(user_id, parsed_info)
                    self.processed_members.add(user_id)
                    logger.info(f"保存成员信息: {user_id} - {card}")
                else:
                    await self.report_invalid_format(user_id, card)
                    logger.info(f"报告不符合格式的成员: {user_id} - {card}")
                    
            except Exception as e:
                logger.error(f"处理成员信息失败: {e}")

    def parse_nickname_format(self, nickname: str) -> Dict[str, str]:
        try:
            # 匹配格式: "1组-爱豆(迷你名字)-10001(迷你号)"
            pattern = r'^(\d+)组-([^-]+)\(([^)]+)\)-(\d+)\(([^)]+)\)$'
            match = re.match(pattern, nickname)
            
            if match:
                group_num = match.group(1)
                mini_name = match.group(2)
                mini_id = match.group(4)
                
                return {
                    'group': group_num,
                    'mini_name': mini_name,
                    'mini_id': mini_id
                }
            
            return None
            
        except Exception as e:
            logger.error(f"解析昵称格式失败: {nickname}, 错误: {e}")
            return None

    async def save_member_info(self, qq_id: str, info: Dict[str, str]):
        try:
            # 保存格式: 迷你号:几组:迷你号:qq号
            save_line = f"{info['mini_id']}:{info['group']}:{info['mini_id']}:{qq_id}\n"
            
            with open(self.save_file, 'a', encoding='utf-8') as f:
                f.write(save_line)
                
            logger.info(f"成功保存成员信息: {save_line.strip()}")
            
        except Exception as e:
            logger.error(f"保存成员信息失败: {e}")

    async def report_invalid_format(self, qq_id: str, nickname: str):
        try:
            report_message = f"发现不符合格式的群成员:\nQQ号: {qq_id}\n群名称: {nickname}\n群号: {self.target_group_id}"
            
            platforms = self.context.platform_manager.get_insts()
            
            for platform in platforms:
                try:
                    await platform.send_private_msg(self.report_qq_id, report_message)
                    logger.info(f"成功发送报告给 {self.report_qq_id}")
                    return
                except Exception as e:
                    logger.warning(f"平台 {platform.__class__.__name__} 发送报告失败: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"发送报告失败: {e}")

    @filter.command("crawl_now")
    async def crawl_now(self, event: AstrMessageEvent):
        user_name = event.get_sender_name()
        logger.info(f"用户 {user_name} 触发立即爬取命令")
        
        yield event.plain_result("开始立即爬取群成员信息...")
        await self.crawl_group_members()
        yield event.plain_result("爬取任务完成！")

    @filter.command("crawl_status")
    async def crawl_status(self, event: AstrMessageEvent):
        processed_count = len(self.processed_members)
        status_msg = f"爬取状态:\n已处理成员数: {processed_count}\n保存文件: {self.save_file}"
        yield event.plain_result(status_msg)

    @filter.command("clear_cache")
    async def clear_cache(self, event: AstrMessageEvent):
        self.processed_members.clear()
        yield event.plain_result("缓存已清除！")

    async def terminate(self):
        logger.info("QQ群成员爬取插件已卸载") 