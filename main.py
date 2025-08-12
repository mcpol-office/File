import os
import json
import random
import datetime
import requests
from typing import Dict, Any

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register("qqbot", "简单工作室", "QQ频道机器人功能移植版，包含天气查询、每日一言、签到系统等功能", "1.0.0", "https://github.com/your-repo")
class QQBotPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.users_file = os.path.join(self.context.data_dir, 'users.json')
        logger.info("QQBot插件初始化完成")

    def load_users(self) -> Dict[str, Any]:
        """读取用户数据"""
        if not os.path.exists(self.users_file):
            logger.info(f"用户数据文件 {self.users_file} 不存在，返回空字典")
            return {}
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                users = json.load(f)
                logger.info(f"读取用户数据成功: {users}")
                return users
        except Exception as e:
            logger.error(f"读取用户数据失败: {e}")
            return {}

    def save_users(self, users: Dict[str, Any]):
        """保存用户数据"""
        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(users, f, ensure_ascii=False, indent=2)
            logger.info(f"保存用户数据成功: {users}")
        except Exception as e:
            logger.error(f"保存用户数据失败: {e}")

    @filter.command("帮助")
    async def help_command(self, event: AstrMessageEvent):
        """帮助命令"""
        logger.info("执行帮助命令")
        help_text = """🤖 机器人帮助信息：
- 运行状态：查看服务器资源
- 帮助：显示此帮助信息
- 关于本机：查看机器人信息
- 天气：查询天气（如：天气 北京）
- 每日一言：获取每日一句名言
- 绑定：绑定QQ号
- 签到：每日签到获得奖励"""
        yield event.plain_result(help_text)

    @filter.command("关于本机")
    async def about_command(self, event: AstrMessageEvent):
        """关于本机命令"""
        logger.info("执行关于本机命令")
        content = """版本：0.0.1-beta
开发者：简单工作室  X 创海云科技
       -奇の简服务器专属bot-"""
        yield event.plain_result(content)

    @filter.command("运行状态")
    async def status_command(self, event: AstrMessageEvent):
        """运行状态命令"""
        logger.info("执行运行状态命令")
        try:
            import psutil
            
            # 获取系统信息
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # 获取运行时间
            boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.datetime.now() - boot_time
            
            status_text = f"""🖥️ 服务器运行状态：
CPU使用率：{cpu_percent}%
内存使用：{memory.percent}% ({memory.used // (1024**3)}GB / {memory.total // (1024**3)}GB)
磁盘使用：{disk.percent}% ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)
运行时间：{uptime.days}天 {uptime.seconds // 3600}小时 {(uptime.seconds % 3600) // 60}分钟"""
            
            yield event.plain_result(status_text)
        except ImportError:
            yield event.plain_result("无法获取系统状态，缺少psutil模块")

    @filter.command("天气")
    async def weather_command(self, event: AstrMessageEvent):
        """天气查询命令"""
        logger.info("执行天气命令")
        message_str = event.message_str
        # 提取地名
        location = message_str.replace("天气", "").strip()
        
        if not location:
            yield event.plain_result("请输入地名，例如：天气 北京")
            return

        weather_data = self.format_weather(location)
        yield event.plain_result(weather_data)

    def get_weather(self, location: str) -> Dict[str, Any]:
        """获取天气数据"""
        url = f'https://apis.juhe.cn/simpleWeather/query?key=50a3bd415158e186903d6e6994157589&city={location.rstrip("市").rstrip("县").rstrip("区")}'
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data['reason'] in ['查询成功!', '查询成功']:
                    return data['result']
                else:
                    return {"error": "查询失败: " + data['reason'] + "重新发送/天气 城市 重试"}
            else:
                return {"error": "请求失败，状态码: " + str(response.status_code)}
        except Exception as e:
            return {"error": f"请求异常: {e}"}

    def format_weather(self, location: str) -> str:
        """格式化天气信息"""
        weather_data = self.get_weather(location)
        if not isinstance(weather_data, dict) or 'error' in weather_data:
            return weather_data['error'] if isinstance(weather_data, dict) else str(weather_data)
        else:
            realtime_weather = weather_data.get('realtime', {}) if isinstance(weather_data.get('realtime', {}), dict) else {}
            result = f"\n{location.rstrip('市').rstrip('县').rstrip('区')}实时天气:\n"
            result += f"{realtime_weather.get('info','')}, 温度: {realtime_weather.get('temperature','')}℃, 湿度: {realtime_weather.get('humidity','')}%, 风向: {realtime_weather.get('direct','')}, 风力: {realtime_weather.get('power','')}级, AQI: {realtime_weather.get('aqi','')}"
            result += "\n未来几天的天气:🌤⛈️☔️"
            future_list = weather_data.get('future', [])
            if not isinstance(future_list, list):
                future_list = []
            for day in future_list:
                if not isinstance(day, dict):
                    continue
                result += f"\n日期: {day.get('date','')}, 天气: {day.get('weather','')}, 温度: {day.get('temperature','')}, 风向: {day.get('direct','')}"
            return result

    @filter.command("每日一言")
    async def daily_quote_command(self, event: AstrMessageEvent):
        """每日一言命令"""
        logger.info("执行每日一言命令")
        
        try:
            # 请求每日一言API
            response = requests.get("https://api.nxvav.cn/api/yiyan/?encode=json&charset=utf-8", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'yiyan' in data:
                    quote = data['yiyan']
                    # 实现欲言又止又说话的效果
                    content = f"嗯...让我想想...\n\n{quote}"
                    yield event.plain_result(content)
                else:
                    yield event.plain_result("今天的话...让我想想...\n\n生活就像一盒巧克力，你永远不知道下一颗是什么味道。")
            else:
                yield event.plain_result("嗯...让我想想...\n\n今天的话...\n\n生活就像一盒巧克力，你永远不知道下一颗是什么味道。")
        except Exception as e:
            logger.error(f"获取每日一言失败: {e}")
            yield event.plain_result("嗯...让我想想...\n\n今天的话...\n\n生活就像一盒巧克力，你永远不知道下一颗是什么味道。")

    @filter.command("绑定")
    async def bind_command(self, event: AstrMessageEvent):
        """绑定QQ号命令"""
        try:
            logger.info("执行绑定命令")
            message_str = event.message_str
            qq = message_str.replace("绑定", "").strip()
            
            if not qq or not qq.isdigit():
                yield event.plain_result("请输入正确的QQ号，例如：绑定 123456789")
                return
                
            users = self.load_users()
            user_id = str(event.unified_msg_origin)
            logger.info(f"绑定时 user_id: {user_id}, users: {users}")
            
            # 检查自己是否已绑定
            if user_id in users and 'qq' in users[user_id]:
                yield event.plain_result(f"你已绑定过QQ号：{users[user_id]['qq']}，如需更换请联系管理员")
                return
                
            # 检查该QQ号是否被其他用户绑定
            for uid, info in users.items():
                if info.get('qq') == qq:
                    yield event.plain_result("该QQ号已被绑定，不能重复绑定")
                    return
                    
            users[user_id] = users.get(user_id, {})
            users[user_id]['qq'] = qq
            self.save_users(users)
            yield event.plain_result(f"✅ 绑定成功！你的QQ号已保存：{qq}")
            
        except Exception as e:
            logger.error(f"绑定命令异常: {e}")
            yield event.plain_result("绑定失败，请联系管理员！")

    @filter.command("签到")
    async def sign_command(self, event: AstrMessageEvent):
        """签到命令"""
        try:
            logger.info("执行签到命令")
            users = self.load_users()
            user_id = str(event.unified_msg_origin)
            logger.info(f"签到时 user_id: {user_id}, users: {users}")
            
            user = users.get(user_id)
            if not user or 'qq' not in user:
                yield event.plain_result("请先绑定QQ号，格式：/绑定 你的QQ号")
                return
                
            today = datetime.date.today().isoformat()
            if user.get('last_sign') == today:
                yield event.plain_result("你今天已经签过到了，明天再来吧！")
                return
                
            coins = random.randint(1, 50)
            # 等级系统
            exp = user.get('exp', 0) + coins  # 每天签到获得的经验=入币数
            level = user.get('level', 1)
            
            # 新的升级规则
            def get_next_level_exp(lv):
                if lv == 1:
                    return 100
                elif lv == 2:
                    return 1000
                else:
                    return 2000
                    
            next_level_exp = get_next_level_exp(level)
            leveled_up = False
            while exp >= next_level_exp:
                exp -= next_level_exp
                level += 1
                next_level_exp = get_next_level_exp(level)
                leveled_up = True
                
            user['last_sign'] = today
            user['coins'] = user.get('coins', 0) + coins
            user['exp'] = exp
            user['level'] = level
            users[user_id] = user
            self.save_users(users)
            
            emoji_list = ['🎉', '✨', '🥳', '💰', '🎁', '😄', '👍', '🍀', '🌟', '🤑']
            emoji = random.choice(emoji_list)
            reply = f"{emoji} 签到成功！\n\n"
            reply += f"获得入币：{coins}\n"
            reply += f"获得经验：{coins}\n"
            reply += f"当前等级：Lv.{level}\n"
            reply += f"当前经验：{exp}/{get_next_level_exp(level)}"
            if leveled_up:
                reply += f"\n{emoji} 恭喜你升级啦！当前等级：Lv.{level}"
            reply += f"\n当前总入币：{user['coins']}"
            
            yield event.plain_result(reply)
            
        except Exception as e:
            logger.error(f"签到命令异常: {e}")
            yield event.plain_result("签到失败，请联系管理员！")

    async def terminate(self):
        """插件卸载时的清理工作"""
        logger.info("QQBot插件正在卸载...") 